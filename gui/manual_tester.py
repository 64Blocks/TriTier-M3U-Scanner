# gui/manual_tester.py
import os
import time
import queue
import threading
import subprocess
import customtkinter as ctk
import config
from utils.helpers import VLC_PATH, categorize_channel, get_host
from database.manager import save_databases, save_health_check_db

class ManualChannelTester:
    def __init__(self, app, selected_channels):
        self.app = app
        self.test_queue = selected_channels
        self.total_to_test = len(selected_channels)
        self.current_process = None

    def start(self):
        if not VLC_PATH:
            self.app.test_queue_queue.put(('log', " [X] ERROR: VLC NOT FOUND!"))
            return
            
        self.app.log(f"  > INITIATING MANUAL TEST FOR {self.total_to_test} CHANNELS...")
        self.app.enable_testing_controls()
        threading.Thread(target=self._run_worker, daemon=True).start()

    def _run_worker(self):
        for i in range(self.app.current_test_idx, self.total_to_test):
            if self.app.stop_requested:
                break
            self.app.pause_event.wait()
            
            name, url, item_id = self.test_queue[i]
            self.app.current_test_idx = i + 1
            
            # ✅ اصلاح: اگر کانال قبلاً در دیتابیس زنده بوده، برای تست دستی مجدداً بررسی می‌شود
            if url in self.app.live_db:
                del self.app.live_db[url] # حذف موقت برای ارزیابی مجدد
                self.app.log(f"  > [{self.app.current_test_idx}/{self.total_to_test}] RE-TESTING (PREVIOUSLY LIVE): {name}")
            else:
                self.app.log(f"  > [{self.app.current_test_idx}/{self.total_to_test}] TESTING (VLC): {name}")
            
            try:
                # اجرای VLC
                self.current_process = subprocess.Popen(
                    [VLC_PATH, url, "--quiet"],
                    creationflags=config.CREATE_NO_WINDOW
                )
                
                # منتظر ماندن برای اتمام یا توقف توسط کاربر
                while self.current_process.poll() is None:
                    if self.app.stop_requested:
                        self.current_process.terminate()
                        break
                    time.sleep(0.1)
                self.current_process = None
                
            except Exception as e:
                self.app.test_queue_queue.put(('log', f" [X] ERROR: {e}"))
                continue

            if not self.app.stop_requested:
                # حلقه دریافت نتیجه از کاربر
                while True:
                    self.app.test_queue_queue.put(('show_dialog', (name, url, self.app.current_test_idx, item_id)))
                    try:
                        result_tuple = self.app.result_queue.get(timeout=300)
                        result_status, res_item_id = result_tuple[0], result_tuple[1]
                        
                        # ✅ ۱. اگر کاربر پنجره را بست، لاگ می‌زند و بدون تغییر در دیتابیس به کانال بعدی می‌رود
                        if result_status == 'skip':
                            self.app.test_queue_queue.put(('log', f" [~] {name} - SKIPPED BY USER"))
                            break 
                        
                        if result_status == 'r': # Retry
                            self.app.test_queue_queue.put(('log', f" [~] {name} - QUEUED FOR RETRY (Waiting 3s)..."))
                            meta = next((res for res in self.app.cached_search_results if res['item_id'] == item_id), {})
                            self._add_to_retry(name, url, meta.get('group', 'General'), meta.get('logo', ''))
                            time.sleep(3)
                            self.app.test_queue_queue.put(('log', f" [~] {name} - RETRYING NOW"))
                            
                            self.current_process = subprocess.Popen([VLC_PATH, url, "--quiet"], creationflags=config.CREATE_NO_WINDOW)
                            time.sleep(5)
                            if self.current_process and self.current_process.poll() is None: 
                                self.current_process.terminate()
                            continue 
                        else:
                            # ✅ ۲. فقط در صورتی که OK یا DEAD زده شود، دیتابیس آپدیت می‌شود
                            self._process_result(name, url, result_status, res_item_id)
                            break 
                            
                    except queue.Empty:
                        self.app.test_queue_queue.put(('log', f"[!] TIMEOUT WAITING FOR RESULT"))
                        break

        # پایان تست
        self.app.test_queue_queue.put(('log', "  > SAVING PROGRESS..."))
        save_databases(self.app.live_db, self.app.host_scores, self.app.search_history, self.app.url_scores)
        save_health_check_db(self.app.url_scores, channel_metadata={}, live_db=self.app.live_db)
        
        self.app.testing = False
        self.app.disable_testing_controls()
        self.app.test_queue_queue.put(('test_complete', None))


    def _process_result(self, name, url, result, item_id):
        meta = next((res for res in self.app.cached_search_results if res['item_id'] == item_id or res.get('full_url') == url), {})
        channel_meta = {url: {"name": name, "logo": meta.get('logo', " "), "group": meta.get('group', "General")}}
        
        if result == 'y':
            category = categorize_channel(name)
            logo = channel_meta[url]["logo"]
            self.app.live_db[url] = (name, 0.0, "OK", category, logo, False)
            self.app.url_scores[url] = 100
            self.app.healthy_urls.add(url)
            self.app.unhealthy_urls.discard(url)
            self.app.test_queue_queue.put(('log', f" [+] {name} - SAVED AS LIVE (⭐⭐⭐⭐⭐)"))
            self.app.host_scores[get_host(url)] = self.app.host_scores.get(get_host(url), 0) + 1
            
        elif result == 'd':
            self.app.url_scores[url] = 0
            self.app.unhealthy_urls.add(url)
            self.app.healthy_urls.discard(url)
            if url in self.app.live_db:
                del self.app.live_db[url]
            self.app.test_queue_queue.put(('log', f" [-] {name} - MARKED AS DEAD (❌)"))
            
            for item in self.app.cached_search_results:
                if item['item_id'] == item_id:
                    item['values'] = ("❌", item['values'][1], item['values'][2])
                    break
            # به‌روزرسانی UI از طریق صف اصلی
            self.app.test_queue_queue.put(('update_health_ui', (item_id, False, 0, "Score: 0")))

        save_databases(self.app.live_db, self.app.host_scores, self.app.search_history, self.app.url_scores)
        save_health_check_db(self.app.url_scores, channel_metadata=channel_meta, live_db=self.app.live_db)

    def _add_to_retry(self, name, url, group, logo=" "):
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)
        retry_file = os.path.join(config.OUTPUT_DIR, "retry.m3u")
        is_duplicate = False
        
        if os.path.exists(retry_file):
            with open(retry_file, "r", encoding="utf-8") as f:
                if url in f.read(): 
                    is_duplicate = True
                    
        if not is_duplicate:
            logo_str = f' tvg-logo="{logo}"' if logo and logo != " " else " "
            with open(retry_file, "a", encoding="utf-8") as f:
                f.write(f'#EXTINF:-1{logo_str} group-title="{group}",{name}\n{url}\n')
            self.app.test_queue_queue.put(('log', f"  > ADDED TO RETRY LIST: {name}"))
        else:
            self.app.test_queue_queue.put(('log', f"  > SKIP RETRY (ALREADY IN LIST): {name}"))
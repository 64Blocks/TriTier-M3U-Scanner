# gui/health_checker.py
import os
import sys
import time
import queue
import threading
import datetime
import concurrent.futures
import config
from core.engine import test_channel_smart
from core.backoff import reset_domain_state
from database.manager import save_health_check_db, save_databases
from utils.helpers import get_quality_tier

class AutoHealthChecker:
    def __init__(self, app, selected_items, mode):
        self.app = app
        self.selected_items = selected_items
        self.mode = mode
        self.total_to_test = len(selected_items)
        
        profile = self.app.active_profile
        self.timeout = profile['recommended_timeout']
        self.ffmpeg_time = profile['recommended_ffmpeg_time']
        
        if mode == 'Fast':
            self.timeout = max(3, self.timeout - 2)
        elif mode == 'Deep':
            self.timeout = self.timeout + 3
            self.ffmpeg_time = self.ffmpeg_time + 2

    def start(self):
        reset_domain_state()
        self.app.log(f"  > INITIATING SMART AUTO HEALTH CHECK ({self.mode} MODE) FOR {self.total_to_test} CHANNELS...")
        self.app.log(f"  > ACTIVE PROFILE: Timeout={self.timeout}s, FFmpeg={self.ffmpeg_time}s")
        self.app.enable_testing_controls()
        threading.Thread(target=self._worker_logic, daemon=True).start()

    def _worker_logic(self):
        task_queue = queue.Queue()
        results = []
        lock = threading.Lock()
        
        self.app.log("="*80)
        self.app.log(f"🚀 STARTING AUTO HEALTH CHECK | MODE: {self.mode} | TOTAL: {self.total_to_test} CHANNELS")
        self.app.log("="*80)

        channel_metadata = {}
        for item_id, name, url in self.selected_items:
            meta = next((res for res in self.app.cached_search_results if res['item_id'] == item_id), {})
            channel_metadata[url] = {'name': name, 'logo': meta.get('logo', ' '), 'group': meta.get('group', 'General')}
            task_queue.put((item_id, name, url))

        def process_single_channel(args):
            item_id, name, url = args
            if self.app.stop_requested: return None
            
            try:
                result = test_channel_smart(url, self.timeout, self.ffmpeg_time, mode=self.mode)
                with lock:
                    results.append(result)
                    score = result['score']
                    self.app.url_scores[url] = score
                    
                    is_healthy = score >= 50
                    if is_healthy:
                        self.app.healthy_urls.add(url)
                        self.app.unhealthy_urls.discard(url)
                    else:
                        self.app.unhealthy_urls.add(url)
                        self.app.healthy_urls.discard(url)
                        
                    if url in self.app.live_db:
                        del self.app.live_db[url]
                        
                    self.app.current_test_idx += 1
                    current_idx = self.app.current_test_idx
                    
                    # ✅ فقط هر ۱۰۰ کانال یکبار UI را به‌روز می‌کنیم تا برنامه فریز نشود
                    if current_idx % 100 == 0 or current_idx == self.total_to_test:
                        status_icon = '✅' if is_healthy else '❌'
                        if self.mode == 'Fast':
                            l_details = f"L1:{result['l1']:>2} | L2:{result['l2']:>2} | --"
                        elif self.mode == 'Normal':
                            l_details = f"L1:{result['l1']:>2} | L2:{result['l2']:>2} | L3:{result['l3']:>2}"
                        else:
                            l_details = f"L1:{result['l1']:>2} | L2:{result['l2']:>2} | L3:{result['l3']:>2} | Pr:{result.get('probe', 0):>2}"
                            
                        display_name = (name[:28] + '..') if len(name) > 30 else name
                        log_msg = f"[{current_idx}/{self.total_to_test}] {status_icon} {display_name:<30} | {l_details} => {score}/100"
                        
                        self.app.test_queue_queue.put(('update_progress', (current_idx, self.total_to_test, name)))
                        self.app.test_queue_queue.put(('update_health_ui', (item_id, is_healthy, score, f"Score: {score}")))
                        self.app.test_queue_queue.put(('log', log_msg))
                        
                return result
            except Exception as e:
                with lock:
                    self.app.current_test_idx += 1
                    self.app.url_scores[url] = 0
                    self.app.unhealthy_urls.add(url)
                    self.app.healthy_urls.discard(url)
                    if url in self.app.live_db: del self.app.live_db[url]
                return {"url": url, "score": 0, "latency": 999, "l1": 0, "l2": 0, "l3": 0, "probe": 0}

        # ✅ استفاده از ThreadPoolExecutor برای مدیریت پایدار و بدون کرش Threadها
        max_workers = 12 if self.mode == 'Deep' else 20 if self.mode == 'Normal' else 30
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = []
                while not task_queue.empty():
                    if self.app.stop_requested: break
                    args = task_queue.get()
                    futures.append(executor.submit(process_single_channel, args))
                
                for future in concurrent.futures.as_completed(futures):
                    if self.app.stop_requested: break
                    future.result()
                    
        except Exception as e:
            self.app.test_queue_queue.put(('log', f" [X] CRITICAL THREAD ERROR: {str(e)}"))

        finally:
            self.app.test_queue_queue.put(('log', "="*80))
            self.app.test_queue_queue.put(('log', "💾 SAVING PROGRESS TO DATABASES..."))
            
            save_health_check_db(self.app.url_scores, channel_metadata, self.app.live_db)
            save_databases(self.app.live_db, self.app.host_scores, self.app.search_history, self.app.url_scores, channel_metadata)
            
            self.app.testing = False
            self.app.disable_testing_controls()
            
            healthy_count = len([r for r in results if r and r.get('score', 0) >= 50])
            unhealthy_count = len([r for r in results if r and r.get('score', 0) < 50])
            
            self.app.test_queue_queue.put(('log', f"🏁 TEST FINISHED | ✅ Healthy: {healthy_count} | ❌ Unhealthy: {unhealthy_count}"))
            self.app.test_queue_queue.put(('log', "="*80))
            self.app.test_queue_queue.put(('auto_test_complete', (healthy_count, unhealthy_count, self.total_to_test, self.mode)))
            
            self.app.root.after(0, lambda: self.app.sort_column(self.app.channels_tree, 'mark', False))
            
            if sys.platform == 'win32':
                try:
                    import winsound
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                except Exception: pass
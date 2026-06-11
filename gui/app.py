import customtkinter as ctk
import threading
from gui.health_checker import AutoHealthChecker
from gui.manual_tester import ManualChannelTester
from gui.live_db_manager import LiveDBManager
from gui.profile_manager import ProfileManager
from tkinter import filedialog, messagebox, ttk
import os, subprocess, time, json, threading, queue, random, sys, shutil, datetime
import config
from utils.helpers import VLC_PATH, get_network_info, get_host, categorize_channel
from database.manager import (load_profiles, save_profiles, create_profile, load_active_profile, 
                              set_active_profile, load_categories, save_categories, load_databases, 
                              save_health_check_db, save_databases)
from core.backoff import reset_domain_state
from core.dns_tester import run_dns_test_with_m3u
from core.engine import test_channel_smart
from gui.theme import apply_theme, COLORS, FONT_DEFAULT, FONT_BOLD, FONT_TITLE, FONT_LARGE, FONT_LOG
from gui import tabs

class IPTVScannerGUI:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("◢ CYBER IPTV MATRIX ◣ [ROOT ACCESS]")
        self.root.geometry("1300x1000")
        
        # ✅ 1. اعمال تم و تعریف فوری تمام متغیرهای کلاس
        apply_theme()
        self.COLORS = COLORS
        self.FONT_DEFAULT = FONT_DEFAULT
        self.FONT_BOLD = FONT_BOLD
        self.FONT_TITLE = FONT_TITLE
        self.FONT_LARGE = FONT_LARGE
        self.FONT_LOG = FONT_LOG
        self.root.configure(fg_color=self.COLORS['bg_main'])

        # ✅ 2. تعریف تمام StringVar ها و متغیرهای حالت
        self.search_file_path = ctk.StringVar()
        self.live_search_var = ctk.StringVar()
        self.live_cat_var = ctk.StringVar(value="All")
        self.live_score_var = ctk.StringVar(value="All")
        self.filter_var = ctk.StringVar()
        self.health_mode_var = ctk.StringVar(value="Normal")
        self.hide_dead_var = ctk.BooleanVar(value=False)
        self.profile_var = ctk.StringVar(value="default")
        self.settings_cat_var = ctk.StringVar(value="Select Category")
        self.eta_var = ctk.StringVar(value="ETA: --:--")
        self.progress_counter_var = ctk.StringVar(value="0/0")
        self.hacker_progress_var = ctk.StringVar(value="[░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 0%")
        self.hacker_spinner_var = ctk.StringVar(value="◴")
        self.found_count_var = ctk.StringVar(value="  > Found: 0 channels  ")
        self.random_count_var = ctk.StringVar(value="  > Ready to pick random channels  ")

        # ✅ 3. تعریف متغیرهای داده‌ای و صف‌ها
        self.live_db, self.host_scores, self.search_history = {}, {}, []
        self.healthy_urls, self.unhealthy_urls, self.url_scores = set(), set(), {}
        self.urls, self.test_queue = [], []
        self.testing, self.stop_requested = False, False
        self.pause_event = threading.Event()
        self.pause_event.set()
        self.is_paused = False
        self.current_process = None
        self.current_test_idx = 0
        self.total_to_test = 0
        self.test_start_time = 0
        self.test_queue_queue, self.result_queue = queue.Queue(), queue.Queue()
        self.cached_search_results, self.search_batch = [], []
        
        # ✅ 4. بارگذاری داده‌های اولیه
        self.categories = load_categories()
        self.profiles = load_profiles()
        self.active_profile = load_active_profile()
        self.profile_manager = ProfileManager(self)
        self.live_db_manager = LiveDBManager(self)
        
        # ✅ 5. ساخت ویجت‌ها و شروع تسک‌های پس‌زمینه
        self.setup_styling()
        self.create_widgets()
        
        self.root.after(50, self._start_background_tasks)
        self.root.after(200, self.update_network_info)
        self.root.after(50, self.check_queues)
        self._animate_spinner()
        
    def _start_background_tasks(self):
        threading.Thread(target=self._load_databases_async, daemon=True).start()

    def _load_databases_async(self):
        data = load_databases()
        self.root.after(0, lambda: self._on_db_loaded(data))

    def _on_db_loaded(self, data):
        self.live_db, self.host_scores, self.search_history, self.healthy_urls, self.unhealthy_urls, self.url_scores = data
        self.refresh_live_channels()
        self.refresh_ranking()

    def setup_styling(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Treeview', background=self.COLORS['bg_main'], foreground=self.COLORS['accent_bright'], 
                        fieldbackground=self.COLORS['bg_main'], rowheight=28, font=self.FONT_DEFAULT, borderwidth=1, relief='flat')
        style.map('Treeview', background=[('selected', self.COLORS['accent_secondary'])], foreground=[('selected', self.COLORS['accent_bright'])])
        style.configure('Treeview.Heading', background=self.COLORS['bg_entry'], foreground=self.COLORS['accent_bright'], font=self.FONT_BOLD, relief='flat')
        style.map('Treeview.Heading', background=[('active', self.COLORS['accent_primary'])])

    def check_queues(self):
        for _ in range(50):
            try:
                msg_type, msg_data = self.test_queue_queue.get_nowait()
                
                if msg_type == 'log': 
                    self.log(msg_data)
                elif msg_type == 'show_dialog': 
                    self.show_test_dialog(*msg_data)
                elif msg_type == 'test_complete': 
                    self.on_test_complete()
                
                elif msg_type == 'add_search_batch':
                    for item in msg_data:
                        prefix, name, display_url, full_url, logo, group = item
                        self.cached_search_results.append({
                            'item_id': full_url, 
                            'name': name, 
                            'full_url': full_url, 
                            'logo': logo, 
                            'group': group, 
                            'values': (prefix, name, display_url)
                        })
                        self.urls.append((name, full_url, logo, group))
                    self.found_count_var.set(f"  > Found: {len(self.cached_search_results)} channels  ")

                elif msg_type == 'update_health_ui': 
                    self.update_health_ui(*msg_data)
                    
                elif msg_type == 'update_progress':
                    self.current_test_idx = msg_data[0]
                    self.total_to_test = msg_data[1]
                    self.progress_counter_var.set(f"{msg_data[0]}/{msg_data[1]}")
                    self._update_hacker_progress(msg_data[0], msg_data[1])
                    try:
                        elapsed = time.time() - self.test_start_time if self.test_start_time else 0
                        rate = elapsed / max(1, msg_data[0])
                        eta = max(0, int((msg_data[1] - msg_data[0]) * rate))
                        self.eta_var.set(f"ETA: {eta//60:02d}:{eta%60:02d}")
                    except: pass
                    self.log(f" [ TESTING {msg_data[0]}/{msg_data[1]}: {msg_data[2]} ] ")
                    
                elif msg_type == 'final_count':
                    self.found_count_var.set(f"  > ✅ Total Ready: {msg_data} channels  ")
                
                elif msg_type == 'apply_final_filter':
                    self.filter_found_channels()
                    
                elif msg_type == 'auto_test_complete':
                    healthy, unhealthy, total, mode = msg_data
                    popup_msg = (f"Smart Auto Health Check Completed! ({mode} Mode)\n"
                                 f"Total Tested: {total}\n"
                                 f"✅ Healthy: {healthy}\n"
                                 f"❌ Unhealthy: {unhealthy}\n"
                                 f"📝 Full log & DB saved to Output folder.")
                    messagebox.showinfo("Test Completed", popup_msg, parent=self.root)

            except queue.Empty: 
                break
                
        self.root.after(50, self.check_queues)

    def update_health_ui(self, item_id, is_healthy, score, msg):
        try:
            for item in self.cached_search_results:
                if item['item_id'] == item_id:
                    from utils.helpers import get_quality_tier
                    tier = get_quality_tier(score)
                    new_values = (tier, item['values'][1], item['values'][2])
                    item['values'] = new_values
                    break
        except Exception as e:
            print(f" [!] UI Update Error: {e}")

    def create_widgets(self):
        net_frame = ctk.CTkFrame(self.root, corner_radius=0, height=40, fg_color=self.COLORS['bg_frame'])
        net_frame.pack(fill="x", padx=15, pady=(0, 5))
        net_frame.pack_propagate(False)

        self.net_dns_var = ctk.StringVar(value="  > DNS: INITIALIZING...  ")
        self.net_status_var = ctk.StringVar(value="  > STATUS: INITIALIZING...  ")
        ctk.CTkLabel(net_frame, textvariable=self.net_dns_var, font=self.FONT_DEFAULT, text_color=self.COLORS['text_main'], anchor="w").pack(side="left", padx=15, fill="y")
        ctk.CTkLabel(net_frame, textvariable=self.net_status_var, font=self.FONT_BOLD, text_color=self.COLORS['text_main'], anchor="e").pack(side="right", padx=15, fill="y")

        self.main_container = ctk.CTkFrame(self.root, fg_color=self.COLORS['bg_main'])
        self.main_container.pack(fill="both", expand=True, padx=15, pady=5)

        self.sidebar = ctk.CTkFrame(self.main_container, width=160, corner_radius=0, fg_color=self.COLORS['bg_frame'], border_width=1, border_color=self.COLORS['accent_secondary'])
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.content_area = ctk.CTkFrame(self.main_container, corner_radius=0, fg_color=self.COLORS['bg_main'])
        self.content_area.pack(side="right", fill="both", expand=True)

        self.tab_frames, self.tab_buttons = {}, {}
        tab_names = ["🔍 SCAN", "📺 LIVE DB", "🔗 SINGLE URL", "🏆 RANKING", "⚡ PROFILE", "⚙️ SETTINGS"]

        for name in tab_names:
            btn = ctk.CTkButton(self.sidebar, text=name, corner_radius=0, fg_color="transparent", text_color=self.COLORS['text_main'], hover_color=self.COLORS['accent_secondary'], font=self.FONT_BOLD, height=50, command=lambda n=name: self.switch_tab(n))
            btn.pack(fill="x", pady=2)
            self.tab_buttons[name] = btn
            self.tab_frames[name] = ctk.CTkFrame(self.content_area, corner_radius=0, fg_color=self.COLORS['bg_main'])

        tabs.create_scan_tab(self, self.tab_frames["🔍 SCAN"])
        tabs.create_live_tab(self, self.tab_frames["📺 LIVE DB"])
        tabs.create_single_tab(self, self.tab_frames["🔗 SINGLE URL"])
        tabs.create_ranking_tab(self, self.tab_frames["🏆 RANKING"])
        tabs.create_profile_tab(self, self.tab_frames["⚡ PROFILE"])
        tabs.create_settings_tab(self, self.tab_frames["⚙️ SETTINGS"])
        self.switch_tab("🔍 SCAN")
        
        try:
            self.channels_tree.bind("<Control-a>", lambda e:(self.channels_tree.selection_set(self.channels_tree.get_children()), "break")[1])
            self.root.bind_all("<Control-c>", lambda e:self.root.clipboard_append(self.root.focus_get().selection_get() if hasattr(self.root.focus_get(), "selection_get") else ""))
        except: pass

        progress_frame = ctk.CTkFrame(self.root, fg_color='transparent')
        progress_frame.pack(fill='x', padx=15, pady=(2,2))
        
        self.hacker_progress_label = ctk.CTkLabel(progress_frame, textvariable=self.hacker_progress_var, font=("Courier New", 13, "bold"), text_color=self.COLORS['accent_bright'])
        self.hacker_progress_label.pack(side='left', padx=5)
        self.hacker_spinner_label = ctk.CTkLabel(progress_frame, textvariable=self.hacker_spinner_var, font=("Courier New", 14, "bold"), text_color=self.COLORS['accent_bright'])
        self.hacker_spinner_label.pack(side='left', padx=5)
        ctk.CTkLabel(progress_frame, textvariable=self.progress_counter_var, width=80, font=self.FONT_DEFAULT, text_color=self.COLORS['text_dim']).pack(side='left', padx=10)
        ctk.CTkLabel(progress_frame, textvariable=self.eta_var, width=120, font=self.FONT_DEFAULT, text_color=self.COLORS['text_dim']).pack(side='left')

        log_frame = ctk.CTkFrame(self.root, corner_radius=0, fg_color=self.COLORS['bg_main'], border_width=2, border_color=self.COLORS['accent_bright'])
        log_frame.pack(fill="x", padx=15, pady=(5, 15))
        
        log_btn_frame = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_btn_frame.pack(fill="x", padx=10, pady=5)
        
        self.close_vlc_btn = ctk.CTkButton(log_btn_frame, text="[X] KILL VLC", command=self.force_close_vlc, fg_color=self.COLORS['destructive'], text_color=self.COLORS['bg_main'], hover_color=self.COLORS['destructive_hover'], width=100, state="disabled", font=self.FONT_BOLD)
        self.close_vlc_btn.pack(side="left", padx=(0, 5))
        self.cancel_btn = ctk.CTkButton(log_btn_frame, text="[!] CANCEL", command=self.cancel_testing, fg_color=self.COLORS['destructive'], text_color=self.COLORS['bg_main'], hover_color=self.COLORS['destructive_hover'], width=100, state="disabled", font=self.FONT_BOLD)
        self.cancel_btn.pack(side="left", padx=(0, 5))
        self.pause_btn = ctk.CTkButton(log_btn_frame, text="[||] PAUSE", command=self.pause_testing, fg_color=self.COLORS['accent_bright'], text_color=self.COLORS['bg_main'], hover_color="#4ade80", width=90, state="disabled", font=self.FONT_BOLD)
        self.pause_btn.pack(side="left", padx=(0, 5))
        self.resume_btn = ctk.CTkButton(log_btn_frame, text="[>] RESUME", command=self.resume_testing, fg_color=self.COLORS['accent_bright'], text_color=self.COLORS['bg_main'], hover_color="#4ade80", width=90, state="disabled", font=self.FONT_BOLD)
        self.resume_btn.pack(side="left", padx=(0, 5))
        ctk.CTkButton(log_btn_frame, text="[ ] CLEAR LOG", command=self.clear_log, fg_color=self.COLORS['bg_entry'], text_color=self.COLORS['text_main'], hover_color=self.COLORS['accent_secondary'], width=100, font=self.FONT_BOLD).pack(side="right")
        
        self.log_text = ctk.CTkTextbox(log_frame, height=110, font=self.FONT_LOG, text_color=self.COLORS['accent_bright'], fg_color="#0a0a0a", border_width=0, activate_scrollbars=True)
        self.log_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def switch_tab(self, selected_tab):
        for name, frame in self.tab_frames.items():
            frame.pack_forget()
            self.tab_buttons[name].configure(fg_color="transparent", text_color=self.COLORS['text_main'])
        self.tab_frames[selected_tab].pack(fill="both", expand=True)
        self.tab_buttons[selected_tab].configure(fg_color=self.COLORS['accent_primary'], text_color=self.COLORS['bg_main'])

    def update_network_info(self):
        threading.Thread(target=self._fetch_network_info_worker, daemon=True).start()

    def _fetch_network_info_worker(self):
        dns, status, vpn_text = get_network_info()
        self.root.after(0, lambda: self._apply_network_info(dns, status, vpn_text))

    def _apply_network_info(self, dns, status, vpn_text):
        self.net_dns_var.set(f"  > DNS: {dns}")
        self.net_status_var.set(f"  > {status}{vpn_text}")
        self.root.after(15000, self.update_network_info)

    def enable_testing_controls(self):
        self.cancel_btn.configure(state="normal")
        self.close_vlc_btn.configure(state="normal")
        self.pause_btn.configure(state="normal")
        self.resume_btn.configure(state="disabled")

    def disable_testing_controls(self):
        self.cancel_btn.configure(state="disabled")
        self.close_vlc_btn.configure(state="disabled")
        self.pause_btn.configure(state="disabled")
        self.resume_btn.configure(state="disabled")
        self.stop_requested = False
        self.is_paused = False
        self.pause_event.set()

    def pause_testing(self):
        if self.testing and not self.is_paused:
            self.is_paused = True
            self.pause_event.clear()
            self.pause_btn.configure(state="disabled")
            self.resume_btn.configure(state="normal")
            self.log(" [||] TESTING PAUSED.")

    def resume_testing(self):
        if self.testing and self.is_paused:
            self.is_paused = False
            self.pause_event.set()
            self.pause_btn.configure(state="normal")
            self.resume_btn.configure(state="disabled")
            self.log(" [>] TESTING RESUMED.")

    def cancel_testing(self):
        if self.testing:
            self.stop_requested = True
            self.pause_event.set()
            self.log("\n[!] CANCEL REQUESTED. SAVING PROGRESS AND ABORTING...")
            self.force_close_vlc()
            self.cancel_btn.configure(text="[ ] ABORTING", state="disabled")
            self.pause_btn.configure(state="disabled")
            self.resume_btn.configure(state="disabled")

    def force_close_vlc(self):
        if self.current_process and self.current_process.poll() is None:
            try:
                self.current_process.terminate()
                self.current_process.wait(timeout=2)
            except:
                self.current_process.kill()
            self.log(" [!] VLC PROCESS TERMINATED BY USER")
        else:
            try:
                subprocess.run(["taskkill", "/f", "/im", "vlc.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=config.CREATE_NO_WINDOW)
            except: pass
                    

    def clear_log(self):
        self.log_text.delete("1.0", "end")
        self.log("  > LOG CLEARED")

    def log(self, message):
        try:
            lines = int(self.log_text.index('end-1c').split('.')[0])
            if lines > 5000:
                self.log_text.delete("1.0", "500.0")
        except: pass
            
        try:
            os.makedirs(config.OUTPUT_DIR, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            clean_msg = message.strip()
            with open(os.path.join(config.OUTPUT_DIR, "app_log.txt"), "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {clean_msg}\n")
        except Exception: pass
            
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")

    def sort_column(self, tree, col, reverse):
        l = [(tree.set(k, col), k) for k in tree.get_children('')]
        if col in ['mark', 'score']:
            def health_key(x):
                val = str(x[0]).strip()
                if '❌' in val: return 0
                return val.count('⭐')
            l.sort(key=lambda x: health_key(x), reverse=not reverse)
        else:
            l.sort(key=lambda x: str(x[0]).lower(), reverse=reverse)
             
        for index, (val, k) in enumerate(l):
            tree.move(k, '', index)
        tree.heading(col, command=lambda: self.sort_column(tree, col, not reverse))
    
    def on_tree_click(self, event):
        tree = event.widget
        if tree.identify_region(event.x, event.y) == "cell":
            row_id = tree.identify_row(event.y)
            if not row_id: return
            if tree == self.live_tree:
                self.root.clipboard_clear()
                self.root.clipboard_append(tree.item(row_id, 'values')[0])
            elif tree == self.ranking_tree:
                self.root.clipboard_clear()
                self.root.clipboard_append(tree.item(row_id, 'values')[1])
            elif tree == self.channels_tree:
                col_idx = int(tree.identify_column(event.x).replace('#', '')) - 1
                values = list(tree.item(row_id, 'values'))
                if 0 <= col_idx < len(values):
                    text_to_copy = str(values[col_idx])
                    if col_idx == 2:
                        text_to_copy = next((res['full_url'] for res in self.cached_search_results if res['item_id'] == row_id), text_to_copy)
                    if text_to_copy and not text_to_copy.startswith('['):
                        self.root.clipboard_clear()
                        self.root.clipboard_append(text_to_copy)

    def test_double_click_channel(self, event):
        tree = event.widget
        item = tree.identify_row(event.y)
        if item:
            full_url = next((res['full_url'] for res in self.cached_search_results if res['item_id'] == item), None)
            name = next((res['name'] for res in self.cached_search_results if res['item_id'] == item), "Unknown")
            if full_url:
                from utils.helpers import VLC_PATH
                if not VLC_PATH:
                    return messagebox.showerror("ERROR", "VLC NOT FOUND! Please install VLC Media Player to use Manual Test.", parent=self.root)
                    
                self.test_queue = [(name, full_url, item)]
                self.total_to_test = 1
                self.current_test_idx = 0
                self.test_start_time = time.time()
                self.stop_requested = False
                self.testing = True
                self.log(f"  > TESTING SINGLE: {name}")
                self.enable_testing_controls()
                
                tester = ManualChannelTester(self, self.test_queue)
                tester.start()

    def refresh_scan_list(self):
        # ۱. پاکسازی رابط کاربری
        self.channels_tree.delete(*self.channels_tree.get_children())
        
        # ۲. ذخیره موقت داده‌های فعلی برای بازسازی ایمن
        current_urls = list(self.urls)
        
        # ۳. پاکسازی کامل لیست‌های اصلی برای جلوگیری از تکرار و دو برابر شدن
        self.cached_search_results = []
        self.urls = []
        self.found_count_var.set("  > Found: 0 channels")
        
        # ۴. بازسازی لیست از روی داده‌های موقت (که پاک نشده‌اند)
        if current_urls:
            self.log("  > REFRESHING LOADED CHANNELS LIST...")
            batch = []
            for name, url, logo, group in current_urls:
                display_url = url[:60] + '...' if len(url) > 60 else url
                score = self.url_scores.get(url, 0)
                from utils.helpers import get_quality_tier
                display_prefix = get_quality_tier(score)
                batch.append((display_prefix, name, display_url, url, logo, group))
            
            # ارسال به صورت بچ برای سازگاری کامل با check_queues
            self.test_queue_queue.put(('add_search_batch', batch))
        else:
            self.log("  > NO CHANNELS LOADED. PLEASE SCAN FIRST.")

    def select_10_random_in_scan(self):
        file_path = self.search_file_path.get()
        if not file_path:
            return messagebox.showerror("ERROR", "PLEASE ENTER A FILE PATH OR URL FIRST!", parent=self.root)
        
        all_channels = []
        seen_urls = set()
        lines = []
        import urllib.request
        from utils.helpers import get_random_ua, parse_extinf
        
        self.log(f"  > 🎲 READING SOURCE: {file_path}")
        
        try:
            if file_path.startswith('http://') or file_path.startswith('https://'):
                self.log(f"  > 🌐 FETCHING FROM URL...")
                req = urllib.request.Request(file_path, headers={'User-Agent': get_random_ua()})
                with urllib.request.urlopen(req, timeout=20) as response:
                    raw_data = response.read().decode('utf-8', errors='ignore')
                    lines = raw_data.splitlines()
            else:
                if not os.path.exists(file_path):
                    return messagebox.showerror("ERROR", "FILE NOT FOUND!", parent=self.root)
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
            
            self.log(f"  > 📄 TOTAL LINES IN FILE: {len(lines)}")
                    
            last_name, last_logo, last_group = "Unknown", " ", "General"
            for line in lines:
                line = line.strip()
                if line.startswith("#EXTINF"):
                    last_name, last_logo, last_group = parse_extinf(line)
                elif line.startswith("http"):
                    if last_name != "Unknown" and line not in seen_urls:
                        seen_urls.add(line)
                        all_channels.append((last_name, line, last_logo, last_group))
                        last_name, last_logo, last_group = "Unknown", " ", "General"
            
            self.log(f"  > 📊 TOTAL UNIQUE CHANNELS FOUND: {len(all_channels)}")
                        
            if not all_channels:
                return messagebox.showinfo("INFO", "NO VALID CHANNELS FOUND IN THIS SOURCE!", parent=self.root)
                
            import random
            self.random_channels = random.sample(all_channels, min(10, len(all_channels)))
            self.random_count_var.set(f"   > Selected {len(self.random_channels)} random channels   ")
            
            self.channels_tree.delete(*self.channels_tree.get_children())
            self.cached_search_results, self.urls, self.search_batch = [], [], []
            
            batch = []
            for name, url, logo, group in self.random_channels:
                self.urls.append((name, url, logo, group))
                display_url = url[:60] + '...' if len(url) > 60 else url
                score = self.url_scores.get(url, 0)
                from utils.helpers import get_quality_tier
                display_prefix = get_quality_tier(score)
                batch.append((display_prefix, name, display_url, url, logo, group))
                
            # ۱. ارسال داده‌ها به حافظه
            self.test_queue_queue.put(('add_search_batch', batch))
            
            # ✅ ۲. دستور رسم داده‌ها روی صفحه (این خط معجزه می‌کند!)
            self.test_queue_queue.put(('apply_final_filter', None))
            
            self.log(f"   > ✅ RANDOM SELECTION COMPLETE: {len(self.random_channels)} CHANNELS LOADED TO LIST.")
            
        except Exception as e:
            self.log(f"  > [X] ERROR IN RANDOM SELECTION: {str(e)}")
            messagebox.showerror("ERROR", f"Failed to read source: {str(e)}", parent=self.root)
            
            

    def filter_found_channels(self, *args):
        try:
            query = self.filter_var.get().lower()
            score_filter = self.scan_score_var.get()
            
            self.channels_tree.delete(*self.channels_tree.get_children())
            visible_count = 0
            seen_iids = set()
            
            max_display = 90000
            
            for item in self.cached_search_results:
                if visible_count >= max_display and not query:
                    break
                    
                match_text = query in item['name'].lower() or query in item['full_url'].lower()
                score = int(self.url_scores.get(item['full_url'], 100))
                
                pass_score_filter = True
                if score_filter == "⭐⭐⭐⭐⭐ (90-100)" and not (90 <= score <= 100): pass_score_filter = False
                elif score_filter == "⭐⭐⭐⭐ (70-89)" and not (70 <= score <= 89): pass_score_filter = False
                elif score_filter == "⭐⭐⭐ (50-69)" and not (50 <= score <= 69): pass_score_filter = False
                elif score_filter == "⭐⭐ (30-49)" and not (30 <= score <= 49): pass_score_filter = False
                elif score_filter == "⭐ (1-29)" and not (1 <= score <= 29): pass_score_filter = False
                elif score_filter == "❌ Dead (0)" and score != 0: pass_score_filter = False

                if match_text and pass_score_filter:
                    iid = item['item_id']
                    original_iid = iid
                    counter = 1
                    while iid in seen_iids:
                        iid = f"{original_iid}_{counter}"
                        counter += 1
                    seen_iids.add(iid)
                    self.channels_tree.insert('', 'end', iid=iid, values=item['values'])
                    visible_count += 1
                    
                    if visible_count % 500 == 0:
                        self.root.update()

            total_count = len(self.cached_search_results)
            if visible_count < total_count and not query:
                self.found_count_var.set(f"   > 👁️ Visible: {visible_count} / Total: {total_count} (Limited to 10000 for UI performance)   ")
            else:
                self.found_count_var.set(f"   > 🔍 Found: {visible_count} channels   ")
                
        except Exception as e:
            print(f"[!] Filter Error: {e}")

    def select_all_channels(self):
        self.channels_tree.selection_set(self.channels_tree.get_children())
        self.log("  > ✅ ALL VISIBLE CHANNELS SELECTED.")

    def scan_channels(self):
        self.stop_requested = False
        if not self.search_file_path.get():
            return messagebox.showerror("ERROR", "PLEASE SELECT AN M3U FILE!", parent=self.root)
        keywords = self.keywords_entry.get().strip()
        if keywords and keywords not in self.search_history:
            self.search_history.append(keywords) 
            save_databases(self.live_db, self.host_scores, self.search_history)
        keywords_list = [k.strip().lower() for k in keywords.split(",")] if keywords else []
        self.channels_tree.delete(*self.channels_tree.get_children())
        self.cached_search_results, self.urls, self.search_batch = [], [], []
        self.found_count_var.set("  > Found: 0 channels")
        self.log("  > INITIATING BACKGROUND SCAN (OPTIMIZED)...")
        threading.Thread(target=self._scan_worker, args=(self.search_file_path.get(), keywords_list), daemon=True).start()

    def _scan_worker(self, file_path, keywords_list):
        BATCH_SIZE = 1000
        batch_results = []
        found_count = 0
        seen_urls = set()
        
        kw_lower = [kw.strip().lower() for kw in keywords_list] if keywords_list else []
        
        self.test_queue_queue.put(('log', "   > 🚀 INITIATING HIGH-SPEED SCAN...   "))
        
        try:
            from utils.helpers import get_random_ua, parse_extinf, get_quality_tier
            import urllib.request

            last_name, last_logo, last_group = "Unknown", " ", "General"

            def process_line(line):
                nonlocal found_count, batch_results, last_name, last_logo, last_group
                line = line.strip()
                if not line: 
                    return

                if line.startswith("#EXTINF"):
                    last_name, last_logo, last_group = parse_extinf(line)
                elif line.startswith("http"):
                    if last_name != "Unknown" and line not in seen_urls:
                        if kw_lower:
                            name_lower = last_name.lower()
                            url_lower = line.lower()
                            if not any(kw in name_lower or kw in url_lower for kw in kw_lower):
                                last_name, last_logo, last_group = "Unknown", " ", "General"
                                return

                        seen_urls.add(line)
                        found_count += 1
                        
                        score = self.url_scores.get(line, 0)
                        display_prefix = get_quality_tier(score)
                        display_url = line[:60] + '...' if len(line) > 60 else line
                        
                        batch_results.append((display_prefix, last_name, display_url, line, last_logo, last_group))
                        
                        if len(batch_results) >= BATCH_SIZE:
                            self.test_queue_queue.put(('add_search_batch', batch_results))
                            batch_results = []
                        
                        last_name, last_logo, last_group = "Unknown", " ", "General"

            if file_path.startswith('http://') or file_path.startswith('https://'):
                self.test_queue_queue.put(('log', f"   > 🌐 FETCHING M3U FROM URL...   "))
                req = urllib.request.Request(file_path, headers={'User-Agent': get_random_ua()})
                with urllib.request.urlopen(req, timeout=30) as response:
                    for line in response:
                        if self.stop_requested: break
                        process_line(line.decode('utf-8', errors='ignore'))
            else:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if self.stop_requested: break
                        process_line(line)

            if batch_results and not self.stop_requested:
                self.test_queue_queue.put(('add_search_batch', batch_results))
                
            if not self.stop_requested:
                self.test_queue_queue.put(('log', f"   > ✅ SCAN COMPLETE: TOTAL {found_count} UNIQUE CHANNELS PROCESSED.   "))
                self.test_queue_queue.put(('final_count', found_count))
                self.test_queue_queue.put(('apply_final_filter', None))
                
        except Exception as e:
            self.test_queue_queue.put(('log', f"   > [X] SCAN ERROR: {str(e)}   "))

    def run_auto_health_check(self):
        from utils.helpers import FFMPEG_PATH
        if not FFMPEG_PATH:
            return messagebox.showerror("ERROR", "FFMPEG NOT FOUND! Please install FFmpeg.", parent=self.root)
            
        selected_items_ids = self.channels_tree.selection()
        
        if not selected_items_ids:
            total_in_memory = len(self.cached_search_results)
            if total_in_memory == 0:
                return messagebox.showinfo("INFO", "NO CHANNELS LOADED IN MEMORY. PLEASE SCAN FIRST.", parent=self.root)
                
            confirm = messagebox.askyesno(
                "TEST ALL IN MEMORY?", 
                f"No channels are selected in the UI.\n\nDo you want to run Auto Health Check on ALL {total_in_memory} channels currently in memory?\n\n(This bypasses the UI display limit and is safe for large lists.)",
                parent=self.root
            )
            
            if not confirm:
                return
                
            selected = [(item['item_id'], item['name'], item['full_url']) for item in self.cached_search_results]
            self.log(f"  > INITIATING TEST ON ALL {len(selected)} CHANNELS IN MEMORY...")
            
        else:
            # ✅ بهینه‌سازی حیاتی: ساخت دیکشنری Lookup برای جستجوی آنی (جلوگیری از فریز در انتخاب‌های بزرگ)
            meta_lookup = {res['item_id']: res for res in self.cached_search_results}
            selected = []
            for item_id in selected_items_ids:
                res = meta_lookup.get(item_id)
                if res:
                    selected.append((item_id, res['name'], res['full_url']))
            self.log(f"  > INITIATING TEST ON {len(selected)} SELECTED CHANNELS...")

        self.total_to_test = len(selected)
        self.current_test_idx = 0
        self.test_start_time = time.time()
        self.stop_requested = False
        self.testing = True
        self.is_paused = False
        self.pause_event.set()
        
        mode = self.health_mode_var.get()
        checker = AutoHealthChecker(self, selected, mode)
        checker.start()

    def test_selected_channels(self):
        selected_items_ids = self.channels_tree.selection()
        if not selected_items_ids:
            return messagebox.showerror("ERROR", "PLEASE SELECT CHANNELS FIRST (USE SHIFT/CTRL + CLICK)!", parent=self.root)
            
        meta_lookup = {res['item_id']: res for res in self.cached_search_results}
        selected = []
        for item_id in selected_items_ids:
            res = meta_lookup.get(item_id)
            if res:
                selected.append((res['name'], res['full_url'], item_id))
                
        self.test_queue = selected
        self.total_to_test = len(selected)
        self.current_test_idx = 0
        self.test_start_time = time.time()
        self.stop_requested = False
        self.testing = True
        self.is_paused = False
        self.pause_event.set()
        
        tester = ManualChannelTester(self, selected)
        tester.start()

    def export_clean_m3u(self):
        if not self.url_scores:
            return messagebox.showwarning("WARNING", "NO TESTED CHANNELS TO EXPORT!", parent=self.root)
        
        selected_items = self.live_tree.selection()
        if selected_items:
            selected_urls = [self.live_tree.item(item, 'tags')[0] for item in selected_items]
            self.log(f"  > EXPORTING {len(selected_urls)} SELECTED CHANNELS...")
            from database.manager import export_clean_m3u_selected
            count = export_clean_m3u_selected(self.url_scores, self.live_db, selected_urls)
            messagebox.showinfo("SUCCESS", f"clean.m3u created with {count} selected channels!", parent=self.root)
        else:
            self.log("  > EXPORTING ALL HEALTHY CHANNELS...")
            from database.manager import export_clean_m3u_auto
            count = export_clean_m3u_auto(self.url_scores, self.live_db)
            messagebox.showinfo("SUCCESS", f"clean.m3u created with {count} channels!", parent=self.root)


    def on_test_complete(self):
        self.log("\n  > ALL TESTS COMPLETED SUCCESSFULLY.")
        self.testing = False
        self.disable_testing_controls()
        save_databases(self.live_db, self.host_scores, self.search_history)
        messagebox.showinfo("COMPLETE", "TESTING COMPLETED!\nCHECK THE LOG FOR RESULTS.", parent=self.root)
        
    def show_test_dialog(self, name, url, idx, item_id):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("CHANNEL STATUS")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(fg_color=self.COLORS['bg_frame'])
        
        # ✅ تغییر: بستن پنجره با دکمه X به معنی Skip است، نه Dead
        def on_close():
            dialog.destroy()
            self.result_queue.put(('skip', item_id))  # ارسال skip به جای dead
            
        dialog.protocol("WM_DELETE_WINDOW", on_close)
        
        dialog.update_idletasks()
        width, height = 400, 250
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        ctk.CTkLabel(dialog, text=f"CHANNEL {idx}", font=self.FONT_DEFAULT, text_color=self.COLORS['text_dim']).pack(pady=5)
        ctk.CTkLabel(dialog, text=name, font=self.FONT_TITLE, text_color=self.COLORS['accent_bright'], wraplength=350).pack(pady=15)
        ctk.CTkLabel(dialog, text="STATUS?", font=self.FONT_BOLD, text_color=self.COLORS['text_main']).pack(pady=5)
        
        def on_result(result):
            dialog.destroy()
            self.result_queue.put((result, item_id))
            
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=20, fill="x", padx=30)
        
        ctk.CTkButton(btn_frame, text="[ OK ]", command=lambda: on_result('y'), fg_color=self.COLORS['accent_bright'], text_color=self.COLORS['bg_main'], font=self.FONT_LARGE, width=80, height=50).pack(side="left", expand=True, fill="both", padx=5)
        ctk.CTkButton(btn_frame, text="[ RETRY ]", command=lambda: on_result('r'), fg_color=self.COLORS['accent_primary'], text_color=self.COLORS['bg_main'], font=self.FONT_LARGE, width=80, height=50).pack(side="left", expand=True, fill="both", padx=5)
        ctk.CTkButton(btn_frame, text="[ DEAD ]", command=lambda: on_result('d'), fg_color=self.COLORS['destructive'], text_color=self.COLORS['bg_main'], font=self.FONT_LARGE, width=80, height=50, hover_color=self.COLORS['destructive_hover']).pack(side="left", expand=True, fill="both", padx=5)        
        
    def filter_live_channels(self, *args):
        self.live_db_manager.filter_in_memory() 

    def refresh_live_channels(self):
        self.live_db_manager.refresh_live_channels()

    def edit_selected_live(self):
        self.live_db_manager.edit_selected_live()

    def delete_selected_live(self):
        self.live_db_manager.delete_selected_live()

    def on_profile_select(self, choice):
        self.profile_manager.on_profile_select(choice)

    def update_profile_info(self):
        self.profile_manager.update_profile_info()

    def set_active_profile_btn(self):
        self.profile_manager.set_active()

    def delete_profile(self):
        self.profile_manager.delete()

    def create_profile_btn(self):
        self.profile_manager.create()

    def run_dns_tester(self):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("DNS PERFORMANCE TESTER")
        dialog.geometry("750x650")
        dialog.transient(self.root)
        dialog.configure(fg_color=self.COLORS['bg_frame'])
        
        ctk.CTkLabel(dialog, text="🔬 DNS PERFORMANCE TESTER", font=self.FONT_TITLE, text_color=self.COLORS['accent_bright']).pack(pady=(20, 5))
        ctk.CTkLabel(dialog, text="Select your M3U file first, then click START TEST.", font=self.FONT_DEFAULT, text_color=self.COLORS['text_dim'], wraplength=700).pack(pady=(0, 15))
        
        file_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        file_frame.pack(fill="x", padx=20, pady=10)
        
        initial_path = self.search_file_path.get() if hasattr(self, 'search_file_path') else ""
        m3u_path_var = ctk.StringVar(value=initial_path)
        
        ctk.CTkEntry(file_frame, textvariable=m3u_path_var, width=450, font=self.FONT_DEFAULT, fg_color="#0a0a0a", text_color=self.COLORS['accent_bright'], placeholder_text="M3U file path...", border_width=1, border_color=self.COLORS['accent_bright']).pack(side="left", padx=(0, 10))
        
        def select_file():
            path = filedialog.askopenfilename(filetypes=[("M3U Files", "*.m3u *.m3u8")])
            if path:
                m3u_path_var.set(path)
                if hasattr(self, 'search_file_path'):
                    self.search_file_path.set(path)

        ctk.CTkButton(file_frame, text="📂 BROWSE M3U", command=select_file, fg_color=self.COLORS['accent_primary'], text_color=self.COLORS['bg_main'], font=self.FONT_BOLD, width=130, hover_color=self.COLORS['accent_bright']).pack(side="left")
        
        log_frame = ctk.CTkFrame(dialog, fg_color="#0a0a0a", corner_radius=0, border_width=1, border_color=self.COLORS['accent_secondary'])
        log_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        log_text = ctk.CTkTextbox(log_frame, font=self.FONT_LOG, text_color=self.COLORS['accent_bright'], fg_color="#0a0a0a", border_width=0)
        log_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # ✅ اصلاح حیاتی: به‌روزرسانی لاگ از طریق رشته اصلی (Main Thread) برای جلوگیری از کرش
        def log_callback(msg):
            self.root.after(0, lambda: (log_text.insert("end", msg + "\n"), log_text.see("end")))
        
        def start_test():
            # غیرفعال کردن دکمه در همان رشته اصلی
            start_btn.configure(state="disabled", text=" TESTING...")
            
            def test_worker():
                try:
                    path_to_test = m3u_path_var.get().strip()
                    if not path_to_test or not os.path.exists(path_to_test):
                        log_callback(f" ⚠️ No valid M3U file selected. Running default domain test...\n")
                        path_to_test = None
                    run_dns_test_with_m3u(m3u_path=path_to_test, log_callback=log_callback)
                except Exception as e:
                    log_callback(f"\n❌ ERROR: {e}")
                finally:
                    # ✅ اصلاح حیاتی: فعال کردن مجدد دکمه از طریق رشته اصلی (Main Thread)
                    self.root.after(0, lambda: start_btn.configure(state="normal", text="🚀 START TEST"))
                    
            threading.Thread(target=test_worker, daemon=True).start()

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=15)
        start_btn = ctk.CTkButton(btn_frame, text="🚀 START TEST", command=start_test, fg_color=self.COLORS['accent_bright'], text_color=self.COLORS['bg_main'], font=self.FONT_BOLD, width=150, hover_color="#4ade80")
        start_btn.pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="CLOSE", command=dialog.destroy, fg_color=self.COLORS['destructive'], text_color=self.COLORS['bg_main'], font=self.FONT_BOLD, width=150, hover_color=self.COLORS['destructive_hover']).pack(side="left", padx=10)
        
    def backup_database(self):
        os.makedirs(config.BACKUP_DIR, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        source_file = os.path.join(config.OUTPUT_DIR, "clean.m3u")
        if os.path.exists(source_file):
            backup_path = os.path.join(config.BACKUP_DIR, f"clean_{timestamp}.m3u")
            shutil.copy(source_file, backup_path)
            self.log(f"  > BACKUP CREATED SUCCESSFULLY: {backup_path}")
            messagebox.showinfo("SUCCESS", f"Backup created successfully at:\n{backup_path}")
        else:
            messagebox.showwarning("WARNING", "No 'output/clean.m3u' file found to backup.")

    def add_category(self):
        new_cat = self.cat_entry.get().strip()
        if not new_cat: return
        if new_cat not in self.categories:
            self.categories.append(new_cat)
            save_categories(self.categories)
            self.settings_cat_cb.configure(values=sorted(self.categories))
            # ✅ Safe check to prevent crash if live_cat_cb is removed
            if hasattr(self, 'live_cat_cb'):
                self.live_cat_cb.configure(values=sorted(self.categories))
            self.cat_entry.delete(0, 'end')
            self.log(f"  > CATEGORY ADDED: {new_cat}")
        else:
            messagebox.showwarning("WARNING", "CATEGORY ALREADY EXISTS!", parent=self.root)

    def remove_category(self):
        cat_to_remove = self.settings_cat_var.get()
        if not cat_to_remove or cat_to_remove == "Select Category":
            return messagebox.showwarning("WARNING", "PLEASE SELECT A CATEGORY FROM THE DROPDOWN!", parent=self.root)
        if cat_to_remove in ["General", "Sport", "News", "Animation", "Movie", "Entertainment"]:
            return messagebox.showwarning("WARNING", "DEFAULT CATEGORIES CANNOT BE REMOVED!", parent=self.root)
        if messagebox.askyesno("CONFIRM", f"REMOVE CATEGORY '{cat_to_remove}'?"):
            self.categories.remove(cat_to_remove)
            save_categories(self.categories)
            self.settings_cat_cb.configure(values=sorted(self.categories))
            # ✅ Safe check to prevent crash if live_cat_cb is removed
            if hasattr(self, 'live_cat_cb'):
                self.live_cat_cb.configure(values=sorted(self.categories))
            self.settings_cat_var.set("Select Category")
            self.log(f"  > CATEGORY REMOVED: {cat_to_remove}")
        

    def test_single_url(self):
        name = self.single_name.get().strip() or "MANUAL TEST"
        url = self.single_url.get().strip()
        if not url:
            return messagebox.showerror("ERROR", "PLEASE ENTER URL!", parent=self.root)
        self.log(f"  > TESTING: {name}")
        if VLC_PATH:
            try:
                process = subprocess.Popen([VLC_PATH, url, "--quiet"], creationflags=config.CREATE_NO_WINDOW)
                process.wait()
            except Exception as e:
                self.log(f" [X] ERROR: {e}")
                return
        
        channel_meta = {url: {"name": name, "logo": " ", "group": "General"}}
        
        dialog = ctk.CTkToplevel(self.root)
        dialog.geometry("400x250")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(fg_color=self.COLORS['bg_frame'])
        ctk.CTkLabel(dialog, text=name, font=self.FONT_TITLE, text_color=self.COLORS['accent_bright']).pack(pady=20)
        ctk.CTkLabel(dialog, text="RESULT?", font=self.FONT_BOLD, text_color=self.COLORS['text_main']).pack()
        def on_result(result):
            dialog.destroy()
            if result == 'y':
                self.live_db[url] = (name, 0.0, "OK", categorize_channel(name), " ", False)
                self.host_scores[get_host(url)] = self.host_scores.get(get_host(url), 0) + 1
                self.url_scores[url] = 100
                self.log(f" [+] {name} - SAVED AS OK (⭐⭐⭐⭐⭐)")
            elif result == 'd':
                self.url_scores[url] = 0
                self.log(f" [-] {name} - MARKED AS DEAD (❌)")
            elif result == 'r':
                self.log(f" [~] {name} - QUEUED FOR RETRY")
                # تابع add_to_retry_file در manual_tester تعریف شده، اینجا یک پیاده‌سازی ساده
                os.makedirs(config.OUTPUT_DIR, exist_ok=True)
                retry_file = os.path.join(config.OUTPUT_DIR, "retry.m3u")
                with open(retry_file, "a", encoding="utf-8") as f:
                    f.write(f'#EXTINF:-1 group-title="General",{name}\n{url}\n')
                
            save_databases(self.live_db, self.host_scores, self.search_history, self.url_scores)
            save_health_check_db(self.url_scores, channel_metadata=channel_meta, live_db=self.live_db)
            
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(pady=20, fill="x", padx=30)
        ctk.CTkButton(btn_frame, text="[ OK ]", command=lambda: on_result('y'), fg_color=self.COLORS['accent_bright'], text_color=self.COLORS['bg_main'], font=self.FONT_LARGE, width=80, height=50).pack(side="left", expand=True, fill="both", padx=5)
        ctk.CTkButton(btn_frame, text="[ RETRY ]", command=lambda: on_result('r'), fg_color=self.COLORS['accent_primary'], text_color=self.COLORS['bg_main'], font=self.FONT_LARGE, width=80, height=50).pack(side="left", expand=True, fill="both", padx=5)
        ctk.CTkButton(btn_frame, text="[ DEAD ]", command=lambda: on_result('d'), fg_color=self.COLORS['destructive'], text_color=self.COLORS['bg_main'], font=self.FONT_LARGE, width=80, height=50, hover_color=self.COLORS['destructive_hover']).pack(side="left", expand=True, fill="both", padx=5)

    def refresh_ranking(self):
        for item in self.ranking_tree.get_children(): 
            self.ranking_tree.delete(item)

        host_counts, host_urls = {}, {}
        from utils.helpers import get_quality_tier

        for url, score in self.url_scores.items():
            if score >= 90:
                host = get_host(url)
                host_counts[host] = host_counts.get(host, 0) + 1
                if host not in host_urls: 
                    host_urls[host] = url

        for url in self.live_db.keys():
            if url not in self.url_scores or self.url_scores[url] >= 90:
                host = get_host(url)
                host_counts[host] = host_counts.get(host, 0) + 1
                if host not in host_urls: 
                    host_urls[host] = url

        sorted_hosts = sorted(host_counts.items(), key=lambda x: x[1], reverse=True)
        for rank, (host, count) in enumerate(sorted_hosts, 1):
            if count >= 30: status = "[LEGENDARY]"
            elif count >= 15: status = "[EXCELLENT]"
            elif count >= 5: status = "[GOOD]"
            else: status = "[POOR]"

            display_host = (host[:40] + '...') if len(host) > 40 else host
            self.ranking_tree.insert('', 'end', values=(rank, display_host, count, status), tags=(host_urls.get(host),))

    def run(self):
        self.root.mainloop()

    def _update_hacker_progress(self, current, total):
        if total == 0: total = 1
        percentage = int((current / total) * 100)
        bar_length = 40
        filled = int((current / total) * bar_length)
        empty = bar_length - filled
        bar = "█" * filled + "░" * empty
        self.hacker_progress_var.set(f"[{bar}] {percentage:3d}%")

    def _animate_spinner(self):
        if self.testing:
            spinners = ["◴", "◷", "◶", "◵"]
            current = self.hacker_spinner_var.get()
            try:
                next_idx = (spinners.index(current) + 1) % len(spinners)
            except ValueError:
                next_idx = 0
            self.hacker_spinner_var.set(spinners[next_idx])
        self.root.after(150, self._animate_spinner)

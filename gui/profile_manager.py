# gui/profile_manager.py
import threading
import customtkinter as ctk
from tkinter import messagebox
from database.manager import load_profiles, save_profiles, create_profile, load_active_profile, set_active_profile

class ProfileManager:
    def __init__(self, app):
        self.app = app

    def update_profile_info(self):
        profile_name = self.app.profile_var.get()
        if profile_name in self.app.profiles:
            profile = self.app.profiles[profile_name]
            info_text = (
                f"Profile: {profile_name}\n"
                f"├─ Average Latency: {profile['avg_latency']}s\n"
                f"├─ Average Frames: {profile['avg_frames']}\n"
                f"├─ FFprobe Success Rate: {profile.get('avg_ffprobe_success', 0)*100:.0f}%\n"
                f"├─ Recommended Timeout: {profile['recommended_timeout']}s\n"
                f"├─ Recommended FFmpeg Time: {profile['recommended_ffmpeg_time']}s\n"
                f"├─ Recommended Retry: {profile['recommended_retry']}\n"
                f"└─ Created: {profile.get('created_at', 'N/A')}"
            )
            self.app.profile_info_label.configure(text=info_text)
        else:
            self.app.profile_info_label.configure(text="No profile selected or profile not found")

    def on_profile_select(self, choice):
        self.update_profile_info()
        if choice:
            self.app.new_profile_name.delete(0, 'end')
            self.app.new_profile_name.insert(0, choice)
            self.app.profile_urls_text.delete("1.0", "end")
            self.app.log(f"  > PROFILE '{choice}' SELECTED. READY FOR UPDATE TESTS.")

    def set_active(self):
        profile_name = self.app.profile_var.get()
        if set_active_profile(profile_name):
            self.app.active_profile = load_active_profile()
            self.app.log(f"  > ACTIVE PROFILE SET TO: {profile_name}")
            messagebox.showinfo("SUCCESS", f"Profile '{profile_name}' is now active!", parent=self.app.root)
        else:
            messagebox.showerror("ERROR", "Failed to set active profile!", parent=self.app.root)

    def delete(self):
        profile_name = self.app.profile_var.get()
        if profile_name == "default":
            messagebox.showwarning("WARNING", "Cannot delete default profile!", parent=self.app.root)
            return
        
        if messagebox.askyesno("CONFIRM", f"Are you sure you want to delete profile '{profile_name}'?"):
            if profile_name in self.app.profiles:
                del self.app.profiles[profile_name]
                save_profiles(self.app.profiles)
                
                profile_names = list(self.app.profiles.keys()) if self.app.profiles else ["default"]
                self.app.profile_combo.configure(values=profile_names)
                self.app.profile_var.set("default")
                self.update_profile_info()
                self.app.log(f"  > PROFILE DELETED: {profile_name}")

    def create(self):
        profile_name = self.app.new_profile_name.get().strip()
        urls_text = self.app.profile_urls_text.get("1.0", "end").strip()
        
        if not profile_name:
            return messagebox.showerror("ERROR", "Please enter a profile name!", parent=self.app.root)
        if not urls_text:
            return messagebox.showerror("ERROR", "Please enter at least one URL!", parent=self.app.root)
        
        # پارس کردن URLها از ورودی متنی
        raw_lines = urls_text.split('\n')
        urls, current_url = [], ""
        for line in raw_lines:
            line = line.strip()
            if not line: continue
            if line.startswith('http://') or line.startswith('https://'):
                if current_url: urls.append(current_url)
                current_url = line
            else:
                if current_url: current_url += line
        if current_url: urls.append(current_url)
        
        urls = [url for url in urls if url.startswith('http')]
        if not urls:
            return messagebox.showerror("ERROR", "No valid URLs found!", parent=self.app.root)
        
        self.app.log(f"  > PARSED {len(urls)} VALID URL(S) FROM INPUT")
        
        # اجرای تست در پس‌زمینه
        def safe_log(msg): 
            self.app.test_queue_queue.put(('log', msg))
            
        def create_worker():
            try:
                safe_log(f"  > ==========================================")
                safe_log(f"  > STARTING PROFILE TESTS FOR: {profile_name}")
                safe_log(f"  > ==========================================")
                create_profile(profile_name, urls, self.app.profiles, log_callback=safe_log)
                
                # بارگذاری مجدد پروفایل‌ها پس از اتمام تست
                self.app.profiles = load_profiles()
                self.app.root.after(0, lambda: self._on_profile_created(profile_name))
            except Exception as e:
                self.app.root.after(0, lambda: messagebox.showerror("ERROR", f"Failed to create profile: {e}", parent=self.app.root))
        
        threading.Thread(target=create_worker, daemon=True).start()

    def _on_profile_created(self, profile_name):
        profile_names = list(self.app.profiles.keys())
        self.app.profile_combo.configure(values=profile_names)
        self.app.profile_var.set(profile_name)
        self.update_profile_info()
        self.app.new_profile_name.delete(0, 'end')
        self.app.profile_urls_text.delete("1.0", "end")
        self.app.log(f"  > PROFILE CREATED: {profile_name}")
        messagebox.showinfo("SUCCESS", f"Profile '{profile_name}' created successfully!", parent=self.app.root)
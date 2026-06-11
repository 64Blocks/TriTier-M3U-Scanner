# gui/live_db_manager.py
import customtkinter as ctk
from tkinter import messagebox
from database.manager import load_databases, save_databases
from utils.helpers import get_quality_tier

class LiveDBManager:
    def __init__(self, app):
        self.app = app

    def reload_from_disk(self):
        """فقط این تابع از دیسک می‌خواند (مخصوص دکمه Refresh)"""
        try:
            disk_live_db, disk_host_scores, disk_search_history, disk_healthy, disk_unhealthy, disk_url_scores = load_databases()

            # ✅ ادغام هوشمند: اولویت با امتیازهای موجود در حافظه (RAM) است که تازه‌ترین تست‌ها آنجاست
            for url, score in disk_url_scores.items():
                if url not in self.app.url_scores:
                    self.app.url_scores[url] = score

            self.app.live_db = disk_live_db
            if not self.app.live_db:
                self.app.log(" [!] LIVE DB IS EMPTY. Please run a test and export clean.m3u first.")            
            self.app.host_scores = disk_host_scores
            self.app.search_history = disk_search_history
            self.app.healthy_urls = disk_healthy
            self.app.unhealthy_urls = disk_unhealthy

            self.update_live_tree_view()
            self.app.log(" [✓] LIVE DB RELOADED FROM DISK AND SYNCED WITH RAM.")
        except Exception as e:
            print(f" [!] Live DB Reload Error: {e}")

    def filter_in_memory(self):
        """این تابع فقط در حافظه فیلتر می‌کند (مخصوص جستجو) و به دیسک دست نمی‌زند"""
        self.update_live_tree_view()


    def update_live_tree_view(self):
        """رسم درخت بر اساس داده‌های فعلی حافظه"""
        try:
            if not hasattr(self.app, 'live_tree'): return
            self.app.live_tree.delete(*self.app.live_tree.get_children())
            if not self.app.live_db:
                return

            # ✅ Category filtering removed as requested
            current_cat = "All" 

            search_q = self.app.live_search_var.get().lower()
            score_filter = self.app.live_score_var.get()
            items_to_insert = []

            for url, data in self.app.live_db.items():
                name = data[0] if len(data) > 0 else "Unknown"
                category = data[3] if len(data) > 3 else "Other"
                logo = data[4] if len(data) > 4 else " "

                # Category check bypassed (always True now)
                if search_q and search_q not in name.lower() and search_q not in url.lower(): continue

                # ✅ اولویت با RAM، سپس دیسک، و در نهایت ۰
                score = int(self.app.url_scores.get(url, 0))
                tier = get_quality_tier(score)
                if score_filter == "⭐⭐⭐⭐⭐ (100)" and score != 100: continue
                elif score_filter == "⭐⭐⭐⭐ (>=70)" and not (70 <= score < 100): continue
                elif score_filter == "⭐⭐⭐ (>=50)" and not (50 <= score < 70): continue
                elif score_filter == "⭐⭐ (>=30)" and not (30 <= score < 50): continue
                elif score_filter == "⭐ (>=1)" and not (1 <= score < 30): continue
                elif score_filter == "❌ (0)" and score != 0: continue

                items_to_insert.append((tier, name, url, url, logo if logo and logo.strip() else "No Logo"))

            for item in items_to_insert:
                self.app.live_tree.insert('', 'end', values=item[:3], tags=(item[3], item[4]))
        except Exception as e:
            print(f" [!] Live DB View Update Error: {e}")


    def refresh_live_channels(self):
        # این تابع توسط دکمه Refresh صدا زده می‌شود
        self.reload_from_disk()

    def edit_selected_live(self):
        selection = self.app.live_tree.selection()
        if not selection:
            return messagebox.showwarning("WARNING", "SELECT CHANNELS FIRST!", parent=self.app.root)

        if len(selection) > 1:
            # ✅ ویرایش دسته‌جمعی (شامل تغییر امتیاز)
            dialog = ctk.CTkToplevel(self.app.root)
            dialog.title("BATCH EDIT")
            dialog.geometry("350x250")
            dialog.transient(self.app.root)
            dialog.grab_set()
            dialog.configure(fg_color=self.app.COLORS['bg_frame'])

            ctk.CTkLabel(dialog, text=f"EDIT {len(selection)} CHANNELS:", font=self.app.FONT_BOLD).pack(pady=10)

            ctk.CTkLabel(dialog, text="New Category (Keep Original to ignore):", font=self.app.FONT_DEFAULT).pack(pady=(5,0))
            entry_cat = ctk.CTkComboBox(dialog, width=250, values=["Keep Original"] + self.app.categories)
            entry_cat.set("Keep Original")
            entry_cat.pack(pady=5)

            ctk.CTkLabel(dialog, text="New Score (Keep Original to ignore):", font=self.app.FONT_DEFAULT).pack(pady=(5,0))
            entry_score = ctk.CTkComboBox(dialog, width=250, values=["Keep Original", "100 (⭐⭐⭐⭐⭐)", "0 (❌ Dead)"])
            entry_score.set("Keep Original")
            entry_score.pack(pady=5)

            def save_batch():
                new_cat = entry_cat.get().strip()
                new_score_str = entry_score.get().strip()
                
                if new_score_str == "100 (⭐⭐⭐⭐⭐)": new_score = 100
                elif new_score_str == "0 (❌ Dead)": new_score = 0
                else: new_score = None

                count = 0
                for item in selection:
                    url = self.app.live_tree.item(item, 'tags')[0]
                    if url in self.app.live_db:
                        data = list(self.app.live_db[url])
                        
                        if new_cat != "Keep Original":
                            data[3] = new_cat
                            self.app.live_db[url] = tuple(data)
                        
                        if new_score is not None:
                            self.app.url_scores[url] = new_score
                            if new_score >= 50:
                                self.app.healthy_urls.add(url)
                                self.app.unhealthy_urls.discard(url)
                            else:
                                self.app.unhealthy_urls.add(url)
                                self.app.healthy_urls.discard(url)
                                if url in self.app.live_db:
                                    del self.app.live_db[url]
                        count += 1

                save_databases(self.app.live_db, self.app.host_scores, self.app.search_history)
                save_health_check_db(self.app.url_scores, channel_metadata={}, live_db=self.app.live_db)
                self.reload_from_disk()
                dialog.destroy()
                self.app.log(f"  > UPDATED {count} CHANNELS IN BATCH.")

            ctk.CTkButton(dialog, text="SAVE", command=save_batch, fg_color=self.app.COLORS['accent_bright'], text_color=self.app.COLORS['bg_main']).pack(pady=15)
            return

        # ✅ ویرایش تکی (شامل تغییر امتیاز)
        url = self.app.live_tree.item(selection[0], 'tags')[0]
        data = self.app.live_db[url]
        name = data[0] if len(data) > 0 else "Unknown"
        category = data[3] if len(data) > 3 else "Other"
        logo = data[4] if len(data) > 4 else " "
        current_score = self.app.url_scores.get(url, 100)

        dialog = ctk.CTkToplevel(self.app.root)
        dialog.title("EDIT CHANNEL")
        dialog.geometry("450x400")
        dialog.transient(self.app.root)
        dialog.grab_set()
        dialog.configure(fg_color=self.app.COLORS['bg_frame'])

        ctk.CTkLabel(dialog, text="CHANNEL NAME:", font=self.app.FONT_BOLD, text_color=self.app.COLORS['accent_bright']).pack(pady=(15, 0))
        entry_name = ctk.CTkEntry(dialog, width=350, font=self.app.FONT_DEFAULT, fg_color=self.app.COLORS['bg_entry'])
        entry_name.insert(0, name)
        entry_name.pack(pady=5)

        ctk.CTkLabel(dialog, text="URL:", font=self.app.FONT_BOLD, text_color=self.app.COLORS['accent_bright']).pack(pady=(10, 0))
        entry_url = ctk.CTkEntry(dialog, width=350, font=self.app.FONT_DEFAULT, fg_color=self.app.COLORS['bg_entry'])
        entry_url.insert(0, url)
        entry_url.pack(pady=5)

        ctk.CTkLabel(dialog, text="CATEGORY:", font=self.app.FONT_BOLD, text_color=self.app.COLORS['accent_bright']).pack(pady=(10, 0))
        entry_cat = ctk.CTkComboBox(dialog, width=350, font=self.app.FONT_DEFAULT, fg_color=self.app.COLORS['bg_entry'], values=self.app.categories)
        entry_cat.set(category)
        entry_cat.pack(pady=5)

        ctk.CTkLabel(dialog, text="SCORE:", font=self.app.FONT_BOLD, text_color=self.app.COLORS['accent_bright']).pack(pady=(10, 0))
        entry_score = ctk.CTkComboBox(dialog, width=350, font=self.app.FONT_DEFAULT, fg_color=self.app.COLORS['bg_entry'], 
                                       values=["100 (⭐⭐⭐⭐⭐)", "0 (❌ Dead)"])
        entry_score.set("100 (⭐⭐⭐⭐⭐)" if current_score >= 50 else "0 (❌ Dead)")
        entry_score.pack(pady=5)

        def save():
            new_name = entry_name.get().strip()
            new_url = entry_url.get().strip()
            new_cat = entry_cat.get().strip()
            new_score_str = entry_score.get().strip()
            
            new_score = 100 if "100" in new_score_str else 0

            if not new_name or not new_url:
                return messagebox.showerror("ERROR", "NAME AND URL CANNOT BE EMPTY!", parent=dialog)

            if new_url != url:
                del self.app.live_db[url]
                if url in self.app.url_scores:
                    self.app.url_scores[new_url] = self.app.url_scores.pop(url)

            self.app.live_db[new_url] = (new_name, 0.0, "OK", new_cat, logo, False)
            self.app.url_scores[new_url] = new_score
            
            if new_score >= 50:
                self.app.healthy_urls.add(new_url)
                self.app.unhealthy_urls.discard(new_url)
            else:
                self.app.unhealthy_urls.add(new_url)
                self.app.healthy_urls.discard(new_url)
                if new_url in self.app.live_db:
                    del self.app.live_db[new_url]

            save_databases(self.app.live_db, self.app.host_scores, self.app.search_history)
            save_health_check_db(self.app.url_scores, channel_metadata={}, live_db=self.app.live_db)
            self.reload_from_disk()
            dialog.destroy()
            self.app.log(f"  > EDITED: {new_name} (New Score: {new_score})")

        ctk.CTkButton(dialog, text="SAVE CHANGES", command=save, fg_color=self.app.COLORS['accent_bright'], text_color=self.app.COLORS['bg_main'], font=self.app.FONT_LARGE).pack(pady=20)        
        
    def delete_selected_live(self):
        selection = self.app.live_tree.selection()
        if not selection:
            return messagebox.showwarning("WARNING", "SELECT CHANNELS FIRST!", parent=self.app.root)
            
        if messagebox.askyesno("CONFIRM", f"ARE YOU SURE YOU WANT TO DELETE {len(selection)} CHANNEL(S)?"):
            for item in selection:
                url = self.app.live_tree.item(item, 'tags')[0]
                name = self.app.live_db[url][0]
                del self.app.live_db[url]
                self.app.log(f"  > DELETED: {name}")
                
            save_databases(self.app.live_db, self.app.host_scores, self.app.search_history)
            self.reload_from_disk()
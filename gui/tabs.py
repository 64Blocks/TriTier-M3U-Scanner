import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk
import os
from utils.helpers import VLC_PATH, categorize_channel
from database.manager import load_categories, save_categories

def create_scan_tab(app, parent):
    main_frame = ctk.CTkFrame(parent, fg_color="transparent")
    main_frame.pack(fill="both", expand=True, padx=15, pady=15)

    file_frame = ctk.CTkFrame(main_frame, fg_color=app.COLORS['bg_frame'], border_width=1, border_color=app.COLORS['accent_secondary'])
    file_frame.pack(fill="x", pady=(0, 10))
    ctk.CTkLabel(file_frame, text="📂 Source M3U File:  ", font=app.FONT_BOLD, text_color=app.COLORS['accent_bright']).pack(anchor="w", padx=15, pady=(10, 5))
    
    file_row = ctk.CTkFrame(file_frame, fg_color="transparent")
    file_row.pack(fill="x", padx=15, pady=(0, 10))
    ctk.CTkEntry(file_row, textvariable=app.search_file_path, placeholder_text="Select an M3U file...", font=app.FONT_DEFAULT, fg_color="#0a0a0a", text_color=app.COLORS['accent_bright'], placeholder_text_color=app.COLORS['text_dim'], border_width=1, border_color=app.COLORS['accent_bright']).pack(side="left", fill="x", expand=True, padx=(0, 10))
    ctk.CTkButton(file_row, text="📁 Browse", command=lambda: app.search_file_path.set(filedialog.askopenfilename(filetypes=[("M3U Files", "*.m3u *.m3u8")])), width=100, font=app.FONT_BOLD, fg_color=app.COLORS['accent_primary'], hover_color=app.COLORS['accent_bright'], text_color=app.COLORS['bg_main']).pack(side="right")

    search_frame = ctk.CTkFrame(main_frame, fg_color=app.COLORS['bg_frame'], border_width=1, border_color=app.COLORS['accent_secondary'])
    search_frame.pack(fill="x", pady=(0, 10))
    
    kw_row = ctk.CTkFrame(search_frame, fg_color="transparent")
    kw_row.pack(fill="x", padx=15, pady=10)
    ctk.CTkLabel(kw_row, text="🔍 Keywords:  ", font=app.FONT_BOLD, text_color=app.COLORS['accent_bright'], width=80, anchor="w").pack(side="left", padx=(0, 10))
    
    app.keywords_entry = ctk.CTkEntry(kw_row, placeholder_text="Leave empty to load all... ", font=app.FONT_DEFAULT, fg_color="#0a0a0a", text_color=app.COLORS['accent_bright'], placeholder_text_color=app.COLORS['text_dim'], border_width=1, border_color=app.COLORS['accent_bright'])
    app.keywords_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
    app.keywords_entry.bind('<Return>', lambda event: app.scan_channels())
    ctk.CTkButton(kw_row, text="▶️ Scan", command=app.scan_channels, width=90, font=app.FONT_BOLD, fg_color=app.COLORS['accent_bright'], text_color=app.COLORS['bg_main'], hover_color="#4ade80").pack(side="right")

    cat_row = ctk.CTkFrame(search_frame, fg_color="transparent")
    cat_row.pack(fill="x", padx=15, pady=(0, 10))
    ctk.CTkButton(cat_row, text="🎲 Random 10", command=app.select_10_random_in_scan, width=110, font=app.FONT_BOLD, fg_color=app.COLORS['accent_primary'], text_color=app.COLORS['bg_main'], hover_color=app.COLORS['accent_bright']).pack(side="right")
    ctk.CTkLabel(search_frame, textvariable=app.found_count_var, font=app.FONT_BOLD, text_color=app.COLORS['text_dim']).pack(anchor="w", padx=15, pady=(0, 10))

    filter_row = ctk.CTkFrame(search_frame, fg_color="transparent")
    filter_row.pack(fill="x", padx=15, pady=(0, 10))
    ctk.CTkLabel(filter_row, text="🔎 Filter List:  ", font=app.FONT_BOLD, text_color=app.COLORS['accent_bright'], width=80, anchor="w").pack(side="left", padx=(0, 10))
    
    app.filter_var = ctk.StringVar()
    app.filter_var.trace_add("write", app.filter_found_channels)
    ctk.CTkEntry(filter_row, textvariable=app.filter_var, placeholder_text="Type to filter... ", width=200, font=app.FONT_DEFAULT, fg_color="#0a0a0a", text_color=app.COLORS['accent_bright'], placeholder_text_color=app.COLORS['text_dim'], border_width=1, border_color=app.COLORS['accent_bright']).pack(side="left", padx=(0, 10))
    ctk.CTkButton(filter_row, text="❌ Clear", command=lambda: app.filter_var.set(""), width=70, font=app.FONT_BOLD, fg_color=app.COLORS['bg_frame'], text_color=app.COLORS['destructive'], hover_color=app.COLORS['destructive_hover']).pack(side="left", padx=(0, 10))
    ctk.CTkButton(filter_row, text="🔄 Refresh", command=app.refresh_scan_list, width=90, font=app.FONT_BOLD, fg_color=app.COLORS['bg_entry'], text_color=app.COLORS['accent_bright']).pack(side="right")

    tree_frame = ctk.CTkFrame(main_frame, fg_color=app.COLORS['bg_main'], border_width=1, border_color=app.COLORS['accent_secondary'])
    tree_frame.pack(fill="both", expand=True, pady=(0, 10))
    
    columns = ('mark', 'name', 'url')
    app.channels_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=12) 
    app.channels_tree.heading('mark', text='⭐ Health ⇅', command=lambda: app.sort_column(app.channels_tree, 'mark', False))
    app.channels_tree.heading('name', text='📺 Channel Name ⇅', command=lambda: app.sort_column(app.channels_tree, 'name', False))
    app.channels_tree.heading('url', text='🔗 URL ⇅', command=lambda: app.sort_column(app.channels_tree, 'url', False))
    app.channels_tree.column('mark', width=120, anchor='center')
    app.channels_tree.column('name', width=300)
    app.channels_tree.column('url', width=500) 
      
    scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=app.channels_tree.yview)
    app.channels_tree.configure(yscrollcommand=scrollbar.set)
    app.channels_tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    app.channels_tree.bind('<Button-1>', app.on_tree_click)
    app.channels_tree.bind('<Double-Button-1>', app.test_double_click_channel)

    action_frame = ctk.CTkFrame(main_frame, fg_color=app.COLORS['bg_frame'], border_width=1, border_color=app.COLORS['accent_bright'])
    action_frame.pack(fill="x", side="bottom")
    
    action_top = ctk.CTkFrame(action_frame, fg_color="transparent")
    action_top.pack(fill="x", padx=15, pady=10)
    ctk.CTkLabel(action_top, text="⚙️ Test Mode:  ", font=app.FONT_BOLD, text_color=app.COLORS['accent_bright']).pack(side="left", padx=(0, 10))
    app.health_mode_var = ctk.StringVar(value="Normal")
    ctk.CTkComboBox(action_top, variable=app.health_mode_var, values=["Fast", "Normal", "Deep"], width=110, font=app.FONT_BOLD, fg_color="#0a0a0a", text_color=app.COLORS['accent_bright'], state="readonly").pack(side="left", padx=(0, 20))
    
    ctk.CTkLabel(action_top, text="📊 Filter Score:  ", font=app.FONT_BOLD, text_color=app.COLORS['accent_bright']).pack(side="left", padx=(0, 10))
    app.scan_score_var = ctk.StringVar(value="All")
    score_filters = ["All", "⭐⭐⭐⭐⭐ (90-100)", "⭐⭐⭐⭐ (70-89)", "⭐⭐⭐ (50-69)", "⭐⭐ (30-49)", "⭐ (1-29)", "❌ Dead (0)"]
    ctk.CTkComboBox(action_top, variable=app.scan_score_var, values=score_filters, width=160, font=app.FONT_BOLD, fg_color="#0a0a0a", text_color=app.COLORS['accent_bright'], state="readonly", command=lambda e: app.filter_found_channels()).pack(side="left")    
    
    action_bottom = ctk.CTkFrame(action_frame, fg_color="transparent")
    action_bottom.pack(fill="x", padx=15, pady=(0, 15))
    ctk.CTkButton(action_bottom, text="✅ Select All", command=app.select_all_channels, width=110, font=app.FONT_BOLD, fg_color=app.COLORS['bg_entry'], text_color=app.COLORS['accent_bright'], hover_color=app.COLORS['accent_secondary']).pack(side="left", padx=(0, 10))
    ctk.CTkButton(action_bottom, text="▶️ Manual Test", command=app.test_selected_channels, width=130, font=app.FONT_LARGE, fg_color=app.COLORS['accent_primary'], text_color=app.COLORS['bg_main'], hover_color=app.COLORS['accent_bright']).pack(side="left", padx=(0, 10))
    ctk.CTkButton(action_bottom, text="⚡ Auto Health Check", command=app.run_auto_health_check, width=160, font=app.FONT_LARGE, fg_color=app.COLORS['accent_bright'], text_color=app.COLORS['bg_main'], hover_color="#4ade80").pack(side="right")


def create_live_tab(app, parent):
    ctrl_frame = ctk.CTkFrame(parent, corner_radius=0, height=55, fg_color=app.COLORS['bg_frame'])
    ctrl_frame.pack(fill="x", padx=15, pady=10)
    ctrl_frame.pack_propagate(False)

    ctk.CTkLabel(ctrl_frame, text="  > SEARCH:  ", font=app.FONT_BOLD, text_color=app.COLORS['accent_bright']).pack(side="left", padx=(15, 5))
    app.live_search_var = ctk.StringVar()
    app.live_search_var.trace_add("write", app.filter_live_channels)
    ctk.CTkEntry(ctrl_frame, textvariable=app.live_search_var, width=200, font=app.FONT_DEFAULT, fg_color="#0a0a0a", text_color=app.COLORS['accent_bright'], placeholder_text_color=app.COLORS['text_dim'], border_width=1, border_color=app.COLORS['accent_bright']).pack(side="left", padx=5)

    ctk.CTkLabel(ctrl_frame, text="  > SCORE:  ", font=app.FONT_BOLD, text_color=app.COLORS['accent_bright']).pack(side="left", padx=(15, 5))
    app.live_score_var = ctk.StringVar(value="All")
    app.live_score_cb = ctk.CTkComboBox(ctrl_frame, variable=app.live_score_var, values=["All", "⭐⭐⭐⭐⭐ (100)", "⭐⭐⭐⭐ (>=70)", "⭐⭐⭐ (>=50)", "⭐⭐ (>=30)", "⭐ (>=1)", "❌ (0)"], width=160, font=app.FONT_DEFAULT, fg_color=app.COLORS['bg_entry'], border_color=app.COLORS['accent_secondary'], command=lambda e: app.filter_live_channels())
    app.live_score_cb.pack(side="left", padx=5)
    
    ctk.CTkButton(ctrl_frame, text=" ↻ REFRESH  ", command=app.live_db_manager.reload_from_disk, width=120, font=app.FONT_BOLD, fg_color=app.COLORS['accent_bright'], text_color=app.COLORS['bg_main'], hover_color="#4ade80").pack(side="right", padx=10)


    tree_frame = ctk.CTkFrame(parent, corner_radius=0, fg_color=app.COLORS['bg_main'], border_width=1, border_color=app.COLORS['accent_secondary'])
    tree_frame.pack(fill="both", expand=True, padx=15, pady=10)

    columns = ('score', 'name', 'url')
    app.live_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=20)
    app.live_tree.heading('score', text='⭐ SCORE ⇅', command=lambda: app.sort_column(app.live_tree, 'score', False))
    app.live_tree.heading('name', text='CHANNEL NAME ⇅', command=lambda: app.sort_column(app.live_tree, 'name', False))
    app.live_tree.heading('url', text='URL ⇅', command=lambda: app.sort_column(app.live_tree, 'url', False))

    app.live_tree.column('score', width=100, anchor='center')
    app.live_tree.column('name', width=350)
    app.live_tree.column('url', width=550)

    scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=app.live_tree.yview)
    app.live_tree.configure(yscrollcommand=scrollbar.set)
    app.live_tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    app.live_tree.bind('<Button-1>', lambda e: app.on_tree_click(e))

    btn_frame = ctk.CTkFrame(parent, corner_radius=0, height=55, fg_color="transparent")
    btn_frame.pack(fill="x", padx=15, pady=(0, 10))
    btn_frame.pack_propagate(False)
    
    ctk.CTkButton(btn_frame, text="EDIT", command=app.edit_selected_live, width=100, font=app.FONT_BOLD, fg_color=app.COLORS['accent_primary'], text_color=app.COLORS['bg_main']).pack(side="left", padx=10)
    ctk.CTkButton(btn_frame, text="DELETE", command=app.delete_selected_live, fg_color=app.COLORS['destructive'], text_color=app.COLORS['bg_main'], hover_color=app.COLORS['destructive_hover'], width=100, font=app.FONT_BOLD).pack(side="left", padx=10)
    
    # ✅ دکمه جدید برای ساخت دستی clean.m3u با دسته‌بندی دلخواه
    ctk.CTkButton(btn_frame, text="📥 EXPORT CLEAN M3U", command=app.export_clean_m3u, width=180, font=app.FONT_BOLD, fg_color=app.COLORS['accent_bright'], text_color=app.COLORS['bg_main'], hover_color="#4ade80").pack(side="right", padx=10)


    app.root.after(100, app.refresh_live_channels)

def create_profile_tab(app, parent):
    main_frame = ctk.CTkFrame(parent, corner_radius=0, fg_color=app.COLORS['bg_frame'])
    main_frame.pack(fill="both", expand=True, padx=15, pady=15)
    ctk.CTkLabel(main_frame, text="⚡ PROFILE MANAGEMENT", font=app.FONT_TITLE, text_color=app.COLORS['accent_bright']).pack(pady=(20, 10))
    
    select_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    select_frame.pack(fill="x", padx=20, pady=10)
    ctk.CTkLabel(select_frame, text="ACTIVE PROFILE:  ", font=app.FONT_BOLD, text_color=app.COLORS['accent_bright']).pack(side="left", padx=(0, 10))
    app.profile_var = ctk.StringVar(value="default")
    profile_names = list(app.profiles.keys()) if app.profiles else ["default"]
    app.profile_combo = ctk.CTkComboBox(select_frame, variable=app.profile_var, values=profile_names, width=200, font=app.FONT_DEFAULT, fg_color=app.COLORS['bg_entry'], command=app.on_profile_select)
    app.profile_combo.pack(side="left", padx=5)
    ctk.CTkButton(select_frame, text="SET ACTIVE", command=app.set_active_profile_btn, width=120, font=app.FONT_BOLD, fg_color=app.COLORS['accent_primary'], text_color=app.COLORS['bg_main']).pack(side="left", padx=10)
    ctk.CTkButton(select_frame, text="DELETE PROFILE", command=app.delete_profile, width=120, font=app.FONT_BOLD, fg_color=app.COLORS['destructive'], text_color=app.COLORS['bg_main']).pack(side="left", padx=10)
    
    info_frame = ctk.CTkFrame(main_frame, fg_color=app.COLORS['bg_entry'], corner_radius=0)
    info_frame.pack(fill="x", padx=20, pady=10)
    app.profile_info_label = ctk.CTkLabel(info_frame, text="No profile selected", font=app.FONT_DEFAULT, text_color=app.COLORS['text_main'], justify="left")
    app.profile_info_label.pack(padx=20, pady=15, anchor="w")
    
    create_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    create_frame.pack(fill="x", padx=20, pady=20)
    ctk.CTkLabel(create_frame, text="CREATE NEW PROFILE", font=app.FONT_BOLD, text_color=app.COLORS['accent_bright']).pack(anchor="w", pady=(0, 10))
    
    name_frame = ctk.CTkFrame(create_frame, fg_color="transparent")
    name_frame.pack(fill="x", pady=5)
    ctk.CTkLabel(name_frame, text="Profile Name:  ", font=app.FONT_DEFAULT, text_color=app.COLORS['text_main']).pack(side="left", padx=(0, 10))
    app.new_profile_name = ctk.CTkEntry(name_frame, width=200, font=app.FONT_DEFAULT, fg_color="#0a0a0a", text_color=app.COLORS['accent_bright'], placeholder_text="e.g., Home_Network", placeholder_text_color=app.COLORS['text_dim'], border_width=1, border_color=app.COLORS['accent_bright'])
    app.new_profile_name.pack(side="left", padx=5)
    
    ctk.CTkLabel(create_frame, text="Test URLs (one per line):  ", font=app.FONT_DEFAULT, text_color=app.COLORS['text_main']).pack(anchor="w", pady=(10, 5))
    app.profile_urls_text = ctk.CTkTextbox(create_frame, height=150, font=app.FONT_LOG, fg_color="#0a0a0a", text_color=app.COLORS['accent_bright'], border_width=1, border_color=app.COLORS['accent_bright'])
    app.profile_urls_text.pack(fill="x", pady=5)
    ctk.CTkButton(create_frame, text="CREATE PROFILE", command=app.create_profile_btn, width=150, font=app.FONT_BOLD, fg_color=app.COLORS['accent_bright'], text_color=app.COLORS['bg_main']).pack(pady=10)
    app.update_profile_info()

def create_settings_tab(app, parent):
    ctk.CTkLabel(parent, text="  > SYSTEM SETTINGS  ", font=app.FONT_TITLE, text_color=app.COLORS['accent_bright']).pack(anchor="w", padx=20, pady=(20, 5))
    
    ctk.CTkLabel(parent, text="  > DATABASE BACKUP ", font=app.FONT_TITLE, text_color=app.COLORS['accent_bright']).pack(anchor="w", padx=20, pady=(20, 5))
    ctk.CTkButton(parent, text="CREATE BACKUP OF clean.m3u  ", command=app.backup_database, fg_color=app.COLORS['accent_primary'], text_color=app.COLORS['bg_main'], font=app.FONT_BOLD, width=250).pack(anchor="w", padx=20, pady=5)

    ctk.CTkLabel(parent, text="  > DNS PERFORMANCE TESTER  ", font=app.FONT_TITLE, text_color=app.COLORS['accent_bright']).pack(anchor="w", padx=20, pady=(20, 5))
    ctk.CTkButton(parent, text="DNS TEST", command=app.run_dns_tester, fg_color=app.COLORS['accent_primary'], text_color=app.COLORS['bg_main'], font=app.FONT_BOLD, width=250, hover_color=app.COLORS['accent_bright']).pack(anchor="w", padx=20, pady=5)

    ctk.CTkLabel(parent, text="  > CATEGORY MANAGEMENT  ", font=app.FONT_TITLE, text_color=app.COLORS['accent_bright']).pack(anchor="w", padx=20, pady=(20, 5))
    cat_frame = ctk.CTkFrame(parent, fg_color="transparent")
    cat_frame.pack(fill="x", padx=20, pady=10)
    app.settings_cat_var = ctk.StringVar(value="Select Category")
    app.settings_cat_cb = ctk.CTkComboBox(cat_frame, variable=app.settings_cat_var, values=sorted(app.categories), width=250, font=app.FONT_DEFAULT, fg_color=app.COLORS['bg_entry'], border_color=app.COLORS['accent_secondary'])
    app.settings_cat_cb.pack(side="left", padx=(0, 10))
    ctk.CTkButton(cat_frame, text="REMOVE SELECTED", command=app.remove_category, width=140, font=app.FONT_BOLD, fg_color=app.COLORS['destructive'], text_color=app.COLORS['bg_main'], hover_color=app.COLORS['destructive_hover']).pack(side="left", padx=5)
    app.cat_entry = ctk.CTkEntry(cat_frame, placeholder_text="  > NEW CATEGORY NAME  ", width=250, font=app.FONT_DEFAULT, fg_color="#0a0a0a", text_color=app.COLORS['accent_bright'], placeholder_text_color=app.COLORS['text_dim'], border_width=1, border_color=app.COLORS['accent_bright'])
    app.cat_entry.pack(side="left", padx=(20, 10))
    ctk.CTkButton(cat_frame, text="ADD", command=app.add_category, width=80, font=app.FONT_BOLD, fg_color=app.COLORS['accent_bright'], text_color=app.COLORS['bg_main']).pack(side="left")

def create_single_tab(app, parent):
    ctk.CTkLabel(parent, text="  > SINGLE URL TEST MODULE  ", font=app.FONT_TITLE, text_color=app.COLORS['accent_bright']).pack(anchor="w", padx=20, pady=(20, 10))
    ctk.CTkLabel(parent, text="CHANNEL NAME:  ", font=app.FONT_BOLD, text_color=app.COLORS['accent_bright'], anchor="w").pack(anchor="w", padx=20, pady=(15, 0))
    app.single_name = ctk.CTkEntry(parent, width=500, placeholder_text="  > CHANNEL NAME  ", font=app.FONT_DEFAULT, fg_color="#0a0a0a", text_color=app.COLORS['accent_bright'], placeholder_text_color=app.COLORS['text_dim'], border_width=1, border_color=app.COLORS['accent_bright'])
    app.single_name.pack(padx=20, pady=5)
    ctk.CTkLabel(parent, text="URL:  ", font=app.FONT_BOLD, text_color=app.COLORS['accent_bright'], anchor="w").pack(anchor="w", padx=20, pady=(15, 0))
    app.single_url = ctk.CTkEntry(parent, width=500, placeholder_text="  > HTTP://...  ", font=app.FONT_DEFAULT, fg_color="#0a0a0a", text_color=app.COLORS['accent_bright'], placeholder_text_color=app.COLORS['text_dim'], border_width=1, border_color=app.COLORS['accent_bright'])
    app.single_url.pack(padx=20, pady=5)
    ctk.CTkButton(parent, text="  > MANUAL TEST  ", command=app.test_single_url, fg_color=app.COLORS['accent_bright'], text_color=app.COLORS['bg_main'], font=app.FONT_LARGE, width=200).pack(pady=30)

def create_ranking_tab(app, parent):
    frame = ctk.CTkFrame(parent, corner_radius=0, fg_color=app.COLORS['bg_main'], border_width=1, border_color=app.COLORS['accent_secondary'])
    frame.pack(fill="both", expand=True, padx=15, pady=15)
    columns = ('rank', 'host', 'score', 'status')
    app.ranking_tree = ttk.Treeview(frame, columns=columns, show='headings', height=20)
    app.ranking_tree.heading('rank', text='RANK')
    app.ranking_tree.heading('host', text='HOST / DOMAIN')
    app.ranking_tree.heading('score', text='COUNT')
    app.ranking_tree.heading('status', text='STATUS')
    app.ranking_tree.column('rank', width=60, anchor='center')
    app.ranking_tree.column('host', width=400)
    app.ranking_tree.column('score', width=100, anchor='center')
    app.ranking_tree.column('status', width=150, anchor='center')
    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=app.ranking_tree.yview)
    app.ranking_tree.configure(yscrollcommand=scrollbar.set)
    app.ranking_tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    ctk.CTkButton(parent, text="↻ REFRESH", command=app.refresh_ranking, fg_color=app.COLORS['accent_primary'], text_color=app.COLORS['bg_main'], font=app.FONT_TITLE, width=200).pack(pady=(0, 15))
    app.refresh_ranking()

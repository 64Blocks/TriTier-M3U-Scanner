import customtkinter as ctk

COLORS = {
    'bg_main': '#000000', 'bg_frame': '#000500', 'bg_entry': '#001100',
    'text_main': '#00FF41', 'text_dim': '#008F11', 'accent_bright': '#00FF41',
    'accent_primary': '#008F11', 'accent_secondary': '#003B00',
    'destructive': '#FF0040', 'destructive_hover': '#CC0033'
}

FONT_DEFAULT = ("Lucida Console", 12)
FONT_BOLD = ("Lucida Console", 12, "bold")
FONT_TITLE = ("Lucida Console", 20, "bold")
FONT_LARGE = ("Lucida Console", 14, "bold")
FONT_LOG = ("Lucida Console", 11)

def apply_theme():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("green")
    ctk.ThemeManager.theme["CTkButton"]["corner_radius"] = 0
    ctk.ThemeManager.theme["CTkEntry"]["corner_radius"] = 0
    ctk.ThemeManager.theme["CTkFrame"]["corner_radius"] = 0
    ctk.ThemeManager.theme["CTkComboBox"]["corner_radius"] = 0
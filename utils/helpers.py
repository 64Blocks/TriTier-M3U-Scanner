import os
import sys
import socket
import random
import subprocess
import re
import shutil
import urllib.request
from urllib.parse import urlparse
import config

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

USER_AGENTS = [
    "Mozilla/5.0 (Linux; Android 9; OPPO PHY110 Build/PQ3A.190705.05150936) IPTV Pro/9.1.16 VLC/3.0.18 LibVLC/3.0.18"
]

def get_random_ua():
    return random.choice(USER_AGENTS)

def find_vlc():
    sys_vlc = shutil.which("vlc") or shutil.which("vlc.exe")
    if sys_vlc and os.path.exists(sys_vlc): return sys_vlc
    for path in [r"C:\Program Files\VideoLAN\VLC\vlc.exe", r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"]:
        if os.path.exists(path): return path
    return None

def find_ffmpeg():
    portable_ffmpeg = resource_path("bin/ffmpeg.exe")
    if os.path.exists(portable_ffmpeg): return portable_ffmpeg
    sys_ffmpeg = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
    if sys_ffmpeg and os.path.exists(sys_ffmpeg): return sys_ffmpeg
    for path in [r"C:\ffmpeg\bin\ffmpeg.exe", r"D:\ffmpeg\bin\ffmpeg.exe"]:
        if os.path.exists(path): return path
    return None

# ✅ تعریف ایمن برای جلوگیری از ImportError در PyInstaller
try:
    VLC_PATH = find_vlc()
except Exception:
    VLC_PATH = None

try:
    FFMPEG_PATH = find_ffmpeg()
except Exception:
    FFMPEG_PATH = None

if FFMPEG_PATH:
    dir_path = os.path.dirname(FFMPEG_PATH)
    ffprobe_name = "ffprobe.exe" if sys.platform == 'win32' else "ffprobe"
    FFPROBE_PATH = os.path.join(dir_path, ffprobe_name)
    if not os.path.exists(FFPROBE_PATH):
        FFPROBE_PATH = shutil.which("ffprobe") or shutil.which("ffprobe.exe")
else:
    FFPROBE_PATH = None

def categorize_channel(name):
    name_lower = name.lower().replace("  ", " ").replace("-", " ").replace("_", " ")
    categories = [
        ("Sport", ["espn", "nfl", "nba", "mlb", "nhl", "golf", "tennis", "foxsports", "skysports", "eurosport", "dazn", "beinsports"]),
        ("News", ["cnn", "foxnews", "msnbc", "cnbc", "bloomberg", "bbcnews", "skynews", "france24", "euronews", "aljazera"]),
        ("Animation", ["cartoon", "nickelodeon", "disney", "cbeebies", "cbbc", "pbskids", "cartoonito"]),
        ("Movie", ["hbo", "cinemax", "showtime", "starz", "amc", "skycinema", "film4", "tntfilm", "paramountnetwork"]),
        ("Series", ["comedycentral", "syfy", "bravo", "hallmark", "skyatlantic", "axn", "tvland"]),
        ("Documentary", ["discovery", "tlc", "natgeo", "history", "sciencechannel", "animalplanet", "dmax", "arte"]),
        ("Music", ["mtv", "vh1", "bet", "traceurban", "fuse", "cmt"]),
        ("Entertainment", ["e!", "lifetime", "aande", "canale5", "italia1", "tf1", "france2", "antena3", "rai1", "zdf", "rtl", "bbc", "itv"])
    ]
    for category, keywords in categories:
        if any(keyword in name_lower for keyword in keywords): return category
    
    regional = [
        ("UK Channels", ["bbc", "itv", "channel4", "channel5", "skyuk", "uk"]),
        ("Germany Channels", ["daserste", "zdf", "rtl", "sat1", "prosieben", "ard"]),
        ("France Channels", ["tf1", "france2", "france3", "m6", "canalplus", "arte"]),
        ("Spain Channels", ["antena3", "telecinco", "lasexta", "movistar", "laliga"]),
        ("Italy Channels", ["rai", "canale5", "italia1", "rete4", "skyitalia", "la7"])
    ]
    for category, keywords in regional:
        if any(keyword in name_lower for keyword in keywords): return category
    return "General"

def get_emoji_category(category):
    cat_lower = category.lower()
    if 'sport' in cat_lower: return f"⚽ {category}"
    if 'news' in cat_lower: return f"📰 {category}"
    if 'movie' in cat_lower or 'film' in cat_lower or 'cinema' in cat_lower: return f"🎬 {category}"
    if 'animation' in cat_lower or 'cartoon' in cat_lower or 'kids' in cat_lower: return f"🧸 {category}"
    if 'music' in cat_lower: return f"🎵 {category}"
    if 'doc' in cat_lower or 'documentary' in cat_lower: return f"🎥 {category}"
    if 'religion' in cat_lower or 'quran' in cat_lower: return f"🕌 {category}"
    return f"📺 {category}"

def get_quality_tier(score):
    if score == 0: return "❌"
    elif score >= 90: return "⭐⭐⭐⭐⭐"
    elif score >= 70: return "⭐⭐⭐⭐"
    elif score >= 50: return "⭐⭐⭐"
    elif score >= 30: return "⭐⭐"
    else: return "⭐"

def get_host(url):
    try: return urlparse(url).netloc
    except: return "unknown"

def parse_extinf(line):
    name, logo, group = "Unknown", " ", "General"
    logo_match = re.search(r'tvg-logo="([^"]*)"', line)
    if logo_match: logo = logo_match.group(1).strip()
    group_match = re.search(r'group-title="([^"]*)"', line)
    if group_match: group = group_match.group(1).strip()
    if ',' in line: name = line.split(',')[-1].strip()
    if name.startswith('#EXTINF'): name = "Unknown"
    return name, logo, group

def get_network_info():
    local_ip, public_ip, dns_servers, status = "127.0.0.1", "Unknown", "Unknown", "🔴 Disconnected"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        status = "🟢 Connected"
    except:
        return "System Default", status, " | [NO INTERNET]"
    
    if sys.platform == 'win32':
        try:
            output = subprocess.check_output(['ipconfig', '/all'], creationflags=config.CREATE_NO_WINDOW).decode('utf-8', errors='ignore')
            lines = output.split('\n')
            for i, line in enumerate(lines):
                if 'DNS' in line or 'سرورهای' in line:
                    for j in range(i, min(i + 4, len(lines))):
                        ip_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', lines[j])
                        if ip_match:
                            dns_servers = ip_match.group(1)
                            break
                    if dns_servers != "Unknown": break
        except: pass

    try:
        cmd = ['nslookup', 'myip.opendns.com', 'resolver1.opendns.com']
        output = subprocess.check_output(cmd, creationflags=config.CREATE_NO_WINDOW, timeout=3).decode('utf-8', errors='ignore')
        ips = re.findall(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', output)
        if len(ips) >= 2: public_ip = ips[-1]
    except: pass

    if public_ip == "Unknown":
        try: public_ip = urllib.request.urlopen('https://api.ipify.org', timeout=2).read().decode('utf8')
        except: pass

    vpn_text = " "
    if public_ip != "Unknown" and local_ip != public_ip and not local_ip.startswith("192.168.") and not local_ip.startswith("10."):
        vpn_text = f" | [VPN/PROXY ACTIVE: {public_ip}]"
    elif public_ip != "Unknown":
        vpn_text = f" | [PUBLIC IP: {public_ip}]"
        
    return dns_servers or "System Default", status, vpn_text
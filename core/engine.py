import time
import subprocess
import re
import json
import random
from urllib.parse import urlparse, urljoin
import urllib.request
import config
from utils.helpers import get_random_ua, FFMPEG_PATH, FFPROBE_PATH
from core.backoff import domain_allowed, update_domain

def fetch_url(url, timeout):
    domain = urlparse(url).netloc
    if not domain_allowed(domain):
        time.sleep(0.5)
        return None, 999, False
    try:
        req = urllib.request.Request(url, headers={'User-Agent': get_random_ua(), 'Accept': '*/*', 'Connection': 'keep-alive', 'Cache-Control': 'no-cache'})
        start = time.time()
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read(1024)
        latency = time.time() - start
        update_domain(domain, latency=latency)
        return data, latency, True
    except:
        update_domain(domain, fail=True)
        return None, 999, False

def check_connectivity(url, timeout):
    _, latency, ok = fetch_url(url, timeout)
    return (25, latency) if ok else (0, latency)

def check_segment(url, timeout):
    try:
        content, _, ok = fetch_url(url, timeout)
        if not ok: return 0
        content = content.decode("utf-8", errors="ignore")
        lines = [l.strip() for l in content.splitlines() if l.strip()]
        candidates = [l for l in lines if not l.startswith("#")]
        if not candidates: return 0
        
        first = urljoin(url, candidates[0])
        max_depth = 3
        for _ in range(max_depth):
            if '.m3u8' not in first.lower(): break
            try:
                sub_content, _, ok_sub = fetch_url(first, timeout)
                if not ok_sub: break
                sub_content = sub_content.decode("utf-8", errors="ignore")
                sub_lines = [l.strip() for l in sub_content.splitlines() if l.strip()]
                sub_candidates = [l for l in sub_lines if not l.startswith("#")]
                if sub_candidates: first = urljoin(first, sub_candidates[0])
                else: break
            except: break
            
        start_seg = time.time()
        _, _, ok2 = fetch_url(first, timeout)
        seg_latency = time.time() - start_seg
        if ok2: return 25 if seg_latency < 3.0 else 15
        return 0
    except: return 0

def check_ffprobe_fast(url, timeout=4):
    if not FFPROBE_PATH: return False, {}
    try:
        headers_str = "Accept: */*\r\nConnection: keep-alive\r\n"
        cmd = [FFPROBE_PATH, "-v", "error", "-analyzeduration", "500000", "-probesize", "100000", "-rw_timeout", "3000000",
               "-user_agent", get_random_ua(), "-headers", headers_str, "-show_entries", "stream=codec_type,codec_name", "-of", "json", "-i", url]
        
        # ✅ اصلاح حیاتی: اضافه کردن encoding و errors برای جلوگیری از کرش در کاراکترهای خاص
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=timeout, creationflags=config.CREATE_NO_WINDOW)
        
        if result.returncode == 0 and result.stdout:
            data = json.loads(result.stdout)
            streams = data.get("streams", [])
            has_video = any(s.get("codec_type") == "video" for s in streams)
            has_audio = any(s.get("codec_type") == "audio" for s in streams)
            if has_video or has_audio:
                info = {
                    "video_codec": next((s.get("codec_name") for s in streams if s.get("codec_type") == "video"), "N/A"),
                    "audio_codec": next((s.get("codec_name") for s in streams if s.get("codec_type") == "audio"), "N/A")
                }
                return True, info
        return False, {}
    except: return False, {}

def check_ffmpeg(url, ffmpeg_time):
    if not FFMPEG_PATH: return 0
    domain = urlparse(url).netloc
    try:
        ua = get_random_ua()
        headers_str = "Accept: */*\r\nAccept-Language: en-US,en;q=0.9\r\nConnection: keep-alive\r\nReferer: https://cloudfront.net/\r\n"
        cmd = [FFMPEG_PATH, "-hide_banner", "-v", "info", "-user_agent", ua, "-headers", headers_str, "-rw_timeout", "15000000",
               "-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "2", "-i", url, "-t", str(ffmpeg_time), "-f", "null", "-"]
        
        # ✅ اصلاح حیاتی: اضافه کردن encoding و errors برای جلوگیری از کرش در کاراکترهای خاص
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=(ffmpeg_time * 4) + 40, creationflags=config.CREATE_NO_WINDOW)
        
        err = result.stderr.lower()
        if result.returncode != 0 and "exit code 0" not in err:
            update_domain(domain, fail=True)
            return 0
            
        time_matches = re.findall(r'time=(\d+):(\d+):(\d+\.?\d*)', err)
        processed_time = 0
        if time_matches:
            last_match = time_matches[-1]
            processed_time = int(last_match[0])*3600 + int(last_match[1])*60 + float(last_match[2])
            
        decode_errors_match = re.search(r'(\d+) decode errors', err)
        decode_errors = int(decode_errors_match.group(1)) if decode_errors_match else 0
        frame_match = re.search(r"frame=\s*(\d+)", err)
        frames = int(frame_match.group(1)) if frame_match else 0
        
        if processed_time >= (ffmpeg_time * 0.7) and frames > 0:
            if decode_errors == 0: update_domain(domain); return 50
            elif decode_errors < frames * 0.1: update_domain(domain); return 45
            else: update_domain(domain); return 30
        elif frames > 10 or processed_time > 2:
            update_domain(domain); return 20
        else:
            update_domain(domain, fail=True); return 0
    except subprocess.TimeoutExpired:
        update_domain(domain, timeout=True); return 0
    except Exception:
        update_domain(domain, timeout=True); return 0

def test_channel_smart(url, timeout, ffmpeg_time, mode='Normal'):
    domain = urlparse(url).netloc
    now = time.time()
    from core.backoff import domain_state
    if domain not in domain_state or "last_tested" not in domain_state[domain]:
        domain_state[domain]["last_tested"] = 0.0
    time_since_last = now - domain_state[domain]["last_tested"]
    if time_since_last < 1.5: time.sleep(random.uniform(0.5, 1.5))
    
    score, latency = 0, 999
    l1, l2, l3, probe_bonus = 0, 0, 0, 0

    for _ in range(2):
        l1, lat = check_connectivity(url, timeout)
        latency = lat
        if l1 == 0: continue
        l2 = check_segment(url, timeout)
        if mode == 'Fast':
            score = l1 + l2; break
        elif mode == 'Normal':
            l3 = check_ffmpeg(url, ffmpeg_time); score = l1 + l2 + l3; break
        elif mode == 'Deep':
            probe_ok, _ = check_ffprobe_fast(url, timeout=4)
            probe_bonus = 10 if probe_ok else 0
            l3 = check_ffmpeg(url, ffmpeg_time)
            score = l1 + l2 + l3 + probe_bonus
            break
            
    # ✅ محدودیت نهایی و قطعی: هرگز امتیازی بالاتر از ۱۰۰ برگردانده نمی‌شود (رفع باگ امتیازهای ۱۰۵ و ۱۰۷)
    if score > 100: 
        score = 100 
        
    update_domain(domain, latency=latency if l1 > 0 else None, fail=(score < 50))
    return {"url": url, "score": score, "latency": latency, "l1": l1, "l2": l2, "l3": l3, "probe": probe_bonus}
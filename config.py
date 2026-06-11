import os
import sys

# تنظیمات پنجره در ویندوز برای جلوگیری از باز شدن کنسول سیاه
CREATE_NO_WINDOW = 0x08000000 if sys.platform == 'win32' else 0

# مسیرهای پیش‌فرض
OUTPUT_DIR = "output"
BACKUP_DIR = "backup"

# اطمینان از وجود دایرکتوری‌ها
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

# تنظیمات پیش‌فرض پروفایل
DEFAULT_PROFILE = {
    "avg_latency": 2.0,
    "avg_frames": 20,
    "recommended_timeout": 6,
    "recommended_ffmpeg_time": 3,
    "recommended_retry": 2
}
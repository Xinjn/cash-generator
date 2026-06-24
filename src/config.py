"""
全局配置文件
定义多区域（MY/TH/ID/PH/SG/VN）的货币符号与格式、字体路径、导出设置等
项目级别的常量与配置项统一在此文件中维护。
"""

import os

# 基础路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
OUTPUT_DIR = os.path.join(BASE_DIR, "assets", "output")

# 确保输出目录存在
os.makedirs(OUTPUT_DIR, exist_ok=True)

# =====================
# 区域配置
# ======================
REGIONS = {
    "MY": {
        "name": "Malaysia",
        "currency": "RM",
        "currency_position": "prefix",  # RM 15
        "locale": "en_MY",
        "primary_color": "#FF475A",
        "secondary_color": "#FFE8E9",
        "accent_color": "#D32637",
        "text_color": "#902531",
    },
    "TH": {
        "name": "Thailand",
        "currency": "฿",
        "currency_position": "prefix",  # ฿100
        "locale": "th_TH",
        "primary_color": "#FF475A",
        "secondary_color": "#FFE8E9",
        "accent_color": "#D32637",
        "text_color": "#902531",
    },
    "ID": {
        "name": "Indonesia",
        "currency": "Rp",
        "currency_position": "prefix",  # Rp 15.000
        "locale": "id_ID",
        "primary_color": "#FF475A",
        "secondary_color": "#FFE8E9",
        "accent_color": "#D32637",
        "text_color": "#902531",
    },
    "PH": {
        "name": "Philippines",
        "currency": "₱",
        "currency_position": "prefix",  # ₱50
        "locale": "en_PH",
        "primary_color": "#FF475A",
        "secondary_color": "#FFE8E9",
        "accent_color": "#D32637",
        "text_color": "#902531",
    },
    "SG": {
        "name": "Singapore",
        "currency": "$",
        "currency_position": "prefix",  # $5
        "locale": "en_SG",
        "primary_color": "#FF475A",
        "secondary_color": "#FFE8E9",
        "accent_color": "#D32637",
        "text_color": "#902531",
    },
    "VN": {
        "name": "Vietnam",
        "currency": "₫",
        "currency_position": "suffix",  # 50.000 ₫
        "locale": "vi_VN",
        "primary_color": "#FF475A",
        "secondary_color": "#FFE8E9",
        "accent_color": "#D32637",
        "text_color": "#902531",
    },
}

# =====================
# 字体设置
# ======================
def get_font_path():
    """查找 macOS 上可用的粗体字体。"""
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold Italic.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/Library/Fonts/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None

FONT_PATH = get_font_path()
FONT_FALLBACK = "arial.ttf"

# =====================
# 导出设置
# ======================
EXPORT_FORMATS = ["PNG", "JPG"]
DEFAULT_FORMAT = "PNG"
DEFAULT_QUALITY = 95

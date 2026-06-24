"""
现金券图像生成引擎
核心图像合成模块：基于 template_base.png 模板，通过 9-patch 缩放生成任意尺寸的现金券图片。
负责字体加载、货币格式化、Logo 贴图、金额文字自适应排版等图像绘制逻辑。
所有 GUI 与 CLI 入口均调用此引擎的 generate_coupon() 函数。
"""

import os
import sys
import math
from PIL import Image, ImageDraw, ImageFont

# =====================
# 配置
# ======================

COUNTRY_CONFIG = {
    "MY": {"currency": "RM", "prefix": "RM", "suffix": "", "separator": ",", "decimal": True, "threshold_rb": None},
    "TH": {"currency": "฿", "prefix": "฿", "suffix": "", "separator": ",", "decimal": True, "threshold_rb": None},
    "ID": {"currency": "Rp", "prefix": "Rp", "suffix": "", "separator": ".", "decimal": False, "threshold_rb": 100},
    "PH": {"currency": "₱", "prefix": "₱", "suffix": "", "separator": ",", "decimal": True, "threshold_rb": None},
    "SG": {"currency": "$", "prefix": "$", "suffix": "", "separator": ",", "decimal": True, "threshold_rb": None},
    "VN": {"currency": "₫", "prefix": "", "suffix": "₫", "separator": ".", "decimal": False, "threshold_rb": None},
}

COLOR_TITLE = "#902531"
COLOR_AMOUNT = "#d62f3e"

FONT_BOLD = "EuclidCircularA-Bold.otf"
FONT_MEDIUM = "EuclidCircularA-Medium.otf"
FONT_ROBOTO_BLACK = "Roboto-Black.ttf"
FONT_INTER_BOLD = "Inter-Bold.ttf"
FONT_INTER_REGULAR = "Inter-Regular.ttf"

# =====================
# 模板类型
# ======================
TEMPLATE_LAZCASH = "lazcash"
TEMPLATE_PDV = "pdv"

# 模板文件名映射
TEMPLATE_FILES = {
    TEMPLATE_LAZCASH: "template_base.png",
    TEMPLATE_PDV: "template_base2.png",
}

# 金额样式配置（按模板类型区分）
AMOUNT_CONFIG = {
    TEMPLATE_LAZCASH: {
        "color": COLOR_AMOUNT,
        "default_num_fs": 72,
        "default_sym_fs": 48,
    },
    TEMPLATE_PDV: {
        "color": "#FF0064",
        "default_num_fs": 80,
        "default_sym_fs": 56,
    },
}

# PDV 券类型配置（基于 260x260 模板）
PDV_VOUCHER_TYPE_TEXT = "Platform Voucher"
PDV_VOUCHER_TYPE_COLOR = "#FF0064"
PDV_VOUCHER_TYPE_FONT = FONT_BOLD
PDV_VOUCHER_TYPE_BASE_FS = 28
PDV_VOUCHER_TYPE_LINE_H = 36
PDV_VOUCHER_TYPE_BOX_W = 150
PDV_VOUCHER_TYPE_BOX_H = 72
PDV_VOUCHER_TYPE_TOP = 22

# PDV 消费门槛配置（基于 260x260 模板）
PDV_MINSPEND_COLOR = "#2E3346"
PDV_MINSPEND_FONT = FONT_MEDIUM
PDV_MINSPEND_BASE_FS = 26
PDV_MINSPEND_SMALL_FS = 22
PDV_MINSPEND_TOP_GAP = 10

# PDV 有效内容区比例：260x260 模板下实际可用内容宽度为 200px
PDV_USABLE_RATIO = 200 / 260  # 左右各保留 30px 边距

# 基础布局尺寸（模板尺寸 260x260 时）
BASE_TEMPLATE_W = 260
BASE_TEMPLATE_H = 260
BASE_LOGO_H = 66
BASE_TITLE_H = 28
BASE_GAP_LT = 12       # logo 与标题间距
BASE_GAP_AB = 20       # A 组与 B 组间距（PDV 默认）
LAZCASH_GAP_AB = 12    # LazCash A 组与 B 组间距（减小金额下方空隙）
BASE_GROUP_A_H = 66    # logo/标题行高度
BASE_GROUP_B_H_REF = 120  # 金额组参考高度

DEFAULT_AMT_FS = 72
DEFAULT_SYM_FS = 48


def get_base_dir():
    """解析基础目录，支持打包模式和开发模式。"""
    if getattr(sys, 'frozen', False):
        if sys.platform == "darwin":
            # macOS .app 包：Resources 目录
            exe = sys.executable
            contents = os.path.dirname(os.path.dirname(exe))
            return os.path.join(contents, "Resources")
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resource_path(*parts):
    """构建打包资源的路径。"""
    base = get_base_dir()
    # 优先尝试 _internal 目录（PyInstaller onedir 模式），再尝试直接路径
    candidates = [
        os.path.join(base, "_internal", *parts),
        os.path.join(base, *parts),
        os.path.join(base, "assets", *parts),
        os.path.join(os.path.dirname(base), "assets", *parts),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    # 即使文件不存在也返回最后一个候选路径；调用方会检查
    return candidates[-1]


def load_font(size, font_name=FONT_BOLD):
    """加载打包的 TrueType/OpenType 字体。"""
    font_path = resource_path("fonts", font_name)
    if os.path.exists(font_path):
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            pass
    # 回退到 Roboto 字体
    font_path = resource_path("fonts", FONT_ROBOTO_BLACK)
    if os.path.exists(font_path):
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            pass
    return ImageFont.load_default()


# 系统字体回退路径（macOS）
_FALLBACK_FONT_PATHS = [
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Helvetica.ttc",
]


def load_system_font(size):
    """加载系统字体作为回退。"""
    for fp in _FALLBACK_FONT_PATHS:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()


def load_font_for_text(size, text, font_name=FONT_BOLD):
    """加载能够实际渲染指定文本的字体。
    对于已知存在占位符字形的字符使用特定字体回退。
    TH 的 ฿、PH 的 ₱、VN 的 ₫ 符号优先使用 Inter-Bold 字体。
    """
    # TH/PH/VN 货币符号使用项目中的 Inter-Bold 字体
    if "฿" in text or "₱" in text or "₫" in text:
        inter_path = resource_path("fonts", FONT_INTER_BOLD)
        if os.path.exists(inter_path):
            try:
                return ImageFont.truetype(inter_path, size)
            except Exception:
                pass
        # Inter-Bold 加载失败时回退到系统字体
        return load_system_font(size)
    
    return load_font(size, font_name)


def format_currency(country, amount):
    """按国家特定的货币格式格式化金额。
    SG/MY/PH/TH 支持小数（如 $5.5），ID/VN 仅取整。
    """
    config = COUNTRY_CONFIG[country]
    separator = config["separator"]
    prefix = config["prefix"]
    suffix = config["suffix"]
    threshold_rb = config["threshold_rb"]
    allow_decimal = config["decimal"]

    if allow_decimal and amount != int(amount):
        # 支持小数：保留原始精度，去除末尾无效零
        val_str = str(amount).rstrip('0').rstrip('.')
    else:
        # 取整：四舍五入到整数
        val_int = round(amount)
        val_str = str(val_int)

    # 添加千位分隔符（仅对整数部分）
    if "." in val_str:
        int_part, dec_part = val_str.split(".")
        int_part_fmt = "{:,.0f}".format(int(int_part))
        if separator == ".":
            int_part_fmt = int_part_fmt.replace(",", ".")
        val_str = f"{int_part_fmt}.{dec_part}"
    else:
        val_str = "{:,.0f}".format(int(val_str))
        if separator == ".":
            val_str = val_str.replace(",", ".")

    # 处理基于阈值的格式化（如印尼 Rp 15rb）
    if threshold_rb and round(amount) >= threshold_rb:
        val_int = round(amount)
        rb_val = val_int // 1000
        remainder = val_int % 1000
        if remainder == 0:
            val_str = f"{rb_val}rb"
        else:
            val_str = f"{rb_val}.{remainder // 100}rb"

    if prefix:
        return f"{prefix}{val_str}"
    else:
        return f"{val_str}{suffix}"


def nine_patch_resize(img, target_w, target_h, base_corner=45):
    """
    9-patch 缩放：拉伸中心区域，四角等比缩放。
    base_corner 为原始模板（260x260）中四角的保留尺寸，
    输出放大时四角按相同比例同步放大，保持视觉比例一致。
    例如：base_corner=45，输出 2x 时四角变为 90px。
    """
    orig_w, orig_h = img.size

    # 计算缩放比例
    scale_x = target_w / orig_w
    scale_y = target_h / orig_h

    # 原始图像上的裁剪边界
    sx_start = base_corner
    sx_end = orig_w - base_corner
    sy_start = base_corner
    sy_end = orig_h - base_corner

    # 目标四角尺寸（等比缩放）
    corner_w = int(base_corner * scale_x)
    corner_h = int(base_corner * scale_y)

    # 目标中心可拉伸区域尺寸
    mid_w = target_w - 2 * corner_w
    mid_h = target_h - 2 * corner_h
    if mid_w < 1:
        mid_w = 1
    if mid_h < 1:
        mid_h = 1

    # 裁剪 9 个区域
    top_left = img.crop((0, 0, sx_start, sy_start))
    top_mid = img.crop((sx_start, 0, sx_end, sy_start))
    top_right = img.crop((sx_end, 0, orig_w, sy_start))

    mid_left = img.crop((0, sy_start, sx_start, sy_end))
    mid_center = img.crop((sx_start, sy_start, sx_end, sy_end))
    mid_right = img.crop((sx_end, sy_start, orig_w, sy_end))

    bot_left = img.crop((0, sy_end, sx_start, orig_h))
    bot_mid = img.crop((sx_start, sy_end, sx_end, orig_h))
    bot_right = img.crop((sx_end, sy_end, orig_w, orig_h))

    # 缩放所有区域：四角等比放大，边和中心拉伸填充
    top_left = top_left.resize((corner_w, corner_h), Image.LANCZOS)
    top_mid = top_mid.resize((mid_w, corner_h), Image.LANCZOS)
    top_right = top_right.resize((corner_w, corner_h), Image.LANCZOS)

    mid_left = mid_left.resize((corner_w, mid_h), Image.LANCZOS)
    mid_center = mid_center.resize((mid_w, mid_h), Image.LANCZOS)
    mid_right = mid_right.resize((corner_w, mid_h), Image.LANCZOS)

    bot_left = bot_left.resize((corner_w, corner_h), Image.LANCZOS)
    bot_mid = bot_mid.resize((mid_w, corner_h), Image.LANCZOS)
    bot_right = bot_right.resize((corner_w, corner_h), Image.LANCZOS)

    # 合成最终图像
    new_img = Image.new("RGBA", (target_w, target_h))
    new_img.paste(top_left, (0, 0))
    new_img.paste(top_mid, (corner_w, 0))
    new_img.paste(top_right, (corner_w + mid_w, 0))

    new_img.paste(mid_left, (0, corner_h))
    new_img.paste(mid_center, (corner_w, corner_h))
    new_img.paste(mid_right, (corner_w + mid_w, corner_h))

    new_img.paste(bot_left, (0, corner_h + mid_h))
    new_img.paste(bot_mid, (corner_w, corner_h + mid_h))
    new_img.paste(bot_right, (corner_w + mid_w, corner_h + mid_h))

    return new_img


def get_text_bbox(draw, text, font):
    """获取文字的边界框。"""
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def wrap_text_to_width(draw, text, font, max_width):
    """按最大宽度对英文文本进行自动换行（按空格分词）。"""
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        if current_line:
            test_line = f"{current_line} {word}"
        else:
            test_line = word
        w, _ = get_text_bbox(draw, test_line, font)
        if w <= max_width or not current_line:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)
    return lines


def generate_coupon(country, amount, width, height, padding=0, save=True,
                    template_type=TEMPLATE_LAZCASH, threshold=0, cap=0):
    """
    生成 Lazada 现金券图片。

    参数:
        country: 国家代码（MY, TH, ID, PH, SG, VN）
        amount: 优惠金额（数值）
        width: 输出宽度，单位像素
        height: 输出高度，单位像素
        padding: 四周留白宽度（像素），默认 0
        save: 是否保存到磁盘，默认 True
              - True：生成图片并保存到桌面，返回文件路径（原有行为）
              - False：仅生成图片，不写磁盘，直接返回 PIL Image 对象（用于预览）
        template_type: 模板类型，默认 "lazcash"，可选 "pdv"
        threshold: 消费门槛金额（PDV 模板显示 Min.spend），默认 0 不显示
        cap: 优惠上限金额（PDV 模板预留），默认 0 不显示

    返回:
        save=True 时返回保存的图片路径（str）
        save=False 时返回 PIL Image 对象
    """
    # 统一模板类型标识符
    template_type = template_type.lower().strip()
    if template_type not in TEMPLATE_FILES:
        template_type = TEMPLATE_LAZCASH
    # 留白向内收缩：clamp padding 到合理范围，确保内容区至少保留 1px
    # 最大允许 padding = min(width, height) // 2 - 1
    max_padding = min(width, height) // 2 - 1
    padding = max(0, min(padding, max_padding))

    # 内容区尺寸 = 用户设定尺寸 - 两侧留白；当 padding=0 时与原来完全一致
    content_w = width - 2 * padding
    content_h = height - 2 * padding

    # 加载模板（根据模板类型选择对应背景图）
    template_path = resource_path("templates", TEMPLATE_FILES[template_type])
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template not found: {template_path}")

    base_img = Image.open(template_path).convert("RGBA")

    # 使用 9-patch 缩放模板到内容区尺寸（而非完整画布尺寸）
    bg_img = nine_patch_resize(base_img, content_w, content_h)

    draw = ImageDraw.Draw(bg_img)

    # 加载 Logo（PDV 模板不展示 Logo，仅 LazCash 需要加载）
    logo_img = None
    if template_type == TEMPLATE_LAZCASH:
        logo_path = resource_path("logos", f"logo_{country}.png")
        if not os.path.exists(logo_path):
            raise FileNotFoundError(f"Logo not found: {logo_path}")
        logo_img = Image.open(logo_path).convert("RGBA")

    # 基于内容区尺寸与基础模板的比例计算缩放系数（留白不参与内容缩放）
    scale_c = min(content_w / BASE_TEMPLATE_W, content_h / BASE_TEMPLATE_H)

    # === PDV 券类型文字 ===
    # 在内容区顶部固定区域绘制 "Platform Voucher"，支持自动换行
    if template_type == TEMPLATE_PDV:
        pdv_vt_fs = max(int(PDV_VOUCHER_TYPE_BASE_FS * scale_c), 20)
        pdv_vt_font = load_font(pdv_vt_fs, PDV_VOUCHER_TYPE_FONT)
        pdv_vt_box_w = int(PDV_VOUCHER_TYPE_BOX_W * scale_c)
        pdv_vt_box_h = int(PDV_VOUCHER_TYPE_BOX_H * scale_c)
        pdv_vt_top = int(PDV_VOUCHER_TYPE_TOP * scale_c)

        # 自动换行，确保每行宽度不超过券类型区域宽度
        lines = wrap_text_to_width(draw, PDV_VOUCHER_TYPE_TEXT, pdv_vt_font, pdv_vt_box_w)
        line_height = int(PDV_VOUCHER_TYPE_LINE_H * scale_c)
        total_text_h = len(lines) * line_height

        # 垂直居中于 72px 高的券类型区域
        vt_start_y = pdv_vt_top + (pdv_vt_box_h - total_text_h) // 2
        vt_x = (content_w - pdv_vt_box_w) // 2

        for i, line in enumerate(lines):
            lw, _ = get_text_bbox(draw, line, pdv_vt_font)
            line_y = vt_start_y + i * line_height
            # 每行在 150px 宽度内水平居中
            draw.text((vt_x + (pdv_vt_box_w - lw) // 2, line_y), line,
                      font=pdv_vt_font, fill=PDV_VOUCHER_TYPE_COLOR)

    # === 标题文字 ===
    title_text = "LazCash"

    # === 货币字符串 ===
    currency_str = format_currency(country, amount)

    # === 布局计算 ===
    # A 组：Logo + 标题（水平排列）
    # B 组：金额（货币符号 + 数字）

    # 计算基础比例下的元素尺寸（等比缩放）
    final_logo_h = int(BASE_LOGO_H * scale_c)        # Logo 高度
    final_title_h = int(BASE_TITLE_H * scale_c)      # 标题文字高度
    final_gap_lt = int(BASE_GAP_LT * scale_c)        # Logo 与标题的水平间距
    final_group_a_h = int(BASE_GROUP_A_H * scale_c)  # A 组整体高度
    if template_type == TEMPLATE_LAZCASH:
        final_gap_ab = int(LAZCASH_GAP_AB * scale_c)  # LazCash 减小 A-B 间距，避免金额下方空隙过大
    else:
        final_gap_ab = int(BASE_GAP_AB * scale_c)     # PDV 保持默认 A-B 间距

    # 金额字号自适应：尝试将金额适配到有效内容区 80% 宽度内
    if template_type == TEMPLATE_PDV:
        # PDV 模板 260x260 下有效内容宽度为 200px，金额占满有效内容区宽度
        target_amt_w = int(content_w * PDV_USABLE_RATIO * 1.0)
    else:
        target_amt_w = int(content_w * 0.80)         # LazCash 使用完整内容区宽度
    amount_conf = AMOUNT_CONFIG[template_type]
    best_num_fs = int(amount_conf["default_num_fs"] * scale_c)  # 数字字号初始值
    best_sym_fs = int(amount_conf["default_sym_fs"] * scale_c)  # 符号字号初始值

    # 二分查找最佳字号：在 [20*scale, 120*scale] 范围内搜索
    low_fs = int(20 * scale_c)
    high_fs = int(120 * scale_c)

    font_num = None
    font_sym = None
    sym_w = 0     # 符号宽度
    sym_h = 0     # 符号高度
    num_w = 0     # 数字宽度
    num_h = 0     # 数字高度

    for _ in range(20):
        mid_fs = (low_fs + high_fs) // 2
        sym_fs = int(mid_fs * 0.7)                    # 符号字号 = 数字字号 × 0.7

        font_n = load_font(mid_fs, FONT_BOLD)

        # 将货币字符串拆分为符号(prefix/suffix)和数字两部分
        config = COUNTRY_CONFIG[country]
        prefix = config["prefix"]
        suffix = config["suffix"]
        if prefix and currency_str.startswith(prefix):
            symbol_str = prefix
            number_str = currency_str[len(prefix):]
        elif suffix and currency_str.endswith(suffix):
            symbol_str = suffix
            number_str = currency_str[:-len(suffix)]
        else:
            symbol_str = ""
            number_str = currency_str

        # 数字使用 EuclidCircularA-Bold，符号使用对应回退字体
        font_s = load_font_for_text(sym_fs, symbol_str, FONT_BOLD) if symbol_str else font_n

        # 测量当前字号下符号和数字的像素尺寸
        sw, sh = get_text_bbox(draw, symbol_str, font_s) if symbol_str else (0, 0)
        nw, nh = get_text_bbox(draw, number_str, font_n)

        # 计算总宽度 = 符号宽 + 数字宽 + 间距
        total_w = sw + nw + int(4 * scale_c)

        if total_w <= target_amt_w:
            # 总宽未超限：接受此字号，尝试更大
            best_num_fs = mid_fs
            best_sym_fs = sym_fs
            font_num = font_n
            font_sym = font_s
            sym_w, sym_h = sw, sh
            num_w, num_h = nw, nh
            low_fs = mid_fs + 1
        else:
            # 总宽超限：需要缩小字号
            high_fs = mid_fs - 1

    # 二分查找无结果时的回退：使用初始字号
    if font_num is None:
        font_num = load_font(best_num_fs, FONT_BOLD)
        config = COUNTRY_CONFIG[country]
        prefix = config["prefix"]
        suffix = config["suffix"]
        if prefix and currency_str.startswith(prefix):
            symbol_str = prefix
            number_str = currency_str[len(prefix):]
        elif suffix and currency_str.endswith(suffix):
            symbol_str = suffix
            number_str = currency_str[:-len(suffix)]
        else:
            symbol_str = ""
            number_str = currency_str
        font_sym = load_font_for_text(best_sym_fs, symbol_str, FONT_BOLD) if symbol_str else font_num
        sym_w, sym_h = get_text_bbox(draw, symbol_str, font_sym) if symbol_str else (0, 0)
        num_w, num_h = get_text_bbox(draw, number_str, font_num)

    # 确保字体能够实际渲染这些字符（特殊货币符号可能需要回退到系统字体）
    font_num = load_font_for_text(best_num_fs, number_str, FONT_BOLD)
    if symbol_str:
        font_sym = load_font_for_text(best_sym_fs, symbol_str, FONT_BOLD)
    else:
        font_sym = font_num
    # 用回退字体重新测量尺寸
    sym_w, sym_h = get_text_bbox(draw, symbol_str, font_sym) if symbol_str else (0, 0)
    num_w, num_h = get_text_bbox(draw, number_str, font_num)

    # 获取数字和符号的上方空白（textbbox 上边界偏移）
    # 绘制原点 ≠ 可见像素起点，上方空白导致视觉间距比代码间距大
    num_bbox_full = draw.textbbox((0, 0), number_str, font=font_num)
    num_top_offset = num_bbox_full[1]   # 数字上方空白偏移
    num_bot_offset = num_bbox_full[3]   # 数字底部偏移（用于基线对齐）
    if symbol_str:
        sym_bbox_full = draw.textbbox((0, 0), symbol_str, font=font_sym)
        sym_top_offset = sym_bbox_full[1]   # 符号上方空白偏移
        sym_bot_offset = sym_bbox_full[3]   # 符号底部偏移（用于基线对齐）
    else:
        sym_top_offset = 0
        sym_bot_offset = 0

    # B 组可见高度 = max(符号可见高度, 数字可见高度)
    # 可见高度 = textbbox 高度（已扣除上下空白）
    final_group_b_h = max(num_h, sym_h)

    # 总内容高度 = A 组高度 + A-B间距 + B 组高度
    total_c_h_final = (final_group_a_h + final_gap_ab + final_group_b_h)

    # 垂直居中：起始 y = (内容区高度 - 总内容高度) / 2（基于内容区而非完整画布）
    start_y = (content_h - total_c_h_final) // 2

    # === 绘制 Logo ===
    # LazCash 模板显示 Logo；PDV 模板不展示 Logo
    if template_type == TEMPLATE_LAZCASH and logo_img is not None:
        # 按目标高度等比缩放 Logo 图片
        logo_resized = logo_img.resize((final_logo_h, final_logo_h), Image.LANCZOS)
        logo_aspect = logo_resized.width / logo_resized.height   # 保持原始宽高比
        logo_w_def = int(final_logo_h * logo_aspect)              # 按宽高比计算实际宽度
        logo_resized = logo_img.resize((logo_w_def, final_logo_h), Image.LANCZOS)

        logo_x = int(content_w * 0.12)   # Logo 水平位置：内容区左侧 12% 处
        logo_y = start_y             # Logo 垂直位置：与内容区顶部对齐

        # 透明通道粘贴 Logo（保留圆角等透明区域）
        bg_img.paste(logo_resized, (logo_x, logo_y), logo_resized)

    # === 绘制标题 ===
    # LazCash 模板显示 "LazCash" 标题；PDV 模板使用顶部券类型文字，不显示此标题
    if template_type == TEMPLATE_LAZCASH:
        title_font_size = max(int(30 * scale_c), 20)              # 标题字号，最小 20px
        title_font = load_font(title_font_size, FONT_BOLD)
        tw, th = get_text_bbox(draw, title_text, title_font)       # 测量标题文字尺寸

        title_x = logo_x + logo_w_def + final_gap_lt              # 标题 x = Logo右边 + 间距
        title_y = logo_y + (final_logo_h - th) // 2               # 标题 y = Logo垂直居中

        draw.text((title_x, title_y), title_text, font=title_font, fill=COLOR_TITLE)

    # === 金额区域计算 ===
    if template_type == TEMPLATE_PDV:
        # PDV：金额位于券类型区域正下方，整体组会进一步垂直居中
        pdv_vt_box_h_scaled = int(PDV_VOUCHER_TYPE_BOX_H * scale_c)
        pdv_vt_top_scaled = int(PDV_VOUCHER_TYPE_TOP * scale_c)
        amount_y = pdv_vt_top_scaled + pdv_vt_box_h_scaled - num_top_offset
    else:
        # LazCash：金额区域顶部 y = 内容起始 y + A 组高度 + A-B 间距
        # 减去数字上方空白(num_top_offset)，使视觉间距严格等于 gap_ab
        amount_y = start_y + final_group_a_h + final_gap_ab - num_top_offset

    # 金额总宽度 = 符号宽度 + 数字宽度 + 间距
    total_amt_w = sym_w + num_w + int(4 * scale_c)
    # 金额水平居中：起始 x = (内容区宽度 - 总宽度) / 2（基于内容区而非完整画布）
    amt_x = (content_w - total_amt_w) // 2

    # 拆分货币字符串为符号和数字
    config = COUNTRY_CONFIG[country]
    prefix = config["prefix"]
    suffix = config["suffix"]
    if prefix and currency_str.startswith(prefix):
        symbol_str = prefix
        number_str = currency_str[len(prefix):]
    elif suffix and currency_str.endswith(suffix):
        symbol_str = suffix
        number_str = currency_str[:-len(suffix)]
    else:
        symbol_str = ""
        number_str = currency_str

    # 判断符号位置（前缀还是后缀）
    is_prefix = prefix and currency_str.startswith(prefix)
    is_suffix = suffix and currency_str.endswith(suffix)

    # 基线对齐：复用之前计算的底部偏移（num_bot_offset / sym_bot_offset）
    # 选取数字的基线为基准，调整符号的 y 坐标使两者底部对齐

    # 获取当前模板类型的金额颜色
    amount_color = AMOUNT_CONFIG[template_type]["color"]

    # === PDV 消费门槛文字 ===
    # 位于金额区域下方，threshold > 0 时显示 "Min.spend {金额}"
    # 当 cap > 0 时追加 ", Cap {货币}{上限金额}"
    # Min.spend 与 Cap 共用 200px 宽度（260x260 基准），超出自动换行
    ms_lines = None
    ms_font = None
    ms_fs = 0
    ms_total_h = 0
    ms_top_offset = 0
    ms_start_y = 0
    ms_x = 0
    min_spend_top_gap = 0
    if template_type == TEMPLATE_PDV and threshold > 0:
        min_spend_text = f"Min.spend {format_currency(country, threshold)}"
        if cap > 0:
            min_spend_text += f", Cap {format_currency(country, cap)}"
        # Min.spend 最大宽度按 PDV 有效内容区计算（260x260 下为 200px）
        min_spend_max_w = int(content_w * PDV_USABLE_RATIO)
        min_spend_top_gap = int(PDV_MINSPEND_TOP_GAP * scale_c)

        # 优先尝试一行显示：先基准字号 26px，再缩小为 22px；仍放不下再换行
        base_fs = max(int(PDV_MINSPEND_BASE_FS * scale_c), 16)
        small_fs = max(int(PDV_MINSPEND_SMALL_FS * scale_c), 14)

        ms_lines = None
        for fs in [base_fs, small_fs]:
            # PH/VN/TH 使用 Inter-Regular，其他区域使用 EuclidCircularA-Medium
            if country in ("PH", "VN", "TH"):
                ms_font = load_font(fs, FONT_INTER_REGULAR)
            else:
                ms_font = load_font(fs, PDV_MINSPEND_FONT)
            text_w, _ = get_text_bbox(draw, min_spend_text, ms_font)
            # 允许 10px 容差，避免字体度量/字距导致临界值换行
            if text_w <= min_spend_max_w + int(10 * scale_c):
                ms_lines = [min_spend_text]
                ms_fs = fs
                break

        if ms_lines is None:
            # 仍放不下则换行，强制最多 2 行
            if country in ("PH", "VN", "TH"):
                ms_font = load_font(small_fs, FONT_INTER_REGULAR)
            else:
                ms_font = load_font(small_fs, PDV_MINSPEND_FONT)
            ms_lines = wrap_text_to_width(draw, min_spend_text, ms_font, min_spend_max_w)
            ms_fs = small_fs

        # 强制 Min.spend 最多 2 行：超过则逐级缩小字号，最小到 12px
        min_ms_fs = max(int(12 * scale_c), 10)
        while len(ms_lines) > 2 and ms_fs > min_ms_fs:
            ms_fs -= 1
            if country in ("PH", "VN", "TH"):
                ms_font = load_font(ms_fs, FONT_INTER_REGULAR)
            else:
                ms_font = load_font(ms_fs, PDV_MINSPEND_FONT)
            ms_lines = wrap_text_to_width(draw, min_spend_text, ms_font, min_spend_max_w)

        # 如果缩到最小仍超过 2 行，只保留前两行（极端情况兜底）
        if len(ms_lines) > 2:
            ms_lines = ms_lines[:2]

        ms_line_h = int(ms_fs * 1.2)
        ms_total_h = len(ms_lines) * ms_line_h

        # 水平居中
        ms_x = (content_w - min_spend_max_w) // 2
        # 初始位于金额可见底部下方（后续会随整体组一起垂直居中）
        ms_start_y = amount_y + num_top_offset + num_h + min_spend_top_gap

        # 计算 Min.spend 文字上方空白，用于精确计算组高度
        ms_bbox_full = draw.textbbox((0, 0), ms_lines[0], font=ms_font)
        ms_top_offset = ms_bbox_full[1]

    # === PDV 金额+消费门槛整体组垂直居中 ===
    # 将金额与 Min.spend 视为一个整体，在券类型下方的空间中垂直水平居中
    if template_type == TEMPLATE_PDV:
        pdv_vt_box_h_scaled = int(PDV_VOUCHER_TYPE_BOX_H * scale_c)
        pdv_vt_top_scaled = int(PDV_VOUCHER_TYPE_TOP * scale_c)
        pdv_vt_bottom = pdv_vt_top_scaled + pdv_vt_box_h_scaled

        group_top = amount_y + num_top_offset
        if threshold > 0:
            group_bottom = ms_start_y + ms_top_offset + ms_total_h
        else:
            group_bottom = amount_y + num_top_offset + final_group_b_h
        group_height = group_bottom - group_top

        available_below = content_h - pdv_vt_bottom
        # 组合组上下各预留 5px 间距（基于 260×260 模板）
        group_padding = int(5 * scale_c)
        max_group_height = int(available_below * 0.95)

        # 组合组高度上限：不超过券类型下方可用空间的 95%
        if group_height > max_group_height - 2 * group_padding:
            v_scale = (max_group_height - 2 * group_padding) / group_height

            # 按比例缩小金额字号
            new_num_fs = max(int(best_num_fs * v_scale), 20)
            new_sym_fs = max(int(best_sym_fs * v_scale), 14)
            font_num = load_font_for_text(new_num_fs, number_str, FONT_BOLD)
            if symbol_str:
                font_sym = load_font_for_text(new_sym_fs, symbol_str, FONT_BOLD)
            else:
                font_sym = font_num
            num_w, num_h = get_text_bbox(draw, number_str, font_num)
            sym_w, sym_h = get_text_bbox(draw, symbol_str, font_sym) if symbol_str else (0, 0)
            final_group_b_h = max(num_h, sym_h)
            num_bbox_full = draw.textbbox((0, 0), number_str, font=font_num)
            num_top_offset = num_bbox_full[1]
            num_bot_offset = num_bbox_full[3]
            if symbol_str:
                sym_bbox_full = draw.textbbox((0, 0), symbol_str, font=font_sym)
                sym_top_offset = sym_bbox_full[1]
                sym_bot_offset = sym_bbox_full[3]
            else:
                sym_top_offset = 0
                sym_bot_offset = 0

            # 重新计算金额水平居中位置
            total_amt_w = sym_w + num_w + int(4 * scale_c)
            amt_x = (content_w - total_amt_w) // 2

            # 按比例缩小 Min.spend 字号
            if threshold > 0:
                new_ms_fs = max(int(ms_fs * v_scale), 12)
                if country in ("PH", "VN", "TH"):
                    ms_font = load_font(new_ms_fs, FONT_INTER_REGULAR)
                else:
                    ms_font = load_font(new_ms_fs, PDV_MINSPEND_FONT)
                ms_fs = new_ms_fs
                ms_line_h = int(ms_fs * 1.2)
                ms_lines = wrap_text_to_width(draw, min_spend_text, ms_font, min_spend_max_w)
                ms_total_h = len(ms_lines) * ms_line_h
                ms_bbox_full = draw.textbbox((0, 0), ms_lines[0], font=ms_font)
                ms_top_offset = ms_bbox_full[1]
                # 重新定位 Min.spend 起点
                ms_start_y = amount_y + num_top_offset + num_h + min_spend_top_gap

            # 重新计算组合组高度
            group_top = amount_y + num_top_offset
            if threshold > 0:
                group_bottom = ms_start_y + ms_top_offset + ms_total_h
            else:
                group_bottom = amount_y + num_top_offset + final_group_b_h
            group_height = group_bottom - group_top

        # 在组合组真实高度基础上加上下间距，再进行垂直居中
        padded_height = group_height + 2 * group_padding
        desired_padded_top = pdv_vt_bottom + (available_below - padded_height) // 2
        desired_group_top = desired_padded_top + group_padding
        offset = int(desired_group_top - group_top)

        amount_y += offset
        if threshold > 0:
            ms_start_y += offset

    # === 绘制金额 ===
    if symbol_str:
        # 数字 y 坐标：直接使用金额区域顶部（无上方空白）
        y_num = amount_y
        if country == "MY":
            # MY 使用中线对齐（垂直居中）：符号中心与数字中心对齐
            y_sym = amount_y + num_top_offset + (num_h - sym_h) // 2 - sym_top_offset
        else:
            # 其他区域保持基线对齐（底部对齐）
            y_sym = amount_y + num_bot_offset - sym_bot_offset

        if is_prefix:
            # 前缀模式：先画符号，再画数字
            draw.text((amt_x, y_sym), symbol_str, font=font_sym, fill=amount_color)
            amt_x += sym_w + int(4 * scale_c)
            draw.text((amt_x, y_num), number_str, font=font_num, fill=amount_color)
        elif is_suffix:
            # 后缀模式：先画数字，再画符号
            draw.text((amt_x, y_num), number_str, font=font_num, fill=amount_color)
            amt_x += num_w + int(4 * scale_c)
            draw.text((amt_x, y_sym), symbol_str, font=font_sym, fill=amount_color)
    else:
        # 无符号：只画数字
        y_num = amount_y
        draw.text((amt_x, y_num), number_str, font=font_num, fill=amount_color)

    # === 绘制 PDV 消费门槛文字 ===
    if template_type == TEMPLATE_PDV and threshold > 0:
        for i, line in enumerate(ms_lines):
            lw, _ = get_text_bbox(draw, line, ms_font)
            line_y = ms_start_y + i * ms_line_h
            draw.text((ms_x + (min_spend_max_w - lw) // 2, line_y), line,
                      font=ms_font, fill=PDV_MINSPEND_COLOR)

    # 四周留白（向内收缩）：当 padding > 0 时，创建与用户设定尺寸相同的透明画布，
    # 将内容区图像粘贴到 (padding, padding) 偏移位置，四周边缘保持完全透明（RGBA=(0,0,0,0)）。
    # 最终输出尺寸严格等于 width × height，不会超出用户设定值。
    if padding > 0:
        padded_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        padded_img.paste(bg_img, (padding, padding))
        bg_img = padded_img

    # save=False：仅返回 PIL Image 对象，不写磁盘（用于实时预览，避免产生文件）
    if not save:
        return bg_img

    # === 保存到磁盘 ===
    output_dir = os.path.expanduser("~/Desktop")
    os.makedirs(output_dir, exist_ok=True)

    safe_country = country
    val_clean = str(amount).replace(".", "_")
    template_suffix = "pdv" if template_type == TEMPLATE_PDV else "cash"
    filename = f"coupon_{safe_country}_{val_clean}_{template_suffix}.png"
    output_path = os.path.join(output_dir, filename)

    bg_img.save(output_path, "PNG")
    print(f"Generated: {output_path}")
    return output_path


if __name__ == "__main__":
    # 测试
    for c in ["MY", "TH", "ID", "PH", "SG", "VN"]:
        path = generate_coupon(c, 15, 800, 600)
        print(path)

    # PDV 模板测试
    pdv_path = generate_coupon("SG", 10, 260, 260, template_type=TEMPLATE_PDV, threshold=30)
    print(pdv_path)

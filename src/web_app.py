"""
网页版现金券生成器
基于 Flask 提供 Web 服务，复用 generate.py 图像生成引擎。
支持浏览器访问，跨平台（macOS/Windows/手机）无需安装。
"""

import os
import sys
import io
import base64
from datetime import datetime

from flask import Flask, render_template, request, jsonify

# 将项目 src 目录加入路径，确保能导入 generate
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate import generate_coupon, TEMPLATE_LAZCASH, TEMPLATE_PDV

app = Flask(__name__, template_folder="templates")

# 国家列表
COUNTRIES = ["MY", "TH", "ID", "PH", "SG", "VN"]

# 模板列表
TEMPLATES = [
    {"value": TEMPLATE_LAZCASH, "label": "LazCash"},
    {"value": TEMPLATE_PDV, "label": "PDV (Platform Voucher)"},
]


@app.route("/")
def index():
    """渲染主页。"""
    return render_template(
        "index.html",
        countries=COUNTRIES,
        templates=TEMPLATES,
        default_width=260,
        default_height=260,
    )


@app.route("/api/generate", methods=["POST"])
def api_generate():
    """接收前端参数，生成现金券图片并返回 base64。"""
    try:
        data = request.get_json() or {}

        country = data.get("country", "MY").upper()
        if country not in COUNTRIES:
            return jsonify({"error": f"不支持的国家: {country}"}), 400

        amount = float(data.get("amount", 0))
        width = int(data.get("width", 260))
        height = int(data.get("height", 260))
        padding = int(data.get("padding", 0))
        template_type = data.get("template_type", TEMPLATE_LAZCASH).lower()
        threshold = float(data.get("threshold", 0) or 0)
        cap = float(data.get("cap", 0) or 0)

        if width < 50 or height < 50:
            return jsonify({"error": "宽高至少 50 像素"}), 400
        if amount < 0:
            return jsonify({"error": "金额不能为负数"}), 400

        # 生成图片（不保存磁盘，直接返回内存对象）
        img = generate_coupon(
            country=country,
            amount=amount,
            width=width,
            height=height,
            padding=padding,
            save=False,
            template_type=template_type,
            threshold=threshold,
            cap=cap,
        )

        # 转为 base64 PNG
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        img_b64 = base64.b64encode(buf.read()).decode("utf-8")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"cash_{country}_{amount}_{template_type}_{timestamp}.png"

        return jsonify({
            "success": True,
            "image": f"data:image/png;base64,{img_b64}",
            "filename": filename,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # 默认监听 0.0.0.0，方便同一局域网其他设备访问
    app.run(host="0.0.0.0", port=8080, debug=False)

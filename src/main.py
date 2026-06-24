#!/usr/bin/env python3
"""
程序入口
自动检测运行模式：无参数时启动 PyQt5 GUI（app.py），带 --amount 等 CLI 参数时
进入命令行模式调用 generate.py 引擎生成现金券图片。
"""

import sys
import os
import argparse

# 确保 src 目录在 Python 搜索路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import REGIONS, OUTPUT_DIR
from src.generate import generate_coupon, COUNTRY_CONFIG


def run_cli():
    """命令行模式运行函数。"""
    parser = argparse.ArgumentParser(
        description="生成电商现金券/代金券图片",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --amount 15 --region SG
  python main.py --amount 50 --region MY --width 500 --height 500
  python main.py --amount 100 --region ID --output ~/Desktop/voucher.png
        """
    )
    
    parser.add_argument(
        "--amount", "-a",
        type=int,
        default=None,
        help="优惠金额（数值）"
    )
    parser.add_argument(
        "--region", "-r",
        choices=list(COUNTRY_CONFIG.keys()),
        default="SG",
        help="区域代码（默认: SG）"
    )
    parser.add_argument(
        "--width", "-W",
        type=int,
        default=260,
        help="输出图片宽度，单位像素（默认: 260）"
    )
    parser.add_argument(
        "--height", "-H",
        type=int,
        default=260,
        help="输出图片高度，单位像素（默认: 260）"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="输出文件路径（默认: 自动生成）"
    )
    parser.add_argument(
        "--list-regions",
        action="store_true",
        help="列出可用区域并退出"
    )
    
    args = parser.parse_args()
    
    if args.list_regions:
        print("可用区域:")
        for code, info in COUNTRY_CONFIG.items():
            print(f"  {code:3} - Currency: {info['currency']}")
        return

    if args.amount is None:
        parser.error("未使用 --list-regions 时 --amount 为必填项")
    
    # 使用引擎1（generate.py）生成图片
    output_file = generate_coupon(args.region, args.amount, args.width, args.height)
    
    # 如指定了自定义输出路径则移动文件
    if args.output and args.output != output_file:
        import shutil
        output_dir = os.path.dirname(args.output)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        shutil.move(output_file, args.output)
        output_file = args.output
    
    print(f"Generated: {output_file}")


def run_gui():
    """GUI 模式运行函数。"""
    from src.app import main as app_main
    app_main()


def main():
    """主入口函数 — 自动检测 CLI 或 GUI 模式。"""
    # 检查是否存在 CLI 参数（忽略 PyInstaller 内部参数）
    cli_args = [a for a in sys.argv[1:] if not a.startswith(("-psn_", "-NS"))]
    # 窗口化模式（macOS .app）下，除非明确传入 CLI 参数，否则默认启动 GUI
    if cli_args and any(a.startswith("-") for a in cli_args):
        run_cli()
    elif cli_args:
        # 有非标志参数但无 --amount，仍启动 GUI 以确保安全
        run_gui()
    else:
        run_gui()


if __name__ == "__main__":
    main()

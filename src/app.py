#!/usr/bin/env python3
"""
PyQt5 图形用户界面
基于 PyQt5 构建的主窗口，提供模板选择、国家选择、金额/宽高输入、
实时预览及生成保存等交互控件，调用 generate.py 引擎生成现金券图片。
支持热更新（HOT_RELOAD）。
"""

import io
import os
import sys
import importlib
import queue
import signal

# 确保父目录在 Python 搜索路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QLineEdit, QPushButton, QMessageBox, QFormLayout
)
from PyQt5.QtCore import Qt, QTimer, QByteArray
from PyQt5.QtGui import QFont, QPixmap, QIntValidator, QDoubleValidator

import src.generate as generate
from src.hot_reload import HotReloader

# 跨模块重载保留的全局引用
_current_window = globals().get('_current_window')
_qt_app = globals().get('_qt_app')

# 模板类型显示名称 → generate.py 模板类型标识
TEMPLATE_DISPLAY_MAP = {
    "LazCash (Standard)": generate.TEMPLATE_LAZCASH,
    "PDV": generate.TEMPLATE_PDV,
}


class CouponGeneratorWindow(QMainWindow):
    """现金券生成器主窗口。"""

    def __init__(self):
        super().__init__()
        self._hot_reloader = None
        self._reload_banner_timer = None
        self._reload_queue = queue.Queue()
        self._reload_poll_timer = None
        self._preview_timer = None   # 防抖定时器，避免频繁刷新预览
        self.init_ui()
        self._start_hot_reload()
        # 初始化完成后触发一次预览
        self._schedule_preview_update()

    def init_ui(self):
        # ==========================================
        # 窗口基础设置
        # ==========================================
        self.setWindowTitle("Lazada 优惠券生成器 Pro")
        # 固定窗口大小，扩大以容纳实时预览区域
        self.setFixedSize(420, 700)

        # ==========================================
        # 中央容器与背景色
        # ==========================================
        central_widget = QWidget()
        central_widget.setStyleSheet("background-color: #ececec;")
        self.setCentralWidget(central_widget)

        # ==========================================
        # 主布局：垂直排列所有控件
        # ==========================================
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(12)
        central_widget.setLayout(main_layout)

        # ==========================================
        # 样式定义：QSS（Qt Style Sheets，类似 CSS）
        # ==========================================

        # 分组标题样式：加粗深色
        section_title_style = """
            QLabel {
                color: #1F2937;
                font-size: 14px;
                font-weight: bold;
                padding: 2px 0 4px 0;
            }
        """

        # 标签样式：黑色常规字体
        label_style = """
            QLabel {
                color: #222222;
                font-size: 13px;
                font-weight: normal;
                padding: 2px 0;
            }
        """

        # 输入框样式
        lineedit_style = """
            QLineEdit {
                background-color: #ffffff;
                color: #4B5563;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
                selection-background-color: #3B82F6;
            }
            QLineEdit:focus {
                border: 1px solid #3B82F6;
            }
        """

        # 下拉框样式：参考图蓝色按钮+白色箭头
        _arrow_icon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "assets", "icons", "arrow-down-white.svg"
        )
        combobox_style = f"""
            QComboBox {{
                background-color: #ffffff;
                color: #4B5563;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 6px 10px;
                padding-right: 36px;
                font-size: 13px;
                min-height: 20px;
            }}
            QComboBox:focus {{
                border: 1px solid #3B82F6;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 32px;
                border: none;
                border-left: 1px solid #D1D5DB;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
                background-color: #3B82F6;
            }}
            QComboBox::down-arrow {{
                image: url({_arrow_icon_path});
                width: 12px;
                height: 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: #ffffff;
                color: #4B5563;
                border: 1px solid #D1D5DB;
                border-radius: 4px;
                selection-background-color: #EFF6FF;
                selection-color: #3B82F6;
                outline: none;
                padding: 4px 0;
            }}
        """

        # ==========================================
        # 参数设置分组标题
        # ==========================================
        lbl_section_params = QLabel("参数设置")
        lbl_section_params.setStyleSheet(section_title_style)
        main_layout.addWidget(lbl_section_params)

        # ==========================================
        # 表单布局：左侧标签 + 右侧输入框
        # ==========================================
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form_layout.setFormAlignment(Qt.AlignLeft)

        # ==========================================
        # 第 1 行：模板类型下拉框
        # ==========================================
        lbl_template = QLabel("模板类型:")
        lbl_template.setStyleSheet(label_style)

        self.combo_template = QComboBox()
        self.combo_template.setStyleSheet(combobox_style)
        self.combo_template.addItems(list(TEMPLATE_DISPLAY_MAP.keys()))
        self.combo_template.setMinimumHeight(32)

        form_layout.addRow(lbl_template, self.combo_template)

        # ==========================================
        # 第 2 行：国家/地区选择器
        # ==========================================
        lbl_country = QLabel("国家/地区:")
        lbl_country.setStyleSheet(label_style)

        self.combo_country = QComboBox()
        self.combo_country.setStyleSheet(combobox_style)
        # 从配置模块读取所有国家代码并填入下拉列表
        countries = list(generate.COUNTRY_CONFIG.keys())
        self.combo_country.addItems(countries)
        self.combo_country.setCurrentIndex(0)
        self.combo_country.setMinimumHeight(32)

        form_layout.addRow(lbl_country, self.combo_country)

        # ==========================================
        # 第 3 行：金额输入
        # ==========================================
        lbl_amount = QLabel("金额:")
        lbl_amount.setStyleSheet(label_style)

        self.entry_amount = QLineEdit()
        self.entry_amount.setStyleSheet(lineedit_style)
        self.entry_amount.setText("10")
        self.entry_amount.setMinimumHeight(32)
        self.entry_amount.setValidator(QDoubleValidator(0.0, 999999.0, 2))

        form_layout.addRow(lbl_amount, self.entry_amount)

        # ==========================================
        # 第 4 行：门槛和上限（仅 PDV 模板显示）
        # 参考宽高并排布局：门槛输入 + 上限标签 + 上限输入
        # ==========================================
        self.lbl_threshold = QLabel("门槛:")
        self.lbl_threshold.setStyleSheet(label_style)
        self.lbl_threshold.setObjectName("lbl_threshold")

        self.threshold_cap_widget = QWidget()
        threshold_cap_layout = QHBoxLayout(self.threshold_cap_widget)
        threshold_cap_layout.setContentsMargins(0, 0, 0, 0)
        threshold_cap_layout.setSpacing(8)

        self.entry_threshold = QLineEdit()
        self.entry_threshold.setStyleSheet(lineedit_style)
        self.entry_threshold.setText("30")
        self.entry_threshold.setMinimumHeight(32)
        self.entry_threshold.setValidator(QIntValidator(0, 999999))
        self.entry_threshold.setObjectName("entry_threshold")
        threshold_cap_layout.addWidget(self.entry_threshold)

        self.lbl_cap = QLabel("上限:")
        self.lbl_cap.setStyleSheet(label_style)
        self.lbl_cap.setObjectName("lbl_cap")
        threshold_cap_layout.addWidget(self.lbl_cap)

        self.entry_cap = QLineEdit()
        self.entry_cap.setStyleSheet(lineedit_style)
        self.entry_cap.setText("0")
        self.entry_cap.setMinimumHeight(32)
        self.entry_cap.setValidator(QIntValidator(0, 999999))
        self.entry_cap.setObjectName("entry_cap")
        threshold_cap_layout.addWidget(self.entry_cap)

        form_layout.addRow(self.lbl_threshold, self.threshold_cap_widget)

        # 默认 LazCash 隐藏门槛/上限
        self._set_pdv_fields_visible(False)

        # ==========================================
        # 第 6 行：宽和高同一行
        # ==========================================
        lbl_wh = QLabel("宽 (px):")
        lbl_wh.setStyleSheet(label_style)

        # 用 QHBoxLayout 将宽输入框、高标签、高输入框水平排列
        wh_widget = QWidget()
        wh_layout = QHBoxLayout(wh_widget)
        wh_layout.setContentsMargins(0, 0, 0, 0)
        wh_layout.setSpacing(8)

        self.entry_width = QLineEdit()
        self.entry_width.setStyleSheet(lineedit_style)
        self.entry_width.setText("250")
        self.entry_width.setMinimumHeight(32)
        self.entry_width.setValidator(QIntValidator(1, 99999))
        wh_layout.addWidget(self.entry_width)

        lbl_h = QLabel("高 (px):")
        lbl_h.setStyleSheet(label_style)
        wh_layout.addWidget(lbl_h)

        self.entry_height = QLineEdit()
        self.entry_height.setStyleSheet(lineedit_style)
        self.entry_height.setText("250")
        self.entry_height.setMinimumHeight(32)
        self.entry_height.setValidator(QIntValidator(1, 99999))
        wh_layout.addWidget(self.entry_height)

        form_layout.addRow(lbl_wh, wh_widget)

        # ==========================================
        # 第 5 行：留白输入
        # ==========================================
        lbl_padding = QLabel("留白 (px):")
        lbl_padding.setStyleSheet(label_style)

        self.entry_padding = QLineEdit()
        self.entry_padding.setStyleSheet(lineedit_style)
        self.entry_padding.setText("0")
        self.entry_padding.setMinimumHeight(32)
        self.entry_padding.setValidator(QIntValidator(0, 9999))

        form_layout.addRow(lbl_padding, self.entry_padding)

        # 将表单布局加入主布局
        main_layout.addLayout(form_layout)

        # ==========================================
        # PDV 专属字段显隐控制
        # ==========================================
        self.combo_template.currentIndexChanged.connect(self._on_template_changed)

        # ==========================================
        # 实时预览分组标题
        # ==========================================
        lbl_section_preview = QLabel("实时预览")
        lbl_section_preview.setStyleSheet(section_title_style)
        main_layout.addWidget(lbl_section_preview)

        # ==========================================
        # 预览画布：用于显示生成的优惠券预览图
        # ==========================================
        self.lbl_preview = QLabel()
        self.lbl_preview.setAlignment(Qt.AlignCenter)
        self.lbl_preview.setMinimumHeight(250)
        self.lbl_preview.setMaximumHeight(250)
        self.lbl_preview.setStyleSheet("""
            QLabel {
                background-color: #f9f9f9;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
            }
        """)
        main_layout.addWidget(self.lbl_preview)

        # 预览区域底部小字提示
        lbl_preview_hint = QLabel("Preview 1")
        lbl_preview_hint.setAlignment(Qt.AlignCenter)
        lbl_preview_hint.setStyleSheet("""
            QLabel {
                color: #9CA3AF;
                font-size: 12px;
                padding: 0;
            }
        """)
        main_layout.addWidget(lbl_preview_hint)

        # 弹性空间，将底部按钮推到窗口底部
        main_layout.addStretch(1)

        # ==========================================
        # 底部按钮区域：强制刷新 + 生成并保存
        # ==========================================
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        # 强制刷新按钮（次要按钮：白底）
        self.btn_refresh = QPushButton("🔄 强制刷新")
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #222222;
                border: 1px solid #cccccc;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f5f5f5;
                border-color: #aaaaaa;
            }
            QPushButton:pressed {
                background-color: #e8e8e8;
                border-color: #999999;
            }
        """)
        self.btn_refresh.setMinimumHeight(40)
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        # 点击立即触发预览更新（跳过防抖延迟）
        self.btn_refresh.clicked.connect(self._update_preview)

        # 生成并保存按钮（主要按钮：蓝底）
        self.btn_generate = QPushButton("📁 生成并保存")
        self.btn_generate.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6;
                color: #ffffff;
                border: 1px solid #3B82F6;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2563EB;
                border-color: #2563EB;
            }
            QPushButton:pressed {
                background-color: #1D4ED8;
                border-color: #1D4ED8;
            }
        """)
        self.btn_generate.setMinimumHeight(40)
        self.btn_generate.setCursor(Qt.PointingHandCursor)
        self.btn_generate.clicked.connect(self.on_generate)

        btn_layout.addWidget(self.btn_refresh)
        btn_layout.addWidget(self.btn_generate)
        main_layout.addLayout(btn_layout)

        # ==========================================
        # 信号连接：参数变化时触发预览更新（防抖 300ms）
        # ==========================================
        self.combo_template.currentIndexChanged.connect(self._schedule_preview_update)
        self.combo_country.currentIndexChanged.connect(self._schedule_preview_update)
        self.entry_amount.textChanged.connect(self._schedule_preview_update)
        self.entry_threshold.textChanged.connect(self._schedule_preview_update)
        self.entry_cap.textChanged.connect(self._schedule_preview_update)
        self.entry_width.textChanged.connect(self._schedule_preview_update)
        self.entry_height.textChanged.connect(self._schedule_preview_update)
        self.entry_padding.textChanged.connect(self._schedule_preview_update)

    def _set_pdv_fields_visible(self, visible):
        """控制 PDV 专属字段（门槛、上限）的显示与隐藏。"""
        self.lbl_threshold.setVisible(visible)
        self.threshold_cap_widget.setVisible(visible)

    def _on_template_changed(self, index):
        """模板类型切换时显示/隐藏 PDV 专属字段。"""
        template_text = self.combo_template.currentText()
        is_pdv = TEMPLATE_DISPLAY_MAP.get(template_text) == generate.TEMPLATE_PDV
        self._set_pdv_fields_visible(is_pdv)
        self._schedule_preview_update()

    def _schedule_preview_update(self):
        """防抖触发预览更新：每次调用重置 300ms 定时器，避免频繁生成图片。"""
        if self._preview_timer is None:
            self._preview_timer = QTimer()
            self._preview_timer.setSingleShot(True)
            self._preview_timer.timeout.connect(self._update_preview)
        self._preview_timer.start(300)

    def _update_preview(self):
        """读取当前参数，调用生成引擎，将结果缩放后显示在预览画布上。"""
        try:
            # 读取国家代码（combo 直接存的是国家代码，如 "ID"/"MY"）
            country = self.combo_country.currentText()

            # 解析金额，非法值使用默认值 1
            try:
                amount = float(self.entry_amount.text())
                if amount <= 0:
                    amount = 1.0
            except (ValueError, TypeError):
                amount = 1.0

            # 解析宽度，非法值使用默认值 600
            try:
                width = int(self.entry_width.text())
                if width <= 0:
                    width = 600
            except (ValueError, TypeError):
                width = 600

            # 解析高度，非法值使用默认值 260
            try:
                height = int(self.entry_height.text())
                if height <= 0:
                    height = 260
            except (ValueError, TypeError):
                height = 260

            # 解析留白，非法值使用默认值 0
            try:
                padding = int(self.entry_padding.text())
                if padding < 0:
                    padding = 0
            except (ValueError, TypeError):
                padding = 0

            # 解析门槛与上限（PDV 使用，非法值默认 0）
            try:
                threshold = float(self.entry_threshold.text())
                if threshold < 0:
                    threshold = 0
            except (ValueError, TypeError):
                threshold = 0

            try:
                cap = float(self.entry_cap.text())
                if cap < 0:
                    cap = 0
            except (ValueError, TypeError):
                cap = 0

            # 解析模板类型
            template_type = TEMPLATE_DISPLAY_MAP.get(self.combo_template.currentText(), generate.TEMPLATE_LAZCASH)

            # 调用生成引擎，save=False 直接返回 PIL Image 对象，不产生任何磁盘文件
            pil_image = generate.generate_coupon(
                country, amount, width, height, padding,
                save=False, template_type=template_type,
                threshold=threshold, cap=cap
            )

            # PIL Image → PNG bytes → QByteArray → QPixmap（避免 ImageQt 兼容性问题）
            buffer = io.BytesIO()
            pil_image.save(buffer, format='PNG')
            pixmap = QPixmap()
            pixmap.loadFromData(QByteArray(buffer.getvalue()))
            if pixmap.isNull():
                self.lbl_preview.setText("预览失败\n无法加载图片")
                return

            # 按比例缩放到预览区域大小（不放大）
            preview_w = self.lbl_preview.width()
            preview_h = self.lbl_preview.height()
            img_w = pixmap.width()
            img_h = pixmap.height()
            scale = min(preview_w / img_w, preview_h / img_h, 1.0)
            new_w = int(img_w * scale)
            new_h = int(img_h * scale)
            # 使用 Qt.SmoothTransformation 实现高质量缩放
            self.lbl_preview.setPixmap(
                pixmap.scaled(new_w, new_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )

        except Exception as e:
            # 预览失败时显示错误文字，不弹窗
            self.lbl_preview.setText(f"预览失败\n{e}")

    def _start_hot_reload(self):
        """启动热更新文件监视器。
        使用线程安全的队列 + 轮询定时器将回调调度到主线程。
        """
        self._hot_reloader = HotReloader(
            on_reload_callback=lambda mod_name: self._reload_queue.put(mod_name)
        )
        self._hot_reloader.start()

        # 每 500ms 在主线程上轮询队列
        self._reload_poll_timer = QTimer()
        self._reload_poll_timer.timeout.connect(self._poll_reload_queue)
        self._reload_poll_timer.start(500)

    def _poll_reload_queue(self):
        """检查挂起的重载事件（在主线程上运行）。"""
        while not self._reload_queue.empty():
            try:
                mod_name = self._reload_queue.get_nowait()
                self._on_module_reloaded(mod_name)
            except queue.Empty:
                break

    def _on_module_reloaded(self, mod_name):
        """模块热更新完成后的回调。"""
        if mod_name == "src.app":
            # GUI 模块变更：从新类定义重建窗口
            self._recreate_window()
            return

        # 其他模块变更，仅在窗口标题短暂显示提示
        original_title = self.windowTitle().replace(" [已热更新]", "")
        self.setWindowTitle(f"{original_title} [已热更新]")

        # 2 秒后自动清除标题提示
        if self._reload_banner_timer:
            self._reload_banner_timer.stop()
        self._reload_banner_timer = QTimer()
        self._reload_banner_timer.setSingleShot(True)
        self._reload_banner_timer.timeout.connect(
            lambda: self.setWindowTitle(original_title)
        )
        self._reload_banner_timer.start(2000)

    def _recreate_window(self):
        """使用重载后的模块类定义重建窗口。"""
        global _current_window

        # 停止轮询和热更新监视器
        if self._reload_poll_timer:
            self._reload_poll_timer.stop()
            self._reload_poll_timer = None
        if self._hot_reloader:
            self._hot_reloader.stop()
            self._hot_reloader = None

        # 从重载后的模块获取新类
        app_module = sys.modules.get("src.app")
        if not app_module:
            return
        NewWindowClass = app_module.CouponGeneratorWindow

        # 关闭旧窗口
        self.close()
        self.deleteLater()

        # 使用重载后的类创建新窗口
        new_window = NewWindowClass()
        new_window.show()
        _current_window = new_window
        print("[HotReload] Window recreated from reloaded class")

    def closeEvent(self, event):
        """窗口关闭时停止热更新监视器。"""
        if self._reload_poll_timer:
            self._reload_poll_timer.stop()
        if self._hot_reloader:
            self._hot_reloader.stop()
        super().closeEvent(event)

    def on_generate(self):
        """
        生成并保存按钮点击事件处理函数：
        1. 读取用户输入的国家、金额、宽度、高度
        2. 调用 generate.generate_coupon() 生成券图（留白默认为 0）
        3. 弹出成功或错误提示框
        """
        try:
            # 从控件中读取用户输入
            country = self.combo_country.currentText()       # 当前选中的国家
            amount = float(self.entry_amount.text())         # 金额（转浮点数）
            width = int(self.entry_width.text())             # 宽度（转整数）
            height = int(self.entry_height.text())           # 高度（转整数）
            padding = int(self.entry_padding.text())         # 留白（转整数）

            # 解析门槛与上限（PDV 使用，非法值默认 0）
            try:
                threshold = float(self.entry_threshold.text())
                if threshold < 0:
                    threshold = 0
            except (ValueError, TypeError):
                threshold = 0

            try:
                cap = float(self.entry_cap.text())
                if cap < 0:
                    cap = 0
            except (ValueError, TypeError):
                cap = 0

            # 解析模板类型
            template_type = TEMPLATE_DISPLAY_MAP.get(self.combo_template.currentText(), generate.TEMPLATE_LAZCASH)

            # 调用图像生成引擎，返回输出文件路径（留白从输入框读取）
            output_file = generate.generate_coupon(
                country, amount, width, height, padding,
                template_type=template_type,
                threshold=threshold, cap=cap
            )

            # 成功弹窗提示
            QMessageBox.information(
                self,
                "成功",
                f"Cash已生成:\n{output_file}"
            )
        except ValueError:
            # 输入格式错误时弹窗（如输入了非数字字符）
            QMessageBox.critical(
                self,
                "错误",
                "请输入有效的金额数字\n宽高必须是整数"
            )
        except Exception as e:
            # 其他异常时弹窗，显示具体错误信息
            QMessageBox.critical(
                self,
                "错误",
                str(e)
            )


def main():
    """
    应用程序入口函数：
    1. 创建 QApplication 实例
    2. 设置全局字体
    3. 创建并显示主窗口
    4. 进入事件循环
    """
    global _current_window, _qt_app

    # 创建 Qt 应用对象，必须在所有 GUI 操作之前创建
    _qt_app = QApplication(sys.argv)

    # 注册信号处理：收到 SIGTERM/SIGINT 时优雅退出，避免 macOS 崩溃报告弹窗
    def _graceful_shutdown(signum, frame):
        if _current_window:
            _current_window.close()
        if _qt_app:
            _qt_app.quit()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _graceful_shutdown)
    signal.signal(signal.SIGINT, _graceful_shutdown)

    # 设置应用程序全局字体：Helvetica, 12px
    _qt_app.setFont(QFont("Helvetica", 12))

    # 创建主窗口实例
    _current_window = CouponGeneratorWindow()
    # 显示窗口
    _current_window.show()

    # 进入事件循环，等待用户交互（关闭窗口时退出）
    sys.exit(_qt_app.exec_())


if __name__ == "__main__":
    main()

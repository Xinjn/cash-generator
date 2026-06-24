"""
Tkinter 图形用户界面（备用）
基于 Tkinter 构建的备选 GUI 界面，支持 Dark/Light 模式自动适配，
提供国家选择、金额/宽高输入、实时预览与导出功能。支持热更新。
默认启动入口为 app.py（PyQt5），本文件仅在手动调用时使用。
"""

import os
import sys
import subprocess
import tkinter as tk
from tkinter import messagebox, filedialog
from PIL import Image, ImageTk

import src.config as config
import src.generate as generate
from src.hot_reload import HotReloader


def is_macos_dark_mode():
    """检测 macOS 当前是否为深色模式。"""
    try:
        result = subprocess.run(
            ["defaults", "read", "-g", "AppleInterfaceStyle"],
            capture_output=True,
            text=True,
            timeout=2
        )
        return "Dark" in result.stdout
    except Exception:
        return False


# 颜色方案：同时在深色和浅色模式下可用
# 显式设置所有控件颜色，避免任何元素不可见
if is_macos_dark_mode():
    # 深色模式配色
    COLORS = {
        "window_bg": "#1a1a2e",
        "card_bg": "#16213e",
        "text": "#e0e0e0",
        "text_secondary": "#a0a0a0",
        "input_bg": "#0f3460",
        "input_fg": "#e0e0e0",
        "border": "#404060",
        "btn_primary_bg": "#e94560",
        "btn_primary_fg": "#ffffff",
        "btn_secondary_bg": "#2a2a4a",
        "btn_secondary_fg": "#e0e0e0",
        "accent": "#e94560",
        "preview_bg": "#0f0f1a",
    }
else:
    # 浅色模式配色（匹配参考截图）
    COLORS = {
        "window_bg": "#ececec",
        "card_bg": "#f5f5f5",
        "text": "#222222",
        "text_secondary": "#555555",
        "input_bg": "#ffffff",
        "input_fg": "#222222",
        "border": "#cccccc",
        "btn_primary_bg": "#FF475A",
        "btn_primary_fg": "#ffffff",
        "btn_secondary_bg": "#e0e0e0",
        "btn_secondary_fg": "#333333",
        "accent": "#FF475A",
        "preview_bg": "#ffffff",
    }


class CashGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Cash Coupon Generator")
        self.root.geometry("480x720")
        self.root.minsize(420, 640)
        self.root.configure(bg=COLORS["window_bg"])

        self.preview_image = None
        self.preview_photo = None
        self.current_output_path = None
        self._resize_timer = None
        self._hot_reloader = None
        self._reload_banner_id = None

        self._build_ui()
        self._update_preview()
        self._start_hot_reload()

    def _styled_frame(self, parent, **kwargs):
        """创建带明确背景色的 Frame。"""
        bg = kwargs.pop("bg", COLORS["card_bg"])
        frame = tk.Frame(parent, bg=bg, **kwargs)
        return frame

    def _styled_label(self, parent, text, font=None, fg=None, **kwargs):
        """创建带明确颜色的 Label。"""
        fg = fg or COLORS["text"]
        bg = kwargs.pop("bg", COLORS["card_bg"])
        font = font or ("Helvetica", 12)
        return tk.Label(parent, text=text, font=font, bg=bg, fg=fg, **kwargs)

    def _styled_entry(self, parent, textvariable, font=None, **kwargs):
        """创建带明确颜色的 Entry。"""
        font = font or ("Helvetica", 13)
        entry = tk.Entry(
            parent,
            textvariable=textvariable,
            font=font,
            bg=COLORS["input_bg"],
            fg=COLORS["input_fg"],
            relief=tk.FLAT,
            bd=1,
            highlightthickness=1,
            highlightcolor=COLORS["accent"],
            highlightbackground=COLORS["border"],
            insertbackground=COLORS["text"],
            **kwargs
        )
        return entry

    def _build_ui(self):
        main_frame = self._styled_frame(self.root, bg=COLORS["window_bg"])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=20)

        # ===== 标题 =====
        title = self._styled_label(
            main_frame,
            "Cash Coupon Generator",
            font=("Helvetica", 20, "bold"),
            bg=COLORS["window_bg"]
        )
        title.pack(pady=(0, 4))

        subtitle = self._styled_label(
            main_frame,
            "Multi-region promotional voucher creator",
            font=("Helvetica", 11),
            fg=COLORS["text_secondary"],
            bg=COLORS["window_bg"]
        )
        subtitle.pack(pady=(0, 20))

        # ===== 表单卡片 =====
        card = self._styled_frame(main_frame, bg=COLORS["card_bg"], bd=1, relief=tk.SOLID)
        card.pack(fill=tk.X, pady=(0, 14))
        # 卡片内边距
        card_inner = self._styled_frame(card, bg=COLORS["card_bg"])
        card_inner.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        # 第 0 行：模板类型
        self._add_form_row(card_inner, 0, "Template:", self._create_template_widget)

        # 第 1 行：区域
        self._add_form_row(card_inner, 1, "Region:", self._create_region_widget)

        # 第 2 行：金额
        self._add_form_row(card_inner, 2, "Amount:", self._create_amount_widget)

        # 第 3 行：门槛和上限（仅 PDV 显示，参考宽高并排布局）
        self._add_form_row(card_inner, 3, "Threshold:", self._create_threshold_cap_widget)

        # 第 4 行：宽度
        self._add_form_row(card_inner, 4, "Width (px):", self._create_width_widget)

        # 第 5 行：高度
        self._add_form_row(card_inner, 5, "Height (px):", self._create_height_widget)

        # 第 6 行：留白
        self._add_form_row(card_inner, 6, "Padding (px):", self._create_padding_widget)

        # ===== 快捷金额按钮 =====
        quick_container = self._styled_frame(main_frame, bg=COLORS["window_bg"])
        quick_container.pack(pady=(4, 14))

        self._styled_label(
            quick_container,
            "Quick:",
            font=("Helvetica", 10),
            bg=COLORS["window_bg"]
        ).pack(side=tk.LEFT, padx=(0, 8))

        for val in [5, 10, 15, 20, 50, 100]:
            btn = tk.Button(
                quick_container,
                text=str(val),
                font=("Helvetica", 10),
                width=3,
                bg=COLORS["input_bg"],
                fg=COLORS["input_fg"],
                activebackground=COLORS["accent"],
                activeforeground="#ffffff",
                relief=tk.FLAT,
                bd=0,
                highlightthickness=1,
                highlightbackground=COLORS["border"],
                command=lambda v=val: self._set_amount(v)
            )
            btn.pack(side=tk.LEFT, padx=2)

        # ===== 操作按钮 =====
        btn_container = self._styled_frame(main_frame, bg=COLORS["window_bg"])
        btn_container.pack(pady=(0, 14))

        self.generate_btn = tk.Button(
            btn_container,
            text="Generate Coupon",
            font=("Helvetica", 13, "bold"),
            bg=COLORS["btn_primary_bg"],
            fg=COLORS["btn_primary_fg"],
            activebackground="#D32637",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
            padx=28,
            pady=8,
            cursor="hand2",
            command=self._update_preview
        )
        self.generate_btn.pack(side=tk.LEFT, padx=4)

        self.save_btn = tk.Button(
            btn_container,
            text="Export",
            font=("Helvetica", 13, "bold"),
            bg=COLORS["btn_secondary_bg"],
            fg=COLORS["btn_secondary_fg"],
            activebackground=COLORS["accent"],
            activeforeground="#ffffff",
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
            padx=28,
            pady=8,
            cursor="hand2",
            command=self._export_image
        )
        self.save_btn.pack(side=tk.LEFT, padx=4)

        # ===== 预览区域 =====
        preview_container = tk.Frame(
            main_frame,
            bg=COLORS["preview_bg"],
            bd=1,
            relief=tk.SOLID,
            highlightbackground=COLORS["border"],
            highlightthickness=1
        )
        preview_container.pack(fill=tk.BOTH, expand=True)

        preview_label = self._styled_label(
            preview_container,
            "Preview",
            font=("Helvetica", 11, "bold"),
            bg=COLORS["preview_bg"],
            fg=COLORS["text_secondary"]
        )
        preview_label.pack(anchor=tk.W, padx=10, pady=(6, 2))

        self.preview_canvas = tk.Canvas(
            preview_container,
            bg=COLORS["preview_bg"],
            highlightthickness=0
        )
        self.preview_canvas.pack(fill=tk.BOTH, expand=True, padx=1, pady=(0, 1))

        # 状态栏
        self.status_var = tk.StringVar(value="Ready")
        status_bar = self._styled_label(
            main_frame,
            "",
            font=("Helvetica", 10),
            fg=COLORS["text_secondary"],
            bg=COLORS["window_bg"],
            textvariable=self.status_var
        )
        status_bar.pack(fill=tk.X, pady=(10, 0))

        # 绑定画布尺寸变化事件
        self.preview_canvas.bind("<Configure>", self._on_canvas_resize)

    def _add_form_row(self, parent, row, label_text, widget_factory):
        frame = self._styled_frame(parent, bg=COLORS["card_bg"])
        frame.pack(fill=tk.X, pady=6)

        label = self._styled_label(
            frame,
            label_text,
            font=("Helvetica", 12),
            bg=COLORS["card_bg"],
            width=14,
            anchor=tk.W
        )
        label.pack(side=tk.LEFT)

        widget_frame = self._styled_frame(frame, bg=COLORS["card_bg"])
        widget_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        widget_factory(widget_frame)

    def _create_template_widget(self, parent):
        self.template_var = tk.StringVar(value="LazCash (Standard)")
        self.template_map = {
            "LazCash (Standard)": generate.TEMPLATE_LAZCASH,
            "PDV": generate.TEMPLATE_PDV,
        }

        self.template_option = tk.OptionMenu(
            parent,
            self.template_var,
            *self.template_map.keys(),
            command=self._on_template_change_option
        )
        self.template_option.config(
            font=("Helvetica", 12),
            bg=COLORS["input_bg"],
            fg=COLORS["input_fg"],
            activebackground=COLORS["accent"],
            activeforeground="#ffffff",
            relief=tk.FLAT,
            bd=1,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
        )
        self.template_option["menu"].config(
            bg=COLORS["input_bg"],
            fg=COLORS["input_fg"],
            activebackground=COLORS["accent"],
            activeforeground="#ffffff",
            font=("Helvetica", 12)
        )
        self.template_option.pack(fill=tk.X, ipady=2)

    def _on_template_change_option(self, value):
        self.template_var.set(value)
        self._set_pdv_fields_visible()
        self._update_preview_delayed()

    def _set_pdv_fields_visible(self):
        """根据当前模板类型显示/隐藏 PDV 专属字段。"""
        template_type = self.template_map.get(self.template_var.get(), generate.TEMPLATE_LAZCASH)
        is_pdv = template_type == generate.TEMPLATE_PDV
        # PDV 字段的显隐通过创建时保存的 frame 引用来控制
        if hasattr(self, "threshold_cap_frame"):
            if is_pdv:
                self.threshold_cap_frame.pack(fill=tk.X, pady=6, before=self.width_frame)
            else:
                self.threshold_cap_frame.pack_forget()

    def _create_region_widget(self, parent):
        self.region_var = tk.StringVar(value="SG")
        region_names = [f"{k} - {v['name']} ({v['currency']})" for k, v in config.REGIONS.items()]
        self.region_map = {f"{k} - {v['name']} ({v['currency']})": k for k, v in config.REGIONS.items()}

        # 使用 OptionMenu 替代 Combobox 以保证跨平台渲染一致性
        self.region_option = tk.OptionMenu(
            parent,
            self.region_var,
            *region_names,
            command=self._on_region_change_option
        )
        self.region_option.config(
            font=("Helvetica", 12),
            bg=COLORS["input_bg"],
            fg=COLORS["input_fg"],
            activebackground=COLORS["accent"],
            activeforeground="#ffffff",
            relief=tk.FLAT,
            bd=1,
            highlightthickness=1,
            highlightbackground=COLORS["border"],
        )
        self.region_option["menu"].config(
            bg=COLORS["input_bg"],
            fg=COLORS["input_fg"],
            activebackground=COLORS["accent"],
            activeforeground="#ffffff",
            font=("Helvetica", 12)
        )
        sg_name = f"SG - {config.REGIONS['SG']['name']} ({config.REGIONS['SG']['currency']})"
        self.region_var.set(sg_name)
        self.region_option.pack(fill=tk.X, ipady=2)

    def _create_amount_widget(self, parent):
        self.amount_var = tk.StringVar(value="15")
        self.amount_entry = self._styled_entry(parent, self.amount_var, font=("Helvetica", 14))
        self.amount_entry.pack(fill=tk.X, ipady=4)
        self.amount_entry.bind("<KeyRelease>", lambda e: self._update_preview_delayed())

    def _create_threshold_cap_widget(self, parent):
        # 门槛和上限并排布局：门槛输入 + 上限标签 + 上限输入
        self.threshold_var = tk.StringVar(value="30")
        self.cap_var = tk.StringVar(value="0")

        h_frame = tk.Frame(parent, bg=COLORS["card_bg"])
        h_frame.pack(fill=tk.X)

        self.threshold_entry = self._styled_entry(h_frame, self.threshold_var, font=("Helvetica", 13))
        self.threshold_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)
        self.threshold_entry.bind("<KeyRelease>", lambda e: self._update_preview_delayed())

        cap_label = self._styled_label(h_frame, "Cap:", font=("Helvetica", 12), bg=COLORS["card_bg"])
        cap_label.pack(side=tk.LEFT, padx=(8, 4))

        self.cap_entry = self._styled_entry(h_frame, self.cap_var, font=("Helvetica", 13))
        self.cap_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)
        self.cap_entry.bind("<KeyRelease>", lambda e: self._update_preview_delayed())

        # 保存合并字段所在的行 frame
        self.threshold_cap_frame = parent.master

    def _create_width_widget(self, parent):
        self.width_frame = parent.master
        self.width_var = tk.StringVar(value="260")
        self.width_entry = self._styled_entry(parent, self.width_var, font=("Helvetica", 13))
        self.width_entry.pack(fill=tk.X, ipady=3)
        self.width_entry.bind("<KeyRelease>", lambda e: self._update_preview_delayed())

    def _create_height_widget(self, parent):
        self.height_var = tk.StringVar(value="260")
        self.height_entry = self._styled_entry(parent, self.height_var, font=("Helvetica", 13))
        self.height_entry.pack(fill=tk.X, ipady=3)
        self.height_entry.bind("<KeyRelease>", lambda e: self._update_preview_delayed())

    def _create_padding_widget(self, parent):
        self.padding_var = tk.StringVar(value="0")
        self.padding_entry = self._styled_entry(parent, self.padding_var, font=("Helvetica", 13))
        self.padding_entry.pack(fill=tk.X, ipady=3)
        self.padding_entry.bind("<KeyRelease>", lambda e: self._update_preview_delayed())

    def _on_region_change_option(self, value):
        code = self.region_map.get(value, "SG")
        self.region_var.set(code)
        self._update_preview_delayed()

    def _set_amount(self, value):
        self.amount_var.set(str(value))
        self._update_preview_delayed()

    def _update_preview_delayed(self):
        if self._resize_timer:
            self.root.after_cancel(self._resize_timer)
        self._resize_timer = self.root.after(300, self._update_preview)

    def _on_canvas_resize(self, event=None):
        if self._resize_timer:
            self.root.after_cancel(self._resize_timer)
        self._resize_timer = self.root.after(200, self._update_preview)

    def _get_params(self):
        try:
            amount = float(self.amount_var.get())
            if amount < 0:
                amount = 0
        except ValueError:
            amount = 15

        try:
            width = int(self.width_var.get())
            if width < 1:
                width = 1
        except ValueError:
            width = 260

        try:
            height = int(self.height_var.get())
            if height < 1:
                height = 1
        except ValueError:
            height = 260

        try:
            padding = int(self.padding_var.get())
            if padding < 0:
                padding = 0
        except ValueError:
            padding = 0

        # region_var 被选项切换覆盖，从映射表恢复
        region_display = self.region_var.get()
        region = self.region_map.get(region_display, "SG")

        # 模板类型
        template_display = self.template_var.get()
        template_type = self.template_map.get(template_display, generate.TEMPLATE_LAZCASH)

        # 门槛与上限（PDV 使用，非法值默认 0）
        try:
            threshold = float(self.threshold_var.get())
            if threshold < 0:
                threshold = 0
        except ValueError:
            threshold = 0

        try:
            cap = float(self.cap_var.get())
            if cap < 0:
                cap = 0
        except ValueError:
            cap = 0

        return amount, region, width, height, padding, template_type, threshold, cap

    def _update_preview(self):
        try:
            amount, region, width, height, padding, template_type, threshold, cap = self._get_params()

            path = generate.generate_coupon(
                region, amount, width, height, padding,
                template_type=template_type, threshold=threshold, cap=cap
            )
            self.current_output_path = path

            img = Image.open(path)
            canvas_w = max(self.preview_canvas.winfo_width(), 300)
            canvas_h = max(self.preview_canvas.winfo_height(), 300)

            img_w, img_h = img.size
            scale = min(canvas_w / img_w, canvas_h / img_h, 1.0) * 0.9
            new_w = int(img_w * scale)
            new_h = int(img_h * scale)

            preview = img.resize((new_w, new_h), Image.LANCZOS)
            self.preview_image = preview
            self.preview_photo = ImageTk.PhotoImage(preview)

            self.preview_canvas.delete("all")
            x = (canvas_w - new_w) // 2
            y = (canvas_h - new_h) // 2
            self.preview_canvas.create_image(x, y, anchor=tk.NW, image=self.preview_photo)

            self.status_var.set(f"Preview: {region} {amount} | {width}x{height}")

        except Exception as e:
            self.status_var.set(f"Error: {str(e)}")
            print(f"Preview error: {e}")

    def _start_hot_reload(self):
        """启动热更新文件监视器。"""
        self._hot_reloader = HotReloader(on_reload_callback=self._schedule_reload_callback)
        self._hot_reloader.start()

    def _on_module_reloaded(self, mod_name):
        """模块热更新完成后的回调。
        通过 root.after() 调度到主线程执行。
        """
        if mod_name == "src.gui":
            # GUI 模块变更：从重载后的模块重建 UI
            self._rebuild_ui()
            return

        original_title = self.root.title().replace(" [已热更新]", "")
        self.root.title(f"{original_title} [已热更新]")

        # 2 秒后自动清除提示
        if self._reload_banner_id:
            self.root.after_cancel(self._reload_banner_id)
        self._reload_banner_id = self.root.after(
            2000, lambda: self.root.title(original_title)
        )

    def _rebuild_ui(self):
        """使用重载后的模块类定义重建 UI。"""
        # 停止旧的热更新监视器
        if self._hot_reloader:
            self._hot_reloader.stop()
            self._hot_reloader = None

        # 从重载后的模块获取新类
        gui_module = sys.modules.get("src.gui")
        if not gui_module:
            return
        NewAppClass = gui_module.CashGeneratorApp

        # 清除 root 下的所有控件
        for widget in self.root.winfo_children():
            widget.destroy()

        # 使用新类定义重新初始化
        # 修改自身的 __class__ 以使所有方法使用新代码
        self.__class__ = NewAppClass
        # 重新执行 __init__ 逻辑（跳过热更新启动以避免重复监视）
        self.preview_image = None
        self.preview_photo = None
        self.current_output_path = None
        self._resize_timer = None
        self._hot_reloader = None
        self._reload_banner_id = None
        self._build_ui()
        self._update_preview()
        self._start_hot_reload()
        print("[HotReload] Tkinter UI rebuilt from reloaded class")

    def _schedule_reload_callback(self, mod_name):
        """线程安全包装：将回调调度到 Tkinter 主线程。"""
        self.root.after(0, lambda: self._on_module_reloaded(mod_name))

    def _export_image(self):
        try:
            amount, region, width, height, padding, template_type, threshold, cap = self._get_params()

            template_suffix = "pdv" if template_type == generate.TEMPLATE_PDV else "cash"
            default_name = f"cash_{region}_{amount}_{width}x{height}_{template_suffix}.png"

            file_path = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("All files", "*.*")],
                initialdir=os.path.expanduser("~/Desktop"),
                initialfile=default_name
            )

            if not file_path:
                return

            path = generate.generate_coupon(
                region, amount, width, height, padding,
                template_type=template_type, threshold=threshold, cap=cap
            )

            # 移动到用户指定路径
            if path != file_path:
                import shutil
                shutil.move(path, file_path)
                path = file_path

            self.status_var.set(f"Saved: {os.path.basename(path)}")
            messagebox.showinfo("Export Complete", f"Image saved to:\n{path}")

        except Exception as e:
            messagebox.showerror("Export Error", str(e))
            self.status_var.set(f"Error: {str(e)}")


def main():
    root = tk.Tk()
    app = CashGeneratorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

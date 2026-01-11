
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import re
import json

# --- 1. 样式常量定义 (与主界面保持一致) ---
COLOR_BG_APP = "#f5f6f7"  # APP 整体背景 (极浅的冷灰)
COLOR_CARD = "#ffffff"  # 卡片背景 (纯白)
COLOR_PRIMARY = "#006eff"  # 腾讯蓝 (主色)
COLOR_HOVER = "#3385ff"  # 悬停色
COLOR_TEXT_MAIN = "#1f2329"  # 主要文字
COLOR_TEXT_SUB = "#646a73"  # 次要文字
COLOR_ENTRY_BG = "#f5f6f7"  # 输入框背景 (浅灰)
COLOR_DESTRUCTIVE = "#ff4d4f"  # 删除/清空色

SETTINGS_DIR = "configs"


class RuleEditorApp(ctk.CTkFrame):
    def __init__(self, master, main_app_ref, initial_config=None, edit_mode=False):
        super().__init__(master)

        # 1. 设置整体背景
        self.configure(fg_color=COLOR_BG_APP)
        self.master.configure(fg_color=COLOR_BG_APP)  # 确保弹窗底色也是浅灰
        self.pack(fill="both", expand=True)  # 填满窗口

        self.master = master
        self.main_app_ref = main_app_ref
        self.initial_config = initial_config if initial_config else self._get_default_config()
        self.edit_mode = edit_mode
        self.current_sample_path = ""
        self.filename_segments = []
        self.naming_rule_widgets = []

        # === 2. 核心布局配置 ===
        # 左侧权重 3 (内容区)，右侧权重 1 (工具箱)
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)  # 让内容区可以垂直滚动或扩展

        # === 3. 定义统一的 UI 样式字典 ===
        self.style_card = {
            "fg_color": COLOR_CARD,
            "corner_radius": 15,
            "border_width": 0
        }
        self.style_entry = {
            "fg_color": COLOR_ENTRY_BG,
            "border_width": 0,
            "text_color": COLOR_TEXT_MAIN,
            "corner_radius": 8,
            "height": 36
        }
        self.style_button_primary = {
            "fg_color": COLOR_PRIMARY, "hover_color": COLOR_HOVER, "text_color": "white",
            "corner_radius": 8, "font": ("微软雅黑", 12, "bold"), "height": 36
        }
        self.style_button_secondary = {
            "fg_color": "#eef2f9", "text_color": COLOR_PRIMARY, "hover_color": "#dbe4f5",
            "corner_radius": 8, "height": 36, "font": ("微软雅黑", 12)
        }
        self.style_label_title = {
            "text_color": COLOR_TEXT_SUB, "font": ("微软雅黑", 12, "bold")
        }

        # ================= 左侧：内容滚动区 (Left Column) =================
        # 使用 ScrollableFrame 防止屏幕太小内容显示不全
        self.scroll_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_container.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)
        self.scroll_container.grid_columnconfigure(0, weight=1)

        # --- 卡片 1: 基础信息 ---
        self.frame_top = ctk.CTkFrame(self.scroll_container, **self.style_card)
        self.frame_top.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        self.frame_top.grid_columnconfigure(1, weight=1)

        # 规则名称
        ctk.CTkLabel(self.frame_top, text="规则名称", **self.style_label_title).grid(row=0, column=0, padx=15, pady=15,
                                                                                     sticky="w")
        self.entry_rule_name = ctk.CTkEntry(self.frame_top, placeholder_text="例如: DJI 运动相机", **self.style_entry)
        self.entry_rule_name.grid(row=0, column=1, columnspan=2, padx=(5, 15), pady=15, sticky="ew")

        if self.edit_mode and self.initial_config:
            self.entry_rule_name.insert(0, self.initial_config.get('rule_name', ''))
            self.entry_rule_name.configure(state="disabled")

        # 样本目录
        ctk.CTkLabel(self.frame_top, text="样本目录", **self.style_label_title).grid(row=1, column=0, padx=15,
                                                                                     pady=(0, 15), sticky="w")
        self.entry_sample_dir = ctk.CTkEntry(self.frame_top, **self.style_entry)
        self.entry_sample_dir.grid(row=1, column=1, padx=5, pady=(0, 15), sticky="ew")
        ctk.CTkButton(self.frame_top, text="📂 浏览", width=80, **self.style_button_primary,
                      command=self._browse_sample_dir).grid(row=1, column=2, padx=15, pady=(0, 15))

        # 样本文件下拉 + 重切分
        self.combobox_sample_file = ctk.CTkComboBox(self.frame_top, values=["(请选择样本目录)"], height=36,
                                                    fg_color=COLOR_ENTRY_BG, border_width=0,
                                                    button_color=COLOR_ENTRY_BG,
                                                    text_color=COLOR_TEXT_MAIN, command=self._on_sample_file_select)
        self.combobox_sample_file.grid(row=2, column=0, columnspan=2, padx=15, pady=(0, 15), sticky="ew")

        ctk.CTkButton(self.frame_top, text="🔄 重新切分", width=80, **self.style_button_secondary,
                      command=self._resplit_filename).grid(row=2, column=2, padx=15, pady=(0, 15))

        # --- 卡片 2: 文件名切片预览 ---
        self.frame_segments = ctk.CTkFrame(self.scroll_container, **self.style_card)
        self.frame_segments.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        ctk.CTkLabel(self.frame_segments, text="文件名切片 (点击积木添加到下方)", **self.style_label_title).pack(
            padx=15, pady=(15, 5), anchor="w")

        # ScrollableFrame 背景设为透明，透出卡片的白色
        self.segment_display_frame = ctk.CTkScrollableFrame(self.frame_segments, orientation="horizontal", height=60,
                                                            fg_color="transparent")
        self.segment_display_frame.pack(fill="x", padx=10, pady=(0, 15))
        # 初始加载
        if self.initial_config and self.initial_config.get('sample_file'):
            self.current_sample_path = self.initial_config['sample_file']
            self._display_segments_from_filename(os.path.basename(self.current_sample_path),
                                                 self.initial_config.get('source_split_regex', '[_\\- ]'))

        # --- 卡片 3: 新命名规则构建 ---
        self.frame_naming = ctk.CTkFrame(self.scroll_container, **self.style_card)
        self.frame_naming.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        ctk.CTkLabel(self.frame_naming, text="新命名规则 (拖拽排序 / 点击工具箱添加)", **self.style_label_title).pack(
            padx=15, pady=(15, 5), anchor="w")

        # 积木槽位 (给个极淡的灰色背景，表示区域)
        self.naming_rule_frame = ctk.CTkFrame(self.frame_naming, fg_color="#f9f9f9", corner_radius=8, height=80)
        self.naming_rule_frame.pack(fill="x", padx=15, pady=5)

        # 预览结果 (浅蓝底色，像个提示条)
        self.naming_preview_label = ctk.CTkLabel(self.frame_naming, text="预览: (请构建规则)",
                                                 fg_color="#eef2f9", text_color=COLOR_PRIMARY, corner_radius=8,
                                                 height=40, anchor="w", padx=15)
        self.naming_preview_label.pack(fill="x", padx=15, pady=15)

        # --- 卡片 4: 底部选项 (删除/操作) ---
        self.frame_options = ctk.CTkFrame(self.scroll_container, **self.style_card)
        self.frame_options.grid(row=3, column=0, padx=20, pady=(10, 20), sticky="ew")
        self.frame_options.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.frame_options, text="操作模式", **self.style_label_title).grid(row=0, column=0, padx=15,
                                                                                         pady=15, sticky="w")

        self.operation_mode = ctk.StringVar(value=self.initial_config.get('operation_mode', 'move'))
        ctk.CTkRadioButton(self.frame_options, text="✂️ 剪切 (移动)", variable=self.operation_mode, value="move",
                           fg_color=COLOR_PRIMARY, text_color=COLOR_TEXT_MAIN).grid(row=0, column=1, padx=5, sticky="w")
        ctk.CTkRadioButton(self.frame_options, text="📋 复制 (保留原文件)", variable=self.operation_mode, value="copy",
                           fg_color=COLOR_PRIMARY, text_color=COLOR_TEXT_MAIN).grid(row=0, column=2, padx=5, sticky="w")

        ctk.CTkLabel(self.frame_options, text="清理文件", **self.style_label_title).grid(row=1, column=0, padx=15,
                                                                                         pady=15, sticky="w")

        self.delete_lrf = ctk.BooleanVar(value=".lrf" in self.initial_config.get('delete_extensions', []))
        self.delete_txt = ctk.BooleanVar(value=".txt" in self.initial_config.get('delete_extensions', []))
        self.delete_custom = ctk.BooleanVar(value=bool(self.initial_config.get('delete_custom_exts', [])))

        ctk.CTkCheckBox(self.frame_options, text="删除 .lrf", variable=self.delete_lrf,
                        fg_color=COLOR_PRIMARY, text_color=COLOR_TEXT_MAIN).grid(row=1, column=1, padx=5, sticky="w")
        ctk.CTkCheckBox(self.frame_options, text="删除 .txt", variable=self.delete_txt,
                        fg_color=COLOR_PRIMARY, text_color=COLOR_TEXT_MAIN).grid(row=1, column=2, padx=5, sticky="w")

        # 自定义删除
        self.frame_custom_delete = ctk.CTkFrame(self.frame_options, fg_color="transparent")
        self.frame_custom_delete.grid(row=2, column=1, columnspan=2, padx=5, pady=10, sticky="ew")
        ctk.CTkCheckBox(self.frame_custom_delete, text="自定义:", variable=self.delete_custom,
                        fg_color=COLOR_PRIMARY, text_color=COLOR_TEXT_MAIN,
                        command=self._toggle_custom_delete_entry).pack(side="left")
        self.entry_custom_delete = ctk.CTkEntry(self.frame_custom_delete, placeholder_text=".mov,.thm",
                                                **self.style_entry)
        self.entry_custom_delete.pack(side="left", fill="x", expand=True, padx=5)

        if self.initial_config.get('delete_custom_exts'):
            self.entry_custom_delete.insert(0, ",".join(self.initial_config['delete_custom_exts']))
        self._toggle_custom_delete_entry()

        # ================= 右侧：悬浮工具箱 (Right Column) =================

        self.frame_toolbox = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_toolbox.grid(row=0, column=1, sticky="nsew", padx=(0, 20), pady=20)
        self.frame_toolbox.grid_rowconfigure(99, weight=1)  # 占位，把保存按钮顶到底部

        ctk.CTkLabel(self.frame_toolbox, text="📦 工具箱", font=("微软雅黑", 14, "bold"),
                     text_color=COLOR_TEXT_MAIN).pack(pady=(0, 15))

        # 定义工具箱按钮样式 (白底黑字，投影感)
        style_tool_btn = {
            "fg_color": COLOR_CARD, "text_color": COLOR_TEXT_MAIN,
            "hover_color": "#e1e4e8", "corner_radius": 8, "height": 40, "anchor": "w"
        }

        # 1. 属性组
        ctk.CTkLabel(self.frame_toolbox, text="属性", text_color=COLOR_TEXT_SUB, font=("微软雅黑", 10)).pack(anchor="w",
                                                                                                             pady=(5,
                                                                                                                   2))
        ctk.CTkButton(self.frame_toolbox, text="🗓️ 文件日期", command=lambda: self._add_naming_element("current_date"),
                      **style_tool_btn).pack(fill="x", pady=4)
        ctk.CTkButton(self.frame_toolbox, text="📄 文件类型", command=lambda: self._add_naming_element("extension"),
                      **style_tool_btn).pack(fill="x", pady=4)
        ctk.CTkButton(self.frame_toolbox, text="📂 原文件夹名",
                      command=lambda: self._add_naming_element("original_folder"), **style_tool_btn).pack(fill="x",
                                                                                                          pady=4)

        # 2. 结构组
        ctk.CTkLabel(self.frame_toolbox, text="结构", text_color=COLOR_TEXT_SUB, font=("微软雅黑", 10)).pack(anchor="w",
                                                                                                             pady=(15,
                                                                                                                   2))
        ctk.CTkButton(self.frame_toolbox, text="🔢 自增序号", command=lambda: self._add_naming_element("auto_counter"),
                      **style_tool_btn).pack(fill="x", pady=4)
        ctk.CTkButton(self.frame_toolbox, text="📝 自定义文本", command=lambda: self._add_naming_element("custom_text"),
                      **style_tool_btn).pack(fill="x", pady=4)
        ctk.CTkButton(self.frame_toolbox, text="➖ 连接符 (-)", command=lambda: self._add_naming_element("separator"),
                      **style_tool_btn).pack(fill="x", pady=4)

        # 文件夹分层 (淡黄色背景强调)
        ctk.CTkButton(self.frame_toolbox, text="📂 创建子目录 (/)", fg_color="#fff7e6", text_color="#d48806",
                      hover_color="#ffd591",
                      corner_radius=8, height=40, anchor="w",
                      command=lambda: self._add_naming_element("folder_separator")).pack(fill="x", pady=4)

        # 清空按钮 (红色文字)
        ctk.CTkButton(self.frame_toolbox, text="🗑️ 清空所有规则", fg_color="transparent", text_color=COLOR_DESTRUCTIVE,
                      hover_color="#fff1f0",
                      height=30, font=("微软雅黑", 11), command=self._clear_naming_rules).pack(fill="x", pady=10)

        # 3. 底部保存按钮
        # 使用 Frame 占位，确保按钮在底部
        spacer = ctk.CTkFrame(self.frame_toolbox, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

        ctk.CTkButton(self.frame_toolbox, text="💾 保存所有更改", height=50, corner_radius=25,
                      fg_color=COLOR_PRIMARY, hover_color=COLOR_HOVER, font=("微软雅黑", 14, "bold"),
                      command=self._save_rule).pack(side="bottom", fill="x", pady=0)

        # 恢复编辑状态的UI逻辑
        if self.initial_config and self.initial_config.get('naming_structure'):
            self._reconstruct_naming_ui(self.initial_config['naming_structure'])



    def _get_default_config(self):
        """返回一个空的默认配置"""
        return {
            "rule_name": "",
            "sample_file": "",
            "source_split_regex": "[_\\- ]",
            "naming_structure": [],
            "operation_mode": "move",
            "delete_extensions": [],
            "delete_custom_exts": [],
            "output_preview": ""  # 仅用于显示，不存入实际处理逻辑
        }

    def _browse_sample_dir(self):
        """选择样本文件目录并加载文件列表"""
        path = filedialog.askdirectory()
        if path:
            self.entry_sample_dir.delete(0, tk.END)
            self.entry_sample_dir.insert(0, path)
            self.current_sample_path = ""  # 重置当前样本文件

            files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
            if files:
                self.combobox_sample_file.configure(values=files)
                self.combobox_sample_file.set(files[0])  # 默认选中第一个文件
                self._on_sample_file_select(files[0])
            else:
                self.combobox_sample_file.configure(values=["(无文件)"])
                self.combobox_sample_file.set("(无文件)")
                self._clear_segments_display()  # 清空切片显示
                messagebox.showinfo("提示", "所选目录下没有文件。")

    def _on_sample_file_select(self, filename):
        """用户选择样本文件时，更新切片显示"""
        if filename == "(无文件)":
            self.current_sample_path = ""
            self._clear_segments_display()
            return

        sample_dir = self.entry_sample_dir.get()
        if sample_dir and os.path.exists(sample_dir):
            self.current_sample_path = os.path.join(sample_dir, filename)
            self._display_segments_from_filename(filename, self.initial_config.get('source_split_regex', '[_\\- ]'))
            self._update_naming_preview()  # 样本文件变化时更新预览
        else:
            self.current_sample_path = ""
            messagebox.showwarning("警告", "请先选择有效的样本目录。")
            self._clear_segments_display()

    def _resplit_filename(self):
        """用户点击重新切分时，使用默认规则再次切分"""
        selected_file = self.combobox_sample_file.get()
        if selected_file and selected_file != "(无文件)":
            self._display_segments_from_filename(selected_file,
                                                 self.initial_config.get('source_split_regex', '[_\\- ]'))
        else:
            messagebox.showwarning("警告", "请先选择一个样本文件。")

    def _display_segments_from_filename(self, filename, split_regex='[_\\- ]'):
        """根据文件名和正则切分，并显示为可拖拽的按钮"""
        for widget in self.segment_display_frame.winfo_children():
            widget.destroy()  # 清空旧的切片

        # 尝试通过正则表达式切分文件名（不包含后缀）
        name_stem, name_ext = os.path.splitext(filename)
        segments = re.split(split_regex, name_stem)
        segments = [s for s in segments if s]  # 去除空片段
        self.filename_segments = segments

        for index, seg_text in enumerate(segments):
            # 注意：这里的 command 使用了 lambda 闭包来捕获当前的 index 和 text
            # 点击这个按钮，就会把这个“源积木”添加到下方的规则构建区
            btn = ctk.CTkButton(self.segment_display_frame,
                                text=seg_text,
                                width=len(seg_text) * 10 + 20,  # 根据文字长度动态调整按钮宽度
                                fg_color="transparent",
                                border_width=2,
                                text_color=("gray10", "gray90"),
                                command=lambda i=index, t=seg_text: self._add_naming_element("source_segment",
                                                                                             value={'index': i,
                                                                                                    'text': t}))
            btn.pack(side="left", padx=5, pady=5)

    def _clear_segments_display(self):
        """清空切片显示区"""
        for widget in self.segment_display_frame.winfo_children():
            widget.destroy()
        self.filename_segments = []

    def _add_naming_element(self, type, value=None):
        """核心方法：向规则构建区添加一个积木"""

        # --- 处理需要用户输入的特殊类型 ---
        if type == "custom_text" and value is None:
            dialog = ctk.CTkInputDialog(text="请输入自定义文本 (例如: -Video-):", title="自定义文本")
            text = dialog.get_input()
            if not text: return  # 用户取消
            value = text

        elif type == "separator" and value is None:
            dialog = ctk.CTkInputDialog(text="请输入分隔符 (例如 _ 或 - ):", title="分隔符")
            text = dialog.get_input()
            if not text: return
            value = text
        # === 扩展名积木样式 ===
        elif type == "extension":
            display_text = "[TYPE]"  # 显示的占位符
            block_color = "#8E44AD"  # 紫色
            if value is None: value = "upper"  # 默认大写 (MP4)，也可以存 "lower"

        # --- 创建 UI 表现 (一个带删除按钮的小框) ---
        widget_container = ctk.CTkFrame(self.naming_rule_frame, fg_color=("gray80", "gray30"), corner_radius=6)
        widget_container.pack(side="left", padx=2, pady=2)

        display_text = ""
        block_color = "gray"

        # 根据类型设置显示文本和颜色
        if type == "source_segment":
            display_text = f"[{value['text']}]"  # 显示源文件名片段
            block_color = "#3B8ED0"  # 蓝色
        elif type == "auto_counter":
            display_text = "[🔢 序号]"
            block_color = "#E19C24"  # 黄色
            if value is None: value = {"start": 1, "padding": 3}  # 默认配置
        elif type == "current_date":
            display_text = "[🗓️ 日期]"
            block_color = "#2CC985"  # 绿色
            if value is None: value = "%Y-%m-%d"  # 默认格式
        elif type == "custom_text":
            display_text = f"'{value}'"
            block_color = "#999999"
        elif type == "separator":
            display_text = f" {value} "
            block_color = "#666666"
        elif type == "original_folder":
            display_text = "[📂 原目录]"
            block_color = "#8E44AD"

        # 左移按钮 (<)
        btn_left = ctk.CTkButton(widget_container, text="<", width=15, height=20, fg_color="transparent",
                                 text_color="gray",
                                 font=("Arial", 10), hover_color=("gray70", "gray40"),
                                 command=lambda w=widget_container: self._move_naming_element(w, -1))  # -1 代表向左
        btn_left.pack(side="left", padx=0)

        # 积木标签
        lbl = ctk.CTkLabel(widget_container, text=display_text, text_color="white", fg_color=block_color,
                           corner_radius=4, padx=5)
        lbl.pack(side="left", padx=2, pady=2)

        # 右移按钮 (>)
        btn_right = ctk.CTkButton(widget_container, text=">", width=15, height=20, fg_color="transparent",
                                  text_color="gray",
                                  font=("Arial", 10), hover_color=("gray70", "gray40"),
                                  command=lambda w=widget_container: self._move_naming_element(w, 1))  # 1 代表向右
        btn_right.pack(side="left", padx=0)

        # 删除按钮 (X)
        btn_del = ctk.CTkButton(widget_container, text="×", width=20, height=20, fg_color="transparent",
                                hover_color="red",
                                command=lambda w=widget_container: self._remove_naming_element(w))
        btn_del.pack(side="right", padx=1)

        # --- 存储数据逻辑 ---
        # 我们把这个积木的数据结构存起来，以便保存时转换成 JSON
        element_data = {
            "type": type,
            "value": value,
            "ui_widget": widget_container  # 存下来引用，方便删除
        }
        self.naming_rule_widgets.append(element_data)

        # 实时更新预览
        self._update_naming_preview()

    def _remove_naming_element(self, widget_ref):
        """从 UI 和数据列表中移除积木"""
        # 1. 从 UI 移除
        widget_ref.destroy()

        # 2. 从数据列表移除 (根据 widget 引用匹配)
        self.naming_rule_widgets = [item for item in self.naming_rule_widgets if item["ui_widget"] != widget_ref]

        # 3. 更新预览
        self._update_naming_preview()

    def _clear_naming_rules(self):
        """清空所有规则积木"""
        for item in self.naming_rule_widgets:
            item["ui_widget"].destroy()
        self.naming_rule_widgets = []
        self._update_naming_preview()

    def _reconstruct_naming_ui(self, structure_data):
        """编辑模式下，根据保存的 JSON 结构恢复 UI"""
        self._clear_naming_rules()
        for item in structure_data:
            # 注意：如果是 source_segment，需要根据当前的 filename_segments 尝试恢复 'text' 用于显示
            # 如果当前没有样本文件，就显示 generic text
            type_ = item.get("type")
            value_ = item.get("value")

            if type_ == "source_segment":
                idx = value_['index']
                # 尝试获取对应切片的文本用于显示，如果越界则显示占位符
                text_display = f"切片{idx + 1}"
                if self.filename_segments and idx < len(self.filename_segments):
                    text_display = self.filename_segments[idx]
                value_['text'] = text_display

            self._add_naming_element(type_, value_)

    def _update_naming_preview(self):
        """根据当前的积木列表，实时计算并显示文件名预览"""
        if not self.naming_rule_widgets:
            self.naming_preview_label.configure(text="预览: (规则为空，请添加积木)")
            return

        preview_name = ""
        ext = ".mp4"  # 默认后缀
        if self.current_sample_path:
            _, ext = os.path.splitext(self.current_sample_path)

        for item in self.naming_rule_widgets:
            t = item["type"]
            v = item["value"]

            if t == "source_segment":
                # 如果当前有样本切片，就用真实的；否则显示占位符
                idx = v['index']
                if self.filename_segments and idx < len(self.filename_segments):
                    preview_name += self.filename_segments[idx]
                else:
                    preview_name += f"[切片{idx + 1}]"
            elif t == "auto_counter":
                preview_name += "001"
            elif t == "current_date":
                import datetime
                # 简单处理日期格式
                fmt = v if isinstance(v, str) else "%Y-%m-%d"
                preview_name += datetime.datetime.now().strftime(fmt)
            elif t == "custom_text" or t == "separator":
                preview_name += str(v)
            elif t == "original_folder":
                preview_name += "Foldername"
            elif t == "extension":
                # 去掉点，转大写。例如 ".mp4" -> "MP4"
                ext_str = ext.replace('.', '')
                if v == "upper":
                    preview_name += ext_str.upper()
                else:
                    preview_name += ext_str.lower()

        self.naming_preview_label.configure(text=f"预览结果: {preview_name}{ext}")

    def _toggle_custom_delete_entry(self):
        """切换自定义删除输入框的启用状态"""
        if self.delete_custom.get():
            self.entry_custom_delete.configure(state="normal")
        else:
            self.entry_custom_delete.configure(state="disabled")

    def _save_rule(self):
        """保存当前配置到 JSON 文件"""
        rule_name = self.entry_rule_name.get().strip()
        if not rule_name:
            messagebox.showerror("错误", "请输入规则名称！")
            return

        if not self.naming_rule_widgets:
            messagebox.showwarning("警告", "命名规则为空，生成的文件名可能不正确。")

        # 1. 构建要保存的数据结构
        # 去掉 'ui_widget' 这种 UI 对象，只保留纯数据
        clean_naming_structure = []
        for item in self.naming_rule_widgets:
            clean_item = {
                "type": item["type"],
                "value": item["value"]
            }
            # 对于 source_segment，我们不需要保存当时的 'text'，只需要保存 'index'，因为text是随文件变的
            if item["type"] == "source_segment":
                clean_item["value"] = {"index": item["value"]["index"]}

            clean_naming_structure.append(clean_item)

        # 2. 收集删除后缀
        delete_exts = []
        if self.delete_lrf.get(): delete_exts.append(".lrf")
        if self.delete_txt.get(): delete_exts.append(".txt")

        custom_del_str = self.entry_custom_delete.get().strip()
        custom_del_list = []
        if self.delete_custom.get() and custom_del_str:
            # 处理用户输入的 ".mov, .jpg" 这种格式
            custom_del_list = [x.strip() for x in custom_del_str.replace('，', ',').split(',') if x.strip()]

        # 3. 组装最终字典
        final_config = {
            "rule_name": rule_name,
            "sample_file": self.current_sample_path,
            "source_split_regex": "[_\\- ]",  # 目前写死，以后可以做成可配置
            "naming_structure": clean_naming_structure,
            "operation_mode": self.operation_mode.get(),
            "delete_extensions": delete_exts,
            "delete_custom_exts": custom_del_list,
            # 保存预览文本仅供参考
            "output_preview": self.naming_preview_label.cget("text")
        }

        # 4. 写入文件
        if not os.path.exists(SETTINGS_DIR):
            os.makedirs(SETTINGS_DIR)

        filename = f"{rule_name}.json"
        # 简单的文件名清理，防止非法字符
        filename = "".join([c for c in filename if c.isalpha() or c.isdigit() or c in ' ._-']).strip()

        filepath = os.path.join(SETTINGS_DIR, filename)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(final_config, f, indent=4, ensure_ascii=False)

            messagebox.showinfo("成功", f"规则 '{rule_name}' 已保存！")
            self.master.destroy()  # 关闭编辑器窗口

        except Exception as e:
            messagebox.showerror("保存失败", f"无法保存文件: {e}")

    def _move_naming_element(self, widget_ref, direction):
        """
                处理积木的移动逻辑
                direction: -1 (左移), 1 (右移)
                """
        # 1. 找到当前 widget 在列表中的索引
        current_index = -1
        for i, item in enumerate(self.naming_rule_widgets):
            if item["ui_widget"] == widget_ref:
                current_index = i
                break

        if current_index == -1: return  # 没找到，防呆保护

        # 2. 计算目标索引
        new_index = current_index + direction

        # 3. 边界检查 (不能移出列表范围，比如第0个不能左移)
        if 0 <= new_index < len(self.naming_rule_widgets):
            # A. 交换数据列表中的位置 (Python 交换变量的快捷写法)
            self.naming_rule_widgets[current_index], self.naming_rule_widgets[new_index] = \
                self.naming_rule_widgets[new_index], self.naming_rule_widgets[current_index]

            # B. 重新排列 UI (先隐藏再重新按顺序显示)
            # pack 布局依赖于添加顺序。最简单的方法是先把所有积木都 forget，再按新顺序 pack 一次
            for item in self.naming_rule_widgets:
                item["ui_widget"].pack_forget()  # 先从界面上拿下来

            for item in self.naming_rule_widgets:
                item["ui_widget"].pack(side="left", padx=2, pady=2)  # 再按新顺序挂上去

            # C. 更新下方的文字预览
            self._update_naming_preview()

    def _remove_naming_element(self, widget_ref):
        widget_ref.destroy()
        self.naming_rule_widgets = [item for item in self.naming_rule_widgets if item["ui_widget"] != widget_ref]
        self._update_naming_preview()
# 单独测试这个界面
if __name__ == "__main__":
    root = ctk.CTk()
    root.geometry("1000x800")


    # 模拟主应用的引用
    class MockApp: pass


    app = RuleEditorApp(root, MockApp())
    root.mainloop()
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import json
import os
import threading

# from organizer_core import OrganizerCore

# --- 常量定义 ---
SETTINGS_DIR = "configs"  # 存放规则配置文件的文件夹
DEFAULT_CONFIG_NAME = "default_config.json"
COLOR_BG_WHITE = "#e1e4e8"    # 主背景色 (浅灰)
COLOR_BG_APP = "#f5f6f7"       # APP 整体背景 (极浅的冷灰)
COLOR_CARD = "#ffffff"         # 卡片背景 (纯白)
COLOR_PRIMARY = "#006eff"      # 腾讯蓝/科技蓝 (主色)
COLOR_HOVER = "#3385ff"        # 悬停色 (亮一点的蓝)
COLOR_TEXT_MAIN = "#1f2329"    # 主要文字 (接近纯黑)
COLOR_TEXT_SUB = "#646a73"     # 次要文字 (深灰)
COLOR_ENTRY_BG = "#f5f6f7"     # 输入框内部背景 (浅灰，不刺眼)

ctk.set_appearance_mode("Light")
# ctk.set_default_color_theme("blue")

class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("文件整理助手")
        self.geometry("730x450")  # 调整窗口大小以适应内容
        self.resizable(True, True)
        ctk.set_appearance_mode("System")  # "System" (默认), "Dark", "Light"
        ctk.set_default_color_theme("blue")  # "blue" (默认), "green", "dark-blue"
        self.configure(fg_color=COLOR_BG_WHITE)
        # --- 布局配置 ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)  # 允许下方的日志区或结果区扩展

        # --- 1. 顶部：路径选择与运行按钮 ---
        self.frame_top = ctk.CTkFrame(self)
        self.frame_top.grid(row=0, column=0, padx=20, pady=10, sticky="ew")
        self.frame_top.grid_columnconfigure(1, weight=1)  # Entry 字段占据大部分宽度

        # 源目录
        ctk.CTkLabel(self.frame_top, text="源目录:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.entry_source_dir = ctk.CTkEntry(self.frame_top, placeholder_text="请选择源文件夹", width=300)
        self.entry_source_dir.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(self.frame_top, text="浏览", command=lambda: self._browse_dir(self.entry_source_dir)).grid(row=0,
                                                                                                                 column=2,
                                                                                                                 padx=5,
                                                                                                                 pady=5)

        # 目标目录
        ctk.CTkLabel(self.frame_top, text="目标目录:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.entry_target_dir = ctk.CTkEntry(self.frame_top, placeholder_text="请选择目标文件夹", width=300)
        self.entry_target_dir.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(self.frame_top, text="浏览", command=lambda: self._browse_dir(self.entry_target_dir)).grid(row=1,
                                                                                                                 column=2,
                                                                                                                 padx=5,
                                                                                                                 pady=5)

        # --- 2. 中部：规则选择与编辑 ---
        self.frame_rules = ctk.CTkFrame(self)
        self.frame_rules.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.frame_rules.grid_columnconfigure(0, weight=1)  # 下拉框占据大部分宽度

        ctk.CTkLabel(self.frame_rules, text="选择整理规则:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.config_options = ["(无可用规则)"]  # 假定这里会从文件读取
        self.selected_config_name = ctk.StringVar(value=self.config_options[0])
        self.combobox_config = ctk.CTkComboBox(self.frame_rules,
                                               values=self.config_options,
                                               command=self._on_config_select,
                                               variable=self.selected_config_name)
        self.combobox_config.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # 规则操作按钮
        ctk.CTkButton(self.frame_rules, text="➕ 新建规则", command=self._open_rule_editor).grid(row=0, column=2, padx=5,
                                                                                                pady=5)
        ctk.CTkButton(self.frame_rules, text="⚙️ 编辑当前",
                      command=lambda: self._open_rule_editor(edit_mode=True)).grid(row=0, column=3, padx=5, pady=5)

        # 规则摘要显示区域（默认折叠，只有一行预览）
        self.label_config_summary = ctk.CTkLabel(self.frame_rules, text="当前规则摘要: 未选择", wraplength=700,
                                                 justify="left")
        self.label_config_summary.grid(row=1, column=0, columnspan=4, padx=5, pady=5, sticky="ew")

        # --- 3. 底部：运行与进度 ---
        self.frame_bottom = ctk.CTkFrame(self)
        self.frame_bottom.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        self.frame_bottom.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(self.frame_bottom, orientation="horizontal")
        self.progress_bar.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.progress_bar.set(0)

        self.label_status = ctk.CTkLabel(self.frame_bottom, text="状态: 准备就绪", anchor="w")
        self.label_status.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

        self.button_start = ctk.CTkButton(self.frame_bottom, text="🚀 开始整理", font=("Arial", 16, "bold"),
                                          command=self._start_organizing)
        self.button_start.grid(row=2, column=0, padx=5, pady=10, sticky="ew")

        # 通用样式字典
        # 1. 卡片样式 (去掉了边框，改用纯白背景)
        self.style_card = {
            "fg_color": COLOR_CARD,
            "corner_radius": 15,  # 大圆角
            "border_width": 0,  #
            # "border_color": "..."    # 不需要了
        }

        # 2. 按钮样式
        self.style_button_primary = {
            "fg_color": COLOR_PRIMARY,
            "hover_color": COLOR_HOVER,
            "text_color": "white",
            "corner_radius": 8,
            "font": ("微软雅黑", 12, "bold"),
            "height": 36
        }

        # 3. 输入框样式
        self.style_entry = {
            "fg_color": COLOR_ENTRY_BG,  # 浅灰底
            "border_width": 0,  # 无边框
            "text_color": COLOR_TEXT_MAIN,
            "corner_radius": 8,
            "height": 36
        }

        # --- 布局部分

        # 1. 顶部卡片：路径选择
        self.frame_top = ctk.CTkFrame(self, **self.style_card)
        # 增加 margin (pady/padx) 让卡片浮在灰色背景上
        self.frame_top.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        self.frame_top.grid_columnconfigure(1, weight=1)

        # 标签 (颜色变深灰)
        ctk.CTkLabel(self.frame_top, text="源目录", text_color=COLOR_TEXT_SUB, font=("微软雅黑", 12, "bold")).grid(
            row=0, column=0, padx=15, pady=15)
        self.entry_source_dir = ctk.CTkEntry(self.frame_top, **self.style_entry)
        self.entry_source_dir.grid(row=0, column=1, padx=5, pady=15, sticky="ew")
        ctk.CTkButton(self.frame_top, text="📂 浏览", width=80, **self.style_button_primary,
                      command=lambda: self._browse_dir(self.entry_source_dir)).grid(row=0, column=2, padx=15)

        # 目标目录 (同上，)
        ctk.CTkLabel(self.frame_top, text="目标目录", text_color=COLOR_TEXT_SUB, font=("微软雅黑", 12, "bold")).grid(
            row=1, column=0, padx=15, pady=(0, 15))
        self.entry_target_dir = ctk.CTkEntry(self.frame_top, **self.style_entry)
        self.entry_target_dir.grid(row=1, column=1, padx=5, pady=(0, 15), sticky="ew")
        ctk.CTkButton(self.frame_top, text="📂 浏览", width=80, **self.style_button_primary,
                      command=lambda: self._browse_dir(self.entry_target_dir)).grid(row=1, column=2, padx=15,
                                                                                    pady=(0, 15))

        # 2. 中部卡片
        self.frame_rules = ctk.CTkFrame(self, **self.style_card)
        self.frame_rules.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.frame_rules.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.frame_rules, text="整理规则", text_color=COLOR_TEXT_SUB, font=("微软雅黑", 12, "bold")).grid(
            row=0, column=0, padx=15, pady=15)

        # 下拉框美化
        self.combobox_config = ctk.CTkComboBox(self.frame_rules, values=["(加载中...)"],
                                               height=36, corner_radius=8,
                                               fg_color=COLOR_ENTRY_BG,  # 浅灰底
                                               border_width=0,  # 无边框
                                               button_color=COLOR_ENTRY_BG,  # 按钮同色，隐形
                                               button_hover_color="#e1e4e8",  # 悬停微灰
                                               text_color=COLOR_TEXT_MAIN,
                                               dropdown_fg_color="white",
                                               command=self._on_config_select)
        self.combobox_config.grid(row=0, column=1, padx=5, pady=15, sticky="ew")

        # 按钮组
        ctk.CTkButton(self.frame_rules, text="➕ 新建", width=80, **self.style_button_primary,
                      command=self._open_rule_editor).grid(row=0, column=2, padx=5)
        ctk.CTkButton(self.frame_rules, text="⚙️ 编辑", width=80, fg_color="#eef2f9", text_color=COLOR_PRIMARY,
                      hover_color="#dbe4f5", corner_radius=8, height=36,
                      command=lambda: self._open_rule_editor(edit_mode=True)).grid(row=0, column=3, padx=15)


        # 摘要
        self.label_config_summary = ctk.CTkLabel(self.frame_rules, text="当前规则摘要: ...", text_color="#999999",
                                                 font=("微软雅黑", 11), anchor="w")
        self.label_config_summary.grid(row=1, column=1, columnspan=3, padx=5, pady=(0, 15), sticky="ew")

        # 3. 底部卡片：操作
        self.frame_bottom = ctk.CTkFrame(self, **self.style_card)
        self.frame_bottom.grid(row=2, column=0, padx=20, pady=(10, 20), sticky="ew")
        self.frame_bottom.grid_columnconfigure(0, weight=1)

        # 进度条
        self.progress_bar = ctk.CTkProgressBar(self.frame_bottom, height=6, corner_radius=3,
                                               progress_color=COLOR_PRIMARY, fg_color="#e1e4e8")
        self.progress_bar.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        self.progress_bar.set(0)

        self.label_status = ctk.CTkLabel(self.frame_bottom, text="准备就绪", text_color="#999999",
                                         font=("微软雅黑", 11), anchor="w")
        self.label_status.grid(row=1, column=0, padx=20, pady=(0, 5), sticky="ew")

        # 大按钮 (大圆角)
        self.button_start = ctk.CTkButton(self.frame_bottom, text="🚀 立即开始整理", height=50, corner_radius=25,
                                          fg_color=COLOR_PRIMARY, hover_color=COLOR_HOVER,
                                          font=("微软雅黑", 16, "bold"),
                                          command=self._start_organizing)
        self.button_start.grid(row=2, column=0, padx=20, pady=(10, 25), sticky="ew")
        # --- 初始化 ---
        self._load_all_configs()
        self._load_last_session_settings()  # 加载上次的目录和选中的规则

    def _browse_dir(self, entry_widget):
        """打开目录选择对话框并更新 Entry 字段"""
        path = filedialog.askdirectory()
        if path:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, path)
            self._save_last_session_settings()  # 每次目录改变就保存

    def _load_all_configs(self):
        """扫描 'configs' 文件夹加载所有规则文件"""
        if not os.path.exists(SETTINGS_DIR):
            os.makedirs(SETTINGS_DIR)

        config_files = [f for f in os.listdir(SETTINGS_DIR) if f.endswith(".json")]
        self.config_options = [os.path.splitext(f)[0] for f in config_files]  # 文件名作为选项

        if not self.config_options:
            self.config_options = ["(无可用规则)"]

        self.combobox_config.configure(values=self.config_options)

        if self.config_options[0] == "(无可用规则)" or not self.selected_config_name.get() in self.config_options:
            self.selected_config_name.set(self.config_options[0])
            self.label_config_summary.configure(text="当前规则摘要: 未选择")
        else:
            # 重新加载时保持选中状态
            self.combobox_config.set(self.selected_config_name.get())
            self._on_config_select(self.selected_config_name.get())  # 刷新摘要

    def _on_config_select(self, config_name):
        """当用户选择不同的规则时更新摘要"""
        if config_name == "(无可用规则)":
            self.label_config_summary.configure(text="当前规则摘要: 未选择")
            self.current_config_data = {}
            return

        config_path = os.path.join(SETTINGS_DIR, config_name + ".json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.current_config_data = json.load(f)
                    # TODO: 根据 self.current_config_data 生成一个友好的摘要文本
                    summary_text = f"模式: {self.current_config_data.get('operation_mode', '剪切').capitalize()} | " \
                                   f"命名: {self.current_config_data.get('output_preview', '待配置')} | " \
                                   f"清理: {', '.join(self.current_config_data.get('delete_extensions', [])) or '无'}"
                    self.label_config_summary.configure(text=f"当前规则摘要: {summary_text}")
            except Exception as e:
                messagebox.showerror("错误", f"加载规则 '{config_name}' 失败: {e}")
                self.label_config_summary.configure(text="当前规则摘要: 加载失败")
                self.current_config_data = {}
        else:
            self.label_config_summary.configure(text="当前规则摘要: 文件不存在")
            self.current_config_data = {}

        self._save_last_session_settings()  # 保存当前选中的规则

    def _open_rule_editor(self, edit_mode=False):
        """打开规则编辑器窗口"""
        from rule_editor import RuleEditorApp  # 动态导入，避免循环依赖

        editor_window = ctk.CTkToplevel(self)
        editor_window.title("规则编辑器" if edit_mode else "新建整理规则")
        editor_window.geometry("1000x800")  # 编辑器窗口可能需要更大

        initial_config = None
        if edit_mode and self.selected_config_name.get() != "(无可用规则)":
            config_path = os.path.join(SETTINGS_DIR, self.selected_config_name.get() + ".json")
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    initial_config = json.load(f)
            else:
                messagebox.showwarning("提示", "当前规则文件不存在，将创建新规则。")

        # 实例化编辑器，传入主窗口引用和初始配置
        RuleEditorApp(editor_window, self, initial_config, edit_mode)
        editor_window.transient(self)  # 1. 告诉系统这个弹窗从属于主窗口 (一直在上面)
        editor_window.grab_set()  # 2. 独占模式：在关闭它之前，不能点主窗口
        editor_window.focus_force()  # 3. 强行获取焦点

        # 监听编辑器窗口关闭事件，刷新配置列表
        self.wait_window(editor_window)
        self._load_all_configs()  # 刷新下拉框内容，因为可能新增或修改了规则

    def _start_organizing(self):
        """开始文件整理任务，使用线程防止界面卡顿"""
        source_dir = self.entry_source_dir.get()
        target_dir = self.entry_target_dir.get()
        config_name = self.selected_config_name.get()

        if not source_dir or not target_dir:
            messagebox.showerror("错误", "请选择源目录和目标目录。")
            return
        if not os.path.exists(source_dir):
            messagebox.showerror("错误", "源目录不存在。")
            return
        if not os.path.exists(target_dir):
            messagebox.showerror("错误", "目标目录不存在。")
            return
        if config_name == "(无可用规则)":
            messagebox.showwarning("警告", "未选择整理规则，请新建或选择一个规则。")
            return
        if not self.current_config_data:
            messagebox.showerror("错误", "当前规则数据无效，请编辑或选择有效规则。")
            return

        # 禁用按钮，显示进度
        self.button_start.configure(state="disabled", text="正在整理...")
        self.progress_bar.set(0)
        self.label_status.configure(text="状态: 正在整理文件...")

        # 使用线程运行实际的文件处理逻辑
        threading.Thread(target=self._run_organizing_logic, daemon=True).start()

    def _run_organizing_logic(self):
        """这里是实际的文件处理逻辑，会更新进度条和状态"""
        # from organizer_core import OrganizerCore # 再次导入，确保在线程中可用

        # # 假定 OrganizerCore 接收配置数据，并有一个 process 方法
        # core = OrganizerCore(self.current_config_data)
        #
        # def update_progress_callback(current, total, filename=""):
        #     # 在主线程更新UI
        #     self.after(0, lambda: self._update_ui_progress(current, total, filename))
        #
        # stats = core.process_files(self.entry_source_dir.get(), self.entry_target_dir.get(), update_progress_callback)
        #
        # self.after(0, lambda: self._show_completion_message(stats))

        # --- 模拟耗时操作 ---
        total_steps = 100
        for i in range(total_steps):
            time.sleep(0.05)  # 模拟文件处理时间
            self.after(0, lambda i=i: self._update_ui_progress(i + 1, total_steps, f"模拟文件_{i + 1}.mp4"))

        # 模拟完成，显示结果
        stats = {'moved': 50, 'deleted': 5, 'errors': 2}
        self.after(0, lambda: self._show_completion_message(stats))

    def _update_ui_progress(self, current, total, filename=""):
        """在主线程中更新UI (进度条和状态标签)"""
        if total == 0:
            progress_value = 0
        else:
            progress_value = current / total

        self.progress_bar.set(progress_value)
        self.label_status.configure(text=f"状态: 正在处理 {filename} ({current}/{total})")

    def _show_completion_message(self, stats):
        """任务完成后显示消息框并重置UI"""
        messagebox.showinfo("任务完成", f"整理任务已完成！\n"
                                        f"移动/复制文件: {stats.get('moved', 0)} 个\n"
                                        f"删除文件: {stats.get('deleted', 0)} 个\n"
                                        f"处理错误: {stats.get('errors', 0)} 个")
        self.label_status.configure(text="状态: 整理完成")
        self.progress_bar.set(0)
        self.button_start.configure(state="normal", text="🚀 开始整理")

    def _save_last_session_settings(self):
        """保存上次会话的目录和选中的规则"""
        session_settings = {
            "last_source_dir": self.entry_source_dir.get(),
            "last_target_dir": self.entry_target_dir.get(),
            "last_selected_config": self.selected_config_name.get()
        }
        with open("last_session.json", 'w', encoding='utf-8') as f:
            json.dump(session_settings, f, indent=4)

    def _load_last_session_settings(self):
        """加载上次会话的目录和选中的规则"""
        if os.path.exists("last_session.json"):
            try:
                with open("last_session.json", 'r', encoding='utf-8') as f:
                    session_settings = json.load(f)
                    # 1. 设置源目录
                    last_source = session_settings.get("last_source_dir", "")
                    self.entry_source_dir.delete(0, "end")  # 先清空
                    self.entry_source_dir.insert(0, last_source)  # 再写入

                    # 2. 设置目标目录
                    last_target = session_settings.get("last_target_dir", "")
                    self.entry_target_dir.delete(0, "end")  # 先清空
                    self.entry_target_dir.insert(0, last_target)  # 再写入


                    last_config = session_settings.get("last_selected_config", "")
                    if last_config in self.config_options:
                        self.selected_config_name.set(last_config)
                        self._on_config_select(last_config)  # 刷新摘要
                    else:
                        self.selected_config_name.set(self.config_options[0])
                        self.label_config_summary.configure(text="当前规则摘要: 未选择")
            except Exception as e:
                print(f"加载上次会话设置失败: {e}")


if __name__ == "__main__":
    import time  # 用于模拟耗时操作

    app = MainApp()
    app.mainloop()
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from typing import List, Tuple, Dict
import sys
from datetime import datetime
import subprocess
import platform
import threading
import queue

# 尝试导入windnd库（仅Windows平台）
DRAG_DROP_AVAILABLE = False
if platform.system() == "Windows":
    try:
        import windnd
        DRAG_DROP_AVAILABLE = True
    except ImportError:
        DRAG_DROP_AVAILABLE = False

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.pdf_processor import PDFTitleExtractor

# 定义文件状态常量
class FileStatus:
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"

class MainWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("PDF文件标题提取器")
        self.root.geometry("1000x700")
        
        self.pdf_processor = PDFTitleExtractor()
        # 存储文件信息的字典
        self.file_info = {}  # {filename: {"path": str, "status": FileStatus, "error": str}}
        
        self.setup_ui()
        self.setup_bindings()
        
    def setup_ui(self):
        # 创建主框架
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建工具栏
        self.create_toolbar()
        
        # 创建主容器（使用PanedWindow）
        self.paned = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        # 文件列表面板
        self.create_file_list_panel()
        
        # 预览面板
        self.create_preview_panel()
        
        # 状态栏
        self.create_status_bar()
        
        # 配置右键菜单
        self.create_context_menu()
        
    def create_toolbar(self):
        """创建工具栏"""
        self.toolbar = ttk.Frame(self.main_frame)
        self.toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        # 文件操作组
        ttk.Button(self.toolbar, text="选择文件", command=self.select_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.toolbar, text="选择文件夹", command=self.select_directory).pack(side=tk.LEFT, padx=2)
        ttk.Separator(self.toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)
        
        # 列表操作组
        ttk.Button(self.toolbar, text="清空列表", command=self.clear_list).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.toolbar, text="移除已处理", command=self.remove_processed).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.toolbar, text="移除选中", command=self.remove_selected).pack(side=tk.LEFT, padx=2)
        ttk.Separator(self.toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=5, fill=tk.Y)
        
        # 批处理操作组
        ttk.Button(self.toolbar, text="批量预览", command=self.preview_batch_rename).pack(side=tk.LEFT, padx=2)
        self.batch_button = ttk.Button(self.toolbar, text="批量处理", command=self.start_batch_process)
        self.batch_button.pack(side=tk.LEFT, padx=2)
        self.stop_button = ttk.Button(self.toolbar, text="停止", command=self.stop_batch_process, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=2)
        
    def create_file_list_panel(self):
        """创建文件列表面板"""
        self.file_list_frame = ttk.LabelFrame(self.paned, text="文件列表")
        self.paned.add(self.file_list_frame, weight=1)
        
        # 创建Treeview替代Listbox
        columns = ("文件名", "状态", "大小", "修改时间")
        self.file_tree = ttk.Treeview(self.file_list_frame, columns=columns, show="headings")
        
        # 配置列
        self.file_tree.heading("文件名", text="文件名")
        self.file_tree.heading("状态", text="状态")
        self.file_tree.heading("大小", text="大小")
        self.file_tree.heading("修改时间", text="修改时间")
        
        self.file_tree.column("文件名", width=200)
        self.file_tree.column("状态", width=80)
        self.file_tree.column("大小", width=80)
        self.file_tree.column("修改时间", width=120)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(self.file_list_frame, orient=tk.VERTICAL, command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=scrollbar.set)
        
        # 布局
        self.file_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 配置拖放功能（Windows平台）
        if DRAG_DROP_AVAILABLE:
            windnd.hook_dropfiles(self.file_tree, func=self.handle_drop_files)
            # 添加支持拖放的提示
            ttk.Label(self.file_list_frame, text="支持拖放文件或文件夹到此处").pack(side=tk.BOTTOM, pady=5)
        else:
            ttk.Label(self.file_list_frame, text="拖放功能不可用，请使用'选择文件'或'选择文件夹'按钮导入文件").pack(side=tk.BOTTOM, pady=5)
        
    def create_preview_panel(self):
        """创建预览面板"""
        self.preview_frame = ttk.LabelFrame(self.paned, text="文件预览")
        self.paned.add(self.preview_frame, weight=1)
        
        # 文件信息区域
        self.info_frame = ttk.LabelFrame(self.preview_frame, text="文件信息")
        self.info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.file_info_text = tk.Text(self.info_frame, height=4, wrap=tk.WORD)
        self.file_info_text.pack(fill=tk.X, padx=5, pady=5)
        
        # 标题选择区域
        self.title_frame = ttk.LabelFrame(self.preview_frame, text="标题选择")
        self.title_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.title_var = tk.StringVar()
        self.title_radios = []
        
        # 自定义标题输入
        ttk.Label(self.title_frame, text="自定义标题:").pack(fill=tk.X, pady=5)
        self.custom_title_entry = ttk.Entry(self.title_frame)
        self.custom_title_entry.pack(fill=tk.X, pady=5)
        
        # 预览新文件名
        ttk.Label(self.title_frame, text="预览新文件名:").pack(fill=tk.X, pady=5)
        self.preview_label = ttk.Label(self.title_frame, text="", wraplength=300)
        self.preview_label.pack(fill=tk.X, pady=5)
        
        # 确认重命名按钮
        self.rename_button = ttk.Button(self.preview_frame, text="确认重命名", command=self.rename_selected_file)
        self.rename_button.pack(pady=10)
        
    def create_status_bar(self):
        """创建状态栏"""
        self.status_bar = ttk.Frame(self.main_frame)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=2)
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self.status_bar, 
            mode='determinate', 
            variable=self.progress_var
        )
        self.progress_bar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        
        # 状态信息
        self.status_label = ttk.Label(self.status_bar, text="就绪")
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        self.file_count_label = ttk.Label(self.status_bar, text="文件数: 0")
        self.file_count_label.pack(side=tk.RIGHT, padx=5)
        
        # 处理队列和标志
        self.process_queue = queue.Queue()
        self.is_processing = False
        
    def create_context_menu(self):
        """创建右键菜单"""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="在资源管理器中显示", command=self.show_in_explorer)
        self.context_menu.add_command(label="复制文件名", command=self.copy_filename)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="从列表中移除", command=self.remove_selected)
        self.context_menu.add_command(label="重置状态", command=self.reset_status)
        
    def setup_bindings(self):
        """设置快捷键和事件绑定"""
        self.file_tree.bind('<<TreeviewSelect>>', self.on_select_file)
        self.file_tree.bind('<Button-3>', self.show_context_menu)
        self.root.bind('<Delete>', lambda e: self.remove_selected())
        self.root.bind('<Control-a>', self.select_all)
        
    def show_context_menu(self, event):
        """显示右键菜单"""
        if self.file_tree.selection():
            self.context_menu.post(event.x_root, event.y_root)
            
    def show_in_explorer(self):
        """在资源管理器中显示选中的文件"""
        selection = self.file_tree.selection()
        if not selection:
            return
            
        filename = self.file_tree.item(selection[0])['values'][0]
        file_path = self.file_info[filename]['path']
        
        if platform.system() == "Windows":
            subprocess.run(['explorer', '/select,', file_path])
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(['open', '-R', file_path])
            
    def copy_filename(self):
        """复制选中的文件名到剪贴板"""
        selection = self.file_tree.selection()
        if not selection:
            return
            
        filename = self.file_tree.item(selection[0])['values'][0]
        self.root.clipboard_clear()
        self.root.clipboard_append(filename)
        
    def select_all(self, event=None):
        """选择所有文件"""
        for item in self.file_tree.get_children():
            self.file_tree.selection_add(item)
            
    def clear_list(self):
        """清空文件列表"""
        if messagebox.askyesno("确认", "确定要清空文件列表吗？"):
            self.file_tree.delete(*self.file_tree.get_children())
            self.file_info.clear()
            self.update_status()
            
    def remove_processed(self):
        """移除已处理的文件"""
        for item in self.file_tree.get_children():
            values = self.file_tree.item(item)['values']
            if values[1] == FileStatus.SUCCESS:
                self.file_tree.delete(item)
                filename = values[0]
                if filename in self.file_info:
                    del self.file_info[filename]
        self.update_status()
        
    def remove_selected(self):
        """移除选中的文件"""
        selection = self.file_tree.selection()
        for item in selection:
            values = self.file_tree.item(item)['values']
            filename = values[0]
            self.file_tree.delete(item)
            if filename in self.file_info:
                del self.file_info[filename]
        self.update_status()
        
    def reset_status(self):
        """重置选中文件的状态"""
        selection = self.file_tree.selection()
        for item in selection:
            values = self.file_tree.item(item)['values']
            filename = values[0]
            if filename in self.file_info:
                self.file_info[filename]['status'] = FileStatus.PENDING
                self.file_info[filename]['error'] = ""
                self.file_tree.set(item, "状态", FileStatus.PENDING)
        
    def update_status(self):
        """更新状态栏信息"""
        total = len(self.file_tree.get_children())
        success = sum(1 for item in self.file_tree.get_children() 
                     if self.file_tree.item(item)['values'][1] == FileStatus.SUCCESS)
        failed = sum(1 for item in self.file_tree.get_children() 
                    if self.file_tree.item(item)['values'][1] == FileStatus.FAILED)
        
        self.file_count_label.config(
            text=f"总计: {total} | 成功: {success} | 失败: {failed}"
        )
        
    def get_file_size_str(self, size_in_bytes: int) -> str:
        """将文件大小转换为人类可读的格式"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_in_bytes < 1024:
                return f"{size_in_bytes:.1f}{unit}"
            size_in_bytes /= 1024
        return f"{size_in_bytes:.1f}GB"
        
    def add_file_to_list(self, file_path: str):
        """添加文件到列表，避免重复"""
        file_path = os.path.abspath(file_path)
        filename = os.path.basename(file_path)
        
        # 检查文件是否已在列表中
        for item in self.file_tree.get_children():
            if self.file_tree.item(item)['values'][0] == filename:
                return
                
        # 获取文件信息
        file_stat = os.stat(file_path)
        size_str = self.get_file_size_str(file_stat.st_size)
        mod_time = datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M')
        
        # 添加到树形列表
        self.file_tree.insert('', 'end', values=(
            filename,
            FileStatus.PENDING,
            size_str,
            mod_time
        ))
        
        # 保存文件信息
        self.file_info[filename] = {
            "path": file_path,
            "status": FileStatus.PENDING,
            "error": ""
        }
        
        self.update_status()
        
    def handle_drop_files(self, file_paths):
        """处理拖放文件 - 支持windnd库"""
        for file_path in file_paths:
            # windnd返回的是字节字符串，需要解码
            if isinstance(file_path, bytes):
                file_path = file_path.decode('gbk')  # Windows中文环境通常使用GBK编码
                
            if os.path.isdir(file_path):
                # 如果是文件夹，添加其中的所有PDF文件
                for root, _, files in os.walk(file_path):
                    for file in files:
                        if file.lower().endswith('.pdf'):
                            full_path = os.path.join(root, file)
                            self.add_file_to_list(full_path)
            elif file_path.lower().endswith('.pdf'):
                # 如果是PDF文件，直接添加
                self.add_file_to_list(file_path)
        
    def on_select_file(self, event):
        """处理文件选择事件"""
        selection = self.file_tree.selection()
        if not selection:
            return
            
        # 获取选中的文件信息
        item = selection[0]
        values = self.file_tree.item(item)['values']
        filename = values[0]
        file_info = self.file_info.get(filename)
        
        if not file_info:
            return
            
        # 更新文件信息显示
        file_path = file_info['path']
        file_stat = os.stat(file_path)
        
        info_text = f"文件名: {filename}\n"
        info_text += f"路径: {file_path}\n"
        info_text += f"大小: {self.get_file_size_str(file_stat.st_size)}\n"
        info_text += f"修改时间: {datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}"
        
        self.file_info_text.delete('1.0', tk.END)
        self.file_info_text.insert('1.0', info_text)
        
        # 清除现有的单选按钮
        for radio in self.title_radios:
            radio.destroy()
        self.title_radios.clear()
        
        # 获取标题候选列表
        candidates = self.pdf_processor.extract_title_candidates(file_path)
        
        # 创建新的单选按钮
        for i, (title, size) in enumerate(candidates):
            radio = ttk.Radiobutton(
                self.title_frame,
                text=f"[字体大小: {size:.1f}] {title}",
                value=title,
                variable=self.title_var,
                command=self.update_preview
            )
            radio.pack(fill=tk.X, pady=2)
            self.title_radios.append(radio)
            
        if candidates:
            self.title_var.set(candidates[0][0])
            self.update_preview()
            
    def rename_selected_file(self):
        """重命名选中的文件"""
        selection = self.file_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个文件")
            return
            
        item = selection[0]
        values = self.file_tree.item(item)['values']
        filename = values[0]
        file_info = self.file_info.get(filename)
        
        if not file_info:
            messagebox.showerror("错误", f"找不到文件 {filename} 的信息")
            return
            
        title = self.title_var.get()
        
        # 如果自定义标题不为空，使用自定义标题
        custom_title = self.custom_title_entry.get().strip()
        if custom_title:
            title = custom_title
            
        try:
            new_filename = self.pdf_processor.process_filename(title, filename)
            new_path = os.path.join(os.path.dirname(file_info['path']), new_filename)
            
            # 检查目标文件是否已存在
            if os.path.exists(new_path):
                if not messagebox.askyesno("文件已存在", 
                    f"文件 {new_filename} 已存在，是否覆盖？"):
                    return
                    
            os.rename(file_info['path'], new_path)
            
            # 更新文件信息
            self.file_info[new_filename] = {
                "path": new_path,
                "status": FileStatus.SUCCESS,
                "error": ""
            }
            del self.file_info[filename]
            
            # 更新树形列表
            self.file_tree.set(item, "文件名", new_filename)
            self.file_tree.set(item, "状态", FileStatus.SUCCESS)
            
            self.update_status()
            messagebox.showinfo("成功", f"文件已重命名为:\n{new_filename}")
            
        except Exception as e:
            self.file_info[filename]['status'] = FileStatus.FAILED
            self.file_info[filename]['error'] = str(e)
            self.file_tree.set(item, "状态", FileStatus.FAILED)
            self.update_status()
            messagebox.showerror("错误", f"重命名失败: {str(e)}")
            
    def select_file(self):
        """选择文件"""
        filetypes = (("PDF files", "*.pdf"), ("All files", "*.*"))
        files = filedialog.askopenfilenames(filetypes=filetypes)
        for file in files:
            self.add_file_to_list(file)
            
    def select_directory(self):
        """选择文件夹"""
        directory = filedialog.askdirectory()
        if directory:
            for root, _, files in os.walk(directory):
                for file in files:
                    if file.lower().endswith('.pdf'):
                        full_path = os.path.join(root, file)
                        self.add_file_to_list(full_path)
                        
    def update_preview(self):
        """更新预览"""
        selection = self.file_tree.selection()
        if not selection:
            return
            
        filename = self.file_tree.item(selection[0])['values'][0]
        title = self.title_var.get()
        
        # 如果自定义标题不为空，使用自定义标题
        custom_title = self.custom_title_entry.get().strip()
        if custom_title:
            title = custom_title
            
        new_filename = self.pdf_processor.process_filename(title, filename)
        self.preview_label.config(text=new_filename)
        
    def preview_batch_rename(self):
        """批量预览重命名结果"""
        preview_window = tk.Toplevel(self.root)
        preview_window.title("批量重命名预览")
        preview_window.geometry("800x600")
        
        # 创建预览列表
        columns = ("原文件名", "新文件名")
        preview_tree = ttk.Treeview(preview_window, columns=columns, show="headings")
        preview_tree.heading("原文件名", text="原文件名")
        preview_tree.heading("新文件名", text="新文件名")
        preview_tree.column("原文件名", width=350)
        preview_tree.column("新文件名", width=350)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(preview_window, orient=tk.VERTICAL, command=preview_tree.yview)
        preview_tree.configure(yscrollcommand=scrollbar.set)
        
        # 获取待处理的文件
        pending_items = [
            item for item in self.file_tree.get_children()
            if self.file_tree.item(item)['values'][1] != FileStatus.SUCCESS
        ]
        
        # 生成预览数据
        for item in pending_items:
            filename = self.file_tree.item(item)['values'][0]
            file_path = self.file_info[filename]['path']
            
            # 提取标题
            title_candidates = self.pdf_processor.extract_title_candidates(file_path)
            if title_candidates:
                title = title_candidates[0][0]
                new_filename = self.pdf_processor.process_filename(title, filename)
                preview_tree.insert("", tk.END, values=(filename, new_filename))
        
        # 布局
        preview_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 添加按钮
        button_frame = ttk.Frame(preview_window)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(button_frame, text="确认重命名", 
                   command=lambda: self.start_batch_process(preview_window)).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="取消", 
                   command=preview_window.destroy).pack(side=tk.RIGHT)
    
    def start_batch_process(self, preview_window=None):
        """开始批量处理"""
        if self.is_processing:
            return
            
        # 获取待处理的文件
        pending_items = [
            item for item in self.file_tree.get_children()
            if self.file_tree.item(item)['values'][1] != FileStatus.SUCCESS
        ]
        
        if not pending_items:
            messagebox.showinfo("提示", "没有待处理的文件")
            return
            
        if preview_window:
            preview_window.destroy()
        else:
            if not messagebox.askyesno("确认", f"是否要处理 {len(pending_items)} 个文件？"):
                return
            
        # 更新UI状态
        self.is_processing = True
        self.batch_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.progress_var.set(0)
        
        # 将待处理文件加入队列
        for item in pending_items:
            self.process_queue.put(item)
            
        # 启动处理线程
        total_files = len(pending_items)
        self.processed_count = 0
        
        def process_thread():
            while not self.process_queue.empty() and self.is_processing:
                item = self.process_queue.get()
                self.process_single_file(item)
                self.processed_count += 1
                progress = (self.processed_count / total_files) * 100
                self.progress_var.set(progress)
                self.status_label.config(text=f"正在处理: {self.processed_count}/{total_files}")
                self.root.update()
                
            # 处理完成或被中止
            self.is_processing = False
            self.batch_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            
            if not self.process_queue.empty():
                self.status_label.config(text="处理已中止")
            else:
                self.status_label.config(text="处理完成")
                messagebox.showinfo("完成", "批量处理已完成")
                
        threading.Thread(target=process_thread, daemon=True).start()
        
    def stop_batch_process(self):
        """停止批量处理"""
        if self.is_processing:
            if messagebox.askyesno("确认", "确定要停止处理吗？"):
                self.is_processing = False
                
    def process_single_file(self, item):
        """处理单个文件"""
        values = self.file_tree.item(item)['values']
        filename = values[0]
        file_info = self.file_info.get(filename)
        
        if not file_info or values[1] == FileStatus.SUCCESS:
            return
            
        try:
            # 获取标题
            file_path = file_info['path']
            candidates = self.pdf_processor.extract_title_candidates(file_path)
            
            if not candidates:
                raise Exception("无法提取标题")
                
            title = candidates[0][0]  # 使用第一个候选标题
            
            # 生成新文件名
            new_filename = self.pdf_processor.process_filename(title, filename)
            new_path = os.path.join(os.path.dirname(file_path), new_filename)
            
            # 检查文件是否存在
            if os.path.exists(new_path):
                base, ext = os.path.splitext(new_path)
                counter = 1
                while os.path.exists(new_path):
                    new_path = f"{base}_{counter}{ext}"
                    counter += 1
                    
            # 重命名文件
            os.rename(file_path, new_path)
            
            # 更新文件信息
            self.file_info[new_filename] = {
                "path": new_path,
                "status": FileStatus.SUCCESS,
                "error": ""
            }
            del self.file_info[filename]
            
            # 更新UI
            self.file_tree.set(item, "文件名", new_filename)
            self.file_tree.set(item, "状态", FileStatus.SUCCESS)
            
        except Exception as e:
            self.file_info[filename]['status'] = FileStatus.FAILED
            self.file_info[filename]['error'] = str(e)
            self.file_tree.set(item, "状态", FileStatus.FAILED)
            
        self.update_status()
        
    def run(self):
        self.root.mainloop()
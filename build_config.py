import sys
import os
from PyInstaller.__main__ import run

def build():
    # 基本配置参数
    common_options = [
        'main.py',  # 主程序入口
        '--name=PDF文件标题提取器',  # 程序名称
        '--noconsole',  # 不显示控制台窗口
        '--clean',  # 清理临时文件
        '--add-data=resources;resources',  # 添加资源文件夹
        '--hidden-import=tkinter',  # 添加tkinter
        '--hidden-import=tkinter.ttk',  # 添加tkinter.ttk
        '--hidden-import=windnd',  # 添加windnd库
        '--onefile',  # 打包成单个文件
    ]
    
    # Windows特定配置
    if sys.platform.startswith('win'):
        options = common_options + [
            '--icon=resources/app_icon.ico',  # Windows图标
            '--add-data=resources;resources',  # Windows路径分隔符是分号
        ]
    # macOS特定配置
    elif sys.platform.startswith('darwin'):
        options = common_options + [
            '--icon=resources/app_icon.png',  # 使用PNG图标代替icns
            '--add-data=resources:resources',  # macOS路径分隔符是冒号
            '--target-arch=universal2',  # 支持Intel和Apple Silicon
        ]
    else:
        print("不支持的操作系统")
        return
    
    # 运行PyInstaller
    run(options)

if __name__ == '__main__':
    build()
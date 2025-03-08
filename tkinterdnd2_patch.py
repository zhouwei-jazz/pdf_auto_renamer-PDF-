"""
tkinterdnd2 补丁文件，用于修复 PyInstaller 打包时的导入问题
"""
import os
import sys
import tkinter

# 添加 tix 模块的替代方案
if not hasattr(tkinter, 'tix'):
    tkinter.tix = None

# 确保 tkinterdnd2 可以正确导入
def patch_tkinterdnd2():
    try:
        import tkinterdnd2
        print("tkinterdnd2 已成功导入")
        return True
    except ImportError as e:
        print(f"tkinterdnd2 导入失败: {e}")
        return False

if __name__ == "__main__":
    patch_tkinterdnd2() 
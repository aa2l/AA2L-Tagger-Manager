import os
import sys
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog
from .config import PROJECT_ROOT

def select_output_directory():
    """弹出文件夹选择对话框，返回所选路径"""
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    path = filedialog.askdirectory(title="选择输出目录")
    root.destroy()
    return path if path else ""

def open_folder_thread(path):
    try:
        if sys.platform == 'win32':
            subprocess.Popen(['explorer', path])
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', path])
        else:
            subprocess.Popen(['xdg-open', path])
    except Exception as e:
        print(f"打开文件夹失败: {e}")

def open_output_folder(folder_path: str):
    abs_path = os.path.abspath(folder_path)
    if not os.path.exists(abs_path):
        try:
            os.makedirs(abs_path, exist_ok=True)
        except Exception as e:
            return f"创建目录失败: {e}"
    threading.Thread(target=open_folder_thread, args=(abs_path,), daemon=True).start()
    return f"正在打开文件夹: {abs_path}"

def get_images_in_folder(folder):
    """递归获取文件夹下所有图片文件路径"""
    if not os.path.exists(folder):
        return []
    exts = ('.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp')
    images = []
    for root, dirs, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(exts):
                images.append(os.path.join(root, f))
    return sorted(images)
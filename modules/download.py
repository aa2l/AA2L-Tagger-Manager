import os
import sys
import threading
import subprocess
import gradio as gr
from .utils import get_images_in_folder
from .config import DEFAULT_DOWNLOAD_DIR

# ================= 下载训练集模块 =================
download_process = None
download_stop_flag = False

def check_gallery_dl():
    try:
        subprocess.run(['gallery-dl', '--version'], capture_output=True, check=True)
        return True
    except:
        return False

def install_gallery_dl():
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'gallery-dl'], check=True)
        return True
    except:
        return False

def get_images_in_folder(folder):
    if not os.path.exists(folder):
        return []
    exts = ('.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp')
    images = []
    for root, dirs, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(exts):
                images.append(os.path.join(root, f))
    return sorted(images)

def download_in_thread(urls_text, output_dir):
    global download_process, download_stop_flag
    download_stop_flag = False
    urls = [line.strip() for line in urls_text.strip().splitlines() if line.strip()]
    if not urls:
        gr.Warning("未输入任何URL")
        return
    os.makedirs(output_dir, exist_ok=True)
    if not check_gallery_dl():
        gr.Info("未找到 gallery-dl，正在尝试安装...")
        if install_gallery_dl():
            gr.Info("gallery-dl 安装成功，继续下载...")
        else:
            gr.Warning("gallery-dl 安装失败，请手动运行：pip install gallery-dl")
            return
    total = len(urls)
    for idx, url in enumerate(urls):
        if download_stop_flag:
            gr.Info(f"用户停止下载，已处理 {idx}/{total} 个URL")
            break
        cmd = ['gallery-dl', '-d', output_dir, url]
        process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        download_process = process
        process.wait()
        if process.returncode == 0:
            gr.Info(f"已完成 {idx+1}/{total}: {url}")
        else:
            gr.Warning(f"下载失败 {idx+1}/{total}: {url}")
        download_process = None
    gr.Info("全部下载完成")

def start_download(urls_text, output_dir):
    thread = threading.Thread(target=download_in_thread, args=(urls_text, output_dir), daemon=True)
    thread.start()
    gr.Info("已开始下载，请稍后点击「刷新预览」查看结果")
    return None

def stop_download():
    global download_process, download_stop_flag
    download_stop_flag = True
    if download_process is not None:
        download_process.terminate()
        gr.Info("正在停止下载...")
    else:
        gr.Info("没有正在进行的下载")
    return None

def refresh_preview(folder):
    return get_images_in_folder(folder)

def delete_selected_image(folder, idx, current_images):
    # 重新扫描目录获取最新文件列表，避免使用可能过期的 current_images
    all_images = get_images_in_folder(folder)
    if idx is None or idx < 0 or idx >= len(all_images):
        gr.Warning("未选中有效图片（请先点击图片选中）")
        return gr.update(), -1, "未选中"
    file_path = all_images[idx]
    try:
        os.remove(file_path)
        new_images = get_images_in_folder(folder)
        gr.Info(f"已删除 {os.path.basename(file_path)}")
        return gr.update(value=new_images), -1, "已清除选中"
    except Exception as e:
        gr.Warning(f"删除失败: {e}")
        return gr.update(), -1, "删除失败"

def clear_all_images(folder):
    if not os.path.exists(folder):
        gr.Warning("文件夹不存在")
        return [], -1, "未选中"
    count = 0
    for root, dirs, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp')):
                try:
                    os.remove(os.path.join(root, f))
                    count += 1
                except:
                    pass
    new_images = get_images_in_folder(folder)
    gr.Info(f"已删除 {count} 张图片")
    return new_images, -1, "已清空，选中已重置"
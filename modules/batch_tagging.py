import os
import re
import inspect
import shutil
from PIL import Image
from typing import List
import gradio as gr
from .model_loader import get_tagger
from .config import DEFAULT_OUTPUT_DIR

def batch_tagging(files: List, output_dir: str, threshold: float, resize_mode: str,
                  enable_batch: bool, batch_size: int, copy_images: bool,
                  rename_sequential: bool, progress=gr.Progress()):
    if not files:
        return "请上传图片文件", None

    image_paths = []
    original_basenames = []
    ext_list = []
    for file in files:
        if isinstance(file, tuple):
            file_path = file[0]          
        elif hasattr(file, 'name'):      
            file_path = file.name
        elif isinstance(file, str):
            file_path = file
        else:
            continue                    
        if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
            image_paths.append(file_path)
            base = os.path.splitext(os.path.basename(file_path))[0]
            ext = os.path.splitext(file_path)[1]
            original_basenames.append(base)
            ext_list.append(ext)

    output_text_paths = []
    if rename_sequential:
        for idx, ext in enumerate(ext_list, start=1):
            txt_path = os.path.join(output_dir, f"{idx}.txt")
            output_text_paths.append(txt_path)
    else:
        for base in original_basenames:
            txt_path = os.path.join(output_dir, f"{base}.txt")
            output_text_paths.append(txt_path)

    try:
        target_size = None
        if resize_mode.startswith("手动缩放"):
            match = re.search(r'(\d+)x(\d+)', resize_mode)
            if match:
                w = int(match.group(1))
                h = int(match.group(2))
                target_size = (w, h)

        images = []
        for path in image_paths:
            img = Image.open(path).convert('RGB')
            if target_size is not None:
                img = img.resize(target_size, Image.Resampling.LANCZOS)
            images.append(img)

        progress(0, desc="正在加载模型...")
        tagger = get_tagger()
        sig = inspect.signature(tagger.tag)
        kwargs = {}
        if 'general_threshold' in sig.parameters and 'character_threshold' in sig.parameters:
            kwargs['general_threshold'] = threshold
            kwargs['character_threshold'] = threshold
        elif 'threshold' in sig.parameters:
            kwargs['threshold'] = threshold
        else:
            print("警告: 当前版本的 tag 方法不支持设置阈值，将使用默认值。")
        
        total = len(images)
        results = []
        if not enable_batch:
            progress(0.1, desc="全批量处理中...")
            results = tagger.tag(images, **kwargs)
            progress(1.0, desc="处理完成！")
        else:
            batch_size = max(1, min(batch_size, 21))
            for start_idx in range(0, total, batch_size):
                end_idx = min(start_idx + batch_size, total)
                batch = images[start_idx:end_idx]
                batch_results = tagger.tag(batch, **kwargs)
                results.extend(batch_results)
                progress(end_idx / total, desc=f"正在处理图片 {end_idx}/{total}")

        tags_list = []
        for result, output_path in zip(results, output_text_paths):
            all_tag_list = result.general_tags + result.character_tags
            tags_str = ', '.join(all_tag_list)
            tags_list.append(tags_str)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(tags_str)
        
        if copy_images:
            for idx, src_path in enumerate(image_paths):
                ext = os.path.splitext(src_path)[1]
                if rename_sequential:
                    dest_name = f"{idx+1}{ext}"
                else:
                    dest_name = os.path.basename(src_path)
                dest_path = os.path.join(output_dir, dest_name)
                shutil.copy2(src_path, dest_path)
        
        progress(1.0, desc="处理完成！")
        return f"成功处理 {len(files)} 张图片并输出文件", tags_list
    except Exception as e:
        return f"批量打标过程中出错: {str(e)}", None
    pass
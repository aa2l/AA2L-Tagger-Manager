import os
import gradio as gr

def transfer_and_refresh(output_dir):
    """
    传输标签文件至批量修改界面
    返回: (target_dir 的 update, status 文本, preview_summary 文本, preview_text 文本)
    """
    if not os.path.exists(output_dir):
        return gr.update(value=""), "输出目录不存在，请先打标生成文件。", "", ""
    txt_files = [f for f in os.listdir(output_dir) if f.endswith('.txt')]
    if not txt_files:
        return gr.update(value=output_dir), "当前目录下无打标.txt文件", "", ""
    
    # 动态导入预览函数，避免循环依赖
    from modules.modify_tags import preview_tags_from_dir
    summary, text = preview_tags_from_dir(output_dir)
    return gr.update(value=output_dir), f"已将输出目录设置为 {output_dir}，并加载预览。", summary, text
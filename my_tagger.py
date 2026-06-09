import os
import sys
import atexit
import service_manager
import settings_manager
from modules.transfer import transfer_and_refresh
import modules.preset_manager as preset_manager

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(PROJECT_ROOT, "model_cache")
HUB_CACHE_DIR = os.path.join(CACHE_DIR, "hub")
os.environ["HF_HOME"] = CACHE_DIR
os.environ["HF_HUB_CACHE"] = HUB_CACHE_DIR
os.environ["HUGGINGFACE_HUB_CACHE"] = HUB_CACHE_DIR
os.makedirs(HUB_CACHE_DIR, exist_ok=True)
import huggingface_hub as hf_hub
hf_hub.constants.HF_HUB_CACHE = HUB_CACHE_DIR
sys.path.insert(0, PROJECT_ROOT)

import gradio as gr
from modules.config import MODEL_REPO
from modules.batch_tagging import batch_tagging
from modules.modify_tags import preview_tags_from_dir, operate_on_dir
from modules.download import (
    start_download, stop_download, refresh_preview,
    delete_selected_image, clear_all_images
)
from modules.utils import select_output_directory, open_output_folder, get_images_in_folder
import base64
from pathlib import Path

def get_image_base64(image_path):
    path = Path(image_path)
    if path.exists():
        with open(path, "rb") as f:
            ext = path.suffix.lower()[1:]
            base64_str = base64.b64encode(f.read()).decode()
            return f"data:image/{ext};base64,{base64_str}"
    return None

def create_ui():
    settings = settings_manager.init_settings()

    avatar_base64 = get_image_base64("aa2l.png")
    avatar_html = f'<img src="{avatar_base64}" style="width:48px; height:48px; border-radius:50%; margin-right:15px;">' if avatar_base64 else ''

    with gr.Blocks(title="AA2L Tagger & Manager") as demo:
        gr.HTML(f'''
        <div style="display: flex; align-items: center; margin-bottom: 10px;">
            {avatar_html}
            <h1 style="margin:0; font-size:2rem;">AA2L Tagger & Manager</h1>
        </div>
        ''')
        # 全局按钮行
        with gr.Row():
            shutdown_btn = gr.Button(" 关闭服务", variant="secondary")
            log_btn = gr.Button(" 打开服务终端", variant="secondary")

        with gr.Tabs() as tabs:
            # ========= 0. 下载训练集 =========
            with gr.TabItem("0.  下载训练集"):
                gr.Markdown("### 使用URL批量下载图片（支持 Danbooru 等站点）")
                with gr.Row():
                    with gr.Column(scale=3):
                        url_input = gr.Textbox(label="输入URL（每行一个）", lines=5, placeholder="例如：\nhttps://danbooru.donmai.us/posts/123456\nhttps://danbooru.donmai.us/posts?tags=1girl")
                        with gr.Row():
                            download_btn = gr.Button("开始下载", variant="primary")
                            stop_btn = gr.Button("停止下载", variant="stop")
                        with gr.Row():
                            open_folder_btn = gr.Button("打开 download_P 文件夹", variant="secondary")
                            migrate_btn = gr.Button("将图片迁移到批量打标", variant="secondary")
                    with gr.Column(scale=1):
                        output_dir_download = gr.Textbox(label="下载目录", value=settings["download_dir"], lines=1)
                        refresh_btn = gr.Button("刷新预览")
                        delete_selected_btn = gr.Button("删除选中图片", variant="secondary")
                        clear_all_btn = gr.Button("清空所有图片", variant="secondary")
                        selected_index = gr.State(-1)
                        selected_label = gr.Textbox(label="当前选中", value="未选中", interactive=False)
                gallery_preview = gr.Gallery(label="已下载图片预览", columns=4, height=500, object_fit="contain", allow_preview=True)
                gr.Markdown("""
                **📖 使用说明：**  
                1. 在左侧文本框输入图片URL（每行一个） 
                2. 点击「开始下载」，下载的图片会保存到右侧指定的「下载目录」中。  
                3. 下载完成后点击「刷新预览」查看已下载的图片缩略图。  
                4. 可以选中图片删除，或「清空所有图片」。  
                5. 点击「将图片迁移到批量打标」可直接将下载的图片导入到“批量打标”页面进行处理。
                """)
            # ========= 1. 批量打标 =========
            with gr.TabItem("1.  批量打标"):
                with gr.Row():
                    with gr.Column():
                        input_gallery = gr.Gallery(
                            label="上传图片",
                            file_types=["image"],
                            type="filepath",
                            height=300,
                            columns=3,
                            object_fit="contain",
                            allow_preview=True
                        )
                        threshold_slider = gr.Slider(label="置信度阈值", minimum=0.1, maximum=1.0, value=settings["threshold"], step=0.05)
                        resize_mode = gr.Dropdown(
                            choices=[
                                "模型内部缩放（原图模式）",
                                "手动缩放 384x384",
                                "手动缩放 448x448（推荐）",
                                "手动缩放 512x512"
                            ],
                            value=settings["resize_mode"],
                            label="图像预处理模式",
                            info="手动缩放可大幅提升速度，对精度影响极小"
                        )
                        with gr.Row():
                            enable_batch_checkbox = gr.Checkbox(label="启用分批次处理", value=settings["enable_batch"])
                            batch_size_slider = gr.Slider(
                                label="批次大小 (每批图片数)",
                                minimum=1,
                                maximum=21,
                                step=1,
                                value=settings["batch_size"],
                                interactive=True
                            )
                        with gr.Row():
                            output_dir = gr.Textbox(label="输出目录", value=settings["output_dir"], lines=1, scale=4)
                            browse_btn = gr.Button("浏览", scale=1)
                        copy_images_checkbox = gr.Checkbox(label="将原图复制到输出目录", value=settings["copy_images"])
                        rename_sequential_checkbox = gr.Checkbox(label="重命名输出文件为序号 (1,2,3...)", value=settings["rename_sequential"])
                        with gr.Row():
                            tag_btn = gr.Button("开始打标", variant="primary")
                            open_btn = gr.Button("打开输出文件夹", variant="secondary")
                    with gr.Column():
                        output_status = gr.Textbox(label="处理状态", lines=2, interactive=False)
                        transfer_btn = gr.Button("传输标签文件至批量修改界面", variant="secondary")
                        output_tags = gr.JSON(label="生成的标签（示例）")
                gr.Markdown("""
                **📖 使用说明：**  
                1. 上传图片（支持多张），调整置信度阈值（推荐0.35）和预处理模式。  
                2. 可选“启用分批次处理”并设置批次大小，可实时查看进度。  
                3. 设置输出目录，可选“复制原图”和“重命名输出文件为序号”。  
                4. 点击「开始打标」生成对应 `.txt` 标签文件。  
                5. 标签文件示例会显示在右侧框。  
                6. 可通过「传输标签文件至批量修改界面」一键将当前输出目录传给“批量修改标签”页面。
                """)
            # ========= 2. 批量修改标签 =========
            with gr.TabItem("2.  批量修改标签"):
                with gr.Row():
                    with gr.Column(scale=1):
                        target_dir = gr.Textbox(label="目标文件夹（存放 .txt 标签文件的目录）", value=settings["target_dir"], lines=1)
                        with gr.Row():
                            load_btn = gr.Button("加载/刷新", variant="secondary")
                            operate_btn = gr.Button("执行操作", variant="primary")
                        with gr.Group():
                            gr.Markdown("###  按标签名/序号操作")
                            with gr.Row():
                                operation_mode = gr.Dropdown(
                                    choices=["删除标签", "替换标签", "添加前缀", "添加后缀"],
                                    value="删除标签",
                                    label="操作类型"
                                )
                                use_index = gr.Checkbox(label="使用序号（否则按标签名）", value=False)
                            target_input = gr.Textbox(
                                label="目标（标签名或序号）",
                                placeholder="例如: solo 或 2",
                                lines=1,
                                info="删除/替换时需填写目标标签名或序号；添加操作忽略此项"
                            )
                            new_tag_input = gr.Textbox(
                                label="标签内容（多个用英文逗号分隔）",
                                placeholder="例如: 1girl, solo, blush",
                                lines=1,
                                info="替换时填写新标签；添加操作时填写要增加的标签（可多个）；删除操作时此项将被忽略"
                            )

                        
                        # =========标签预设管理 =========
                        with gr.Group(elem_classes="no-border-group"):
                            gr.Markdown("### 标签预设")
                            with gr.Row():
                                preset_dropdown = gr.Dropdown(
                                    choices=preset_manager.get_preset_names(),
                                    label="选择预设组",
                                    interactive=True,
                                    scale=3
                                )
                                apply_preset_btn = gr.Button("应用预设", variant="secondary", size="sm", scale=1)
                                delete_preset_btn = gr.Button("删除选中预设", variant="secondary", size="sm", scale=1)
                        with gr.Row():
                            preset_accordion = gr.Accordion("管理预设", open=False, elem_classes="no-border-accordion")
                            with preset_accordion:
                                new_preset_name = gr.Textbox(label="预设组名", placeholder="例如: aa2l", lines=1)
                                new_preset_tags = gr.Textbox(label="标签列表（英文逗号分隔）", placeholder="1girl, solo, blush", lines=2)
                                with gr.Row():
                                    save_preset_btn = gr.Button("保存/更新预设", variant="primary")
                                preset_status = gr.Textbox(label="操作反馈", interactive=False, lines=1)
                        gr.Markdown("""
                        **📖 使用说明：**  
                        1. 选择存放 `.txt` 标签文件的文件夹，点击「加载/刷新」右侧会显示标签频次排行。  
                        2. 选择操作类型（删除/替换/添加前缀/添加后缀）。  
                        3. 若“使用序号”则输入排行中的数字序号（逗号分隔），否则直接输入标签名（逗号分隔）。  
                        4. 对于删除/替换，在「目标」框填写要操作的标签名或序号；替换还需填写「标签内容」（新标签名）。  
                        5. 对于添加前缀/后缀，直接在「标签内容」框填写要添加的标签（多个用逗号分隔）。  
                        6. 点击「执行操作」后，所有 `.txt` 文件会被直接修改，并自动刷新排行榜。  
                        7. 可使用“标签预设”功能保存常用标签组（如触发词），一键应用到当前操作。
                        """)
                    with gr.Column(scale=1):
                        with gr.Accordion("标签频次排行", open=True):
                            preview_summary = gr.Textbox(label="统计摘要", lines=2, interactive=False)
                            preview_text = gr.Textbox(label="排行列表（格式：序号_[频次]_标签）", lines=20, interactive=False)
                        modify_status = gr.Textbox(label="处理状态", lines=10, interactive=False)

                                # ========= 3. 帮助说明 =========
            with gr.TabItem("3.  帮助说明"):
                with gr.Row():
                    # 左侧：折叠面板（文字内容）
                    with gr.Column(scale=3):
                        with gr.Accordion(" 快速启动 ", open=False):
                            gr.Markdown("""
                            1. **安装 Python**  
                               确保已安装 Python 3.8 或更高版本（[官网下载](https://www.python.org/downloads/)）。  
                               安装时请勾选 **“Add Python to PATH”**。
                            
                            2. **运行启动脚本**  
                               双击项目文件夹中的 `run.bat`。  
                               - 首次运行会自动创建虚拟环境并安装依赖（需要联网，模型约 2GB 会自动下载）。  
                               - 安装完成后，浏览器会自动打开 `http://127.0.0.1:7860`。
                            
                            3. **关闭程序**  
                               在 Web 界面顶部点击「关闭服务」按钮。
                            """)
                        with gr.Accordion(" 功能教程", open=False):
                            gr.Markdown("""
                            ### 0. 下载训练集
                            - 支持 Danbooru 等网站 URL，每行一个。  
                            - 点击「开始下载」，图片保存到指定目录。  
                            - 可预览、删除单张或清空所有图片。  
                            - 一键迁移到“批量打标”页面继续处理。

                            ### 1. 批量打标
                            - 上传图片（支持多张）。  
                            - 调节置信度阈值（0.35 为推荐值）。  
                            - 选择图像预处理模式。  
                            - 可选分批次处理，实时显示进度。  
                            - 输出 `.txt` 标签文件，格式：`tag1, tag2, ...`。  
                            - 支持复制原图到输出目录、序号重命名。

                            ### 2. 批量修改标签
                            - 选择存放 `.txt` 的文件夹，加载后右侧显示标签频次排行。  
                            - 操作类型：删除、替换、添加前缀、添加后缀。  
                            - 可按标签名操作，或按排行序号操作（支持多个，逗号分隔）。  
                            - 预设功能：保存常用标签组（如触发词），一键应用到当前操作。  
                            - 修改后自动刷新排行。
                            """)
                        with gr.Accordion(" 常见问题 (FAQ)", open=False):
                            gr.Markdown("""。
                            **Q: 模型下载失败或卡住怎么办？**  
                            A: 可以手动下载模型文件放到 `model_cache/hub` 目录，或设置镜像源（本项目已配置 HF 镜像）。

                            **Q: 如何更新到最新版本？**  
                            A: 拉取最新代码后，重新运行 `run.bat`，依赖会自动检查更新。
                                        
                            **Q: 删除/替换标签支持中文吗？**  
                            A: 支持，但请注意大小写（不区分大小写匹配）。
                            """)
                        with gr.Accordion(" 项目介绍 ", open=False):
                            gr.Markdown("""
                            **AA2L Tagger & Manager**  
                            一个基于 WD Tagger 的本地批量图像打标与标签管理工具，专为 AI 训练者设计。

                             **主要特性**  
                            - 批量打标（WD ViT Large V3）  
                            - 标签频次统计与批量修改（删除/替换/添加前后缀）  
                            - 集成 gallery-dl，支持批量下载 Danbooru 等站点图片  
                            - 标签预设管理  
                            - 跨页面数据流转  
                            - 配置持久化，记忆用户设置  
                            - 完全本地运行
                            - 提供 Web UI，操作简便

                            **依赖项**  
                            Python 3.8+、Gradio、wdtagger、onnxruntime、Pillow、timm、gallery-dl

                            **项目地址**  
                            [GitHub 仓库] https://github.com/aa2l/AA2L-Tagger-Manager

                             **许可证**  
                            
                            """)

                    # 右侧：头像 + 宣传信息
                    with gr.Column(scale=1, min_width=200):
                        # 随机选择头像文件（50%概率）
                        import base64
                        import random
                        avatar_files = ["aa3l.png", "aa4l.png", "aa5l.png", "aa6l.png"]
                        chosen_avatar = random.choice(avatar_files)
                        big_avatar_path = chosen_avatar
                        if os.path.exists(big_avatar_path):
                            with open(big_avatar_path, "rb") as f:
                                img_data = base64.b64encode(f.read()).decode()
                            avatar_html = f'<img src="data:image/png;base64,{img_data}" style="width:150px; height:150px; border-radius:50%; object-fit:cover; display:block; margin:20px auto 10px auto;">'
                            gr.HTML(avatar_html)
                        else:
                            # 如果图片缺失，显示一个占位符
                            gr.Markdown("###  作者")
                        # 宣传信息（始终显示）
                        gr.Markdown("""
                        <div style="text-align: center; margin-top: 10px;">
                            <h3> 作者：@aa2l</h3>
                            <p>学习交流 QQ 群：<strong>1019353738</strong></p>
                            <p>我们涉及的领域：</p>
                            <p>===================================</p>
                            <p>AI类:Anima,Nai,SD,NewBie,Flux,Z-image,gpt-sovice;及其它开源库和闭源模型</p>
                            <p>===================================</p>
                            <p>绘画:纸绘,板绘PS,CSP,SAI</p>
                            <p>===================================</p>
                            <p>后期视设平设:Pr,Ae,Ps,Ai,Id</p>
                            <p>===================================</p>
                            <p>开发:Transformer,Gradio,Ren.py,</p>
                            <p>===================================</p>
                            <p>漫画原理(分镜脚本,漫画理论,漫符后期,美术)</p>
                            <p>===================================</p>
                            <p>写作(出版社文稿)</p>
                            <p>===================================</p>
                        </div>
                        """)
            # ========= 所有事件绑定 =========
            # 配置持久化绑定
            threshold_slider.change(lambda v: settings_manager.update_setting("threshold", v), inputs=[threshold_slider])
            resize_mode.change(lambda v: settings_manager.update_setting("resize_mode", v), inputs=[resize_mode])
            enable_batch_checkbox.change(lambda v: settings_manager.update_setting("enable_batch", v), inputs=[enable_batch_checkbox])
            batch_size_slider.change(lambda v: settings_manager.update_setting("batch_size", v), inputs=[batch_size_slider])
            output_dir.change(lambda v: settings_manager.update_setting("output_dir", v), inputs=[output_dir])
            copy_images_checkbox.change(lambda v: settings_manager.update_setting("copy_images", v), inputs=[copy_images_checkbox])
            rename_sequential_checkbox.change(lambda v: settings_manager.update_setting("rename_sequential", v), inputs=[rename_sequential_checkbox])
            output_dir_download.change(lambda v: settings_manager.update_setting("download_dir", v), inputs=[output_dir_download])
            target_dir.change(lambda v: settings_manager.update_setting("target_dir", v), inputs=[target_dir])

            # 下载训练集事件
            download_btn.click(start_download, inputs=[url_input, output_dir_download], outputs=None)
            stop_btn.click(stop_download, inputs=[], outputs=None)

            def refresh_and_reset(folder):
                images = get_images_in_folder(folder)
                return images, -1, "未选中"
            refresh_btn.click(refresh_and_reset, inputs=[output_dir_download], outputs=[gallery_preview, selected_index, selected_label])

            def on_select(evt: gr.SelectData):
                idx = evt.index
                if idx is None:
                    return -1, "未选中"
                value = evt.value
                if isinstance(value, tuple) and len(value) > 0:
                    path = value[0]
                else:
                    path = value
                if path and isinstance(path, str):
                    return idx, os.path.basename(path)
                else:
                    return idx, f"已选中第 {idx+1} 张图片"
            gallery_preview.select(fn=on_select, inputs=None, outputs=[selected_index, selected_label])

            delete_selected_btn.click(delete_selected_image, inputs=[output_dir_download, selected_index, gallery_preview], outputs=[gallery_preview, selected_index, selected_label])
            clear_all_btn.click(clear_all_images, inputs=[output_dir_download], outputs=[gallery_preview, selected_index, selected_label])
            open_folder_btn.click(fn=open_output_folder, inputs=[output_dir_download], outputs=[output_status])

            def migrate_images(folder):
                if not os.path.exists(folder):
                    gr.Warning("下载目录不存在")
                    return gr.update(value=[])
                images = get_images_in_folder(folder)
                if not images:
                    gr.Warning("没有找到图片")
                    return gr.update(value=[])
                return gr.update(value=images)
            migrate_btn.click(fn=migrate_images, inputs=[output_dir_download], outputs=[input_gallery])

            # 批量打标事件
            tag_btn.click(
                batch_tagging,
                inputs=[input_gallery, output_dir, threshold_slider, resize_mode,
                        enable_batch_checkbox, batch_size_slider, copy_images_checkbox,
                        rename_sequential_checkbox],
                outputs=[output_status, output_tags]
            )
            open_btn.click(open_output_folder, inputs=[output_dir], outputs=[output_status])
            browse_btn.click(select_output_directory, inputs=[], outputs=[output_dir])

            # 批量修改标签事件
            transfer_btn.click(
                fn=transfer_and_refresh,
                inputs=[output_dir],
                outputs=[target_dir, output_status, preview_summary, preview_text]
            )
            load_btn.click(
                fn=preview_tags_from_dir,
                inputs=[target_dir],
                outputs=[preview_summary, preview_text]
            )
            operate_btn.click(
                fn=operate_on_dir,
                inputs=[target_dir, operation_mode, target_input, use_index, new_tag_input],
                outputs=[modify_status]
            ).then(
                fn=preview_tags_from_dir,
                inputs=[target_dir],
                outputs=[preview_summary, preview_text]
            )

            # 全局按钮事件
            def shutdown_with_info():
                result = service_manager.shutdown_service()
                gr.Info(result)
                return None

            def log_with_info():
                result = service_manager.show_log_terminal()
                gr.Info(result)
                return None

            shutdown_btn.click(fn=shutdown_with_info, inputs=[], outputs=[])
            log_btn.click(fn=log_with_info, inputs=[], outputs=[])

            # 预设管理事件
            def apply_preset_to_current(preset_name, operation_mode):
                if not preset_name:
                    gr.Warning("请先选择一个预设组")
                    return gr.update(), gr.update(), gr.update()
                tags = preset_manager.get_preset_tags(preset_name)
                if not tags:
                    gr.Warning(f"预设组 '{preset_name}' 没有标签")
                    return gr.update(), gr.update(), gr.update()
                tags_str = preset_manager.format_tags_for_input(tags)
                if operation_mode in ["删除标签", "替换标签"]:
                    return gr.update(value=tags_str), gr.update(), gr.update(open=False)
                else:
                    return gr.update(), gr.update(value=tags_str), gr.update(open=False)

            def save_preset(group_name, tags_str):
                if not group_name:
                    gr.Warning("预设组名不能为空")
                    return gr.update(), "请输入组名"
                success, msg = preset_manager.add_or_update_preset(group_name, tags_str)
                if success:
                    gr.Info(msg)
                    return gr.Dropdown(choices=preset_manager.get_preset_names()), msg
                else:
                    gr.Warning(msg)
                    return gr.update(), msg

            def delete_preset(group_name):
                if not group_name:
                    gr.Warning("请选择要删除的预设组")
                    return gr.Dropdown(choices=preset_manager.get_preset_names()), "未选择预设组"
                success, msg = preset_manager.delete_preset(group_name)
                if success:
                    gr.Info(msg)
                    return gr.Dropdown(choices=preset_manager.get_preset_names()), msg
                else:
                    gr.Warning(msg)
                    return gr.update(), msg

            apply_preset_btn.click(
                fn=apply_preset_to_current,
                inputs=[preset_dropdown, operation_mode],
                outputs=[target_input, new_tag_input, preset_accordion]
            )
            save_preset_btn.click(
                fn=save_preset,
                inputs=[new_preset_name, new_preset_tags],
                outputs=[preset_dropdown, preset_status]
            )
            delete_preset_btn.click(
                fn=delete_preset,
                inputs=[preset_dropdown],
                outputs=[preset_dropdown, preset_status]
            )
        
        # 底部信息
        gr.HTML('''
        <div style="text-align: center; margin-top: 30px; padding: 10px; border-top: 1px solid #e0e0e0; color: #666;">
             本工具为@aa2l个人制作 <br>
            如有问题或进行学习交流欢迎访问学社q群:1019353738

        </div>
        ''')
        
        # 页面加载时刷新下载预览
        demo.load(fn=refresh_preview, inputs=output_dir_download, outputs=gallery_preview)

    return demo

if __name__ == "__main__":
    # 自定义 CSS
    custom_css = """
    /* 去除输入框焦点时的蓝色/白色外发光 */
    input:focus, textarea:focus, select:focus, .gr-textarea:focus, .gr-box:focus-within {
        outline: none !important;
        box-shadow: none !important;
        border-color: #f97316 !important;
    }
    /* 按钮 hover 效果 */
    .gr-button:hover {
        background-color: #f97316 !important;
        border-color: #f97316 !important;
    }
    /* 去掉管理预设区域的白色边框 */
    .no-border-group,
    .no-border-group .gr-group,
    .no-border-group .gr-box,
    .no-border-accordion,
    .no-border-accordion .gr-accordion,
    .no-border-accordion > div,
    .no-border-accordion details,
    .no-border-accordion .gr-box {
        border: none !important;
        box-shadow: none !important;
        background: transparent !important;
    }
    """
    demo = create_ui()
    demo.launch(
        share=False,
        theme=gr.themes.Soft(
            primary_hue="orange",
            secondary_hue="orange",
            font=gr.themes.GoogleFont("Inter")
        ),
        css=custom_css
    )
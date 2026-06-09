import os
import gradio as gr
from collections import Counter
from typing import List

def scan_txt_files(folder):
    """扫描文件夹下所有 .txt 文件，返回文件路径列表和所有标签的列表"""
    if not os.path.exists(folder):
        return [], []
    txt_files = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith('.txt')]
    all_tags = []
    for file_path in txt_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            tags = [tag.strip() for tag in content.split(',') if tag.strip()]
            all_tags.extend(tags)
        except:
            continue
    return txt_files, all_tags

def preview_tags_from_dir(folder, progress=gr.Progress()):
    """根据文件夹预览标签频次排行"""
    txt_files, all_tags = scan_txt_files(folder)
    if not txt_files:
        return "未找到任何 .txt 文件。", ""
    if not all_tags:
        return "文件内容为空或没有有效标签。", ""

    tag_counts = Counter(all_tags)
    sorted_tags = tag_counts.most_common()

    lines = []
    for idx, (tag, count) in enumerate(sorted_tags, start=1):
        lines.append(f"{idx}_[{count}]_{tag}")
    formatted_text = "\n".join(lines)

    summary = f"共扫描到 {len(tag_counts)} 种标签，总计 {len(all_tags)} 次。（来自 {len(txt_files)} 个文件）"
    return summary, formatted_text

def get_tag_rankings_from_dir(folder):
    """获取文件夹内标签排行（供序号定位使用）"""
    _, all_tags = scan_txt_files(folder)
    if not all_tags:
        return [], 0
    tag_counts = Counter(all_tags)
    sorted_tags = tag_counts.most_common()
    return sorted_tags, len(all_tags)

def operate_on_dir(folder, operation: str, target: str, use_index: bool,
                   new_tag: str, progress=gr.Progress()):
    op_map = {
        "删除标签": "delete",
        "替换标签": "replace",
        "添加前缀": "prepend",
        "添加后缀": "append"
    }
    operation = op_map.get(operation, operation)
    if operation not in ["delete", "replace", "prepend", "append"]:
        return f"不支持的操作类型: {operation}"

    if not os.path.exists(folder):
        return f"文件夹不存在: {folder}"

    txt_files, _ = scan_txt_files(folder)
    if not txt_files:
        return "未找到任何 .txt 文件。"

    if operation in ["delete", "replace"]:
        rankings, total_tags = get_tag_rankings_from_dir(folder)
        if not rankings:
            return "无法获取标签排行，请确保文件夹内有有效标签文件。"

        # 清理目标
        target = target.strip().strip(',')
        if not target:
            return "请输入目标标签或序号。"

        # 分割目标（删除支持多个，替换只取第一个）
        target_items = [item.strip() for item in target.split(',') if item.strip()]
        if not target_items:
            return "请输入至少一个目标标签或序号。"

        if operation == "replace":
            if len(target_items) > 1:
                return "替换操作仅支持单个目标，请只输入一个标签名或序号。"
            single_target = target_items[0]
            if use_index:
                try:
                    idx = int(single_target) - 1
                    if 0 <= idx < len(rankings):
                        tag_to_operate = rankings[idx][0]
                    else:
                        return f"序号 {single_target} 超出范围（1-{len(rankings)}）。"
                except ValueError:
                    return "请输入有效的数字序号。"
            else:
                tag_to_operate = single_target
            if not new_tag:
                return "替换操作需要提供新标签名。"
            new_tag = new_tag.strip()
            # 用于匹配的集合
            targets_set = {tag_to_operate.lower()}
            replace_map = {tag_to_operate.lower(): new_tag}
        else:  # 删除操作
            targets_set = set()
            if use_index:
                for item in target_items:
                    try:
                        idx = int(item) - 1
                        if 0 <= idx < len(rankings):
                            targets_set.add(rankings[idx][0].lower())
                        else:
                            return f"序号 {item} 超出范围（1-{len(rankings)}）。"
                    except ValueError:
                        return f"序号 '{item}' 无效，请输入数字序号。"
            else:
                targets_set = {item.lower() for item in target_items}
            if not targets_set:
                return "未指定有效的目标标签。"
            replace_map = None

    elif operation in ["prepend", "append"]:
        if not new_tag:
            return "添加操作需要填写标签内容。"
        raw_tags = [t.strip() for t in new_tag.split(',') if t.strip()]
        if not raw_tags:
            return "标签内容无效，请用英文逗号分隔多个标签。"
        new_tags_list = raw_tags
    else:
        return "未知操作"

    processed_count = 0
    log_lines = []
    total_files = len(txt_files)
    for i, file_path in enumerate(txt_files):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            # 按逗号分割，保留原始空格并去除每个标签首尾空格
            old_tags = [tag.strip() for tag in content.split(',') if tag.strip()]

            if operation == "delete":
                new_tags = [t for t in old_tags if t.lower() not in targets_set]
            elif operation == "replace":
                new_tags = []
                for t in old_tags:
                    lower_t = t.lower()
                    if lower_t in replace_map:
                        new_tags.append(replace_map[lower_t])
                    else:
                        new_tags.append(t)
            elif operation == "prepend":
                new_tags = new_tags_list + old_tags
            elif operation == "append":
                new_tags = old_tags + new_tags_list
            else:
                continue

            if new_tags == old_tags:
                log_lines.append(f" {os.path.basename(file_path)}: 未找到匹配标签，未做修改。")
            else:
                new_content = ', '.join(new_tags)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                processed_count += 1
                log_lines.append(f"已修改: {os.path.basename(file_path)}")
            progress(i / total_files, desc=f"正在处理: {os.path.basename(file_path)}")
        except Exception as e:
            log_lines.append(f"处理失败: {os.path.basename(file_path)}, 错误: {str(e)}")
            continue
    summary = f"成功修改 {processed_count} 个文件。\n" + "\n".join(log_lines)
    return summary
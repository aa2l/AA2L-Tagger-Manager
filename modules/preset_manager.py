# modules/preset_manager.py
import os
import json

PRESET_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tag_presets.json")

def load_presets():
    """加载预设文件，返回字典 {group_name: [tag1, tag2, ...]}"""
    if not os.path.exists(PRESET_FILE):
        return {}
    try:
        with open(PRESET_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_presets(presets):
    """保存预设字典到文件"""
    try:
        with open(PRESET_FILE, "w", encoding="utf-8") as f:
            json.dump(presets, f, indent=2, ensure_ascii=False)
        return True
    except:
        return False

def get_preset_names():
    """返回所有预设组名称列表"""
    presets = load_presets()
    return list(presets.keys())

def get_preset_tags(group_name):
    """获取指定预设组的标签列表（字符串列表）"""
    presets = load_presets()
    return presets.get(group_name, [])

def add_or_update_preset(group_name, tags_str):
    """添加或更新预设组，tags_str 为逗号分隔的字符串"""
    if not group_name or not group_name.strip():
        return False, "预设组名不能为空"
    tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
    if not tags:
        return False, "至少输入一个有效标签"
    presets = load_presets()
    presets[group_name.strip()] = tags
    if save_presets(presets):
        return True, f"预设组 '{group_name}' 已保存，共 {len(tags)} 个标签"
    else:
        return False, "保存失败"

def delete_preset(group_name):
    """删除预设组"""
    if not group_name:
        return False, "未指定预设组"
    presets = load_presets()
    if group_name not in presets:
        return False, f"预设组 '{group_name}' 不存在"
    del presets[group_name]
    if save_presets(presets):
        return True, f"已删除预设组 '{group_name}'"
    else:
        return False, "删除失败"

def format_tags_for_input(tags_list):
    """将标签列表格式化为适合填入输入框的字符串（逗号+空格）"""
    return ', '.join(tags_list)
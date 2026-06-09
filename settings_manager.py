# settings_manager.py
import os
import json
import atexit
from typing import Dict, Any

CONFIG_FILE = "user_config.json"

# 默认配置（首次启动或配置文件损坏时使用）
DEFAULT_SETTINGS = {
    "threshold": 0.35,
    "resize_mode": "手动缩放 448x448（推荐）",
    "enable_batch": False,
    "batch_size": 4,
    "output_dir": "./output_tags",
    "copy_images": False,
    "rename_sequential": False,
    "download_dir": "./download_P",
    "target_dir": "./output_tags",      # 批量修改标签页的文件夹路径

}

# 全局变量
_current_settings = None

def _load_from_disk() -> Dict[str, Any]:
    """从磁盘加载配置，如果文件不存在或损坏则返回默认配置"""
    if not os.path.exists(CONFIG_FILE):
        return DEFAULT_SETTINGS.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # 合并默认值保证新增配置项不会因旧文件缺失而报错
            merged = DEFAULT_SETTINGS.copy()
            merged.update(data)
            return merged
    except Exception:
        return DEFAULT_SETTINGS.copy()

def _save_to_disk(settings: Dict[str, Any]):
    """将配置写入磁盘"""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[配置] 保存失败: {e}")

def init_settings():
    """初始化配置系统：加载磁盘配置并注册退出保存钩子"""
    global _current_settings
    _current_settings = _load_from_disk()
    atexit.register(_save_on_exit)
    return _current_settings

def get_current_settings() -> Dict[str, Any]:
    """获取当前内存中的配置（只读，如需修改请调用 update_setting）"""
    if _current_settings is None:
        return DEFAULT_SETTINGS.copy()
    return _current_settings

def update_setting(key: str, value: Any):
    """仅更新内存配置，不写磁盘（等待程序退出时统一保存）"""
    global _current_settings
    if _current_settings is None:
        _current_settings = DEFAULT_SETTINGS.copy()
    _current_settings[key] = value

def _save_on_exit():
    """atexit 回调：将内存配置写入磁盘"""
    if _current_settings is not None:
        _save_to_disk(_current_settings)
        print("[配置] 已自动保存用户设置")
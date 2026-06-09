import os

# 项目根目录（被导入时计算）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(PROJECT_ROOT, "model_cache")
MODEL_REPO = "SmilingWolf/wd-vit-large-tagger-v3"
DEFAULT_OUTPUT_DIR = "./output_tags"
DEFAULT_DOWNLOAD_DIR = "./download_P"


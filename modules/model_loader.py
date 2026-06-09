from wdtagger import Tagger
from .config import MODEL_REPO
import os

_tagger_instance = None
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "model_cache", "hub")

def get_tagger():
    global _tagger_instance
    if _tagger_instance is None:
        _tagger_instance = Tagger(model_repo=MODEL_REPO, cache_dir=CACHE_DIR)
        print("模型已加载（CPU 推理模式）")
    return _tagger_instance
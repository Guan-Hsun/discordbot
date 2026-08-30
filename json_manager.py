import json
import os

def load_json(filename):
    """讀取指定的 JSON 檔案，若不存在或損壞則回傳空字典"""
    if not os.path.exists(filename):
        return {}
    try:
        with open(filename, 'r', encoding="utf8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_json(filename, data):
    """將資料寫入指定的 JSON 檔案"""
    with open(filename, "w", encoding="utf8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
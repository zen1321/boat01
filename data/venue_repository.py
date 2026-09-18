import json
from pathlib import Path
from typing import Any, Dict, List

# JSONファイルのパス設定 (data_json/venue_types.json)
JSON_PATH = (
    Path(__file__).resolve().parent.parent / "data_json" / "venue_types.json"
)


def _load_venue_types() -> Dict[str, Any]:
    """JSONファイルから競艇場タイプデータを読み込む"""
    if not JSON_PATH.exists():
        return {}
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_all_venues() -> List[str]:
    """全競艇場名のリストを取得（画面選択用）"""
    data = _load_venue_types()
    return list(data.keys())


def get_venue_type_info(venue_name: str) -> Dict[str, Any]:
    """競艇場名から設定データを取得"""
    data = _load_venue_types()

    # 該当する場があれば返し、なければ標準のデフォルト値を返す
    if venue_name in data:
        return data[venue_name]

    return {
        "venue_type": "標準",
        "water_type": "静水",
        "course1_score": 3.0,
        "course2_score": 1.5,
        "course3_score": 1.5,
        "course4_score": 1.0,
        "course5_score": 0.5,
        "course6_score": 0.0,
    }


def get_course_score(venue_name: str, course_no: int) -> float:
    """指定した競艇場・コース番号のスコア補正値を取得"""
    info = get_venue_type_info(venue_name)
    key = f"course{course_no}_score"
    return float(info.get(key, 0.0))
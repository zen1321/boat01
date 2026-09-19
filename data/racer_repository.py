import json
from pathlib import Path
from typing import Any

# パス設定
RANK_JSON_PATH = (
    Path(__file__).resolve().parent.parent / "data_json" / "rank_scores.json"
)
MOTOR_JSON_PATH = (
    Path(__file__).resolve().parent.parent / "data_json" / "motor_score_rules.json"
)
RACER_JSON_PATH = (
    Path(__file__).resolve().parent.parent / "data_json" / "fan2604.json"
)

# 選手データのキャッシュ
_racers_cache = {}


def _load_rank_scores() -> dict:
    if not RANK_JSON_PATH.exists():
        return {"A1": 1.5, "A2": 1.0, "B1": 0.0, "B2": -1.0}
    with open(RANK_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_motor_score_rules() -> dict:
    """motor_score_rules.json からデータを読み込む"""
    if not MOTOR_JSON_PATH.exists():
        return {}
    with open(MOTOR_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_racers_data() -> dict:
    """fan2604.json を読み込み、登番(toban)をキーにした辞書としてキャッシュする"""
    global _racers_cache
    if _racers_cache:
        return _racers_cache

    if not RACER_JSON_PATH.exists():
        print(f"警告: 選手データファイルが見つかりません: {RACER_JSON_PATH}")
        return {}

    try:
        with open(RACER_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            _racers_cache = {str(item.get("toban", "")).strip(): item for item in data}
    except Exception as e:
        print(f"fan2604.json 読み込みエラー: {e}")
        _racers_cache = {}

    return _racers_cache


## rank_scoresから階級スコアを取得
def get_rank_score_from_db(rank: str) -> float:
    scores = _load_rank_scores()
    normalized_rank = str(rank).strip().upper()
    return float(scores.get(normalized_rank, 0.0))


## venue_typeから競艇場タイプを取得
def get_venue_type_from_db(venue_name: str) -> str:
    from data.venue_repository import get_venue_type_info
    info = get_venue_type_info(venue_name)
    return info.get("venue_type", "標準")


## motor_score_rulesから2連対率のスコアを取得
def get_motor_score_from_db(motor_2in_rate: float, venue_type: str) -> float:
    rules_data = _load_motor_score_rules()
    rules = rules_data.get(venue_type, [])

    if not rules:
        return 0.0

    sorted_rules = sorted(rules, key=lambda x: x["min_rate"], reverse=True)
    for rule in sorted_rules:
        if motor_2in_rate >= float(rule["min_rate"]):
            return float(rule["score"])

    return 0.0


def get_water_type_from_db(venue_name: str) -> str:
    from data.venue_repository import get_venue_type_info
    info = get_venue_type_info(venue_name)
    return info.get("water_type", "静水")


def get_venue_course_score_from_db(venue_name: str, course: int) -> float:
    from data.venue_repository import get_course_score
    return get_course_score(venue_name, course)


def get_racer_by_id(racer_id: Any) -> dict:
    """登番(racer_id)からJSON(fan2604.json)を参照して選手情報を取得"""
    racers = _load_racers_data()
    racer_key = str(racer_id).strip()
    return racers.get(racer_key, {})
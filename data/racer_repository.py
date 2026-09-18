import json
from pathlib import Path
from data.db_connector import get_connection

# パス設定
RANK_JSON_PATH = (
    Path(__file__).resolve().parent.parent / "data_json" / "rank_scores.json"
)
MOTOR_JSON_PATH = (
    Path(__file__).resolve().parent.parent / "data_json" / "motor_score_rules.json"
)


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


## rank_scoresから階級スコアを取得
def get_rank_score_from_db(rank: str) -> float:
    scores = _load_rank_scores()
    normalized_rank = str(rank).strip().upper()
    return float(scores.get(normalized_rank, 0.0))


## venue_typeから競艇場タイプを取得
def get_venue_type_from_db(venue_name: str) -> str:
    # 先ほど作成した venue_repository から競艇場タイプを取得するよう統合可能
    from data.venue_repository import get_venue_type_info
    info = get_venue_type_info(venue_name)
    return info.get("venue_type", "標準")


## motor_score_rulesから2連対率のスコアを取得（JSON読み込みへ移行）
def get_motor_score_from_db(motor_2in_rate: float, venue_type: str) -> float:
    rules_data = _load_motor_score_rules()
    rules = rules_data.get(venue_type, [])

    if not rules:
        return 0.0

    # min_rate が高い順にソートして判定
    sorted_rules = sorted(rules, key=lambda x: x["min_rate"], reverse=True)
    for rule in sorted_rules:
        if motor_2in_rate >= float(rule["min_rate"]):
            return float(rule["score"])

    return 0.0


##
def get_water_type_from_db(venue_name: str) -> str:
    from data.venue_repository import get_venue_type_info
    info = get_venue_type_info(venue_name)
    return info.get("water_type", "静水")


##
def get_venue_course_score_from_db(venue_name: str, course: int) -> float:
    from data.venue_repository import get_course_score
    return get_course_score(venue_name, course)


##
def get_racer_by_id(racer_id: int) -> dict:
    """選手IDから選手情報を取得"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM racers WHERE racer_id = ?",
        (racer_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    return {}
from data.db_connector import get_connection


##rank_scoresから階級スコアを取得
def get_rank_score_from_db(rank: str) -> float:
    conn = get_connection()
    cursor = conn.cursor()

    normalized_rank = str(rank).strip().upper()
    cursor.execute(
        "SELECT score FROM rank_scores WHERE rank = ?", (normalized_rank,)
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        return float(row["score"])
    return 0.0  # 未定義・見つからない場合は0.0点

##venue_typeから競艇場タイプを取得
def get_venue_type_from_db(venue_name: str) -> str:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT venue_type FROM venue_types WHERE venue_name = ?", (venue_name,)
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        return row["venue_type"]
    return "標準"  # 登録がない場合はデフォルト「標準」

##motor_score_rulesから2連対立のスコアを取得
def get_motor_score_from_db(motor_2in_rate: float, venue_type: str) -> float:
    conn = get_connection()
    cursor = conn.cursor()

    # 該当タイプのルールを threshold (min_rate) 降順で取得
    cursor.execute(
        """
        SELECT min_rate, score FROM motor_score_rules
        WHERE venue_type = ?
        ORDER BY min_rate DESC
    """,
        (venue_type,),
    )
    rules = cursor.fetchall()
    conn.close()

    if not rules:
        # ルールが存在しない場合のバックアップ処理
        return 0.0

    # 高いしきい値から判定
    for rule in rules:
        if motor_2in_rate >= float(rule["min_rate"]):
            return float(rule["score"])

    return 0.0

##
def get_water_type_from_db(venue_name: str) -> str:
    """venue_types テーブルから競艇場の水面タイプ（静水 / 難水）を取得"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT water_type FROM venue_types WHERE venue_name = ?",
        (venue_name,),
    )
    row = cursor.fetchone()
    conn.close()

    if row and row["water_type"]:
        return row["water_type"]
    return "静水"  # 未登録時のデフォルト

##
def get_venue_course_score_from_db(venue_name: str, course: int) -> float:
    """競艇場名と進入コース（1~6）に応じたコース基準スコアをDBから取得"""
    if not (1 <= course <= 6):
        return 0.0

    column_name = f"course{course}_score"
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        f"SELECT {column_name} FROM venue_types WHERE venue_name = ?",
        (venue_name,),
    )
    row = cursor.fetchone()
    conn.close()

    if row and row[column_name] is not None:
        return float(row[column_name])

    # 標準のデフォルト値
    default_scores = {1: 3.0, 2: 2.0, 3: 1.0, 4: 0.5, 5: -1.0, 6: -2.0}
    return default_scores.get(course, 0.0)


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
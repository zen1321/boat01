from typing import Any, Dict, List, Optional


def _safe_float(val: Any, default: Optional[float] = None) -> Optional[float]:
    """欠損値('-', None, 0.0等)を安全にfloatまたはNoneへ変換する"""
    if val is None:
        return default
    if isinstance(val, (int, float)):
        v = float(val)
        return v if v > 0.0 else default
    try:
        s = str(val).strip()
        if not s or s in ("-", "None", "null", "0", "0.0"):
            return default
        v = float(s)
        return v if v > 0.0 else default
    except (ValueError, TypeError):
        return default


def _get_st_val(d: Dict[str, Any]) -> float:
    """直前STを優先取得し、欠損時は平均STで代替する"""
    ex_st = _safe_float(d.get("exhibition_st"))
    if ex_st is not None:
        return ex_st
    avg_st = _safe_float(d.get("avg_st"))
    return avg_st if avg_st is not None else 0.15


def _get_rank_ascending(values: List[Optional[float]], target_val: Optional[float]) -> int:
    """タイム等の値が小さい（早い）順の順位を算出する（欠損時は最下位6位）"""
    if target_val is None:
        return 6
    valid_vals = [v for v in values if v is not None]
    if not valid_vals:
        return 6
    sorted_unique = sorted(list(set(valid_vals)))
    return sorted_unique.index(target_val) + 1 if target_val in sorted_unique else 6


def evaluate_makurisashi_pattern(
    race_racers_data: List[Dict[str, Any]],
    race_exhibition_data: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """パターン③【まくり差し】判定ロジック

    :param race_racers_data: 6艇分の出走表データ（pit_no順）
    :param race_exhibition_data: 6艇分の展示データ（pit_no順）
    :return: 判定結果辞書
    """
    if len(race_racers_data) != 6 or len(race_exhibition_data) != 6:
        raise ValueError("6艇分のデータが必要です。")

    # 1号艇〜6号艇のデータをマッピング
    racers_map = {r["pit_no"]: r for r in race_racers_data}
    ex_map = {e["pit_no"]: e for e in race_exhibition_data}

    # 各艇の必要要素抽出
    st_map = {
        pit: _get_st_val(ex_map[pit]) for pit in range(1, 7)
    }

    # タイム要素
    lap_times = [_safe_float(ex_map[pit].get("lap_time")) for pit in range(1, 7)]
    turn_feet = [_safe_float(ex_map[pit].get("turn_foot")) for pit in range(1, 7)]

    # 旋回足順位付け（周回タイム順位と回り足順位のうち良い方を採用）
    turn_eval_ranks = {}
    for pit in range(1, 7):
        lap_rank = _get_rank_ascending(lap_times, lap_times[pit - 1])
        turn_rank = _get_rank_ascending(turn_feet, turn_feet[pit - 1])
        turn_eval_ranks[pit] = min(lap_rank, turn_rank)

    # 周回タイム単独順位
    lap_ranks = {pit: _get_rank_ascending(lap_times, lap_times[pit - 1]) for pit in range(1, 7)}

    # --------------------------------------------------------------------------
    # 1. Aランク判定（3コースまくり差し）
    # --------------------------------------------------------------------------
    # 【旋回足】3号艇の「一周タイム」または「まわり足タイム」が 1位〜2位
    cond_a_p3_turn = turn_eval_ranks[3] <= 2
    # 【ST】3号艇の直前ST <= 0.15
    cond_a_p3_st = st_map[3] <= 0.15
    # 【イン展開】1号艇の直前ST <= 0.16
    cond_a_p1_st = st_map[1] <= 0.16
    # 【カベ状態】2号艇のSTが3号艇と同等か、やや遅い（3号艇より先行しない）
    cond_a_p2_st = st_map[2] >= (st_map[3] - 0.02)

    if cond_a_p3_turn and cond_a_p3_st and cond_a_p1_st and cond_a_p2_st:
        return {
            "rank": "A",
            "pattern_name": "3コースまくり差し",
            "is_valid": True,
            "bet_policy": "軸: 3-1 | 相手: 4, 5",
            "formation_examples": ["3-1-全", "3-145-145"],
            "details": {
                "p3_st": st_map[3],
                "p1_st": st_map[1],
                "p2_st": st_map[2],
                "p3_turn_rank": turn_eval_ranks[3],
            },
        }

    # --------------------------------------------------------------------------
    # 2. Bランク判定（5コースまくり差し）
    # --------------------------------------------------------------------------
    # 【旋回足】5号艇の「一周タイム」または「まわり足タイム」が 1位
    cond_b_p5_turn = turn_eval_ranks[5] == 1
    # 【展開の引き金】4号艇（または3号艇）が攻める展開（ST <= 0.14 または 回り足/周回順位 <= 2）
    cond_b_trigger = (
        (st_map[4] <= 0.14 or turn_eval_ranks[4] <= 2)
        or (st_map[3] <= 0.14 or turn_eval_ranks[3] <= 2)
    )
    # 【ST】5号艇の直前ST <= 0.16
    cond_b_p5_st = st_map[5] <= 0.16

    if cond_b_p5_turn and cond_b_trigger and cond_b_p5_st:
        return {
            "rank": "B",
            "pattern_name": "5コースまくり差し（連動穴）",
            "is_valid": True,
            "bet_policy": "軸: 5 | 相手: 1, 4, 6",
            "formation_examples": ["5-14-146", "4-5-全"],
            "details": {
                "p5_st": st_map[5],
                "p5_turn_rank": turn_eval_ranks[5],
                "trigger_p4_st": st_map[4],
            },
        }

    # --------------------------------------------------------------------------
    # 3. Cランク判定（6コースまくり差し - 超特大万舟アラート）
    # --------------------------------------------------------------------------
    # 【旋回足】6号艇の「一周タイム」が6艇中 単独1位
    cond_c_p6_lap = (lap_ranks[6] == 1) and (
        len([v for v in lap_times if v is not None and v == lap_times[5]]) == 1
    )
    # 【ST】6号艇の直前ST <= 0.14
    cond_c_p6_st = st_map[6] <= 0.14
    # 【混戦条件】1〜4号艇の旋回評価順位がいずれも1位ではない（前団混戦・流れ気配）
    cond_c_front_fight = all(turn_eval_ranks[pit] > 1 for pit in range(1, 5))

    if cond_c_p6_lap and cond_c_p6_st and cond_c_front_fight:
        return {
            "rank": "C",
            "pattern_name": "6コースまくり差し（大穴アラート）",
            "is_valid": True,
            "bet_policy": "軸: 6（1~2着指定）",
            "formation_examples": ["6-12-全", "1-6-全"],
            "details": {
                "p6_st": st_map[6],
                "p6_lap_rank": lap_ranks[6],
            },
        }

    # 条件に当てはまらない場合
    return {
        "rank": "C",
        "pattern_name": "まくり差し非適用",
        "is_valid": False,
        "reason": "まくり差し判定基準未達成",
    }
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


def evaluate_sashi_pattern(
    race_racers_data: List[Dict[str, Any]],
    race_exhibition_data: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """パターン④【差し】判定ロジック

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
    straights = [_safe_float(ex_map[pit].get("straight_line")) for pit in range(1, 7)]
    ex_times = [_safe_float(ex_map[pit].get("exhibition_time")) for pit in range(1, 7)]

    # 旋回足順位付け（回り足タイム順位または一周タイム順位のうち良い方）
    turn_eval_ranks = {}
    for pit in range(1, 7):
        lap_rank = _get_rank_ascending(lap_times, lap_times[pit - 1])
        turn_rank = _get_rank_ascending(turn_feet, turn_feet[pit - 1])
        turn_eval_ranks[pit] = min(lap_rank, turn_rank)

    # 伸び足順位（展示タイム・直線タイム）
    straight_ranks = {pit: _get_rank_ascending(straights, straights[pit - 1]) for pit in range(1, 7)}
    ex_ranks = {pit: _get_rank_ascending(ex_times, ex_times[pit - 1]) for pit in range(1, 7)}

    # --------------------------------------------------------------------------
    # 1. Aランク判定（2コース鋭角差し）
    # --------------------------------------------------------------------------
    # 【旋回足】2号艇の「まわり足タイム」または「一周タイム」が 1位
    cond_a_p2_turn = turn_eval_ranks[2] == 1
    # 【インのスキ】1号艇の直前ST >= 0.16 または F持ち
    p1_is_f = ex_map[1].get("is_flying", False) or (st_map[1] < 0.0)
    cond_a_p1_gap = (st_map[1] >= 0.16) or p1_is_f
    # 【ST比較】2号艇の直前STが1号艇と同等以上 または 0.03秒以内の遅れ
    cond_a_st_diff = (st_map[2] <= st_map[1]) or ((st_map[2] - st_map[1]) <= 0.03)
    # 【カベ維持】3号艇が上から叩いてこない（3号艇の展示順位およびSTが突出していない）
    cond_a_p3_block = not (st_map[3] <= 0.12 and ex_ranks[3] == 1)

    if cond_a_p2_turn and cond_a_p1_gap and cond_a_st_diff and cond_a_p3_block:
        return {
            "rank": "A",
            "pattern_name": "2コース差し（2頭逆転）",
            "is_valid": True,
            "bet_policy": "軸: 2-1 | 相手: 3, 4, 5",
            "formation_examples": ["2-1-345"],
            "details": {
                "p2_st": st_map[2],
                "p1_st": st_map[1],
                "p2_turn_rank": turn_eval_ranks[2],
            },
        }

    # --------------------------------------------------------------------------
    # 2. Bランク判定（カド差し / 4コース差し）
    # --------------------------------------------------------------------------
    # 【競り合い発生】3号艇のST・行き足が良い（まくり意欲）
    cond_b_p3_attack = (st_map[3] <= 0.14) or (straight_ranks[3] <= 2)
    # 【1号艇の抵抗】1号艇の勝率・能力が高く抵抗気配（全国勝率 >= 6.00 または A級）
    p1_win_rate = _safe_float(racers_map[1].get("national_win_rate"), 0.0)
    p1_rank = str(racers_map[1].get("rank", ""))
    cond_b_p1_resist = (p1_win_rate >= 6.00) or ("A" in p1_rank)
    # 【攻め手の足】4号艇の「まわり足」または「出足」が上位（1〜3位）
    cond_b_p4_turn = turn_eval_ranks[4] <= 3

    if cond_b_p3_attack and cond_b_p1_resist and cond_b_p4_turn:
        return {
            "rank": "B",
            "pattern_name": "4コースカド差し",
            "is_valid": True,
            "bet_policy": "軸: 4 | 相手: 1, 5",
            "formation_examples": ["4-15-1256"],
            "details": {
                "p4_st": st_map[4],
                "p4_turn_rank": turn_eval_ranks[4],
                "p1_win_rate": p1_win_rate,
            },
        }

    # --------------------------------------------------------------------------
    # 3. Cランク判定（5・6コース展開差し）
    # --------------------------------------------------------------------------
    # 【旋回足】5号艇または6号艇の「まわり足タイム」が単独1位
    p5_is_single_top = (turn_eval_ranks[5] == 1) and (
        len([v for k, v in turn_eval_ranks.items() if v == 1]) == 1
    )
    p6_is_single_top = (turn_eval_ranks[6] == 1) and (
        len([v for k, v in turn_eval_ranks.items() if v == 1]) == 1
    )
    cond_c_outer_turn = p5_is_single_top or p6_is_single_top

    # 【前団の混戦】3号艇・4号艇の攻め気配（ST <= 0.14 または 展示/直線順位 <= 2）
    cond_c_front_fight = (st_map[3] <= 0.14 or ex_ranks[3] <= 2) or (
        st_map[4] <= 0.14 or ex_ranks[4] <= 2
    )

    if cond_c_outer_turn and cond_c_front_fight:
        target_pit = 5 if p5_is_single_top else 6
        return {
            "rank": "C",
            "pattern_name": f"{target_pit}コース最内差し（紐・穴軸）",
            "is_valid": True,
            "bet_policy": f"{target_pit}号艇を2・3着指定",
            "formation_examples": [f"123-{target_pit}-全", f"34-{target_pit}-1234"],
            "details": {
                "target_pit": target_pit,
                "p5_turn_rank": turn_eval_ranks[5],
                "p6_turn_rank": turn_eval_ranks[6],
            },
        }

    # 条件に当てはまらない場合
    return {
        "rank": "C",
        "pattern_name": "差し非適用",
        "is_valid": False,
        "reason": "差し判定基準未達成",
    }
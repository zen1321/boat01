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


def evaluate_kad_attack_pattern(
    race_racers_data: List[Dict[str, Any]],
    race_exhibition_data: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """パターン②【カドまくり（叩き）】判定ロジック

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
    straights = [_safe_float(ex_map[pit].get("straight_line")) for pit in range(1, 7)]
    ex_times = [_safe_float(ex_map[pit].get("exhibition_time")) for pit in range(1, 7)]

    p1_ex_time = ex_times[0]
    p3_ex_time = ex_times[2]
    p4_ex_time = ex_times[3]

    p3_straight = straights[2]
    p4_straight = straights[3]

    # 展示タイム順位
    p1_ex_rank = _get_rank_ascending(ex_times, p1_ex_time)
    p3_ex_rank = _get_rank_ascending(ex_times, p3_ex_time)
    p4_ex_rank = _get_rank_ascending(ex_times, p4_ex_time)

    # 直線タイム順位
    p3_straight_rank = _get_rank_ascending(straights, p3_straight)
    p4_straight_rank = _get_rank_ascending(straights, p4_straight)

    # 伸び足（展示タイム順位 or 直線タイム順位）の最高順位
    p3_speed_rank = min(p3_ex_rank, p3_straight_rank)
    p4_speed_rank = min(p4_ex_rank, p4_straight_rank)

    # --------------------------------------------------------------------------
    # 1. Cランク判定（カドまくり不成立・見送り条件）
    # --------------------------------------------------------------------------
    # (1) 3号艇・4号艇の伸び足（展示・直線）がともに4位以下
    weak_attackers = (p3_speed_rank >= 4) and (p4_speed_rank >= 4)

    # (2) 1号艇の壁（1号艇の展示タイムがダントツ1位）
    is_p1_dantotsu = (p1_ex_rank == 1) and all(
        (p1_ex_time is not None and t is not None and (t - p1_ex_time) >= 0.03)
        for i, t in enumerate(ex_times) if i != 0
    )

    if weak_attackers or is_p1_dantotsu:
        return {
            "rank": "C",
            "pattern_name": "まくり不成立（見送り）",
            "is_valid": False,
            "reason": "攻撃艇の伸び不足または1号艇がダントツ",
            "details": {
                "weak_attackers": weak_attackers,
                "is_p1_dantotsu": is_p1_dantotsu,
            },
        }

    # --------------------------------------------------------------------------
    # 2. Aランク判定（4カド一撃まくり）
    # --------------------------------------------------------------------------
    # 【攻め手】4号艇の直前ST <= 0.13
    cond_a_p4_st = st_map[4] <= 0.13
    # 【伸び足】4号艇の展示タイム（または直線タイム）が1位
    cond_a_p4_speed = p4_speed_rank == 1
    # 【カベ崩壊】3号艇の直前ST >= 0.18 または 4号艇より0.05秒以上遅い
    cond_a_wall = (st_map[3] >= 0.18) or (st_map[3] - st_map[4] >= 0.05)
    # 【イン叩き】1号艇より展示タイムが0.04秒以上速い
    cond_a_p1_beat = (
        (p1_ex_time is not None)
        and (p4_ex_time is not None)
        and (p1_ex_time - p4_ex_time >= 0.04)
    )

    if cond_a_p4_st and cond_a_p4_speed and cond_a_wall and cond_a_p1_beat:
        return {
            "rank": "A",
            "pattern_name": "4カドまくり警戒",
            "is_valid": True,
            "bet_policy": "軸: 4 | 相手: 1, 5, 6 | 消し: 2, 3",
            "formation_examples": ["4-56-156", "4-1-56"],
            "details": {
                "p4_st": st_map[4],
                "p3_st": st_map[3],
                "p4_speed_rank": p4_speed_rank,
                "ex_time_diff": round(p1_ex_time - p4_ex_time, 2) if (p1_ex_time and p4_ex_time) else None,
            },
        }

    # --------------------------------------------------------------------------
    # 3. Bランク判定（3コースまくり・絞り）
    # --------------------------------------------------------------------------
    # 【攻め手】3号艇の直前ST <= 0.13
    cond_b_p3_st = st_map[3] <= 0.13
    # 【伸び足】3号艇の展示タイム（または直線タイム）が1位〜2位
    cond_b_p3_speed = p3_speed_rank <= 2
    # 【壁崩壊】2号艇の直前ST >= 0.18
    cond_b_p2_wall = st_map[2] >= 0.18
    # 【1号艇の不安】1号艇の直前ST >= 0.17
    cond_b_p1_st = st_map[1] >= 0.17

    if cond_b_p3_st and cond_b_p3_speed and cond_b_p2_wall and cond_b_p1_st:
        return {
            "rank": "B",
            "pattern_name": "3コースまくり",
            "is_valid": True,
            "bet_policy": "軸: 3 | 相手: 1, 4, 5 | 消し: 2",
            "formation_examples": ["3-14-145"],
            "details": {
                "p3_st": st_map[3],
                "p2_st": st_map[2],
                "p1_st": st_map[1],
                "p3_speed_rank": p3_speed_rank,
            },
        }

    # 条件に当てはまらない場合はC扱い
    return {
        "rank": "C",
        "pattern_name": "カドまくり非適用",
        "is_valid": False,
        "reason": "A/B判定基準未達成（壁が機能している等）",
        "details": {
            "p2_st": st_map[2],
            "p3_st": st_map[3],
            "p4_st": st_map[4],
        },
    }
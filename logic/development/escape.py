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


def evaluate_escape_pattern(
    race_racers_data: List[Dict[str, Any]],
    race_exhibition_data: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """パターン①【イン逃げ（逃げ）】判定ロジック

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
    avg_st_map = {
        pit: _safe_float(racers_map[pit].get("avg_st"), 0.15) for pit in range(1, 7)
    }

    # 1号艇のタイム要素
    lap_times = [_safe_float(ex_map[pit].get("lap_time")) for pit in range(1, 7)]
    turn_feet = [_safe_float(ex_map[pit].get("turn_foot")) for pit in range(1, 7)]
    straights = [_safe_float(ex_map[pit].get("straight_line")) for pit in range(1, 7)]
    ex_times = [_safe_float(ex_map[pit].get("exhibition_time")) for pit in range(1, 7)]

    p1_ex_time = ex_times[0]
    p1_straight = straights[0]

    # 周回・回り足の総合評価用順位（周回タイム順位・回り足順位の平均から算出）
    p1_lap_rank = _get_rank_ascending(lap_times, lap_times[0])
    p1_turn_rank = _get_rank_ascending(turn_feet, turn_feet[0])
    p1_turn_eval_rank = min(p1_lap_rank, p1_turn_rank)  # 周回か回り足のどちらかが良ければ評価

    # 直線タイム順位
    p1_straight_rank = _get_rank_ascending(straights, p1_straight)

    # --------------------------------------------------------------------------
    # 1. Cランク判定（イン逃げ条件付き・危険なイン / 失敗フラグ）
    # --------------------------------------------------------------------------
    # (1) 1号艇のST遅れ（直前ST >= 0.20 または 展示F）
    p1_is_f = ex_map[1].get("is_flying", False) or (st_map[1] < 0.0)
    p1_st_delay = (st_map[1] >= 0.20) or p1_is_f

    # (2) 壁崩壊（2号艇および3号艇の直前STがともに >= 0.19）
    wall_collapsed = (st_map[2] >= 0.19) and (st_map[3] >= 0.19)

    # (3) 強烈なダッシュ攻め（3,4,5号艇の展示/直線タイムが1号艇より0.05秒以上速く、かつST <= 0.13）
    strong_attack = False
    for pit in [3, 4, 5]:
        target_ex = ex_times[pit - 1]
        target_straight = straights[pit - 1]
        target_st = st_map[pit]

        is_fast_ex = (
            (p1_ex_time is not None)
            and (target_ex is not None)
            and (p1_ex_time - target_ex >= 0.05)
        )
        is_fast_straight = (
            (p1_straight is not None)
            and (target_straight is not None)
            and (p1_straight - target_straight >= 0.05)
        )

        if (is_fast_ex or is_fast_straight) and (target_st <= 0.13):
            strong_attack = True
            break

    # Cランク判定
    if p1_st_delay or wall_collapsed or strong_attack:
        return {
            "rank": "C",
            "pattern_name": "イン逃げ条件付き（危険なイン）",
            "is_valid": False,
            "reason": "イン逃げ失敗フラグ検知",
            "details": {
                "p1_st_delay": p1_st_delay,
                "wall_collapsed": wall_collapsed,
                "strong_attack": strong_attack,
            },
        }

    # --------------------------------------------------------------------------
    # 2. Aランク判定（イン逃げ鉄板）
    # --------------------------------------------------------------------------
    # ・1号艇直前ST <= 0.15 (または平均ST <= 0.14)
    cond_a_p1_st = (st_map[1] <= 0.15) or (avg_st_map[1] <= 0.14)
    # ・1号艇周回/回り足が1~3位
    cond_a_p1_turn = p1_turn_eval_rank <= 3
    # ・2号艇直前ST <= 0.17
    cond_a_p2_st = st_map[2] <= 0.17
    # ・4,5号艇展示タイムが1号艇より0.05秒以上速くない
    p4_fast = (
        (p1_ex_time is not None)
        and (ex_times[3] is not None)
        and (p1_ex_time - ex_times[3] >= 0.05)
    )
    p5_fast = (
        (p1_ex_time is not None)
        and (ex_times[4] is not None)
        and (p1_ex_time - ex_times[4] >= 0.05)
    )
    cond_a_outer_threat = not (p4_fast or p5_fast)

    if cond_a_p1_st and cond_a_p1_turn and cond_a_p2_st and cond_a_outer_threat:
        return {
            "rank": "A",
            "pattern_name": "イン逃げ鉄板",
            "is_valid": True,
            "bet_policy": "1-23-全 または 1-23-234",
            "details": {
                "p1_st": st_map[1],
                "p2_st": st_map[2],
                "p1_turn_rank": p1_turn_eval_rank,
            },
        }

    # --------------------------------------------------------------------------
    # 3. Bランク判定（イン逃げ有力）
    # --------------------------------------------------------------------------
    # ・1号艇直前ST <= 0.17
    cond_b_p1_st = st_map[1] <= 0.17
    # ・1号艇直線タイムが1~4位
    cond_b_p1_straight = p1_straight_rank <= 4
    # ・2号艇または3号艇の直前ST < 0.18
    cond_b_wall = (st_map[2] < 0.18) or (st_map[3] < 0.18)

    if cond_b_p1_st and cond_b_p1_straight and cond_b_wall:
        return {
            "rank": "B",
            "pattern_name": "イン逃げ有力",
            "is_valid": True,
            "bet_policy": "1-234-2345",
            "details": {
                "p1_st": st_map[1],
                "p1_straight_rank": p1_straight_rank,
                "wall_st": min(st_map[2], st_map[3]),
            },
        }

    # 条件に当てはまらない場合はC扱い
    return {
        "rank": "C",
        "pattern_name": "イン逃げ非適用",
        "is_valid": False,
        "reason": "A/B判定基準未達成",
    }
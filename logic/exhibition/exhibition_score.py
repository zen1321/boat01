from typing import Any, Dict, List, Optional


def _safe_float(val: Any) -> Optional[float]:
    """文字列やNone、'-'、0などの欠損値を安全にfloatまたはNoneに変換する"""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        v = float(val)
        return v if v > 0.0 else None
    try:
        s = str(val).strip()
        if not s or s in ("-", "None", "null", "0", "0.0"):
            return None
        v = float(s)
        return v if v > 0.0 else None
    except (ValueError, TypeError):
        return None


def _rank_list_safe(
    values: List[Optional[float]], ascending: bool = True
) -> List[int]:
    """欠損値(None)を考慮した順位付けを行う。欠損値は最下位(6位)とする。"""
    valid_vals = [v for v in values if v is not None]

    # 有効データがない場合は全員6位扱い
    if not valid_vals:
        return [6] * len(values)

    sorted_unique = sorted(list(set(valid_vals)), reverse=not ascending)

    ranks = []
    for v in values:
        if v is None:
            ranks.append(6)  # 欠損艇は6位扱い
        else:
            ranks.append(sorted_unique.index(v) + 1)
    return ranks


def evaluate_combination_score(rank1: int, rank2: int) -> float:
    """2つの評価項目（周回/周り足、または展示/直線）の順位組み合わせから加算点を算出"""
    ranks = sorted([rank1, rank2])
    r_first, r_second = ranks[0], ranks[1]

    if r_first == 1 and r_second == 1:
        return 2.0
    elif r_first == 1 and r_second == 2:
        return 1.5
    elif r_first == 1 and r_second >= 3:
        return 1.0
    elif r_first == 2 and r_second >= 2:
        return 0.5
    else:  # 両方3位以下 (r_first >= 3)
        return 0.0


def calculate_race_exhibition_scores(
    race_exhibition_data: List[Dict],
) -> List[Dict]:
    """1レース全6艇の展示データを受け取り、進入コース別の展示評価スコアを算出する（欠損ガード機能付き）"""
    if len(race_exhibition_data) != 6:
        raise ValueError("1レース6艇分のデータが必要です。")

    # 安全な数値抽出（欠損している場合はNone）
    lap_times = [_safe_float(d.get("lap_time")) for d in race_exhibition_data]
    turn_feet = [_safe_float(d.get("turn_foot")) for d in race_exhibition_data]
    exhibition_times = [
        _safe_float(d.get("exhibition_time")) for d in race_exhibition_data
    ]
    straight_lines = [
        _safe_float(d.get("straight_line")) for d in race_exhibition_data
    ]

    # 欠損値を考慮した順位付け (タイム・評価値が小さいほど1位)
    lap_ranks = _rank_list_safe(lap_times, ascending=True)
    turn_ranks = _rank_list_safe(turn_feet, ascending=True)
    ex_ranks = _rank_list_safe(exhibition_times, ascending=True)
    straight_ranks = _rank_list_safe(straight_lines, ascending=True)

    results = []

    for i, data in enumerate(race_exhibition_data):
        course = data.get("entry_course", i + 1)

        # 1, 2, 4, 6コース：周回・周り足で評価
        if course in [1, 2, 4, 6]:
            r1 = lap_ranks[i]
            r2 = turn_ranks[i]
            eval_type = "周回・周り足"
            score = evaluate_combination_score(r1, r2)

        # 3, 5コース：展示・直線で評価
        elif course in [3, 5]:
            r1 = ex_ranks[i]
            r2 = straight_ranks[i]
            eval_type = "展示・直線"
            score = evaluate_combination_score(r1, r2)

        else:
            r1, r2, eval_type, score = 6, 6, "不明", 0.0

        results.append(
            {
                "pit_no": data.get("pit_no", i + 1),
                "entry_course": course,
                "eval_type": eval_type,
                "target_rank1": r1,
                "target_rank2": r2,
                "exhibition_score": score,
            }
        )

    return results
from typing import Dict, List


def _rank_list(values: List[float], ascending: bool = True) -> List[int]:
    """数値リストから同着を考慮した順位リストを作成するヘルパー関数 (STが小さい/早いほど1位)"""
    sorted_vals = sorted(list(set(values)), reverse=not ascending)
    return [sorted_vals.index(v) + 1 for v in values]


def calculate_single_exhibition_st_score(
    ex_st_rank: int,
    avg_st: float,
    is_flying: bool = False,
    is_missing: bool = False,
) -> float:
    """1艇あたりの展示STスコアを算出

    判定ルール:
    - 直前STデータなし(欠損)          : 0.0点
    - 直前STでFを切っている            : 0.0点
    - 直前STが2位以内 & 平均ST 0.14以下  : 1.5点
    - 直前STが2位以内 & 平均ST 0.15以上  : 0.5点
    - 直前STが3位以下 & 平均ST 0.14以下  : 1.0点
    - それ以外（3位以下 & 平均ST 0.15以上）: 0.0点
    """
    # 0. 展示ST欠損（"-"）判定、またはフライング判定
    if is_missing or is_flying:
        return 0.0

    # 1. 直前STが2位以内の場合
    if ex_st_rank <= 2:
        if avg_st <= 0.14:
            return 1.5
        else:  # avg_st >= 0.15
            return 0.5

    # 2. 直前STが3位以下の場合
    else:
        if avg_st <= 0.14:
            return 1.0
        else:  # avg_st >= 0.15
            return 0.0


def calculate_race_exhibition_st_scores(
    race_st_data: List[Dict],
) -> List[Dict]:
    """1レース全6艇の展示STデータを受け取り、展示STスコアを算出（欠損ガード機能付き）

    :param race_st_data: 6艇分の辞書リスト
        各辞書に必要なキー:
        - pit_no: 艇番 (1~6)
        - exhibition_st: 直前展示ST (float, 例: 0.11, Fの場合は -0.01 や 0.00未満, 欠損は 0.0)
        - avg_st: 平均ST (float, 例: 0.13)
        - is_flying: (任意) フライング判定フラグ (bool)
    :return: 各艇の展示STスコア結果リスト
    """
    if len(race_st_data) != 6:
        raise ValueError("1レース6艇分のデータが必要です。")

    # フライング艇・欠損艇を除外せずに順位付け用のSTリストを作成
    st_values = []
    for d in race_st_data:
        st_val = float(d.get("exhibition_st", 0.0) or 0.0)
        # 欠損（0.0）またはフライング（0.0未満）の場合は最下位扱いとして 99.0 を設定
        if st_val <= 0.0 or d.get("is_flying", False):
            st_values.append(99.0)
        else:
            st_values.append(st_val)

    # 6艇中での展示ST順位を算出（早い/小さいほど1位）
    st_ranks = _rank_list(st_values, ascending=True)

    results = []
    for i, data in enumerate(race_st_data):
        ex_st = float(data.get("exhibition_st", 0.0) or 0.0)
        avg_st = float(data.get("avg_st", 0.15) or 0.15)

        is_f = ex_st < 0.0 or data.get("is_flying", False)
        is_missing = ex_st == 0.0  # 0.0 を欠損（"-"）と判断

        rank = st_ranks[i]

        score = calculate_single_exhibition_st_score(
            ex_st_rank=rank,
            avg_st=avg_st,
            is_flying=is_f,
            is_missing=is_missing,
        )

        # 順位表示の調整（フライングは'F'、欠損は'-'）
        if is_missing:
            display_rank = "-"
        elif is_f:
            display_rank = "F"
        else:
            display_rank = rank

        results.append(
            {
                "pit_no": data.get("pit_no"),
                "exhibition_st": ex_st,
                "ex_st_rank": display_rank,
                "avg_st": avg_st,
                "is_flying": is_f,
                "is_missing": is_missing,
                "exhibition_st_score": score,
            }
        )

    return results
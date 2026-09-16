def calculate_avg_st_score(avg_st: float) -> float:
    """平均ST（スタートタイミング）に応じた加減算スコアを算出

    :param avg_st: 平均ST (例: 0.14)
    :return: 平均STスコア (float)

    判定基準:
    - 0.12秒以下  : +2.0点
    - 0.13~0.14秒 : +1.0点
    - 0.15~0.16秒 :  0.0点
    - 0.17~0.18秒 : -0.5点
    - 0.19秒以上  : -1.5点
    """
    if avg_st <= 0.12:
        return 2.0
    elif avg_st <= 0.14:
        return 1.0
    elif avg_st <= 0.16:
        return 0.0
    elif avg_st <= 0.18:
        return -0.5
    else:
        return -1.5
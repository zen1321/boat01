from typing import Any, Dict


def calculate_wind_score(
    pit_no: int, wind_direction: str, wind_speed: float
) -> float:
    """風向および風速に応じたスコアを算出

    :param pit_no: 艇番 (1~6)
    :param wind_direction: 風向 ('追い風', '向かい風' など)
    :param wind_speed: 風速 (m)
    :return: 風影響スコア (float)
    """
    if wind_speed < 4.0:
        return 0.0  # 4m未満は影響なし

    # 追い風 4m以上
    if wind_direction in ["追い風", "追風"]:
        scores = {1: -0.5, 2: 1.5, 3: 1.5, 4: 1.0, 5: 1.0, 6: 1.0}
        return scores.get(pit_no, 0.0)

    # 向かい風 4m以上
    elif wind_direction in ["向かい風", "向風"]:
        scores = {1: 0.0, 2: 0.0, 3: 1.0, 4: 1.0, 5: 1.0, 6: 1.0}
        return scores.get(pit_no, 0.0)

    return 0.0


def calculate_race_wind_scores(
    wind_direction: str, wind_speed: float
) -> Dict[int, float]:
    """1レース分（1~6号艇）の風スコアを一括算出"""
    return {
        pit: calculate_wind_score(pit, wind_direction, wind_speed)
        for pit in range(1, 7)
    }


# 動作確認用テスト
if __name__ == "__main__":
    print("--- 追い風 5m の各艇スコア ---")
    print(calculate_race_wind_scores("追い風", 5.0))

    print("\n--- 向かい風 4m の各艇スコア ---")
    print(calculate_race_wind_scores("向かい風", 4.0))

    print("\n--- 追い風 3m（4m未満） の各艇スコア ---")
    print(calculate_race_wind_scores("追い風", 3.0))
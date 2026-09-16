from typing import Any, Dict, List
from logic.development.escape import evaluate_escape_pattern
from logic.development.kad_attack import evaluate_kad_attack_pattern
from logic.development.makurisashi import evaluate_makurisashi_pattern
from logic.development.sashi import evaluate_sashi_pattern


def analyze_race_development(
    race_racers_data: List[Dict[str, Any]],
    race_exhibition_data: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """6艇の出走表データと展示データから全4パターンの展開を評価し、最有力展開と買い目を算出する。

    :param race_racers_data: 6艇分の出走表データ（pit_no順）
    :param race_exhibition_data: 6艇分の展示データ（pit_no順）
    :return: 総合展開判定結果辞書
    """
    # 1. 各パターンの判定を実行
    res_escape = evaluate_escape_pattern(race_racers_data, race_exhibition_data)
    res_kad = evaluate_kad_attack_pattern(race_racers_data, race_exhibition_data)
    res_makuri = evaluate_makurisashi_pattern(race_racers_data, race_exhibition_data)
    res_sashi = evaluate_sashi_pattern(race_racers_data, race_exhibition_data)

    results = {
        "escape": res_escape,
        "kad_attack": res_kad,
        "makurisashi": res_makuri,
        "sashi": res_sashi,
    }

    # 2. 成立している展開（is_valid == True）の抽出
    valid_patterns = [
        {"type": key, **val} for key, val in results.items() if val.get("is_valid")
    ]

    # ランク優先度マッピング (A=3, B=2, C=1)
    rank_score = {"A": 3, "B": 2, "C": 1}

    # 成立判定がない場合は「波乱・判定不可」
    if not valid_patterns:
        return {
            "primary_development": "混戦（波乱含み・判定外）",
            "primary_rank": "C",
            "bet_policy": "見送り、または選手単体スコア上位軸の流し買い",
            "all_evaluations": results,
            "recommended_formations": [],
        }

    # 3. 優先度（Aランク優先 ＞ 発見順）でメイン展開（主軸展開）を判定
    sorted_patterns = sorted(
        valid_patterns, key=lambda x: rank_score.get(x["rank"], 0), reverse=True
    )

    primary = sorted_patterns[0]

    # 買い目フォーメーションの集約
    formations = primary.get("formation_examples", [])
    if "bet_policy" in primary and not formations:
        formations = [primary["bet_policy"]]

    # 副展開（2番目に有力な展開）が存在する場合の記録
    sub_development = sorted_patterns[1] if len(sorted_patterns) > 1 else None

    return {
        "primary_development": primary.get("pattern_name"),
        "primary_rank": primary.get("rank"),
        "bet_policy": primary.get("bet_policy"),
        "recommended_formations": formations,
        "sub_development": (
            sub_development.get("pattern_name") if sub_development else None
        ),
        "valid_pattern_count": len(valid_patterns),
        "all_evaluations": results,
    }
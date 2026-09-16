from typing import Any, Dict, List
from logic.development import analyze_race_development


def generate_final_betting_recommendation(
    racer_scores: List[Dict[str, Any]],
    race_racers_data: List[Dict[str, Any]],
    race_exhibition_data: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """選手スコアと展開予想ロジックを合体させ、最終的な買い目と資金配分比率を算出する

    :param racer_scores: 6艇分の選手スコア結果 [{'pit_no': 1, 'total_score': 85.5, ...}, ...]
    :param race_racers_data: 6艇分の出走表データ（pit_no順）
    :param race_exhibition_data: 6艇分の展示データ（pit_no順）
    :return: 最終買い目判定辞書
    """
    # 1. 展開ロジックの評価を実行
    dev_result = analyze_race_development(race_racers_data, race_exhibition_data)
    primary_dev = dev_result["primary_development"]
    primary_rank = dev_result["primary_rank"]

    # 2. 選手スコアを順位ソート
    sorted_racers_by_score = sorted(
        racer_scores, key=lambda x: x["total_score"], reverse=True
    )
    top_score_pit = sorted_racers_by_score[0]["pit_no"]

    # 3. 信頼度判定
    confidence_level = "HIGH" if primary_rank == "A" else ("MEDIUM" if primary_rank == "B" else "LOW")
    if primary_dev == "イン逃げ鉄板" and top_score_pit != 1:
        confidence_level = "MEDIUM"

    # 4. 買い目の生成処理
    recommended_bets = []

    if primary_dev == "イン逃げ鉄板":
        # 【イン逃げ鉄板】1頭固定・2着は1号艇を除いた最高スコア艇に固定
        non_1_racers = [r for r in sorted_racers_by_score if r["pit_no"] != 1]
        
        # 1号艇を除いて最もスコアが高い艇（2着固定）
        top_non_1_pit = non_1_racers[0]["pit_no"]
        p2_candidates = [top_non_1_pit]

        # 3番手候補: 1号艇以外の最高スコア(S2)との差が 3.0 以内の艇
        base_score = non_1_racers[0]["total_score"]
        p3_candidates = [
            r["pit_no"] for r in non_1_racers
            if (base_score - r["total_score"]) <= 3.0
        ]

        raw_combinations = []
        for p2 in p2_candidates:
            for p3 in p3_candidates:
                if p2 != p3:
                    raw_combinations.append((1, p2, p3))

        total_combos = len(raw_combinations)
        if total_combos > 0:
            weight_per_bet = round(100 / total_combos, 1)
            for c in raw_combinations:
                recommended_bets.append({
                    "bet": f"{c[0]}-{c[1]}-{c[2]}",
                    "weight": weight_per_bet
                })
        else:
            # 万が一3着候補が絞り込めなかった場合のセーフティ
            recommended_bets = [{"bet": f"1-{top_non_1_pit}-全", "weight": 100.0}]

    elif primary_dev in ["イン逃げ有力"]:
        recommended_bets = [
            {"bet": "1-2-全", "weight": 40},
            {"bet": "1-3-全", "weight": 30},
            {"bet": "1-4-全", "weight": 30},
        ]

    elif "まくり" in primary_dev:
        # 軸艇（1着）の設定判定
        if "5コース" in primary_dev or "5号艇" in primary_dev:
            attacker_pit = 5
        elif "6コース" in primary_dev or "6号艇" in primary_dev:
            attacker_pit = 6
        else:
            attacker_pit = 4 if "4カド" in primary_dev else 3

        # 軸艇ごとの2着候補の設定
        p2_map = {
            3: [1, 4],
            4: [1, 5],
            5: [1, 6],
            6: [1, 5]
        }
        p2_candidates = p2_map.get(attacker_pit, [1, 2])

        # 組み合わせ生成 (頭-2着-全)
        raw_combinations = []
        for p2 in p2_candidates:
            for p3 in range(1, 7):
                if p3 != attacker_pit and p3 != p2:
                    raw_combinations.append((attacker_pit, p2, p3))

        total_combos = len(raw_combinations)
        if total_combos > 0:
            weight_per_bet = round(100 / total_combos, 1)
            for c in raw_combinations:
                recommended_bets.append({
                    "bet": f"{c[0]}-{c[1]}-{c[2]}",
                    "weight": weight_per_bet
                })

    elif "差し" in primary_dev:
        sashi_pit = 2 if "2コース" in primary_dev else 4
        recommended_bets = [
            {"bet": f"{sashi_pit}-1-全", "weight": 60},
            {"bet": f"{sashi_pit}-3-全", "weight": 20},
            {"bet": f"{sashi_pit}-4-全", "weight": 20},
        ]

    else:
        # 混戦・判定なし（上位スコア組）
        top1, top2, top3, top4 = [r["pit_no"] for r in sorted_racers_by_score[:4]]
        recommended_bets = [
            {"bet": f"{top1}-{top2}-{top3}", "weight": 40},
            {"bet": f"{top1}-{top2}-{top4}", "weight": 30},
            {"bet": f"{top1}-{top3}-{top2}", "weight": 30},
        ]

    return {
        "confidence": confidence_level,
        "primary_development": primary_dev,
        "development_rank": primary_rank,
        "top_score_pit": top_score_pit,
        "betting_policy": dev_result.get("bet_policy"),
        "recommended_bets": recommended_bets,
        "development_details": dev_result,
    }
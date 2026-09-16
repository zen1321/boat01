import itertools
from typing import Any, Dict, List


def generate_focused_bets(
    results: List[Dict[str, Any]], gap_threshold: float = 1.5
) -> Dict[str, Any]:
    """1.5点差を基準とした同着（グループ化）判定を行い、3連単の絞り込み買い目を生成する"""
    if not results or len(results) < 3:
        return {
            "pattern_name": "データ不足",
            "formation_text": "-",
            "tickets": [],
            "total_count": 0,
            "description": "有効な出走艇データが不足しています。",
        }

    # スコア順にソート
    sorted_results = sorted(results, key=lambda x: x["total_score"], reverse=True)

    # 各艇の情報を取り出す
    racers = [
        {"pit": r["pit_no"], "score": float(r["total_score"])}
        for r in sorted_results
    ]

    # グループ分け（最高スコアから1.5点以内を同一階層として判定）
    tiers: List[List[Dict[str, Any]]] = []
    remaining_racers = list(racers)

    while remaining_racers and len(tiers) < 3:
        tier_max_score = remaining_racers[0]["score"]
        current_tier = [
            r
            for r in remaining_racers
            if (tier_max_score - r["score"]) <= gap_threshold
        ]
        tiers.append(current_tier)
        # グループに割り振られた艇を除外
        remaining_racers = [r for r in remaining_racers if r not in current_tier]

    tier1 = tiers[0] if len(tiers) > 0 else []
    tier2 = tiers[1] if len(tiers) > 1 else []
    tier3 = tiers[2] if len(tiers) > 2 else []

    tickets: List[str] = []
    pattern_name = ""
    description = ""
    formation_text = ""

    # --------------------------------------------------------------------------
    # パターンA：1強型（トップが単独軸）
    # --------------------------------------------------------------------------
    if len(tier1) == 1:
        p1 = [tier1[0]["pit"]]
        pattern_name = "🎯 1強型（軸固定）"

        if len(tier2) >= 2:
            p2 = [r["pit"] for r in tier2]
            p3 = [r["pit"] for r in tier2]
            description = f"{p1[0]}号艇が単独トップ。2着・3着争いの {','.join(map(str, p2))}号艇（同格）へ流します。"
        elif len(tier2) == 1:
            p2 = [tier2[0]["pit"]]
            p3 = [r["pit"] for r in tier3[:2]] if tier3 else [r["pit"] for r in racers[2:4]]
            description = f"{p1[0]}号艇が本命、{p2[0]}号艇が対抗。3着候補に {','.join(map(str, p3))}号艇を紐付けます。"
        else:
            p2 = [r["pit"] for r in racers[1:3]]
            p3 = [r["pit"] for r in racers[1:4]]
            description = f"{p1[0]}号艇を1着固定にして上位展開へ流します。"

        for st_1 in p1:
            for st_2 in p2:
                if st_2 == st_1:
                    continue
                for st_3 in p3:
                    if st_3 in (st_1, st_2):
                        continue
                    tickets.append(f"{st_1}-{st_2}-{st_3}")

        p1_str = ",".join(map(str, p1))
        p2_str = ",".join(map(str, sorted(set(p2))))
        p3_str = ",".join(map(str, sorted(set(p3))))
        formation_text = f"{p1_str} - {p2_str} - {p3_str}"

    # --------------------------------------------------------------------------
    # パターンB：2強型（上位2艇が1.5点差以内の同着扱い）
    # --------------------------------------------------------------------------
    elif len(tier1) == 2:
        p1 = [r["pit"] for r in tier1]
        pattern_name = "⚔️ 2強型（折り返し軸）"

        p2 = [r["pit"] for r in tier1]
        if tier2:
            p3 = [r["pit"] for r in tier2[:3]]
        else:
            p3 = [r["pit"] for r in racers[2:4]]

        description = f"{p1[0]}号艇と{p1[1]}号艇のスコア差が1.5点以内の接戦。両艇の折り返しを軸とし、相手 {','.join(map(str, p3))}号艇へ流します。"

        for st_1 in p1:
            for st_2 in p2:
                if st_2 == st_1:
                    continue
                for st_3 in p3:
                    if st_3 in (st_1, st_2):
                        continue
                    tickets.append(f"{st_1}-{st_2}-{st_3}")

        p1_str = ",".join(map(str, sorted(p1)))
        p2_str = ",".join(map(str, sorted(p2)))
        p3_str = ",".join(map(str, sorted(set(p3))))
        formation_text = f"{p1_str} - {p2_str} - {p3_str}"

    # --------------------------------------------------------------------------
    # パターンC：混戦型（上位3艇以上が1.5点差以内）
    # --------------------------------------------------------------------------
    else:
        p1 = [r["pit"] for r in tier1[:3]]
        pattern_name = "🔥 混戦型（上位BOX）"
        description = f"上位{len(p1)}艇（{','.join(map(str, p1))}号艇）のスコアが1.5点差以内にひしめく混戦。上位陣の3連単BOXに絞ります。"

        for perm in itertools.permutations(p1, 3):
            tickets.append(f"{perm[0]}-{perm[1]}-{perm[2]}")

        p_str = ",".join(map(str, sorted(p1)))
        formation_text = f"{p_str} (3連単BOX)"

    # 重複排除＆ソート
    tickets = sorted(list(dict.fromkeys(tickets)))

    return {
        "pattern_name": pattern_name,
        "formation_text": formation_text,
        "tickets": tickets,
        "total_count": len(tickets),
        "description": description,
    }
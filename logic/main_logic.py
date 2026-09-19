from typing import Any, Dict, List

from data.racer_repository import get_racer_by_id
from logic.exhibition.exhibition_score import calculate_race_exhibition_scores
from logic.exhibition.exhibition_st_score import (
    calculate_race_exhibition_st_scores,
)
from logic.racer.avg_st_score import calculate_avg_st_score
from logic.racer.course_score import calculate_course_score
from logic.racer.motor_score import calculate_motor_score
from logic.racer.rank_score import calculate_rank_score
from logic.racer.win_rate_score import calculate_win_rate_score
from logic.weather.tide_score import calculate_race_tide_scores
from logic.weather.wind_score import calculate_race_wind_scores


def _safe_float_val(val: Any, default: float = 0.0) -> float:
    """型キャストエラーを塞ぐ安全なfloat化ヘルパー"""
    if val is None:
        return default
    try:
        s = str(val).strip()
        if not s or s in ("-", "None", "null"):
            return default
        return float(s)
    except (ValueError, TypeError):
        return default


def calculate_racer_total_score(
    racer_id: Any,
    national_win_rate: float,
    local_win_rate: float,
    motor_rate: float,
    avg_st: float,
    entry_course: int,
    venue_name: str,
    rank: str = None,
) -> Dict[str, Any]:
    """選手情報に関する基本スコア（小計）を集計する"""
    if rank is None or not str(rank).strip():
        racer_info = get_racer_by_id(racer_id)
        rank = racer_info.get("rank", "B1") if racer_info else "B1"

    r_score = calculate_rank_score(rank)
    w_score = calculate_win_rate_score(
        national_win_rate=_safe_float_val(national_win_rate),
        local_win_rate=_safe_float_val(local_win_rate),
        venue=venue_name,
    )

    m_score = calculate_motor_score(
        motor_2in_rate=_safe_float_val(motor_rate), venue=venue_name
    )

    st_score = calculate_avg_st_score(avg_st=_safe_float_val(avg_st, 0.15))
    c_score = calculate_course_score(
        course=int(_safe_float_val(entry_course, 1)), venue=venue_name
    )

    total_racer_score = round(
        r_score + w_score + m_score + st_score + c_score, 2
    )

    return {
        "racer_id": racer_id,
        "venue_name": venue_name,
        "entry_course": entry_course,
        "total_racer_score": total_racer_score,
        "breakdown": {
            "rank_score": r_score,
            "win_rate_score": w_score,
            "motor_score": m_score,
            "avg_st_score": st_score,
            "course_score": c_score,
        },
    }


def calculate_full_race_scores(
    venue_name: str,
    race_racers_data: List[Dict[str, Any]],
    race_exhibition_data: List[Dict[str, Any]],
    weather_info: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """1レース全6艇の「選手基本情報」「直前展示情報」「気象条件」を全て合算し、総合スコアと予測順位を算出する"""
    if len(race_racers_data) != 6 or len(race_exhibition_data) != 6:
        raise ValueError("6艇分のデータが必要です。")

    # 1. 各艇の選手基本スコアを算出
    racer_scores_map = {}
    for r_data in race_racers_data:
        pit = r_data["pit_no"]
        racer_scores_map[pit] = calculate_racer_total_score(
            racer_id=r_data.get("racer_id", 0),
            national_win_rate=r_data.get("national_win_rate", 0.0),
            local_win_rate=r_data.get("local_win_rate", 0.0),
            motor_rate=r_data.get("motor_rate", 0.0),
            avg_st=r_data.get("avg_st", 0.15),
            entry_course=r_data.get("entry_course", pit),
            venue_name=venue_name,
            rank=r_data.get("rank"),
        )

    # 2. 直前展示タイム評価スコアの算出（欠損対応済み）
    try:
        ex_scores = calculate_race_exhibition_scores(race_exhibition_data)
        ex_score_map = {res["pit_no"]: res for res in ex_scores}
    except Exception:
        ex_score_map = {}

    # 3. 展示ST評価スコアの算出（エラーガード）
    try:
        st_scores = calculate_race_exhibition_st_scores(race_exhibition_data)
        st_score_map = {res["pit_no"]: res for res in st_scores}
    except Exception:
        st_score_map = {}

    # 4. 気象（風）影響スコアの一括算出
    wind_scores = calculate_race_wind_scores(
        wind_direction=weather_info.get("wind_direction", ""),
        wind_speed=_safe_float_val(weather_info.get("wind_speed")),
    )

    # 5. 気象（潮）影響スコアの一括算出
    tide_scores = calculate_race_tide_scores(
        tide_state=weather_info.get("tide_state", "")
    )

    # 6. 最終スコアの合算と構造化
    final_results = []
    for ex_data in race_exhibition_data:
        pit = ex_data["pit_no"]
        course = ex_data.get("entry_course", pit)

        racer_res = racer_scores_map.get(
            pit, {"total_racer_score": 0.0, "breakdown": {}}
        )
        ex_res = ex_score_map.get(
            pit, {"exhibition_score": 0.0, "eval_type": "データなし"}
        )
        st_res = st_score_map.get(
            pit, {"exhibition_st_score": 0.0, "ex_st_rank": 6}
        )

        w_score = wind_scores.get(pit, 0.0) if isinstance(wind_scores, dict) else 0.0
        t_score = tide_scores.get(pit, 0.0) if isinstance(tide_scores, dict) else 0.0

        total_score = round(
            racer_res["total_racer_score"]
            + ex_res.get("exhibition_score", 0.0)
            + st_res.get("exhibition_st_score", 0.0)
            + w_score
            + t_score,
            2,
        )

        final_results.append(
            {
                "pit_no": pit,
                "entry_course": course,
                "total_score": total_score,
                "score_breakdown": {
                    "racer_base_subtotal": racer_res["total_racer_score"],
                    "racer_breakdown": racer_res["breakdown"],
                    "exhibition_score": ex_res.get("exhibition_score", 0.0),
                    "exhibition_st_score": st_res.get("exhibition_st_score", 0.0),
                    "wind_score": w_score,
                    "tide_score": t_score,
                },
                "details": {
                    "exhibition_eval_type": ex_res.get("eval_type"),
                    "ex_st_rank": st_res.get("ex_st_rank"),
                },
            }
        )

    final_results.sort(key=lambda x: x["total_score"], reverse=True)
    for rank_no, item in enumerate(final_results, 1):
        item["predicted_rank"] = rank_no

    return final_results
from data.racer_repository import get_rank_score_from_db


def calculate_rank_score(rank: str) -> float:
    """階級に応じた加減算スコアをDBから取得して算出"""
    return get_rank_score_from_db(rank)
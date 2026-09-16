from data.racer_repository import get_venue_course_score_from_db


def calculate_course_score(course: int, venue: str = "平和島") -> float:
    """進入コースと競艇場名からコース別成績スコアを算出

    :param course: 進入コース (1~6)
    :param venue: 競艇場名 (例: '平和島')
    :return: コース別スコア (float)
    """
    return get_venue_course_score_from_db(venue, course)
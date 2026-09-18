from data.venue_repository import get_course_score

def calculate_course_score(course: int, venue: str = "平和島") -> float:
    """進入コースと競艇場名からコース別成績スコアを算出

    :param course: 進入コース (1~6)
    :param venue: 競艇場名 (例: '平和島')
    :return: コース別スコア (float)
    """
    # DBではなく JSON 読み込み関数（get_course_score）を呼び出す
    return get_course_score(venue_name=venue, course_no=course)
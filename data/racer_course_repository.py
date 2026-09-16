import os
import sqlite3
from typing import Any, Dict

DB_PATH = os.path.join(os.path.dirname(__file__), "boat_race.db")


def get_racer_course_stat(
    racer_id: int, course_no: int, db_path: str = DB_PATH
) -> Dict[str, Any]:
    """登番と進入コース番号から選手のコース成績を取得し、各着率を計算する"""
    default_res = {
        "entry_count": 0,
        "avg_st": 0.0,
        "win_1st_rate": 0.0,
        "win_2nd_rate": 0.0,
        "win_3rd_rate": 0.0,
        "win_3in_rate": 0.0,
    }

    if not os.path.exists(db_path):
        return default_res

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        query = """
            SELECT entry_count, avg_st, win_1st, win_2nd, win_3rd, win_4th, win_5th, win_6th
            FROM racer_course_stats
            WHERE racer_id = ? AND course_no = ?
        """
        cursor.execute(query, (int(racer_id), int(course_no)))
        row = cursor.fetchone()
        conn.close()

        if row:
            entry_count = row[0] or 0
            avg_st = row[1] if row[1] is not None else 0.0
            win_1st = row[2] or 0
            win_2nd = row[3] or 0
            win_3rd = row[4] or 0

            if entry_count > 0:
                win_1st_rate = (win_1st / entry_count) * 100
                win_2nd_rate = (win_2nd / entry_count) * 100
                win_3rd_rate = (win_3rd / entry_count) * 100
                win_3in_rate = ((win_1st + win_2nd + win_3rd) / entry_count) * 100
            else:
                win_1st_rate = 0.0
                win_2nd_rate = 0.0
                win_3rd_rate = 0.0
                win_3in_rate = 0.0

            return {
                "entry_count": entry_count,
                "avg_st": avg_st,
                "win_1st_rate": win_1st_rate,
                "win_2nd_rate": win_2nd_rate,
                "win_3rd_rate": win_3rd_rate,
                "win_3in_rate": win_3in_rate,
            }

        return default_res

    except Exception as e:
        print(f"racer_course_stats データ取得エラー: {e}")
        return default_res
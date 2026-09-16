import os
import sqlite3
from typing import List

DB_PATH = os.path.join(os.path.dirname(__file__), "boat_race.db")

# フォールバック用の24競艇場リスト
DEFAULT_VENUES = [
#     "桐生",
#     "戸田",
#     "江戸川",
#     "平和島",
#     "多摩川",
#     "浜名湖",
#     "蒲郡",
#     "常滑",
#     "津",
#     "三国",
#     "びわこ",
#     "住之江",
#     "尼崎",
#     "鳴門",
#     "丸亀",
#     "児島",
#     "宮島",
#     "徳山",
#     "下関",
#     "若松",
#     "芦屋",
#     "福岡",
#     "唐津",
#     "大村",
]


def get_all_venues(db_path: str = DB_PATH) -> List[str]:
    """venue_types テーブルから競艇場名一覧を取得する

    :param db_path: データベースファイルのパス
    :return: 競艇場名のリスト
    """
    if not os.path.exists(db_path):
        return DEFAULT_VENUES

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # venue_types テーブルから venue_name を取得
        cursor.execute(
            "SELECT venue_name FROM venue_types"
        )
        rows = cursor.fetchall()
        conn.close()

        if rows:
            return [row[0] for row in rows]
        return DEFAULT_VENUES

    except sqlite3.Error:
        # カラム名等が異なる場合のフォールバック（nameやid指定等）
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM venue_types")
            rows = cursor.fetchall()
            conn.close()
            if rows:
                return [row[0] for row in rows]
        except Exception:
            pass
        return DEFAULT_VENUES
import os
import re
from typing import Any, Dict, List, Tuple


def _safe_float(val_str: str, default: float = 0.0) -> float:
    """文字列を安全にfloat型に変換する（'-' や空文字、Noneの場合は default 値を返す）"""
    if not val_str:
        return default
    cleaned = str(val_str).strip()
    if cleaned in ("-", "None", "null", ""):
        return default
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return default


def _clean_st_value(st_str: str) -> float:
    """F.09 や F0.09 などのフライング表記、および '-' などの欠損表記を数値 (0.09) に変換してパースする"""
    if not st_str or str(st_str).strip() in ("-", "None", "null", ""):
        return 0.0

    cleaned = re.sub(r"[FL\.]+", ".", str(st_str)).strip()
    if cleaned.startswith("."):
        cleaned = "0" + cleaned
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def load_race_detail_from_txt(
    file_path: str = "txt_data/race_detail.txt",
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """txtファイル（行＝項目、列＝1〜6号艇）から情報を読み込み、ロジック用データ構造に変換する

    :param file_path: txtファイルのパス
    :return: (race_racers_data, race_exhibition_data) のタプル
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    # 項目ごとに行に分割（タブまたは2個以上のスペースで分割）
    matrix = []
    for line in lines:
        if line.startswith("#"):
            continue
        items = re.split(r"\t+|\s{2,}", line)
        if len(items) == 1:
            items = line.split()  # 単一スペース区切りへのフォールバック
        matrix.append(items)

    if len(matrix) < 15:
        raise ValueError(
            f"データ行数が不足しています（必要: 15行, 取得: {len(matrix)}行）。"
        )

    racers_data = []
    exhibition_data = []

    # 各列（0~5 = 1号艇~6号艇）ごとにデータを抽出[cite: 2]
    for col_idx in range(6):
        pit_no = col_idx + 1
        entry_course = pit_no

        racer_id = int(_safe_float(matrix[1][col_idx], 0))
        racer_name = matrix[2][col_idx]
        rank = matrix[3][col_idx]
        term = matrix[4][col_idx]  # 期
        birthplace = matrix[5][col_idx]
        motor_rate = _safe_float(matrix[6][col_idx])
        avg_st = _clean_st_value(matrix[7][col_idx])
        national_win_rate = _safe_float(matrix[8][col_idx])
        local_win_rate = _safe_float(matrix[9][col_idx])

        # 直前展示データ（'-' の場合は 0.0 に安全変換）
        exhibition_time = _safe_float(matrix[10][col_idx])
        lap_time = _safe_float(matrix[11][col_idx])

        # 回り足・直線の数値変換（'-' 等の欠損時は 0.0）
        turn_foot = _safe_float(matrix[12][col_idx], default=0.0)
        straight_line = _safe_float(matrix[13][col_idx], default=0.0)

        exhibition_st = _clean_st_value(matrix[14][col_idx])

        racers_data.append(
            {
                "pit_no": pit_no,
                "entry_course": entry_course,
                "racer_id": racer_id,
                "racer_name": racer_name,
                "rank": rank,
                "term": term,
                "birthplace": birthplace,
                "national_win_rate": national_win_rate,
                "local_win_rate": local_win_rate,
                "motor_rate": motor_rate,
                "avg_st": avg_st,
            }
        )

        exhibition_data.append(
            {
                "pit_no": pit_no,
                "entry_course": entry_course,
                "lap_time": lap_time,
                "turn_foot": turn_foot,
                "exhibition_time": exhibition_time,
                "straight_line": straight_line,
                "exhibition_st": exhibition_st,
                "avg_st": avg_st,
            }
        )

    return racers_data, exhibition_data
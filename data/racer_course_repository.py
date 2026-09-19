import json
import os
from pathlib import Path
from typing import Any, Dict, Union

# JSONファイルのパス設定（fan2604.json）
JSON_PATH = Path(__file__).resolve().parent.parent / "data_json" / "fan2604.json"

# パフォーマンス向上のため、JSONデータをキャッシュ保持
_racers_cache: Dict[str, Dict[str, Any]] = {}


def _safe_int(val: Any, default: int = 0) -> int:
    """文字列（例: '030', ' 005 ' 等）を安全に数値型(int)に変換する"""
    if val is None:
        return default
    try:
        s_val = str(val).strip()
        return int(s_val) if s_val else default
    except (ValueError, TypeError):
        return default


def _load_racers_data(json_path: Union[str, Path] = JSON_PATH) -> Dict[str, Dict[str, Any]]:
    """JSONファイルを読み込んで登番(toban)をキーにした辞書を作成・キャッシュする"""
    global _racers_cache
    if _racers_cache:
        return _racers_cache

    target_path = Path(json_path)

    if not target_path.exists():
        print(f"警告: 選手データファイルが見つかりません: {target_path}")
        return {}

    try:
        with open(target_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # 登番(toban)をキーとして辞書化
            _racers_cache = {str(item.get("toban", "")).strip(): item for item in data}
    except Exception as e:
        print(f"JSON読み込みエラー: {e}")
        _racers_cache = {}

    return _racers_cache


def get_racer_basic_info(racer_id: str, json_path: Union[str, Path] = JSON_PATH) -> Dict[str, str]:
    """
    登番(racer_id)から選手データ(fan2604.json)を参照し、
    名前(漢字)、ランク、今期平均STを取得して返す。
    """
    default_res = {"name": "", "rank": "", "st_avg": ""}
    
    racers = _load_racers_data(json_path)
    racer_key = str(racer_id).strip()

    if racer_key not in racers:
        return default_res

    racer = racers[racer_key]
    
    # 名前の取得（全角スペース等を整形）
    raw_name = str(racer.get("name_kanji", "")).replace("\u3000", " ").strip()
    
    # ランクの取得 (例: A1, B1)
    rank = str(racer.get("rank", "")).strip()
    
    # 今期平均STの取得・フォーマット (例: "021" -> "0.21")
    raw_st = str(racer.get("st_avg", "")).strip()
    st_avg = ""
    if raw_st.isdigit():
        st_val = float(raw_st) / 100.0
        st_avg = f"{st_val:.2f}"

    return {
        "name": raw_name,
        "rank": rank,
        "st_avg": st_avg,
    }


def get_racer_course_stat(
    racer_id: str, course_no: int, json_path: Union[str, Path] = JSON_PATH
) -> Dict[str, Any]:
    """
    登番(racer_id)と進入コース番号(course_no)から選手データを参照し、
    各着率(1着率, 2着率, 3着率)および3連対率(%)を計算して返却する。
    """
    default_res = {
        "entry_count": 0,
        "win_1st_rate": 0.0,
        "win_2nd_rate": 0.0,
        "win_3rd_rate": 0.0,
        "win_3in_rate": 0.0,
    }

    racers = _load_racers_data(json_path)
    racer_key = str(racer_id).strip()

    if racer_key not in racers:
        return default_res

    racer = racers[racer_key]
    c_num = int(course_no)

    if c_num < 1 or c_num > 6:
        return default_res

    try:
        # コースごとの進入回数および各着数を数値型(int)へ安全にキャストして取得
        entry_count = _safe_int(racer.get(f"c{c_num}_entries"))
        c_1st = _safe_int(racer.get(f"c{c_num}_1st_places"))
        c_2nd = _safe_int(racer.get(f"c{c_num}_2nd_places"))
        c_3rd = _safe_int(racer.get(f"c{c_num}_3rd_places"))

        print(f"DEBUG [登番:{racer_key} コース:{c_num}]: 進入回数={entry_count}, 1着={c_1st}, 2着={c_2nd}, 3着={c_3rd}")

        if entry_count > 0:
            # 各着率および3連対率の算出（パーセンテージ表記）
            win_1st_rate = round((c_1st / entry_count) * 100, 2)
            win_2nd_rate = round((c_2nd / entry_count) * 100, 2)
            win_3rd_rate = round((c_3rd / entry_count) * 100, 2)
            win_3in_rate = round(((c_1st + c_2nd + c_3rd) / entry_count) * 100, 2)
        else:
            win_1st_rate = 0.0
            win_2nd_rate = 0.0
            win_3rd_rate = 0.0
            win_3in_rate = 0.0

        return {
            "entry_count": entry_count,
            "win_1st_rate": win_1st_rate,
            "win_2nd_rate": win_2nd_rate,
            "win_3rd_rate": win_3rd_rate,
            "win_3in_rate": win_3in_rate,
        }

    except Exception as e:
        print(f"コース成績計算エラー (登番: {racer_id}, コース: {course_no}): {e}")
        return default_res
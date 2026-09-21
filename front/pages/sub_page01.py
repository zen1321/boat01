import json
import os
import re
import sys
from pathlib import Path
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# プロジェクトルートを Python パスに追加
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# --- 保存先パスの設定 (data_json/ProgramSchedule.json) ---
DATA_JSON_DIR = project_root / "data_json"
SAVE_PATH = DATA_JSON_DIR / "ProgramSchedule.json"


def parse_kyotei_txt_fixed(text_content: str) -> dict:
    """
    競艇番組TXTをパースする関数
    構造: 開催 ➔ 日付 ➔ 会場 ➔ レース ➔ レース情報 + 選手6人
    """
    normalized_content = text_content.replace('\xa0', ' ').replace('\u00a0', ' ').replace(' ', ' ')
    lines = normalized_content.splitlines()
    
    event_date = ""
    venues = []
    
    current_venue = None
    current_race = None
    in_entries = False

    # 1. 日付の取得
    for line in lines:
        if "年" in line and "月" in line and "日" in line:
            m = re.search(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日', line)
            if m:
                y, m_str, d = m.groups()
                event_date = f"{y}-{int(m_str):02d}-{int(d):02d}"
                break

    for line in lines:
        line_raw = line.rstrip()
        if not line_raw:
            continue

        # 会場ブロック開始 (例: 24BBGN)
        if "BBGN" in line_raw:
            if current_venue:
                if current_race:
                    current_venue["races"].append(current_race)
                    current_race = None
                venues.append(current_venue)

            venue_code = line_raw[:2] if len(line_raw) >= 2 else ""
            current_venue = {
                "venue_code": venue_code,
                "venue_name": "",
                "title": "",
                "day_number": None,
                "races": []
            }
            current_race = None
            in_entries = False
            continue

        # 会場ブロック終了 (例: 24BEND)
        if "BEND" in line_raw:
            if current_race and current_venue:
                current_venue["races"].append(current_race)
                current_race = None
            if current_venue:
                venues.append(current_venue)
                current_venue = None
            in_entries = False
            continue

        if current_venue is not None:
            # 会場名取得
            if "ボートレース" in line_raw and not current_venue["venue_name"]:
                m = re.search(r'ボートレース([^\s]+)', line_raw)
                if m:
                    current_venue["venue_name"] = m.group(1).strip()

            # 開催日数
            if "第" in line_raw and "日" in line_raw and not current_venue["day_number"]:
                m = re.search(r'第\s*([０-９0-9]+)\s*日', line_raw)
                if m:
                    num_str = m.group(1).translate(str.maketrans("０１２３４５６７８９", "0123456789"))
                    current_venue["day_number"] = int(num_str)

            # タイトル名
            if ("杯" in line_raw or "カップ" in line_raw or "記念" in line_raw or "賞" in line_raw or "競走" in line_raw) and "＊＊＊" not in line_raw:
                if not current_venue["title"] and not line_raw.strip().startswith("ボートレース"):
                    current_venue["title"] = line_raw.strip()

            # レースヘッダー判定
            if ("Ｒ" in line_raw or "R" in line_raw) and "電話投票締切予定" in line_raw:
                if current_race:
                    current_venue["races"].append(current_race)

                r_match = re.search(r'([０-９0-9]{1,2})\s*[ＲR]', line_raw)
                race_num = 0
                if r_match:
                    r_str = r_match.group(1).translate(str.maketrans("０１２３４５６７８９", "0123456789"))
                    race_num = int(r_str)

                title_match = re.search(r'[ＲR]\s+([^\s]+)', line_raw)
                race_title = title_match.group(1) if title_match else "一般"

                time_match = re.search(r'(\d{1,2}:\d{2}|[０-９]{1,2}：[０-９]{2})', line_raw)
                closing_time = ""
                if time_match:
                    closing_time = time_match.group(1).translate(str.maketrans("０１２３４５６７８９：", "0123456789:"))

                current_race = {
                    "race_info": {
                        "race_number": race_num,
                        "title": race_title,
                        "distance_m": 1800,
                        "telephone_closing_time": closing_time
                    },
                    "entries": []
                }
                in_entries = False
                continue

            # 出走表ヘッダーのスキップ
            if "艇 選手 選手" in line_raw or "登番" in line_raw:
                in_entries = True
                continue

            if line_raw.startswith("----------------") or line_raw.startswith("==="):
                continue

            # 選手データ行の判定と抽出 (1〜6号艇)
            if current_race and in_entries:
                stripped_line = line_raw.strip()
                first_char = stripped_line[0] if stripped_line else ""
                if first_char in ["1", "2", "3", "4", "5", "6"]:
                    
                    pattern = (
                        r'^\s*([1-6])\s+'                             # 1:艇番
                        r'(\d{4})\s*'                                 # 2:登番
                        r'([^\d]+?)\s*'                               # 3:氏名
                        r'(\d{2})\s*'                                 # 4:年齢
                        r'([^\d]+?)\s*'                               # 5:支部
                        r'(\d{2})\s*'                                 # 6:体重
                        r'([A-B][1-2])\s+'                            # 7:級別
                        r'([\d\.]+)\s+([\d\.]+)\s+'                   # 8:全国勝率, 9:全国2率
                        r'([\d\.]+)\s+([\d\.]+)\s+'                   # 10:当地勝率, 11:当地2率
                        r'(\d+)\s+([\d\.]+)\s+'                       # 12:モーターNO, 13:モーター2率
                        r'(\d+)\s+([\d\.]+)\s*'                       # 14:ボートNO, 15:ボート2率
                        r'(.{12,18})?'                                # 16:今節成績および早見（末尾可変長）
                    )
                    
                    m = re.match(pattern, line_raw)
                    if m:
                        (
                            boat_no, reg_no, name, age, branch, weight, rank,
                            n_win, n_2nd, l_win, l_2nd,
                            m_no, m_2nd, b_no, b_2nd,
                            rest_str
                        ) = m.groups()

                        rest_str = rest_str or ""
                        early_race = None
                        m_early = re.search(r'(\d{1,2})\s*$', rest_str)
                        if m_early:
                            early_race = int(m_early.group(1))
                            results_part = rest_str[:m_early.start()].strip()
                        else:
                            results_part = rest_str.strip()

                        recent_results = [results_part[i:i+2].strip() for i in range(0, len(results_part), 2) if results_part[i:i+2].strip()]

                        entry = {
                            "boat_number": int(boat_no),
                            "registration_number": int(reg_no),
                            "name": name.strip().replace(" ", ""),
                            "age": int(age),
                            "branch": branch.strip().replace(" ", ""),
                            "weight_kg": int(weight),
                            "rank": rank,
                            "national_win_rate": float(n_win),
                            "national_2nd_rate": float(n_2nd),
                            "local_win_rate": float(l_win),
                            "local_2nd_rate": float(l_2nd),
                            "motor_no": int(m_no),
                            "motor_2nd_rate": float(m_2nd),
                            "boat_no": int(b_no),
                            "boat_2nd_rate": float(b_2nd),
                            "recent_results": recent_results,
                            "early_race_number": early_race
                        }
                        current_race["entries"].append(entry)

    if current_venue:
        if current_race:
            current_venue["races"].append(current_race)
        venues.append(current_venue)

    return {
        "event": {
            "date": event_date,
            "venues": venues
        }
    }


# --- UIコンポーネント ---

# メイン画面へ戻るボタン
col_nav, _ = st.columns([2, 8])
with col_nav:
    if st.button("⬅️ メイン予測画面へ戻る", use_container_width=True):
        st.switch_page("pages/main_page.py")

st.markdown("---")
st.title("📄 競艇番組表（公式TXT）➔ JSON 変換 & 出走表確認")

# 1. TXTファイルのアップロード
uploaded_file = st.file_uploader("競艇番組テキスト（例: B260919.TXT）をアップロード", type=["txt", "TXT"])

parsed_data = None

if uploaded_file is not None:
    raw_bytes = uploaded_file.getvalue()
    
    try:
        content = raw_bytes.decode("cp932")
    except UnicodeDecodeError:
        content = raw_bytes.decode("utf-8", errors="replace")

    parsed_data = parse_kyotei_txt_fixed(content)

    os.makedirs(DATA_JSON_DIR, exist_ok=True)
    
    try:
        if SAVE_PATH.exists():
            os.remove(SAVE_PATH)

        with open(SAVE_PATH, "w", encoding="utf-8") as f:
            json.dump(parsed_data, f, ensure_ascii=False, indent=2)
        st.success(f"📁 最新のJSONファイルを保存・更新しました: `{SAVE_PATH}`")
    except Exception as e:
        st.error(f"❌ 保存中にエラーが発生しました: {e}")

# 2. 保存済みの JSON データが存在すれば読み込み
elif SAVE_PATH.exists():
    try:
        with open(SAVE_PATH, "r", encoding="utf-8") as f:
            parsed_data = json.load(f)
        st.info("ℹ️ 既存の `ProgramSchedule.json` データを読み込みました。")
    except Exception as e:
        st.error(f"❌ 既存JSONの読み込み中にエラーが発生しました: {e}")

# 3. レースデータ表示＆コピペ欄の出力
if parsed_data and "event" in parsed_data and "venues" in parsed_data["event"]:
    st.markdown("---")
    st.subheader("📊 レース情報・出走表の確認")

    event_date = parsed_data["event"].get("date", "不明")
    venues = parsed_data["event"].get("venues", [])

    if not venues:
        st.warning("表示できる競艇場データがありません。")
    else:
        st.caption(f"開催日: **{event_date}**")

        col_v, col_r = st.columns(2)

        # 競艇場選択
        venue_options = {f"{v.get('venue_name', '不明')} ({v.get('venue_code', '')})": v for v in venues}
        selected_venue_name = col_v.selectbox("競艇場を選択", list(venue_options.keys()))
        selected_venue = venue_options[selected_venue_name]

        # レース選択
        races = selected_venue.get("races", [])
        if not races:
            st.warning("この競艇場のレースデータはありません。")
        else:
            race_options = {f"第 {r['race_info']['race_number']} レース ({r['race_info']['title']})": r for r in races}
            selected_race_label = col_r.selectbox("レースを選択", list(race_options.keys()))
            selected_race = race_options[selected_race_label]

            # レースタイトルの表示
            race_info = selected_race["race_info"]
            st.markdown(f"### {selected_venue.get('venue_name')} 第{race_info['race_number']}R ： {race_info['title']}")

            # 出走艇一覧の表示
            entries = selected_race.get("entries", [])
            if entries:
                display_list = []

                reg_nos = []
                motor_2nds = []
                national_wins = []
                local_wins = []

                for entry in entries:
                    display_list.append({
                        "艇番": entry["boat_number"],
                        "登番": entry["registration_number"],
                        "選手名": entry["name"],
                        "級別": entry["rank"],
                        "年齢": entry["age"],
                        "支部": entry["branch"],
                        "全国勝率": entry["national_win_rate"],
                        "全国2連率": entry["national_2nd_rate"],
                        "当地勝率": entry["local_win_rate"],
                        "当地2連率": entry["local_2nd_rate"],
                        "モーターNO": entry["motor_no"],
                        "モーター2連率": entry["motor_2nd_rate"],
                        "ボートNO": entry["boat_no"],
                        "ボート2連率": entry["boat_2nd_rate"],
                        "今節成績": " ".join(entry["recent_results"])
                    })

                    reg_nos.append(str(entry["registration_number"]))
                    motor_2nds.append(str(entry["motor_2nd_rate"]))
                    national_wins.append(str(entry["national_win_rate"]))
                    local_wins.append(str(entry["local_win_rate"]))

                df = pd.DataFrame(display_list)
                st.dataframe(df, use_container_width=True, hide_index=True)

                # コピペ欄（メイン予測画面に貼り付け可能なフォーマット）
                # st.markdown("#### 📋 データコピペ欄")
                # st.caption("1行目: 登番（項目名なし） / 2行目: 2連対率 / 3行目: 全国 / 4行目: 当地（タブ区切り）")

                # copy_rows = [
                #     "\t".join(reg_nos),
                #     "2連対率\t" + "\t".join(motor_2nds),
                #     "全国\t" + "\t".join(national_wins),
                #     "当地\t" + "\t".join(local_wins)
                # ]
                # formatted_copy_text = "\n".join(copy_rows)

                # st.text_area("以下をコピーしてご利用ください", value=formatted_copy_text, height=140)

                st.markdown("#### 📋 データコピペ欄")
                st.caption("1行目: 登番（項目名なし） / 2行目: 2連対率 / 3行目: 全国 / 4行目: 当地（タブ区切り）")

                copy_rows = [
                    "\t".join(reg_nos),
                    "2連対率\t" + "\t".join(motor_2nds),
                    "全国\t" + "\t".join(national_wins),
                    "当地\t" + "\t".join(local_wins)
                ]
                formatted_copy_text = "\n".join(copy_rows)

                st.text_area("以下をコピーしてご利用ください", value=formatted_copy_text, height=140, key="copy_text_area")

                # --- クリップボードコピーボタン（JavaScript連携） ---
                # JSON文字列として安全にJavaScriptへ埋め込み
                js_copy_text = json.dumps(formatted_copy_text)

                copy_button_html = f"""
                <div style="margin-top: 5px;">
                    <button id="copyBtn" style="
                        background-color: #FF4B4B;
                        color: white;
                        border: none;
                        padding: 8px 16px;
                        font-size: 14px;
                        border-radius: 8px;
                        cursor: pointer;
                        width: 100%;
                        font-weight: bold;
                        transition: background-color 0.3s;
                    ">
                        📋 テキストをクリップボードにコピー
                    </button>
                </div>

                <script>
                    document.getElementById('copyBtn').addEventListener('click', function() {{
                        const textToCopy = {js_copy_text};
                        navigator.clipboard.writeText(textToCopy).then(function() {{
                            const btn = document.getElementById('copyBtn');
                            btn.innerText = '✅ コピー完了！';
                            btn.style.backgroundColor = '#2e7d32';
                            setTimeout(function() {{
                                btn.innerText = '📋 テキストをクリップボードにコピー';
                                btn.style.backgroundColor = '#FF4B4B';
                            }}, 2000);
                        }}).catch(function(err) {{
                            alert('コピーに失敗しました: ' + err);
                        }});
                    }});
                </script>
                """

                # HTMLコンポーネントを埋め込み
                components.html(copy_button_html, height=50)
                
            else:
                st.info("このレースの出走選手データがありません。")
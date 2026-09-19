import io
import os
import sys
from pathlib import Path

# プロジェクトルート（boat_prediction）をPythonパスに追加
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

import pandas as pd
import streamlit as st
from data.racer_course_repository import get_racer_course_stat, get_racer_basic_info
from data.venue_repository import get_all_venues
from logic.betting_decision import generate_final_betting_recommendation
from logic.main_logic import calculate_full_race_scores

st.set_page_config(
    page_title="ボートレース総合予測", page_icon="🚤", layout="wide"
)

st.title("🚤 ボートレース総合スコア予測")
st.caption(
    "Webサイトからデータを貼り付けて表に反映し、スコアと順位・買い目を算出します。"
)

# ------------------------------------------------------------------------------
# 1. 画面上部設定: 競艇場 & 気象条件
# ------------------------------------------------------------------------------
st.subheader("⚙️ レース基本設定 & 気象条件")

col_top1, col_top2, col_top3 = st.columns(3)

with col_top1:
    st.markdown("##### 📍 競艇場選択")
    venue_list = get_all_venues()
    default_index = venue_list.index("江戸川") if "江戸川" in venue_list else 0
    selected_venue = st.selectbox("競艇場", venue_list, index=default_index)

with col_top2:
    st.markdown("##### 🌬️ 風条件")
    wind_direction = st.selectbox("風向", ["無風", "追い風", "向かい風"], index=0)

    default_wind_speed = 0.0 if wind_direction == "無風" else 5.0

    wind_speed = st.number_input(
        "風速 (m)",
        min_value=0.0,
        max_value=15.0,
        value=default_wind_speed,
        step=1.0,
        key=f"wind_speed_input_{wind_direction}",
    )

with col_top3:
    st.markdown("##### 🌊 潮条件")
    tide_state = st.selectbox(
        "潮の状態", ["なし", "満潮", "干潮", "中潮", "小潮"], index=0
    )

weather_info = {
    "wind_direction": wind_direction,
    "wind_speed": wind_speed,
    "tide_state": tide_state,
}

st.markdown("---")

# ------------------------------------------------------------------------------
# 2. 縦12項目 × 6艇 のデータ一括コピペ & 表編集エリア
# ------------------------------------------------------------------------------
index_items = [
    "登録番号",  # 0行目
    "名前",      # 1行目
    "ランク",    # 2行目
    "2連対率",  # 3行目
    "今期",      # 4行目 (今期ST)
    "全国",      # 5行目
    "当地",      # 6行目
    "展示",      # 7行目
    "周回",      # 8行目
    "周り足",    # 9行目
    "直線",      # 10行目
    "ST",        # 11行目
]
columns = [f"{i+1}号艇" for i in range(6)]

if "grid_df" not in st.session_state:
    st.session_state.grid_df = pd.DataFrame(
        "", index=index_items, columns=columns, dtype=object
    )

if "input_text" not in st.session_state:
    st.session_state.input_text = ""


def clear_text():
    st.session_state.input_text = ""


def reset_grid():
    st.session_state.grid_df = pd.DataFrame(
        "", index=index_items, columns=columns, dtype=object
    )


st.subheader("📋 1. Webサイトからのデータ貼り付け")

raw_text = st.text_area(
    label="コピペ用エリア",
    key="input_text",
    height=120,
    placeholder="例:\nST\t.18\t.01\t.15\t.22\t.16\t.18",
    label_visibility="collapsed",
)

col_btn1, col_btn2, col_btn3, _ = st.columns([2, 2, 2, 4])

with col_btn1:
    if st.button("📥 表に反映する", type="primary", use_container_width=True):
        if raw_text.strip():
            try:
                import re

                lines = [line.strip() for line in raw_text.strip().splitlines() if line.strip()]

                # 入力行ごとの解析
                for r, line in enumerate(lines):
                    row_values = [v.strip() for v in re.split(r"\s+", line) if v.strip()]
                    if not row_values:
                        continue

                    first_val = row_values[0]

                    # --- 行位置（target_row_idx）の特定ロジック修正 ---
                    if first_val in index_items:
                        # 先頭文字が項目名（例：「2連対率」「全国」）に一致する場合
                        target_row_idx = index_items.index(first_val)
                        clean_values = row_values[1:]  # 項目名を除外
                    else:
                        # 先頭文字が項目名でない場合（例：数字のみの登録番号行）
                        if r == 0:
                            target_row_idx = index_items.index("登録番号")
                        else:
                            # 万が一項目名のないデータ行が続いた場合のフォールバック
                            target_row_idx = min(r, len(index_items) - 1)
                        clean_values = row_values

                    # --- セッション状態の表（grid_df）へ格納 ---
                    if target_row_idx < len(index_items):
                        cols_to_copy = min(len(clean_values), 6)
                        for c in range(cols_to_copy):
                            val_str = str(clean_values[c]).strip()

                            # データ整形（%, F., . 補正）
                            clean_val = (
                                val_str.replace("%", "")
                                .replace("％", "")
                                .replace("F.", "0.")
                                .replace("f.", "0.")
                                .replace("L.", "0.")
                            )
                            if clean_val.startswith("."):
                                clean_val = "0" + clean_val

                            st.session_state.grid_df.iloc[target_row_idx, c] = clean_val

                # --- 登録番号をキーにして「名前」「ランク」「今期ST」をJSONから自動補完 ---
                toban_row_idx = index_items.index("登録番号")
                name_row_idx = index_items.index("名前")
                rank_row_idx = index_items.index("ランク")
                st_row_idx = index_items.index("今期")

                for c in range(6):
                    toban_val = str(st.session_state.grid_df.iloc[toban_row_idx, c]).strip()
                    if toban_val:
                        info = get_racer_basic_info(toban_val)
                        if info["name"]:
                            st.session_state.grid_df.iloc[name_row_idx, c] = info["name"]
                        if info["rank"]:
                            st.session_state.grid_df.iloc[rank_row_idx, c] = info["rank"]
                        if info["st_avg"]:
                            st.session_state.grid_df.iloc[st_row_idx, c] = info["st_avg"]

                st.success("データを反映し、登番から選手情報（名前・ランク・今期ST）を補完しました！")
                st.rerun()
            except Exception as e:
                st.error(f"データの解析に失敗しました: {e}")
        else:
            st.warning("テキストエリアにデータが入力されていません。")

with col_btn2:
    st.button("🧹 エリアをクリア", use_container_width=True, on_click=clear_text)

with col_btn3:
    st.button("🗑️ 表をリセット", use_container_width=True, on_click=reset_grid)

st.subheader("2. データ確認・微調整")

edited_df = st.data_editor(
    st.session_state.grid_df,
    num_rows="fixed",
    use_container_width=True,
    key="boat_editor",
)
st.session_state.grid_df = edited_df

# ------------------------------------------------------------------------------
# 4. 進入コース設定
# ------------------------------------------------------------------------------
st.markdown("---")
st.markdown("#### 🧭 進入コース設定")
st.caption("前付け等のコース変動がある場合は各艇の進入コースを変更してください（初期値は枠番通り）。")

course_cols = st.columns(6)
updated_courses = []

for i, col in enumerate(course_cols):
    pit_no = i + 1
    with col:
        chosen_course = st.selectbox(
            f"{pit_no}号艇 コース",
            options=[1, 2, 3, 4, 5, 6],
            index=pit_no - 1,
            key=f"entry_course_pit_{pit_no}",
        )
        updated_courses.append(chosen_course)

# ------------------------------------------------------------------------------
# 3. 入力データからの抽出＆データ整形
# ------------------------------------------------------------------------------
def safe_float(val, default=0.0):
    try:
        return float(val) if str(val).strip() != "" else default
    except (ValueError, TypeError):
        return default

racers_data = []
exhibition_data = []

for pit_no in range(1, 7):
    col_name = f"{pit_no}号艇"
    col_data = edited_df[col_name]

    r_id = str(col_data.get("登録番号", "")).strip() or f"400{pit_no}"
    r_name = str(col_data.get("名前", "")).strip() or f"選手{pit_no}"
    r_rank = str(col_data.get("ランク", "")).strip() or "B1"

    chosen_course = updated_courses[pit_no - 1]
    
    ex_col_name = f"{chosen_course}号艇"
    ex_col_data = edited_df[ex_col_name]

    racers_data.append(
        {
            "pit_no": pit_no,
            "entry_course": chosen_course,
            "racer_id": r_id,
            "racer_name": r_name,
            "rank": r_rank,
            "motor_rate": safe_float(col_data.get("2連対率"), 30.0),
            "avg_st": safe_float(col_data.get("今期"), 0.15),
            "national_win_rate": safe_float(col_data.get("全国"), 5.0),
            "local_win_rate": safe_float(col_data.get("当地"), 5.0),
        }
    )

    exhibition_data.append(
        {
            "pit_no": pit_no,
            "entry_course": chosen_course,
            "exhibition_time": safe_float(ex_col_data.get("展示"), 6.70),
            "lap_time": safe_float(ex_col_data.get("周回"), 37.0),
            "turn_foot": safe_float(ex_col_data.get("周り足"), 1.5),
            "straight_line": safe_float(ex_col_data.get("直線"), 1.5),
            "exhibition_st": safe_float(ex_col_data.get("ST"), 0.15),
        }
    )

# ------------------------------------------------------------------------------
# 5. 予測実行 & 結果表示
# ------------------------------------------------------------------------------
st.markdown("---")
if st.button("🚀 レーススコア予測を実行", type="primary", use_container_width=True):
    try:
        results = calculate_full_race_scores(
            venue_name=selected_venue,
            race_racers_data=racers_data,
            race_exhibition_data=exhibition_data,
            weather_info=weather_info,
        )

        st.success(f"【{selected_venue}】予測集計が完了しました！")

        st.subheader("🎫 展開予想 ＆ 3連単推奨買い目")

        bet_recommendation = generate_final_betting_recommendation(
            racer_scores=results,
            race_racers_data=racers_data,
            race_exhibition_data=exhibition_data,
        )

        col_dev1, col_dev2, col_dev3 = st.columns(3)
        with col_dev1:
            st.metric(label="主展開予想", value=bet_recommendation["primary_development"])
        with col_dev2:
            st.metric(label="展開ランク", value=f"{bet_recommendation['development_rank']} ランク")
        with col_dev3:
            st.metric(label="総合信頼度", value=bet_recommendation["confidence"])

        st.info(f"💡 **買い目方針:** {bet_recommendation['betting_policy']}")

        col_bet1, col_bet2 = st.columns([1, 1])

        with col_bet1:
            st.markdown("##### 🎯 推奨買い目一覧")
            bets_list = bet_recommendation.get("recommended_bets", [])
            if bets_list:
                df_bets = pd.DataFrame(bets_list)
                df_bets.columns = ["買い目 (3連単)", "推奨配分 (比率 %)"]
                st.dataframe(df_bets, use_container_width=True, hide_index=True)
            else:
                st.write("買い目データなし")

        with col_bet2:
            with st.expander("🔍 展開ロジックの評価詳細を表示"):
                st.json(bet_recommendation.get("development_details", {}))

        st.markdown("---")

        st.subheader("📊 総合評価一覧")
        table_rows = []
        for r in results:
            sb = r["score_breakdown"]
            rb = sb["racer_breakdown"]
            table_rows.append(
                {
                    "予測順位": f"{r['predicted_rank']}位",
                    "艇番": f"{r['pit_no']}号艇",
                    "進入": f"{r['entry_course']}コース",
                    "総合スコア": r["total_score"],
                    "選手基本": sb["racer_base_subtotal"],
                    "階級": rb.get("rank_score", 0),
                    "勝率": rb.get("win_rate_score", 0),
                    "モーター": rb.get("motor_score", 0),
                    "平均ST": rb.get("avg_st_score", 0),
                    "コース": rb.get("course_score", 0),
                    "展示": sb["exhibition_score"],
                    "展示ST": sb["exhibition_st_score"],
                    "風": sb["wind_score"],
                    "潮": sb["tide_score"],
                }
            )

        df_results = pd.DataFrame(table_rows)
        st.dataframe(df_results, use_container_width=True, hide_index=True)

        st.subheader("⚙️ モーター・展示足比較（上位3位ハイライト）")

        detail_rows = []
        for r, ex in zip(racers_data, exhibition_data):
            detail_rows.append(
                {
                    "艇番号": f"{r['pit_no']}号艇",
                    "モータ2連対率": float(r["motor_rate"]),
                    "展示タイム": float(ex["exhibition_time"]),
                    "周回タイム": float(ex["lap_time"]),
                    "回り足": float(ex["turn_foot"]),
                    "直線": float(ex["straight_line"]),
                }
            )

        df_detail = pd.DataFrame(detail_rows)

        def highlight_top3(df: pd.DataFrame) -> pd.DataFrame:
            styles = pd.DataFrame("", index=df.index, columns=df.columns)

            color_1st = "background-color: #ffcdd2; color: #b71c1c; font-weight: bold;"
            color_2nd = "background-color: #fff9c4; color: #826a00; font-weight: bold;"
            color_3rd = "background-color: #c8e6c9; color: #1b5e20; font-weight: bold;"

            ascending_rules = {
                "モータ2連対率": False,
                "展示タイム": True,
                "周回タイム": True,
                "回り足": True,
                "直線": True,
            }

            for col, is_asc in ascending_rules.items():
                if col in df.columns:
                    unique_vals = sorted(df[col].dropna().unique(), reverse=not is_asc)
                    for idx, val in df[col].items():
                        if len(unique_vals) > 0 and val == unique_vals[0]:
                            styles.loc[idx, col] = color_1st
                        elif len(unique_vals) > 1 and val == unique_vals[1]:
                            styles.loc[idx, col] = color_2nd
                        elif len(unique_vals) > 2 and val == unique_vals[2]:
                            styles.loc[idx, col] = color_3rd

            return styles

        styled_df = (
            df_detail.style
            .format({
                "モータ2連対率": "{:.1f}",
                "展示タイム": "{:.2f}",
                "周回タイム": "{:.2f}",
                "回り足": "{:.2f}",
                "直線": "{:.2f}",
            })
            .apply(highlight_top3, axis=None)
        )

        st.dataframe(styled_df, use_container_width=True, hide_index=True)

        st.subheader("🎯 進入コース別実績（勝率一覧）")

        course_stats_rows = []
        for r in racers_data:
            stats = get_racer_course_stat(
                racer_id=r["racer_id"],
                course_no=r["entry_course"]
            )
            course_stats_rows.append(
                {
                    "艇番": f"{r['pit_no']}号艇",
                    "1着率": float(stats.get("win_1st_rate", 0.0)),
                    "2着率": float(stats.get("win_2nd_rate", 0.0)),
                    "3着率": float(stats.get("win_3rd_rate", 0.0)),
                    "3連対率": float(stats.get("win_3in_rate", 0.0)),
                }
            )

        df_course_stats = pd.DataFrame(course_stats_rows)

        def highlight_green_gradient(df: pd.DataFrame) -> pd.DataFrame:
            styles = pd.DataFrame("", index=df.index, columns=df.columns)

            green_colors = [
                "background-color: #2e7d32; color: #ffffff; font-weight: bold;",
                "background-color: #4caf50; color: #ffffff; font-weight: bold;",
                "background-color: #81c784; color: #000000; font-weight: bold;",
                "background-color: #a5d6a7; color: #000000;",
                "background-color: #c8e6c9; color: #000000;",
                "background-color: #e8f5e9; color: #000000;",
            ]

            target_cols = ["1着率", "2着率", "3着率", "3連対率"]
            for col in target_cols:
                if col in df.columns:
                    unique_vals = sorted(df[col].dropna().unique(), reverse=True)
                    for idx, val in df[col].items():
                        if val in unique_vals:
                            rank_idx = unique_vals.index(val)
                            if rank_idx < len(green_colors):
                                styles.loc[idx, col] = green_colors[rank_idx]

            return styles

        styled_course_df = (
            df_course_stats.style
            .format({
                "1着率": "{:.1f}%",
                "2着率": "{:.1f}%",
                "3着率": "{:.1f}%",
                "3連対率": "{:.1f}%",
            })
            .apply(highlight_green_gradient, axis=None)
        )

        st.dataframe(styled_course_df, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"計算エラーが発生しました: {e}")
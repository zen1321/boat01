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
from data.racer_course_repository import get_racer_course_stat
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

    # 風向に応じた風速の初期値（デフォルト値）の設定
    default_wind_speed = 0.0 if wind_direction == "無風" else 5.0

    # 1.0 刻み（step=1.0）に変更し、風向選択に連動した key を設定
    wind_speed = st.number_input(
        "風速 (m)",
        min_value=0.0,
        max_value=15.0,
        value=default_wind_speed,
        step=1.0,  # ← 1.0刻みに変更
        key=f"wind_speed_input_{wind_direction}",  # 風向が変わった際に初期値を再適用するためのキー
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
# 2. 縦13項目 × 6艇 のデータ一括コピペ & 表編集エリア
# ------------------------------------------------------------------------------
index_items = [
    "艇番号",  # 0行目 (項目名なしで読み込み)
    "登録番号",  # 1行目 (項目名なしで読み込み)
    "名前",  # 2行目 (項目名なしで読み込み)
    "ランク",  # 3行目 (項目名なしで読み込み)
    "2連対率",  # 4行目 (ここから項目名あり/なし両対応)
    "今期",  # 5行目
    "全国",  # 6行目
    "当地",  # 7行目
    "展示",  # 8行目
    "周回",  # 9行目
    "周り足",  # 10行目
    "直線",  # 11行目
    "ST",  # 12行目
]
columns = [f"{i+1}号艇" for i in range(6)]
# セッション状態の保持
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
# --- 「📥 表に反映する」ボタンの解析処理 ---
    if st.button("📥 表に反映する", type="primary", use_container_width=True):
        if raw_text.strip():
            try:
                import re

                # 1. 改行で分割し、空行を除外
                lines = [line.strip() for line in raw_text.strip().splitlines() if line.strip()]

                for r, line in enumerate(lines):
                    # タブまたはスペースで要素を分割
                    row_values = [v.strip() for v in re.split(r"\s+", line) if v.strip()]

                    if not row_values:
                        continue

                    first_val = row_values[0]

                    # --- 行の位置（target_row_idx）の特定 ---
                    # A. 0～3行目（艇番号、登録番号、名前、ランク）は上からの行番号で割り当て
                    if r < 4:
                        target_row_idx = r
                        # 項目名が含まれていれば除外、値だけならそのまま
                        clean_values = row_values[1:] if first_val in index_items else row_values

                    # B. 4行目以降（2連対率～ST）は項目名判定（無ければ順に割り当て）
                    else:
                        if first_val in index_items:
                            target_row_idx = index_items.index(first_val)
                            clean_values = row_values[1:]  # 項目名を除外
                        else:
                            start_default = index_items.index("2連対率")
                            target_row_idx = start_default + (r - 4)
                            clean_values = row_values

                    # --- セッション状態の表（grid_df）へ格納 ---
                    if target_row_idx < len(index_items):
                        cols_to_copy = min(len(clean_values), 6)
                        for c in range(cols_to_copy):
                            val_str = str(clean_values[c]).strip()

                            # データ成形（% 除去 & .10 → 0.10 補正）
                            clean_val = val_str.replace("%", "").replace("％", "")
                            if clean_val.startswith("."):
                                clean_val = "0" + clean_val

                            st.session_state.grid_df.iloc[target_row_idx, c] = clean_val

                st.success("艇番号を含む13項目のデータをズレなく反映しました！")
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
# 4. 進入コース設定（データ抽出の前に設定を取得）
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
# 3. 入力データからの抽出＆データ整形（進入コースに応じた自動紐付け）
# ------------------------------------------------------------------------------
def safe_float(val, default=0.0):
    try:
        return float(val) if str(val).strip() != "" else default
    except (ValueError, TypeError):
        return default
racers_data = []
exhibition_data = []

for pit_no in range(1, 7):
    # 枠番順（1〜6号艇の列）から前半データを取得
    col_name = f"{pit_no}号艇"
    col_data = edited_df[col_name]

    r_id = str(col_data.get("登録番号", "")).strip() or f"400{pit_no}"
    r_name = str(col_data.get("名前", "")).strip() or f"選手{pit_no}"
    r_rank = str(col_data.get("ランク", "")).strip() or "B1"

    # 対象艇の進入コースを取得（例：2号艇が3コースに入った場合は chosen_course = 3）
    chosen_course = updated_courses[pit_no - 1]
    
    # 「展示〜ST」は進入順に並んでいるため、進入コースの列（chosen_course号艇の列）から取得
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

        # 展開予想 ＆ 3連単推奨買い目
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

        # 総合評価一覧テーブル表示
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

        # モーター・展示足ハイライト表示
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

        # 進入コース別実績
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
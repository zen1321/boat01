import io
import os
import sys
from pathlib import Path

# プロジェクトルートを Python パスに追加
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pandas as pd
import streamlit as st
from data.racer_course_repository import get_racer_basic_info, get_racer_course_stat
from data.venue_repository import get_all_venues
from logic.betting_decision import generate_final_betting_recommendation
from logic.main_logic import calculate_full_race_scores

# --- タイトル ＆ 新画面への遷移ボタン ---
st.title("🚤 ボートレース総合スコア予測")

col_head1, col_head2 = st.columns([7, 3])
with col_head1:
    st.caption("Webサイトからデータを貼り付けて表に反映し、スコアと順位・買い目を算出します。")
with col_head2:
    if st.button("⚙️ サブ機能01画面へ移動", type="secondary", use_container_width=True):
        st.switch_page("pages/sub_page01.py")

st.markdown("---")

# ------------------------------------------------------------------------------
# 1. 画面上部設定: 競艇場 & 気象条件
# ------------------------------------------------------------------------------
st.subheader("1. 開催情報・気象条件")

venues_data = get_all_venues()
venue_names = list(venues_data.keys())

col1, col2, col3, col4, col5 = st.columns([2, 1.5, 1.5, 2, 2])

with col1:
    selected_venue = st.selectbox("競艇場", venue_names, index=0)

with col2:
    wind_direction = st.selectbox(
        "風向", ["追い風", "向かい風", "左横風", "右横風", "無風"], index=0
    )

with col3:
    wind_speed = st.number_input(
        "風速 (m)", min_value=0.0, max_value=15.0, value=2.0, step=0.5
    )

with col4:
    tide_condition = st.selectbox(
        "潮目", ["中潮", "大潮", "小潮", "長潮", "若潮"], index=0
    )

with col5:
    wave_height = st.number_input(
        "波高 (cm)", min_value=0.0, max_value=30.0, value=2.0, step=1.0
    )

st.markdown("---")

# ------------------------------------------------------------------------------
# 2. 直前データコピペ & エディタ反映エリア
# ------------------------------------------------------------------------------
st.subheader("2. 直前データ・コース進入設定")

# 初期データフレームの構築 (6艇 x 11項目)
index_items = [
    "登録番号",
    "名前",
    "ランク",
    "今期",
    "2連対率",
    "全国",
    "当地",
    "展示",
    "周回",
    "ST",
    "チルト",
]
default_cols = [f"{i}号艇" for i in range(1, 7)]

if "grid_df" not in st.session_state:
    st.session_state.grid_df = pd.DataFrame(
        "", index=index_items, columns=default_cols
    )

col_text, col_ctrl = st.columns([6, 4])

with col_text:
    pasted_text = st.text_area(
        "コピペ欄 (タブ区切りテキスト)",
        height=140,
        placeholder="例:\n4001\t4002\t4003\t4004\t4005\t4006\n2連対率\t35.2\t40.1\t28.5\t50.0\t31.0\t42.3",
    )

with col_ctrl:
    target_row_label = st.selectbox("反映先項目", index_items, index=0)
    col_b1, col_b2 = st.columns(2)

    with col_b1:
        if st.button("📥 表に反映する", use_container_width=True):
            if pasted_text.strip():
                lines = [
                    line.strip()
                    for line in pasted_text.strip().split("\n")
                    if line.strip()
                ]

                # 選択された項目インデックスを取得
                target_row_idx = index_items.index(target_row_label)

                for line in lines:
                    if target_row_idx >= len(index_items):
                        break

                    # タブまたは連続スペースで分割
                    values = [
                        v.strip()
                        for v in line.replace("\t", " ").split(" ")
                        if v.strip()
                    ]

                    # 項目名が先頭に含まれている場合は除去
                    clean_values = []
                    for val in values:
                        if val in index_items or val in ["2連対率", "全国", "当地"]:
                            continue
                        clean_values.append(val)

                    if clean_values:
                        cols_to_copy = min(len(clean_values), 6)
                        for c in range(cols_to_copy):
                            val_str = str(clean_values[c]).strip()

                            # パーセント記号の削除
                            clean_val = val_str.replace("%", "").replace("％", "")

                            # --- 【修正箇所①】 ST行のフライング(F)判定処理 ---
                            if index_items[target_row_idx] == "ST":
                                if clean_val.startswith(("F.", "f.")):
                                    clean_val = "-" + clean_val[2:]
                                elif clean_val.startswith(("F", "f")) and len(clean_val) > 1:
                                    clean_val = "-" + clean_val[1:]
                                elif clean_val.startswith(("L.", "l.")):
                                    clean_val = "0.0"  # 出遅れ(L)は欠損/0扱い
                            else:
                                clean_val = clean_val.replace("F.", "0.").replace("f.", "0.").replace("L.", "0.")

                            if clean_val.startswith("."):
                                clean_val = "0" + clean_val
                            elif clean_val.startswith("-."):
                                clean_val = "-0" + clean_val[2:]

                            st.session_state.grid_df.iloc[target_row_idx, c] = clean_val

                        target_row_idx += 1

                st.success("指定項目から順に反映しました！")
            else:
                st.warning("テキストが入力されていません。")

    with col_b2:
        if st.button("🗑️ クリア", use_container_width=True):
            st.session_state.grid_df = pd.DataFrame(
                "", index=index_items, columns=default_cols
            )
            st.rerun()

# 編集可能なデータエディタの表示
edited_df = st.data_editor(
    st.session_state.grid_df, use_container_width=True, height=420
)

st.markdown("#### 進入コース設定")
c_cols = st.columns(6)
updated_courses = []
for i in range(1, 7):
    with c_cols[i - 1]:
        c_val = st.selectbox(
            f"{i}号艇 進入",
            options=[1, 2, 3, 4, 5, 6],
            index=i - 1,
            key=f"course_select_{i}",
        )
        updated_courses.append(c_val)

st.markdown("---")


# 安全な float 変換関数
def safe_float(val, default=0.0):
    try:
        if val is None or str(val).strip() == "":
            return default
        return float(val)
    except ValueError:
        return default


# ------------------------------------------------------------------------------
# 3. 入力データからの抽出＆データ整形
# ------------------------------------------------------------------------------
racers_data = []
exhibition_data = []

for pit_no in range(1, 7):
    col_name = f"{pit_no}号艇"
    col_data = edited_df[col_name]

    r_id = str(col_data.get("登録番号", "")).strip() or f"400{pit_no}"
    r_name = str(col_data.get("名前", "")).strip() or f"選手{pit_no}"
    r_rank = str(col_data.get("ランク", "")).strip() or "B1"

    # 進入コースに基づく直前データの参照
    chosen_course = updated_courses[pit_no - 1]
    ex_col_name = f"{chosen_course}号艇"
    ex_col_data = edited_df[ex_col_name]

    # --- 【修正箇所②】 展示STのフライング判定とフラグ保持 ---
    raw_ex_st = safe_float(ex_col_data.get("ST"), 0.15)
    is_f_flag = raw_ex_st < 0.0  # マイナス値の場合はフライングフラグをTrueに設定

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
            "exhibition_st": raw_ex_st,  # マイナス値を保持したまま引き渡す
            "is_flying": is_f_flag,      # 明示的にフライングフラグを連携
        }
    )

# ------------------------------------------------------------------------------
# 4. 予測計算処理の実行
# ------------------------------------------------------------------------------
if st.button("🚀 予測スコアを算出する", type="primary", use_container_width=True):
    with st.spinner("各指標を計算中..."):
        try:
            results = calculate_full_race_scores(
                venue_name=selected_venue,
                wind_direction=wind_direction,
                wind_speed_m=wind_speed,
                tide_condition=tide_condition,
                wave_height_cm=wave_height,
                racers_data=racers_data,
                exhibition_data=exhibition_data,
            )

            # 結果データフレームの作成
            res_rows = []
            for r in results:
                pit = r["pit_no"]
                r_info = next(item for item in racers_data if item["pit_no"] == pit)
                ex_info = next(
                    item for item in exhibition_data if item["pit_no"] == pit
                )

                bd = r["score_breakdown"]
                dt = r["details"]

                res_rows.append(
                    {
                        "艇番": pit,
                        "選手名": r_info["racer_name"],
                        "進入": r["entry_course"],
                        "総合スコア": r["total_score"],
                        "選手素点": bd["racer_base_subtotal"],
                        "展示タイム点": bd["exhibition_score"],
                        "展示ST点": bd["exhibition_st_score"],
                        "風点": bd["wind_score"],
                        "潮点": bd["tide_score"],
                        "展示順位": dt.get("exhibition_rank", "-"),
                        "展示ST順位": dt.get("exhibition_st_rank", "-"),
                    }
                )

            df_res = pd.DataFrame(res_rows)
            df_res = df_res.sort_values(
                by="総合スコア", ascending=False
            ).reset_index(drop=True)
            df_res.index = df_res.index + 1  # 予想順位 (1位〜)

            # ------------------------------------------------------------------
            # 5. 結果表示: スコア一覧 & 買い目推奨
            # ------------------------------------------------------------------
            st.markdown("---")
            st.subheader("3. 予測結果 & 買い目推奨")

            col_res1, col_res2 = st.columns([6, 4])

            with col_res1:
                st.markdown("#### 📊 予測スコア一覧")

                # ヒートマップ風カラーリング
                def color_scores(val):
                    if isinstance(val, (int, float)):
                        if val >= 15.0:
                            return "background-color: #d1e7dd; color: #0f5132; font-weight: bold;"
                        elif val >= 10.0:
                            return "background-color: #fff3cd; color: #664d03;"
                    return ""

                styled_df = df_res.style.applymap(
                    color_scores, subset=["総合スコア"]
                ).format(
                    {
                        "総合スコア": "{:.2f}",
                        "選手素点": "{:.2f}",
                        "展示タイム点": "{:.2f}",
                        "展示ST点": "{:.2f}",
                        "風点": "{:.2f}",
                        "潮点": "{:.2f}",
                    }
                )

                st.dataframe(styled_df, use_container_width=True)

            with col_res2:
                st.markdown("#### 🎯 最終買い目推奨")

                final_recommendation = generate_final_betting_recommendation(
                    results
                )

                st.info(
                    f"**本命買い目 (3連単)**:\n\n"
                    f"### {final_recommendation.get('honmei', '1-2-3')}"
                )

                if "ana" in final_recommendation:
                    st.warning(
                        f"**穴・抑え買い目**:\n\n"
                        f"### {final_recommendation['ana']}"
                    )

                if "reason" in final_recommendation:
                    st.caption(f"判断理由: {final_recommendation['reason']}")

            # ------------------------------------------------------------------
            # 6. コース別過去成績（データリポジトリ連携）
            # ------------------------------------------------------------------
            st.markdown("---")
            st.subheader("4. 出走選手のコース別実績（参考データ）")

            course_stat_rows = []
            for r_info in racers_data:
                r_id = r_info["racer_id"]
                course = r_info["entry_course"]

                # 成績データおよび基本情報の取得
                c_stat = get_racer_course_stat(r_id, course)
                b_info = get_racer_basic_info(r_id)

                if c_stat:
                    course_stat_rows.append(
                        {
                            "艇番": r_info["pit_no"],
                            "選手名": r_info["racer_name"],
                            "進入": course,
                            "出走回数": c_stat.get("run_count", 0),
                            "1着率": c_stat.get("win_rate_1st", 0.0),
                            "2着率": c_stat.get("win_rate_2nd", 0.0),
                            "3着率": c_stat.get("win_rate_3rd", 0.0),
                            "3連対率": c_stat.get("triple_rate", 0.0),
                            "平均ST": c_stat.get("avg_st", 0.15),
                        }
                    )
                else:
                    course_stat_rows.append(
                        {
                            "艇番": r_info["pit_no"],
                            "選手名": r_info["racer_name"],
                            "進入": course,
                            "出走回数": 0,
                            "1着率": 0.0,
                            "2着率": 0.0,
                            "3着率": 0.0,
                            "3連対率": 0.0,
                            "平均ST": 0.15,
                        }
                    )

            df_course_stats = pd.DataFrame(course_stat_rows)

            def style_rates(df):
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
                        unique_vals = sorted(
                            df[col].dropna().unique(), reverse=True
                        )
                        for idx, val in df[col].items():
                            if val in unique_vals:
                                rank_idx = unique_vals.index(val)
                                if rank_idx < len(green_colors):
                                    styles.loc[idx, col] = green_colors[
                                        rank_idx
                                    ]

                return styles

            styled_course_df = df_course_stats.style.format(
                {
                    "1着率": "{:.1f}%",
                    "2着率": "{:.1f}%",
                    "3着率": "{:.1f}%",
                    "3連対率": "{:.1f}%",
                    "平均ST": "{:.2f}",
                }
            ).apply(style_rates, axis=None)

            st.dataframe(styled_course_df, use_container_width=True)

        except Exception as e:
            st.error(f"予測処理中にエラーが発生しました: {e}")
            st.exception(e)
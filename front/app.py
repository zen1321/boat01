import sys
from pathlib import Path

# プロジェクトルート（boat_prediction）をPythonパスに追加
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

import os
import pandas as pd
import streamlit as st
from data.racer_course_repository import get_racer_course_stat
from data.txt_repository import load_race_detail_from_txt
from data.venue_repository import get_all_venues
from logic.main_logic import calculate_full_race_scores
from logic.betting_decision import generate_final_betting_recommendation  # 展開予想・買い目決定モジュール

st.set_page_config(
    page_title="ボートレース総合予測", page_icon="🚤", layout="wide"
)

st.title("🚤 ボートレース総合スコア予測")
st.caption("txtファイル（`txt_data/race_detail.txt`）からデータを自動取得し、スコアと順位を算出します。")

# ------------------------------------------------------------------------------
# 1. 画面上部設定: 競艇場・気象条件 & txtファイル読み込み
# ------------------------------------------------------------------------------
st.subheader("⚙️ レース基本設定 & 気象条件")

col_top1, col_top2, col_top3 = st.columns(3)

with col_top1:
    st.markdown("##### 📍 競艇場 & データ読み込み")
    venue_list = get_all_venues()
    default_index = venue_list.index("江戸川") if "江戸川" in venue_list else 0
    selected_venue = st.sidebar.selectbox("競艇場", venue_list, index=default_index) if hasattr(st, "sidebar") and False else st.selectbox("競艇場", venue_list, index=default_index)

    # txtファイル読み込み処理（指定パスから直接読み込み）
    txt_path = "txt_data/race_detail.txt"
    racers_data = None
    exhibition_data = None

    try:
        if os.path.exists(txt_path):
            racers_data, exhibition_data = load_race_detail_from_txt(txt_path)
            st.info(f"「{txt_path}」をロードしました")
        else:
            st.warning(f"「{txt_path}」が見つかりません")
    except Exception as e:
        st.error(f"データ読み込みエラー: {e}")

with col_top2:
    st.markdown("##### 🌬️ 風条件")
    wind_direction = st.selectbox("風向", ["無風", "追い風", "向かい風"], index=0)
    wind_speed = st.number_input("風速 (m)", min_value=0.0, max_value=15.0, value=0.0, step=0.5)

with col_top3:
    st.markdown("##### 🌊 潮条件")
    tide_state = st.selectbox("潮の状態", ["なし", "満潮", "干潮", "中潮", "小潮"], index=0)

weather_info = {
    "wind_direction": wind_direction,
    "wind_speed": wind_speed,
    "tide_state": tide_state,
}

st.markdown("---")

# ------------------------------------------------------------------------------
# 2. メインエリア: 進入コース設定 & データ確認テーブル表示
# ------------------------------------------------------------------------------
st.subheader("📋 出走表・展示データ & 進入コース設定")

if racers_data and exhibition_data:
    st.markdown("#### 🧭 進入コース設定")
    st.caption("前付け等のコース変動がある場合は、各艇の進入コースを変更してください（初期値は枠番通り）。")

    course_cols = st.columns(6)
    updated_courses = []

    for i, col in enumerate(course_cols):
        pit_no = i + 1
        with col:
            default_course = racers_data[i].get("entry_course", pit_no)
            chosen_course = st.selectbox(
                f"{pit_no}号艇 コース",
                options=[1, 2, 3, 4, 5, 6],
                index=default_course - 1,
                key=f"entry_course_pit_{pit_no}"
            )
            updated_courses.append(chosen_course)

    for i in range(len(racers_data)):
        racers_data[i]["entry_course"] = updated_courses[i]
        exhibition_data[i]["entry_course"] = updated_courses[i]

    display_rows = []
    for r, ex in zip(racers_data, exhibition_data):
        display_rows.append(
            {
                "艇番": f"{r['pit_no']}号艇",
                "進入コース": f"{r['entry_course']}コース",
                "登録番号": r["racer_id"],
                "名前": r.get("racer_name", "-"),
                "ランク": r["rank"],
                "期": r.get("term", "-"),
                "出身": r.get("birthplace", "-"),
                "モーター2連率": r["motor_rate"],
                "平均ST": r["avg_st"],
                "全国勝率": r["national_win_rate"],
                "当地勝率": r["local_win_rate"],
                "展示タイム": ex["exhibition_time"],
                "周回タイム": ex["lap_time"],
                "回り足": ex["turn_foot"],
                "直線": ex["straight_line"],
                "展示ST": ex["exhibition_st"],
            }
        )
    
    st.markdown("#### 📊 設定反映後のデータ一覧")
    st.dataframe(pd.DataFrame(display_rows), use_container_width=True, hide_index=True)
else:
    st.warning("「txt_data/race_detail.txt」を配置してください。")

# ------------------------------------------------------------------------------
# 3. 予測実行 & 結果表示
# ------------------------------------------------------------------------------
st.markdown("---")
if st.button("🚀 レーススコア予測を実行", type="primary", use_container_width=True):
    if not racers_data or not exhibition_data:
        st.error("有効なデータがありません。")
    else:
        try:
            results = calculate_full_race_scores(
                venue_name=selected_venue,
                race_racers_data=racers_data,
                race_exhibition_data=exhibition_data,
                weather_info=weather_info,
            )

            st.success(f"【{selected_venue}】予測集計が完了しました！")

            # ------------------------------------------------------------------
            # 3. 展開予想 ＆ 3連単推奨買い目
            # ------------------------------------------------------------------
            st.subheader("🎫 展開予想 ＆ 3連単推奨買い目")

            # 展開予想・推奨買い目の計算ロジック呼び出し
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

            # ------------------------------------------------------------------
            # 総合評価一覧テーブル表示
            # ------------------------------------------------------------------
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

            # ------------------------------------------------------------------
            # 4. モーター・展示足ハイライト表示
            # ------------------------------------------------------------------
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

            format_dict = {
                "モータ2連対率": "{:.1f}",
                "展示タイム": "{:.2f}",
                "周回タイム": "{:.2f}",
                "回り足": "{:.2f}",
                "直線": "{:.2f}",
            }

            styled_df = (
                df_detail.style
                .format(format_dict)
                .apply(highlight_top3, axis=None)
            )

            st.dataframe(styled_df, use_container_width=True, hide_index=True)

            # ------------------------------------------------------------------
            # 5. 進入コース別実績（緑色系グラデーション色付け）
            # ------------------------------------------------------------------
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
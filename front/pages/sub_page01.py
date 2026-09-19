import streamlit as st

# --- メイン画面への戻るボタン ---
col_nav, _ = st.columns([2, 8])
with col_nav:
    if st.button("⬅️ メイン予測画面へ戻る", use_container_width=True):
        st.switch_page("pages/main_page.py")

st.markdown("---")
st.title("⚙️ サブ機能 01（準備中）")
st.caption("この画面の機能は後日実装予定です。")

# --- 開発用プレースホルダー ---
st.info("💡 ここに今後の新規機能を実装していきます。")

col1, col2 = st.columns(2)

with col1:
    st.subheader("設定・入力エリア（仮）")
    st.text_input("サンプル入力項目")
    st.button("実行（ダミー）", use_container_width=True)

with col2:
    st.subheader("出力・結果表示エリア（仮）")
    st.write("結果がここに表示されます。")
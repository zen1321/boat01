import sys
from pathlib import Path
import streamlit as st

# プロジェクトルートを Python パスに追加
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

st.set_page_config(
    page_title="ボートレース総合予測",
    page_icon="🚤",
    layout="wide"
)

BASE_DIR = Path(__file__).resolve().parent

# 各ページオブジェクトの生成
main_page = st.Page(
    BASE_DIR / "pages" / "main_page.py",
    title="総合スコア予測",
    icon="🚤"
)

sub_page01 = st.Page(
    BASE_DIR / "pages" / "sub_page01.py",
    title="サブ機能01",
    icon="⚙️"
)

# ナビゲーションの初期化（サイドバーの自動メニューは非表示）
pg = st.navigation([main_page, sub_page01], position="hidden")
pg.run()
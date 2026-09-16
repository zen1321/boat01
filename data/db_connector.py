import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "boat_race.db")


def get_connection():
    """データベース接続を取得"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """テーブルの初期化作成"""
    conn = get_connection()
    cursor = conn.cursor()

    # 1. 階級スコア定義テーブル
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS rank_scores (
        rank TEXT PRIMARY KEY,
        score REAL NOT NULL
    )
    """
    )

    initial_ranks = [
        ("A1", 1.5),
        ("A2", 1.0),
        ("B1", 0.0),
        ("B2", -1.0),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO rank_scores (rank, score) VALUES (?, ?)",
        initial_ranks,
    )

    # 2. 競艇場マスタテーブル（コース別スコアカラムを追加）
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS venue_types (
        venue_name TEXT PRIMARY KEY,
        venue_type TEXT NOT NULL,
        water_type TEXT NOT NULL,
        course1_score REAL NOT NULL DEFAULT 3.0,
        course2_score REAL NOT NULL DEFAULT 2.0,
        course3_score REAL NOT NULL DEFAULT 1.0,
        course4_score REAL NOT NULL DEFAULT 0.5,
        course5_score REAL NOT NULL DEFAULT -1.0,
        course6_score REAL NOT NULL DEFAULT -2.0
    )
    """
    )

    # 既存のテーブルにコース別カラムが存在しない場合は自動追加
    cursor.execute("PRAGMA table_info(venue_types)")
    columns = [column[1] for column in cursor.fetchall()]
    course_defaults = {
        "course1_score": 3.0,
        "course2_score": 2.0,
        "course3_score": 1.0,
        "course4_score": 0.5,
        "course5_score": -1.0,
        "course6_score": -2.0,
    }

    for col_name, default_val in course_defaults.items():
        if col_name not in columns:
            cursor.execute(
                f"ALTER TABLE venue_types ADD COLUMN {col_name} REAL NOT NULL DEFAULT {default_val}"
            )

    # 全24競艇場のマスタ登録
    initial_venues = [
        ("桐生", "標準", "静水", 3.0, 2.0, 1.0, 0.5, -1.0, -2.0),
        ("戸田", "機力重視", "難水", 3.0, 2.0, 1.0, 0.5, -1.0, -2.0),
        ("江戸川", "機力重視", "難水", 3.0, 2.0, 1.0, 0.5, -1.0, -2.0),
        ("平和島", "機力重視", "難水", 3.0, 2.0, 1.0, 0.5, -1.0, -2.0),
        ("多摩川", "標準", "静水", 3.0, 2.0, 1.0, 0.5, -1.0, -2.0),
        ("浜名湖", "標準", "静水", 3.0, 2.0, 1.0, 0.5, -1.0, -2.0),
        ("蒲郡", "標準", "静水", 3.0, 2.0, 1.0, 0.5, -1.0, -2.0),
        ("常滑", "標準", "静水", 3.0, 2.0, 1.0, 0.5, -1.0, -2.0),
        ("津", "標準", "難水", 3.0, 2.0, 1.0, 0.5, -1.0, -2.0),
        ("三国", "インコース重視", "難水", 3.0, 2.0, 1.0, 0.5, -1.0, -2.0),
        ("びわこ", "標準", "難水", 3.0, 2.0, 1.0, 0.5, -1.0, -2.0),
        ("住之江", "インコース重視", "静水", 3.0, 2.0, 1.0, 0.5, -1.0, -2.0),
        ("尼崎", "インコース重視", "静水", 3.0, 2.0, 1.0, 0.5, -1.0, -2.0),
        ("鳴門", "標準", "難水", 3.0, 2.0, 1.0, 0.5, -1.0, -2.0),
        ("丸亀", "標準", "静水", 3.0, 2.0, 1.0, 0.5, -1.0, -2.0),
        ("児島", "標準", "静水", 3.0, 2.0, 1.0, 0.5, -1.0, -2.0),
        ("宮島", "標準", "難水", 3.0, 2.0, 1.0, 0.5, -1.0, -2.0),
        ("徳山", "インコース重視", "静水", 3.0, 2.0, 1.0, 0.5, -1.0, -2.0),
        ("下関", "インコース重視", "静水", 3.0, 2.0, 1.0, 0.5, -1.0, -2.0),
        ("若松", "標準", "静水", 3.0, 2.0, 1.0, 0.5, -1.0, -2.0),
        ("芦屋", "インコース重視", "静水", 3.0, 2.0, 1.0, 0.5, -1.0, -2.0),
        ("福岡", "標準", "難水", 3.0, 2.0, 1.0, 0.5, -1.0, -2.0),
        ("唐津", "標準", "静水", 3.0, 2.0, 1.0, 0.5, -1.0, -2.0),
        ("大村", "インコース重視", "静水", 3.0, 2.0, 1.0, 0.5, -1.0, -2.0),
    ]

    cursor.executemany(
        """
    INSERT OR IGNORE INTO venue_types (
        venue_name, venue_type, water_type,
        course1_score, course2_score, course3_score,
        course4_score, course5_score, course6_score
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        initial_venues,
    )

    # 3. モータースコア判定ルールテーブル
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS motor_score_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venue_type TEXT NOT NULL,
        min_rate REAL NOT NULL,
        score REAL NOT NULL
    )
    """
    )

    initial_motor_rules = [
        ("標準", 40.0, 2.0),
        ("標準", 30.0, 1.0),
        ("標準", 0.0, -1.0),
        ("機力重視", 40.0, 3.0),
        ("機力重視", 30.0, 1.5),
        ("機力重視", 0.0, -1.5),
        ("インコース重視", 40.0, 1.4),
        ("インコース重視", 30.0, 0.7),
        ("インコース重視", 0.0, -0.7),
    ]

    cursor.execute("SELECT COUNT(*) FROM motor_score_rules")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO motor_score_rules (venue_type, min_rate, score) VALUES (?, ?, ?)",
            initial_motor_rules,
        )

    # 4. 選手情報テーブル
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS racers (
        racer_id INTEGER PRIMARY KEY,
        racer_name TEXT NOT NULL,
        rank TEXT,
        win_rate REAL,
        motor_score REAL,
        avg_st REAL
    )
    """
    )

    # 5. コース別成績テーブル
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS course_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        racer_id INTEGER,
        entry_course INTEGER,
        win_rate_1st REAL,
        win_rate_2nd REAL,
        win_rate_3rd REAL,
        win_rate_4th REAL,
        win_rate_5th REAL,
        win_rate_6th REAL,
        FOREIGN KEY (racer_id) REFERENCES racers (racer_id)
    )
    """
    )

    # 6. 直前・展示・気象データテーブル
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS exhibition_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        race_date TEXT,
        venue TEXT,
        race_no INTEGER,
        pit_no INTEGER,
        entry_course INTEGER,
        exhibition_time REAL,
        lap_time TEXT,
        turn_foot TEXT,
        straight_line TEXT,
        exhibition_st REAL,
        wind_speed REAL,
        tide_level TEXT,
        temperature REAL,
        pressure REAL
    )
    """
    )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(
        "Database updated with course scores (course1_score ~ course6_score)."
    )
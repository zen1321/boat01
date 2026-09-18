import json

# （英語フィールド名, バイト数）の定義
specs = [
    ("toban", 4),                        # 登番
    ("name_kanji", 16),                  # 名前漢字
    ("name_kana", 15),                   # 名前カナ
    ("branch", 4),                       # 支部
    ("rank", 2),                         # 級
    ("era", 1),                          # 年号
    ("birth_date", 6),                   # 生年月日
    ("gender", 1),                       # 性別
    ("age", 2),                          # 年齢
    ("height", 3),                       # 身長
    ("weight", 2),                       # 体重
    ("blood_type", 2),                   # 血液型
    ("win_rate", 4),                     # 勝率
    ("double_win_rate", 4),              # 複勝率
    ("first_places", 3),                 # 1着回数
    ("second_places", 3),                # 2着回数
    ("races_count", 3),                  # 出走回数
    ("final_races", 2),                  # 優出回数
    ("championships", 2),                # 優勝回数
    ("st_avg", 3),                       # 平均スタートタイミング
    ("c1_entries", 3),                   # 1コース進入回数
    ("c1_double_win_rate", 4),           # 1コース複勝率
    ("c1_st_avg", 3),                    # 1コース平均スタートタイミング
    ("c1_st_rank_avg", 3),               # 1コース平均スタート順位
    ("c2_entries", 3),                   # 2コース進入回数
    ("c2_double_win_rate", 4),           # 2コース複勝率
    ("c2_st_avg", 3),                    # 2コース平均スタートタイミング
    ("c2_st_rank_avg", 3),               # 2コース平均スタート順位
    ("c3_entries", 3),                   # 3コース進入回数
    ("c3_double_win_rate", 4),           # 3コース複勝率
    ("c3_st_avg", 3),                    # 3コース平均スタートタイミング
    ("c3_st_rank_avg", 3),               # 3コース平均スタート順位
    ("c4_entries", 3),                   # 4コース進入回数
    ("c4_double_win_rate", 4),           # 4コース複勝率
    ("c4_st_avg", 3),                    # 4コース平均スタートタイミング
    ("c4_st_rank_avg", 3),               # 4コース平均スタート順位
    ("c5_entries", 3),                   # 5コース進入回数
    ("c5_double_win_rate", 4),           # 5コース複勝率
    ("c5_st_avg", 3),                    # 5コース平均スタートタイミング
    ("c5_st_rank_avg", 3),               # 5コース平均スタート順位
    ("c6_entries", 3),                   # 6コース進入回数
    ("c6_double_win_rate", 4),           # 6コース複勝率
    ("c6_st_avg", 3),                    # 6コース平均スタートタイミング
    ("c6_st_rank_avg", 3),               # 6コース平均スタート順位
    ("prev_rank", 2),                    # 前期級
    ("prev_prev_rank", 2),               # 前々期級
    ("prev3_rank", 2),                   # 前々々期級
    ("prev_ability_index", 4),           # 前期能力指数
    ("current_ability_index", 4),        # 今期能力指数
    ("year", 4),                         # 年
    ("period", 1),                       # 期
    ("calc_period_from", 8),             # 算出期間（自）
    ("calc_period_to", 8),               # 算出期間（至）
    ("trainee_period", 3),               # 養成期
    ("c1_1st_places", 3),                # 1コース1着回数
    ("c1_2nd_places", 3),                # 1コース2着回数
    ("c1_3rd_places", 3),                # 1コース3着回数
    ("c1_4th_places", 3),                # 1コース4着回数
    ("c1_5th_places", 3),                # 1コース5着回数
    ("c1_6th_places", 3),                # 1コース6着回数
    ("c1_f_count", 2),                   # 1コースF回数
    ("c1_l0_count", 2),                  # 1コースL0回数
    ("c1_l1_count", 2),                  # 1コースL1回数
    ("c1_k0_count", 2),                  # 1コースK0回数
    ("c1_k1_count", 2),                  # 1コースK1回数
    ("c1_s0_count", 2),                  # 1コースS0回数
    ("c1_s1_count", 2),                  # 1コースS1回数
    ("c1_s2_count", 2),                  # 1コースS2回数
    ("c2_1st_places", 3),                # 2コース1着回数
    ("c2_2nd_places", 3),                # 2コース2着回数
    ("c2_3rd_places", 3),                # 2コース3着回数
    ("c2_4th_places", 3),                # 2コース4着回数
    ("c2_5th_places", 3),                # 2コース5着回数
    ("c2_6th_places", 3),                # 2コース6着回数
    ("c2_f_count", 2),                   # 2コースF回数
    ("c2_l0_count", 2),                  # 2コースL0回数
    ("c2_l1_count", 2),                  # 2コースL1回数
    ("c2_k0_count", 2),                  # 2コースK0回数
    ("c2_k1_count", 2),                  # 2コースK1回数
    ("c2_s0_count", 2),                  # 2コースS0回数
    ("c2_s1_count", 2),                  # 2コースS1回数
    ("c2_s2_count", 2),                  # 2コースS2回数
    ("c3_1st_places", 3),                # 3コース1着回数
    ("c3_2nd_places", 3),                # 3コース2着回数
    ("c3_3rd_places", 3),                # 3コース3着回数
    ("c3_4th_places", 3),                # 3コース4着回数
    ("c3_5th_places", 3),                # 3コース5着回数
    ("c3_6th_places", 3),                # 3コース6着回数
    ("c3_f_count", 2),                   # 3コースF回数
    ("c3_l0_count", 2),                  # 3コースL0回数
    ("c3_l1_count", 2),                  # 3コースL1回数
    ("c3_k0_count", 2),                  # 3コースK0回数
    ("c3_k1_count", 2),                  # 3コースK1回数
    ("c3_s0_count", 2),                  # 3コースS0回数
    ("c3_s1_count", 2),                  # 3コースS1回数
    ("c3_s2_count", 2),                  # 3コースS2回数
    ("c4_1st_places", 3),                # 4コース1着回数
    ("c4_2nd_places", 3),                # 4コース2着回数
    ("c4_3rd_places", 3),                # 4コース3着回数
    ("c4_4th_places", 3),                # 4コース4着回数
    ("c4_5th_places", 3),                # 4コース5着回数
    ("c4_6th_places", 3),                # 4コース6着回数
    ("c4_f_count", 2),                   # 4コースF回数
    ("c4_l0_count", 2),                  # 4コースL0回数
    ("c4_l1_count", 2),                  # 4コースL1回数
    ("c4_k0_count", 2),                  # 4コースK0回数
    ("c4_k1_count", 2),                  # 4コースK1回数
    ("c4_s0_count", 2),                  # 4コースS0回数
    ("c4_s1_count", 2),                  # 4コースS1回数
    ("c4_s2_count", 2),                  # 4コースS2回数
    ("c5_1st_places", 3),                # 5コース1着回数
    ("c5_2nd_places", 3),                # 5コース2着回数
    ("c5_3rd_places", 3),                # 5コース3着回数
    ("c5_4th_places", 3),                # 5コース4着回数
    ("c5_5th_places", 3),                # 5コース5着回数
    ("c5_6th_places", 3),                # 5コース6着回数
    ("c5_f_count", 2),                   # 5コースF回数
    ("c5_l0_count", 2),                  # 5コースL0回数
    ("c5_l1_count", 2),                  # 5コースL1回数
    ("c5_k0_count", 2),                  # 5コースK0回数
    ("c5_k1_count", 2),                  # 5コースK1回数
    ("c5_s0_count", 2),                  # 5コースS0回数
    ("c5_s1_count", 2),                  # 5コースS1回数
    ("c5_s2_count", 2),                  # 5コースS2回数
    ("c6_1st_places", 3),                # 6コース1着回数
    ("c6_2nd_places", 3),                # 6コース2着回数
    ("c6_3rd_places", 3),                # 6コース3着回数
    ("c6_4th_places", 3),                # 6コース4着回数
    ("c6_5th_places", 3),                # 6コース5着回数
    ("c6_6th_places", 3),                # 6コース6着回数
    ("c6_f_count", 2),                   # 6コースF回数
    ("c6_l0_count", 2),                  # 6コースL0回数
    ("c6_l1_count", 2),                  # 6コースL1回数
    ("c6_k0_count", 2),                  # 6コースK0回数
    ("c6_k1_count", 2),                  # 6コースK1回数
    ("c6_s0_count", 2),                  # 6コースS0回数
    ("c6_s1_count", 2),                  # 6コースS1回数
    ("c6_s2_count", 2),                  # 6コースS2回数
    ("no_course_l0_count", 2),           # コースなしL0回数
    ("no_course_l1_count", 2),           # コースなしL1回数
    ("no_course_k0_count", 2),           # コースなしK0回数
    ("no_course_k1_count", 2),           # コースなしK1回数
    ("birthplace", 6)                    # 出身地
]

def convert_fan_txt_to_en_json(input_file, output_file):
    players = []

    with open(input_file, 'rb') as f:
        for line in f:
            line = line.rstrip(b'\r\n')
            if not line:
                continue
            
            player = {}
            curr = 0
            for field_name, byte_len in specs:
                raw_bytes = line[curr:curr+byte_len]
                curr += byte_len
                try:
                    val = raw_bytes.decode('cp932').strip()
                except UnicodeDecodeError:
                    val = raw_bytes.decode('utf-8', errors='ignore').strip()
                player[field_name] = val
            
            players.append(player)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(players, f, ensure_ascii=False, indent=2)

    print(f"変換完了: 全{len(players)}件のデータを英語化して {output_file} に保存しました。")

if __name__ == "__main__":
    convert_fan_txt_to_en_json('fan2604.txt', 'fan2604_en.json')
from data.racer_repository import (
    get_motor_score_from_db,
    get_venue_type_from_db,
)


def calculate_motor_score(motor_2in_rate: float, venue: str = "平和島") -> float:
    """競艇場名とモーター2連対率から、DB管理された判定基準でスコアを算出

    :param motor_2in_rate: モーター2連対率（%） 例: 42.5
    :param venue: 競艇場名 (例: '平和島') または 競艇場タイプ ('標準', '機力重視', 'インコース重視')
    :return: モータ性能スコア (float)
    """
    # venue に競艇場タイプが直接渡されたか、競艇場名が渡されたかを判断
    if venue in ["標準", "機力重視", "インコース重視"]:
        venue_type = venue
    else:
        # DBから競艇場名に対応するタイプを取得
        venue_type = get_venue_type_from_db(venue)

    # DBからスコアを算出して返す
    return get_motor_score_from_db(motor_2in_rate, venue_type)
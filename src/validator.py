"""
Validation Module
打刻時間の妥当性をチェックするロジックを提供します。
"""
import logging
from datetime import datetime, time

logger = logging.getLogger(__name__)

def validate_time(clock_type: str) -> None:
    """
    現在の時刻が指定された打刻タイプの許容範囲内かチェックし、
    範囲外の場合は警告ログを出力します。

    Args:
        clock_type (str): 'in' (出勤) or 'out' (退勤)
    """
    now = datetime.now().time()
    
    # 時間設定
    # 出勤: 08:45 - 09:00
    in_start = time(8, 45)
    in_end = time(9, 0)
    
    # 退勤: 18:00 - 20:00
    out_start = time(18, 0)
    out_end = time(20, 0)

    if clock_type == 'in':
        if not (in_start <= now <= in_end):
            logger.warning(
                f"現在時刻 ({now.strftime('%H:%M')}) は "
                f"推奨出勤時間 ({in_start.strftime('%H:%M')} - {in_end.strftime('%H:%M')}) の範囲外です。"
            )
        else:
            logger.info("現在時刻は推奨出勤時間の範囲内です。")

    elif clock_type == 'out':
        if not (out_start <= now <= out_end):
            logger.warning(
                f"現在時刻 ({now.strftime('%H:%M')}) は "
                f"推奨退勤時間 ({out_start.strftime('%H:%M')} - {out_end.strftime('%H:%M')}) の範囲外です。"
            )
        else:
            logger.info("現在時刻は推奨退勤時間の範囲内です。")

    else:
        logger.warning(f"不明な打刻タイプです: {clock_type}")

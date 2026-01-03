"""
Touch On Time Auto Clock-in Main Script
"""
import sys
import logging
import argparse
from src import config
from src import validator
from src.bitwarden import BitwardenClient
from src.automator import TouchOnTimeAutomator

# -----------------------------------------------------------------------------
# Logging Setup
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=config.LOG_LEVEL,
    format=config.LOG_FORMAT,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("main")

def parse_args():
    parser = argparse.ArgumentParser(description="Touch On Time Auto Clock-In Tool")
    
    # 必須引数: 打刻タイプ
    parser.add_argument(
        "type",
        choices=["in", "out"],
        help="打刻タイプ (in: 出勤, out: 退勤)"
    )
    
    # オプション: 本番実行フラグ
    # 安全設計: デフォルトはDryRun。--live をつけた時だけ本番。
    # config.DRY_RUNがTrueの場合は、たとえ--liveをつけてもconfig優先...にするか迷うが
    # ここではCLI引数がconfigを上書き(より優先)する設計にするのが一般的。
    parser.add_argument(
        "--live",
        action="store_true",
        help="本番実行モード (指定しない場合はDryRun)"
    )
    
    return parser.parse_args()

def run_process(clock_type: str, is_dry_run: bool, session_key: str = None) -> bool:
    """
    打刻プロセスを実行します。
    Args:
        clock_type (str): 'in' or 'out'
        is_dry_run (bool): TrueならDryRun
        session_key (str): Bitwardenセッションキー (Optional)
    Returns:
        bool: 成功ならTrue
    """
    # config更新
    config.DRY_RUN = is_dry_run
    
    logger.info(f"NODE: {'[DRY RUN]' if is_dry_run else '[LIVE EXECUTION]'} / TYPE: {clock_type.upper()}")

    if is_dry_run:
        logger.warning("!!! DRY_RUN モードが有効です。実際の打刻は行われません !!!")

    try:
        # 0. 時間チェック (警告のみ)
        validator.validate_time(clock_type)

        # 1. Bitwardenから認証情報を取得
        bw = BitwardenClient(session_key=session_key)
        creds = bw.get_login_item(config.BITWARDEN_ITEM_NAME)
        username = creds["username"]
        password = creds["password"]
        
        # 2. Automation実行
        with TouchOnTimeAutomator(headless=False) as bot:
            bot.login(username, password)
            
            if clock_type == "in":
                bot.clock_in()
            elif clock_type == "out":
                bot.clock_out()
            
        logger.info("=== 処理が正常に完了しました ===")
        return True

    except Exception as e:
        logger.error(f"エラーが発生したため処理を中断しました: {e}")
        # CLIからの呼び出しでなければ exception を投げるか、Falseを返す
        # ここでは例外を投げて呼び出し元でハンドリングさせる方が安全
        raise

def main():
    args = parse_args()
    
    # モード判定
    is_dry_run = not args.live
    
    logger.info("=== Touch On Time 自動打刻処理開始 ===")

    try:
        run_process(args.type, is_dry_run)
    except Exception as e:
        sys.exit(1)

if __name__ == "__main__":
    main()

"""
Core business logic for Touch On Time Automator
"""
import sys
import logging
from src.config import settings as config
from src.core import validator
from src.core.bitwarden import BitwardenClient
from src.core.credentials import CredentialManager
from src.core.automator import TouchOnTimeAutomator

logger = logging.getLogger("core")

def run_process(clock_type: str, is_dry_run: bool, session_key: str = None, headless: bool = False) -> bool:
    """
    打刻プロセスを実行します。
    Args:
        clock_type (str): 'in' or 'out'
        is_dry_run (bool): TrueならDryRun
        session_key (str): Bitwardenセッションキー (Optional)
        headless (bool): Trueならブラウザを表示しない (Default: False)
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

        # 1. 認証情報の取得 (Local Cache or Bitwarden)
        # SessionKeyがある場合(またはNoneでも)、必要に応じてBitwardenClientを作成するファクトリを渡す
        cm = CredentialManager()
        creds = cm.get_credentials(
            config.BITWARDEN_ITEM_NAME,
            bw_client_factory=lambda: BitwardenClient(session_key=session_key)
        )
        
        username = creds["username"]
        password = creds["password"]
        
        # 2. Automation実行
        with TouchOnTimeAutomator(headless=headless) as bot:
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

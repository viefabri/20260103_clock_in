import logging
from datetime import datetime
from typing import Optional

from src.config import settings as config
from src.core.usecase import run_process
from src.core.bitwarden import BitwardenClient
from src.core.credentials import CredentialManager

logger = logging.getLogger(__name__)

class JobService:
    """
    ジョブ実行管理サービス
    打刻プロセスの実行、認証情報の解決、ログ記録を担当します。
    """

    def run_job(self, clock_type: str, is_dry_run: bool, master_password: Optional[str] = None, headless: bool = False) -> None:
        """
        打刻ジョブを実行します。
        
        Args:
            clock_type (str): 'in' または 'out'
            is_dry_run (bool): テスト実行フラグ
            master_password (Optional[str]): Bitwarden Master Password (キャッシュがない場合に使用)
            headless (bool): ブラウザを非表示にするか
        """
        log_prefix = f"[{datetime.now().strftime('%H:%M:%S')}]"
        # ログメッセージの統一
        msg_start = f"Job Started: {clock_type} (Dry={is_dry_run})"
        
        # 標準出力とロガー両方に出す (Streamlitのログ表示対策)
        print(f"{log_prefix} {msg_start}")
        logger.info(msg_start)

        try:
            # 1. 認証チェック (Local Cache -> Bitwarden)
            cm = CredentialManager()
            
            if cm.is_cached(config.BITWARDEN_ITEM_NAME):
                # ケースA: キャッシュヒット
                logger.info("Cache hit: Starting job without Bitwarden unlock.")
                run_process(clock_type, is_dry_run, session_key=None, headless=headless)
            
            else:
                # ケースB: キャッシュミス (ロック解除が必要)
                if not master_password:
                    raise ValueError("認証キャッシュがなく、Master Passwordも指定されていません。")

                # ロック解除
                bw = BitwardenClient()
                session_key = bw.unlock(master_password)
                if not session_key:
                    raise RuntimeError("Unlock failed (Session key is empty)")
                
                # Sync (最新化)
                bw.sync()
                
                # セッションキーを使用して実行
                run_process(clock_type, is_dry_run, session_key, headless=headless)
            
            msg_end = "Job Completed Successfully."
            print(f"{log_prefix} {msg_end}")
            logger.info(msg_end)
            
        except Exception as e:
            msg_err = f"Job Failed: {e}"
            print(f"{log_prefix} {msg_err}")
            logger.error(msg_err)
            raise e

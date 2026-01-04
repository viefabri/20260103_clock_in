"""
Bitwarden CLI Wrapper Module
"""
import subprocess
import json
import logging
import os
from typing import Dict, Optional

# ロガーの設定
logger = logging.getLogger(__name__)

class BitwardenClient:
    """Bitwarden CLI (bw) を操作するクラス"""

    # Native Binary Path (Project Root relative)
    BW_PATH = "bin/bw_native"

    def __init__(self, session_key: Optional[str] = None):
        self.session_key = session_key
        self._check_session()

    def _check_session(self) -> None:
        """環境変数 BW_SESSION の存在確認 (Warningのみ)"""
        # コンストラクタで渡されているか、環境変数にあればOK
        if not self.session_key and "BW_SESSION" not in os.environ:
            logger.warning("環境変数 'BW_SESSION' が設定されていません。ロック解除が必要な場合があります。")

    def get_status(self) -> str:
        """
        Bitwardenのステータスを取得します ('unlocked', 'locked', 'unauthenticated')
        """
        try:
            # 環境変数を準備
            env = os.environ.copy()
            if self.session_key:
                env["BW_SESSION"] = self.session_key

            # env=os.environ.copy() はデフォルトの挙動だが、明示的に
            res = subprocess.run(
                [self.BW_PATH, "status"], 
                capture_output=True, 
                text=True, 
                env=env, # 環境変数を渡す
                check=True
            )
            data = json.loads(res.stdout)
            return data.get("status", "unknown")
        except Exception as e:
            logger.error(f"Status check failed: {e}")
            return "error"

    def unlock(self, master_password: str) -> Optional[str]:
        """
        マスターパスワードでロック解除を行い、セッションキーを返します。
        解除失敗時は None (または例外)
        """
        try:
            # Node.js readlineエラー回避のため、引数渡しに変更
            # (セキュリティ上の懸念はあるが、subprocess経由なのでShell履歴には残らない)
            proc = subprocess.run(
                [self.BW_PATH, "unlock", "--raw", master_password],
                capture_output=True,
                text=True,
                check=True
            )
            session_key = proc.stdout.strip()
            self.session_key = session_key
            return session_key
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to unlock: {e.stderr}")
            raise RuntimeError(f"ロック解除に失敗しました: {e.stderr}")

    def get_login_item(self, item_name_or_id: str) -> Dict[str, str]:
        """
        指定されたアイテムのログイン情報(ユーザー名, パスワード)を取得します。

        Args:
            item_name_or_id (str): Bitwardenのアイテム名またはID

        Returns:
            Dict[str, str]: {'username': '...', 'password': '...'}

        Raises:
            RuntimeError: 取得に失敗した場合
        """
        logger.info(f"Bitwardenからアイテム '{item_name_or_id}' を取得します...")

        cmd = [self.BW_PATH, "get", "item", item_name_or_id]

        try:
            # 環境変数を準備
            env = os.environ.copy()
            if self.session_key:
                env["BW_SESSION"] = self.session_key

            # 実行
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                check=True
            )
            
            data = json.loads(result.stdout)
            
            # login 情報を抽出
            login_data = data.get("login", {})
            username = login_data.get("username")
            password = login_data.get("password")

            if not username or not password:
                raise ValueError("ユーザー名またはパスワードが見つかりません。")

            logger.info("認証情報の取得に成功しました。")
            return {
                "username": username,
                "password": password
            }

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip()
            logger.error(f"Bitwarden CLI エラー: {error_msg}")
            raise RuntimeError(f"Bitwardenからの取得に失敗しました: {error_msg}")
        except json.JSONDecodeError:
            logger.error("Bitwarden CLI の出力をJSONとしてパースできませんでした。")
            raise RuntimeError("Bitwarden出力のパースエラー")
        except Exception as e:
            logger.error(f"予期せぬエラーが発生しました: {e}")
            raise

    def sync(self) -> None:
        """
        Bitwardenの保管庫を最新化(sync)します。
        Unlock済みの session_key が必要です。
        """
        logger.info("Bitwarden保管庫を同期しています...")
        try:
            env = os.environ.copy()
            if self.session_key:
                env["BW_SESSION"] = self.session_key
            
            subprocess.run(
                [self.BW_PATH, "sync"],
                env=env,
                check=True,
                capture_output=True
            )
            logger.info("同期に成功しました。")
        except subprocess.CalledProcessError as e:
            logger.error(f"Sync failed: {e}")
            # 同期失敗は致命的ではない場合もあるが、警告を出す
            logger.warning("保管庫の同期に失敗しましたが、処理を継続します。")

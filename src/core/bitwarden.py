"""
Bitwarden CLI ラッパーモジュール
"""
import subprocess
import json
import logging
import os
import shutil
from typing import Dict, Optional

# ロガーの設定
logger = logging.getLogger(__name__)

class BitwardenClient:
    """Bitwarden CLI (bw) を操作するクラス"""

    def __init__(self, session_key: Optional[str] = None):
        self.session_key = session_key
        # パスの解決: 環境変数 -> システムパス -> フォールバック
        self.bw_path = self._resolve_bw_path()
        self._check_session()

    def _resolve_bw_path(self) -> str:
        """Bitwarden CLIのバイナリパスを解決する"""
        # 1. 環境変数優先
        if env_path := os.environ.get("BW_CLI_PATH"):
            return env_path
        # 2. システムパス (shutil.which)
        if sys_path := shutil.which("bw"):
            return sys_path
        # 3. フォールバック (プロジェクト内バイナリ)
        return "bin/bw_native"

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
                [self.bw_path, "status"], 
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
            # [セキュリティ修正]
            # パスワードは引数ではなく標準入力(stdin)経由で渡すことで、
            # psコマンド等によるプロセスリストからの漏洩を防ぐ。
            #
            # [リスク受容]
            # アーキテクチャ上、master_password はPythonプロセスのメモリ上に一時的に存在します。
            # 完全自動化要件のため、このトレードオフは受容されています。
            
            # note: 一部のCLIは改行を期待するため、念のため付与する
            input_pass = master_password if master_password.endswith('\n') else master_password + '\n'

            proc = subprocess.run(
                [self.bw_path, "unlock", "--raw"],
                input=input_pass,
                text=True,
                encoding="utf-8", # [エンコーディング] OSロケール依存防止
                capture_output=True,
                check=True
            )
            session_key = proc.stdout.strip()
            self.session_key = session_key
            return session_key
        except subprocess.CalledProcessError as e:
            # エラーメッセージにパスワードが含まれていないか注意 (stdin経由なら通常は含まれない)
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

        cmd = [self.bw_path, "get", "item", item_name_or_id]

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
                [self.bw_path, "sync"],
                env=env,
                check=True,
                capture_output=True
            )
            logger.info("同期に成功しました。")
        except subprocess.CalledProcessError as e:
            logger.error(f"Sync failed: {e}")
            # 同期失敗は致命的ではない場合もあるが、警告を出す
            logger.warning("保管庫の同期に失敗しましたが、処理を継続します。")

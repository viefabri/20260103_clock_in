
import json
import logging
import os
import stat
from typing import Dict, Optional

from .bitwarden import BitwardenClient

logger = logging.getLogger(__name__)

class CredentialManager:
    """
    認証情報を管理するクラス
    
    1. ローカルキャッシュ (.secrets.json) からの取得を試みる
    2. なければ Bitwarden から取得し、キャッシュする
    """

    def __init__(self, cache_file: str = ".secrets.json"):
        # プロジェクトルートからの相対パスとして扱う
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.cache_path = os.path.join(base_dir, cache_file)

    def is_cached(self, item_name: str) -> bool:
        """
        指定されたアイテムがキャッシュに存在するか確認します。
        
        Returns:
            bool: キャッシュが存在すればTrue
        """
        return self._load_from_cache(item_name) is not None

    def get_credentials(
        self, 
        item_name: str, 
        bw_client_factory: Optional[callable] = None
    ) -> Dict[str, str]:
        """
        認証情報を取得します。

        Args:
            item_name (str): Bitwarden上のアイテム名
            bw_client_factory (callable, optional): BitwardenClientのインスタンスを生成する関数。
                                                  キャッシュミス時にのみ呼び出されます。
        
        Returns:
            Dict[str, str]: {'username': '...', 'password': '...'}
        """
        # 1. ローカルキャッシュを試行
        creds = self._load_from_cache(item_name)
        if creds:
            logger.info("ローカルキャッシュから認証情報を取得しました。")
            return creds

        # 2. キャッシュミス -> Bitwardenから取得
        logger.info("キャッシュが見つからないため、Bitwardenから取得します。")
        
        if not bw_client_factory:
            # ファクトリがない場合はデフォルトで生成（引数なし）
            bw_client = BitwardenClient()
        else:
            bw_client = bw_client_factory()

        # Bitwardenから取得
        creds = bw_client.get_login_item(item_name)
        
        # 3. キャッシュに保存
        self._save_to_cache(item_name, creds)
        
        return creds

    def _load_from_cache(self, item_name: str) -> Optional[Dict[str, str]]:
        if not os.path.exists(self.cache_path):
            return None
        
        try:
            # 権限チェック (参考程度)
            # st = os.stat(self.cache_path)
            # if st.st_mode & 0o777 != 0o600:
            #     logger.warning("キャッシュファイルの権限が推奨設定(600)ではありません。")

            with open(self.cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get(item_name)
        except Exception as e:
            logger.warning(f"キャッシュの読み込みに失敗しました: {e}")
            return None

    def _save_to_cache(self, item_name: str, creds: Dict[str, str]) -> None:
        try:
            # 既存データを読み込み
            existing_data = {}
            if os.path.exists(self.cache_path):
                try:
                    with open(self.cache_path, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                except Exception:
                    pass # 新規作成扱い

            # データを更新
            existing_data[item_name] = creds

            # 保存
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, indent=2, ensure_ascii=False)
            
            # パーミッション設定 (600: 所有者のみ読み書き)
            os.chmod(self.cache_path, stat.S_IRUSR | stat.S_IWUSR)
            logger.info("認証情報をローカルキャッシュに保存しました。")
            
        except Exception as e:
            logger.error(f"キャッシュの保存に失敗しました: {e}")

    def clear_cache(self) -> None:
        """キャッシュファイルを削除します"""
        if os.path.exists(self.cache_path):
            try:
                os.remove(self.cache_path)
                logger.info("ローカルキャッシュを削除しました。")
            except Exception as e:
                logger.error(f"キャッシュ削除エラー: {e}")

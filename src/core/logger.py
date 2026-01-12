import logging
import os
import sys
from src.config import settings as config

def setup_logging(name: str = "app", log_file: str = "app.log") -> logging.Logger:
    """
    アプリケーション全体のロギング設定を行います。
    
    Args:
        name (str): ロガーの名前
        log_file (str): ログファイル名 (logs/ ディレクトリ配下)
    
    Returns:
        logging.Logger: 設定済みのロガーインスタンス
    """
    # ログディレクトリの確保
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    log_path = os.path.join(log_dir, log_file)
    
    # ルートロガーの設定 (一度だけ)
    # Streamlitや他のライブラリのログも拾うため、basicConfigを使用
    logging.basicConfig(
        level=config.LOG_LEVEL,
        format=config.LOG_FORMAT,
        handlers=[
            logging.FileHandler(log_path, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ],
        force=True # 既存の設定を上書き
    )
    
    return logging.getLogger(name)

def get_logger(name: str) -> logging.Logger:
    """
    指定された名前のロガーを取得します。
    (設定は setup_logging で完了している前提)
    """
    return logging.getLogger(name)

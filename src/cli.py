"""
CLI Entry Point for Touch On Time Automator
"""
import sys
import logging
import argparse
from src import config
from src.core import run_process

# -----------------------------------------------------------------------------
# Logging Setup
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=config.LOG_LEVEL,
    format=config.LOG_FORMAT,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("cli")

def parse_args():
    parser = argparse.ArgumentParser(description="Touch On Time Auto Clock-In Tool")
    
    # 必須引数: 打刻タイプ
    parser.add_argument(
        "type",
        choices=["in", "out"],
        help="打刻タイプ (in: 出勤, out: 退勤)"
    )
    
    # オプション: 本番実行フラグ
    parser.add_argument(
        "--live",
        action="store_true",
        help="本番実行モード (指定しない場合はDryRun)"
    )
    
    return parser.parse_args()

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

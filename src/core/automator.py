"""
Touch On Time 用 Selenium 自動化モジュール
"""
import time
import logging
from typing import Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager

from src.config import settings as config

logger = logging.getLogger(__name__)

class TouchOnTimeAutomator:
    """Touch On Time 自動打刻クラス"""

    def __init__(self, headless: bool = False):
        self.driver: Optional[webdriver.Chrome] = None
        self.headless = headless

    def __enter__(self):
        self.setup_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.teardown_driver()

    def setup_driver(self) -> None:
        """Selenium WebDriverのセットアップ"""
        logger.info("WebDriverを起動しています...")
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        
        # 一般的なオプション
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        try:
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=chrome_options
            )
            self.driver.implicitly_wait(10) # デフォルト待機時間
            logger.info("WebDriver起動完了")
        except Exception as e:
            logger.critical(f"WebDriverの起動に失敗しました: {e}")
            raise

    def teardown_driver(self) -> None:
        """ブラウザを閉じる"""
        if self.driver:
            logger.info("ブラウザを終了します")
            self.driver.quit()
            self.driver = None

    def login(self, username: str, password: str) -> None:
        """
        Touch On Time 個人画面へのログイン処理
        """
        if not self.driver:
            raise RuntimeError("WebDriverが起動していません")

        target_url = config.TOUCH_ON_TIME_URL
        logger.info(f"URLにアクセス: {target_url}")
        self.driver.get(target_url)

        try:
            wait = WebDriverWait(self.driver, 15)
            
            # ID入力フィールド待機 & 入力
            # HTML: <input type="text" id="id" ...>
            logger.info("ログインモーダルの表示を待機しています...")
            id_field = wait.until(EC.visibility_of_element_located((By.ID, "id")))
            id_field.clear()
            id_field.send_keys(username)
            logger.info("IDを入力しました")

            # Password入力フィールド
            # HTML: <input type="password" id="password" ...>
            pass_field = self.driver.find_element(By.ID, "password")
            pass_field.clear()
            pass_field.send_keys(password)
            logger.info("パスワードを入力しました (伏字)")

            # ログインボタン(OKボタン)のクリック
            # HTML: <div class="btn-control-message">OK</div>
            # ログインボタン(OKボタン)のクリック
            # HTML: <div class="btn-control-message">OK</div>
            
            # Use WebDriverWait for the button to be clickable
            logger.info("ログインボタン(OK)の有効化を待機しています...")
            login_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'btn-control-message') and text()='OK']")))
            login_btn.click()
            
            logger.info("ログインボタン(OK)をクリックしました")
            
            # 画面遷移待機: 打刻ボタンが表示されるまで待つ
            logger.info("メイン画面への遷移を待機しています...")
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".record-clock-in")))
            logger.info("ログイン完了: メイン画面を確認しました")

        except TimeoutException:
            logger.error("ログイン画面の要素が見つかりませんでした (Timeout)")
            self.driver.save_screenshot("output/error_login_timeout.png")
            with open("output/error_login_source.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            raise
        except Exception as e:
            logger.error(f"ログイン処理中にエラーが発生しました: {e}")
            self.driver.save_screenshot("output/error_login_generic.png")
            with open("output/error_login_source.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            raise

    def clock_in(self) -> None:
        """
        出勤打刻処理
        """
        self._click_record_button("clock-in", "出勤")

    def clock_out(self) -> None:
        """
        退勤打刻処理
        """
        self._click_record_button("clock-out", "退勤")

    def _click_record_button(self, button_type: str, button_label: str) -> None:
        """
        打刻ボタン共通処理
        Args:
            button_type (str): 'clock-in' or 'clock-out' (CSSクラスの一部)
            button_label (str): ログ出力用の日本語ラベル
        """
        if not self.driver:
            raise RuntimeError("WebDriverが起動していません")

        logger.info(f"{button_label}ボタンを検索しています...")

        try:
            # HTML構造: <div class="record-btn-inner record-clock-in">...</div>
            # クラス名でピンポイントに探す
            target_css = f".record-{button_type}"
            
            wait = WebDriverWait(self.driver, 10)

            # オーバーレイ（通知メッセージ）がある場合は消えるのを待つ
            try:
                # notification_contentが表示されている場合、非表示になるまで最大5秒待つ
                wait_overlay = WebDriverWait(self.driver, 5)
                wait_overlay.until(EC.invisibility_of_element_located((By.ID, "notification_content")))
            except TimeoutException:
                # タイムアウトしても処理は続行する（次のステップでJSクリックなどでカバー）
                logger.warning("通知オーバーレイが消えませんが、処理を続行します。")
            except Exception:
                # その他のエラーは無視
                pass

            target_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, target_css)))
            
            logger.info(f"{button_label}ボタンを発見しました")

            # -----------------------------------------------------------------
            # CRITICAL SAFETY CHECK
            # -----------------------------------------------------------------
            if config.DRY_RUN:
                logger.warning(f"【DRY_RUN】設定が有効です。実際の{button_label}打刻(クリック)はスキップします。")
                logger.info("DRY_RUN: Click action skipped.")
                return
            # -----------------------------------------------------------------

            # 本番動作 (親要素あるいはこの要素自体がクリッカブル)
            try:
                target_button.click()
            except ElementClickInterceptedException:
                logger.warning(f"{button_label}ボタンのクリックが阻害されました。JavaScriptクリックを試行します。")
                self.driver.execute_script("arguments[0].click();", target_button)
            
            logger.info(f"{button_label}ボタンをクリックしました！")
            
            # 完了待機
            # 完了待機 (リクエスト完了を確実にするため)
            # 固定スリープの代わりに、ページ読み込み完了などの指標を使うのが理想ですが、
            # SPA的な挙動かリロードか不明なため、安全マージンとして短い待機とJS実行完了確認を行う
            time.sleep(2) 
            try:
                # アラートが出ている場合は受け入れる (成功メッセージなどの可能性があるため)
                if EC.alert_is_present()(self.driver):
                    self.driver.switch_to.alert.accept()
                    logger.info("アラートを検出・承認しました")
            except:
                pass
            
            logger.info("打刻処理完了待ち: 完了")

        except TimeoutException:
            logger.error(f"{button_label}ボタンが見つかりませんでした (Timeout)")
            self.driver.save_screenshot(f"output/error_{button_type}_not_found.png")
            raise
        except Exception as e:
            logger.error(f"{button_label}打刻処理中にエラーが発生しました: {e}")
            self.driver.save_screenshot(f"output/error_{button_type}_generic.png")
            raise

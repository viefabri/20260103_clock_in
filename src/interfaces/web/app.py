import streamlit as st
import streamlit.components.v1 as components
import logging
import time
import pandas as pd
from datetime import datetime, date, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from src.core.services.job_service import JobService
from src.core.bitwarden import BitwardenClient
from src.core.credentials import CredentialManager
from src.config import settings as config

# -----------------------------------------------------------------------------
# 定数とUIラベル (信頼できる唯一の情報源)
# -----------------------------------------------------------------------------
LBL_MP = "Master Password (Alt+Shift+M)"
LBL_RUN = "今すぐ実行 (Shift+Enter)"
LBL_SCHEDULE = "予約に追加 (Shift+S)"
LBL_TYPE_IN = "出勤 (IN) (Alt+1)"
LBL_TYPE_OUT = "退勤 (OUT) (Alt+2)"
LBL_MODE_TEST = "テスト (Dry Run) (Alt+3)"
LBL_MODE_LIVE = "本番 (Live) (Alt+4)"
LBL_DATE = "Date (Alt+Shift+D)"
LBL_TIME = "Time (Alt+Shift+T)"
LBL_DETAIL = "細かく設定する (Alt+5)"

# -----------------------------------------------------------------------------
# 設定とセットアップ
# -----------------------------------------------------------------------------
from src.core.logger import setup_logging

# -----------------------------------------------------------------------------
# Configuration & Setup
# -----------------------------------------------------------------------------
st.set_page_config(page_title="TouchOnTime Automator", page_icon="⏰")

# ログ設定 (集中管理モジュールを使用)
logger = setup_logging("app")
log_dir = "logs"
import os

# スケジューラ (シングルトン)
@st.cache_resource
def get_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.start()
    return scheduler

scheduler = get_scheduler()

# グローバル永続化 (シングルトン)
# ブラウザを閉じてもサーバーが生きている限り値を保持する
@st.cache_resource
class GlobalSession:
    def __init__(self):
        self.master_password = None

global_session = GlobalSession()

# -----------------------------------------------------------------------------
# ヘルパー関数 (バックグラウンドロジック)
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# UI Layout
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# UI Layout
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# UI Layout
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# UI Layout
# -----------------------------------------------------------------------------
# CSS to hide anchor links (chain icon) for a cleaner look
st.markdown("""
<style>
    /* ヘッダーのアンカーリンク（チェーンアイコン）を非表示にする */
    a.anchor-link {
        display: none !important;
    }
    /* アンカーのクラスが異なる可能性がある新しいStreamlitバージョンのため */
    .stHeading a {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("⏰ Touch On Time Automator")

# === ショートカットと属性の注入 ===
def add_keyboard_shortcuts():
    # Pythonの定数をJSに渡す
    # 分離: 表示用ラベル(LABELS) と 検索用キーワード(KEYS)
    # これにより、UI上の装飾文字(Alt+...)が検索の邪魔をするのを防ぐ
    js_variables = f"""
    const LABELS = {{
        RUN: '{LBL_RUN}',
        SCHEDULE: '{LBL_SCHEDULE}',
        TYPE_IN: '{LBL_TYPE_IN}',
        TYPE_OUT: '{LBL_TYPE_OUT}',
        MODE_TEST: '{LBL_MODE_TEST}',
        MODE_LIVE: '{LBL_MODE_LIVE}',
        DATE: '{LBL_DATE}',
        TIME: '{LBL_TIME}',
        MP: '{LBL_MP}',
        DETAIL: '{LBL_DETAIL}'
    }};
    
    // 検索語句はシンプルに (部分一致でヒットしやすくする)
    const SEARCH_KEYS = {{
        RUN: '今すぐ実行',
        SCHEDULE: '予約に追加',
        TYPE_IN: '出勤 (IN)',
        TYPE_OUT: '退勤 (OUT)',
        MODE_TEST: 'テスト',
        MODE_LIVE: '本番',
        DATE: 'Date', 
        TIME: 'Time',
        MP: 'Master Password',
        DETAIL: '細かく設定する'
    }};
    """

    js_code = f"""
    <script>
    {js_variables}
    
    const doc = window.parent.document;
    
    // --- 1. 属性注入ヘルパー ---
    function assignTestIds() {{
        // ボタン
        assignIdByText(SEARCH_KEYS.RUN, 'btn-run-now');
        assignIdByText(SEARCH_KEYS.SCHEDULE, 'btn-add-schedule');
        
        // ラジオボタンのラベル
        assignIdByText(SEARCH_KEYS.TYPE_IN, 'radio-in', 'label');
        assignIdByText(SEARCH_KEYS.TYPE_OUT, 'radio-out', 'label');
        assignIdByText(SEARCH_KEYS.MODE_TEST, 'radio-dry', 'label');
        assignIdByText(SEARCH_KEYS.MODE_LIVE, 'radio-live', 'label');
        assignIdByText(SEARCH_KEYS.DETAIL, 'chk-detail', 'label');

        // 入力フィールド
        assignInputIdByLabel(SEARCH_KEYS.DATE, 'input-date');
        assignInputIdByLabel(SEARCH_KEYS.TIME, 'input-time');
        assignInputIdByLabel(SEARCH_KEYS.MP, 'input-mp', true); 
    }}

    function assignIdByText(text, testId, tagName='*') {{
        const lowerText = text.toLowerCase();
        const translate = "translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')";
        const xpath = `//${{tagName}}[contains(${{translate}}, '${{lowerText}}')]`;
        
        const result = doc.evaluate(xpath, doc, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
        for (let i = 0; i < result.snapshotLength; i++) {{
            let el = result.snapshotItem(i);
            
            // ヒューリスティック: テキストが長すぎる場合はスキップ（ボタンやラベルそのものではなくコンテナである可能性が高い）
            if (el.innerText && el.innerText.length > text.length + 50) continue;

            if (testId.startsWith('btn') || testId.startsWith('radio') || testId.startsWith('chk')) {{
                 let current = el;
                 let found = false;
                 // クリック可能な要素を見つけるまで上にトラバース
                 while(current && current !== doc.body) {{
                    if (current.tagName === 'BUTTON' || current.tagName === 'LABEL' || current.getAttribute('role') === 'button') {{
                        // 可能なら上書きしないが、優先度を保証する
                        if (!current.hasAttribute('data-testid') || current.getAttribute('data-testid') !== testId) {{
                            current.setAttribute('data-testid', testId);
                        }}
                        found = true;
                        break;
                    }}
                    current = current.parentElement;
                 }}
                 if (!found && tagName !== '*') {{
                     el.setAttribute('data-testid', testId);
                 }}
            }} else {{
                el.setAttribute('data-testid', testId);
            }}
        }}
    }}

    function assignInputIdByLabel(labelText, testId, isPassword=false) {{
        // 1. パスワードの特別対応
        if (isPassword) {{
           const inputs = Array.from(doc.getElementsByTagName('input'));
           const pw = inputs.find(i => i.type === 'password');
           if (pw) {{ pw.setAttribute('data-testid', testId); return; }}
        }}

        const lowerLabel = labelText.toLowerCase();

        // 2. aria-labelでの検索を試みる (大文字小文字無視)
        const inputs = Array.from(doc.getElementsByTagName('input'));
        const ariaTarget = inputs.find(i => {{
            const al = i.getAttribute('aria-label');
            return al && al.toLowerCase().includes(lowerLabel);
        }});
        if (ariaTarget) {{
            ariaTarget.setAttribute('data-testid', testId);
            console.log(`Success: Found ${{labelText}} via aria-label`);
            return; 
        }}

        // 3. 堅牢な検索: 'for'属性を持つラベル
        const translate = "translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')";
        const xpathLabel = `//label[contains(${{translate}}, '${{lowerLabel}}')]`;
        const labelResult = doc.evaluate(xpathLabel, doc, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
        
        for (let i = 0; i < labelResult.snapshotLength; i++) {{
             const label = labelResult.snapshotItem(i);
             // ラベルテキストが長すぎる場合はスキップ
             if (label.innerText && label.innerText.length > labelText.length + 50) continue;

             const forId = label.getAttribute('for');
             if (forId) {{
                 const targetInput = doc.getElementById(forId);
                 if (targetInput) {{
                     targetInput.setAttribute('data-testid', testId);
                     console.log(`Success: Found ${{labelText}} via 'for' attribute`);
                     return; 
                 }}
             }}
        }}

        // 4. フォールバック: 近接検索
        // テキストを含む任意の要素を探す
        const xpathGeneric = `//*[self::p or self::div or self::span or self::label][contains(${{translate}}, '${{lowerLabel}}')]`;
        const result = doc.evaluate(xpathGeneric, doc, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
        
        for (let i = 0; i < result.snapshotLength; i++) {{
             let labelEl = result.snapshotItem(i);
             if (labelEl.innerText && labelEl.innerText.length > labelText.length + 50) continue;
             
             let parent = labelEl.parentElement;
             let levels = 0;
             while(parent && levels < 5) {{
                 // input, select, または textarea を探す
                 const input = parent.querySelector('input');
                 if (input) {{ 
                     // 異なるIDがまだ割り当てられていない場合のみ割り当て
                     if (!input.hasAttribute('data-testid') || input.getAttribute('data-testid') === testId) {{
                        input.setAttribute('data-testid', testId); 
                        console.log(`Success: Found ${{labelText}} via proximity`);
                        return; 
                     }}
                 }}
                 parent = parent.parentElement;
                 if (parent === doc.body) break;
                 levels++;
            }}
        }}
        console.warn(`FAIL: Could not find input for label: ${{labelText}}`);
    }}
    
    // --- 2. IDを使用したイベントハンドラ ---
    if (window.parent._clockInKeyHandler) {{
        doc.removeEventListener('keydown', window.parent._clockInKeyHandler);
    }}

    window.parent._clockInKeyHandler = function(e) {{
        assignTestIds(); // IDを再チェック

        const activeTag = doc.activeElement ? doc.activeElement.tagName.toLowerCase() : "";
        const activeType = doc.activeElement ? doc.activeElement.type : "";
        const isTypingSensitive = (activeType === 'password' || activeTag === 'textarea');

        if (e.altKey && e.shiftKey) {{
             console.log(`Key Detected: Alt+Shift+${{e.key}}`); // デバッグログ
        }}

        // アクション
        if (e.shiftKey && e.key === 'Enter') {{
            clickById('btn-run-now'); e.preventDefault();
        }}
        if (e.shiftKey && (e.key === 's' || e.key === 'S')) {{
            if (!isTypingSensitive) {{ clickById('btn-add-schedule'); e.preventDefault(); }}
        }}

        // トグルとフォーカス
        if (e.altKey) {{
            if (!e.shiftKey) {{
                    if (e.key === '1') clickById('radio-in');
                    if (e.key === '2') clickById('radio-out');
                    if (e.key === '3') clickById('radio-dry');
                    if (e.key === '4') clickById('radio-live');
                    if (e.key === '5') clickById('chk-detail');
            }}
            if (e.shiftKey) {{
                if (e.key === 'D' || e.key === 'd') {{ focusById('input-date'); e.preventDefault(); }}
                if (e.key === 'T' || e.key === 't') {{ focusById('input-time'); e.preventDefault(); }}
                if (e.key === 'M' || e.key === 'm') {{ focusById('input-mp'); e.preventDefault(); }}
            }}
        }}
    }};

    doc.addEventListener('keydown', window.parent._clockInKeyHandler);
    
    // IDを設定するための初回実行
    assignTestIds();
    // DOMの変更を監視 (Streamlitの再描画対応)
    const observer = new MutationObserver(() => {{
        assignTestIds();
    }});
    observer.observe(doc.body, {{ childList: true, subtree: true }});


    // ヘルパー
    function clickById(id) {{
        const el = doc.querySelector(`[data-testid="${{id}}"]`);
        if (el) el.click();
    }}
    function focusById(id) {{
        const el = doc.querySelector(`[data-testid="${{id}}"]`);
        if (el) el.focus();
    }}

    </script>
    """
    components.html(js_code, height=0, width=0)

# === 認証情報管理 (メインエリア) ===
# Global -> Local の同期 (状態の初期化)
if 'master_password' not in st.session_state:
    st.session_state['master_password'] = global_session.master_password if global_session.master_password else ""

# 認証ロジック (ボタンとEnterキーで再利用可能)
def authenticate():
    mp_input = st.session_state['master_password']
    if not mp_input:
        st.error("パスワードを入力してください")
        return
    
    with st.status("認証中...") as s:
        try:
            bw = BitwardenClient()
            key = bw.unlock(mp_input)
            if key:
                global_session.master_password = mp_input
                s.update(label="同期中...", state="running")
                bw.sync()
                s.update(label="認証成功！準備完了", state="complete")
                time.sleep(1)
                # コールバックから呼ばれた場合手動rerunは不要だが、state更新がrerunをトリガーする
            else:
                st.error("ロック解除に失敗しました")
        except Exception as e:
            st.error(f"エラー: {e}")

# ローカルキャッシュの確認
cm = CredentialManager()
has_cache = cm.is_cached(config.BITWARDEN_ITEM_NAME)

# 認証状態のロジック
# 以下の条件で認証済みとする:
# 1. セッションにマスターパスワードがある (手動ログイン)
# OR
# 2. ローカルキャッシュが存在する (自動ログイン)
is_manual_auth = bool(st.session_state.get('master_password') and global_session.master_password)
is_authenticated = is_manual_auth or has_cache

# 認証されていない場合のみ入力フォームを表示
if not is_authenticated:
    add_keyboard_shortcuts()
    st.info(f"👇 Master Passwordを入力して、接続を開始してください。 (Alt+Shift+M)")
    
    # ボタンの垂直配置をテキスト入力の高さに合わせるCSS
    st.markdown("""
    <style>
    div.stButton > button:first-child {
        height: 2.6rem;
        margin-top: 0px; 
    }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        # パスワード入力欄
        # on_change=authenticate はEnterキー押下時にロジックをトリガーする
        mp_input_val = st.text_input(
            LBL_MP, 
            type="password",
            key="master_password", 
            label_visibility="collapsed",
            placeholder="Master Passwordを入力...",
            on_change=authenticate
        )
    with col2:
        # 接続確認ボタン
        # type="secondary" (デフォルト) は中立色
        # on_click=authenticate は同じロジックをトリガーする
        st.button("接続確認", use_container_width=True, on_click=authenticate)

# ログアウト用コールバック関数
def logout_callback():
    st.session_state['master_password'] = ""
    global_session.master_password = None
    # 注意: ログアウトは現在メモリセッションのみをクリアします。
    # ローカルファイルキャッシュは削除しません（必要ならユーザーがファイルシステムから削除）。
    # "ログアウト"で"キャッシュクリア"も行いたい場合は、ここで cm.clear_cache() を呼びます。
    # 現在は、"ログアウト"はUI状態のリセットのみと仮定していますが、キャッシュが存在する場合、
    # ページリロードで再度自動ログインします。
    # キャッシュ利用下で本当に"ログアウト"するには、"デバイスを削除"ボタンが必要かもしれません。
    # 今回の修正では、状態ロジックに任せるために単にリロードします。

# ステータス表示 & メインコンテンツ制御
if is_authenticated:
    # ログイン済みヘッダー
    add_keyboard_shortcuts()
    # st.successの高さに合わせるため、少しCSSで調整するか、あるいはシンプルに並べる
    # ログアウトボタンの垂直配置
    st.markdown("""
    <style>
    /* ログアウトボタンを成功メッセージに合わせる */
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) button {
        height: 3rem; /* st.successのデフォルトの高さ（概算） */
        margin-top: 2px;
    }
    </style>
    """, unsafe_allow_html=True)

    h_col1, h_col2 = st.columns([3, 1])
    with h_col1:
        if is_manual_auth:
            st.success("✅ 認証済み (Bitwarden / Master Password)")
        else:
            st.success("✅ 認証済み (Local Cache)")
            
    with h_col2:
        # キャッシュ済みの場合、"ログアウト"は少し曖昧です。"リロード"かも？
        # しかし一貫性のために"ログアウト"のままにします。
        st.button("ログアウト", on_click=logout_callback, type="secondary", use_container_width=True)
    
    # === メイン: 実行コンソール (認証済み) ===
    tab1, tab2, tab3, tab4 = st.tabs(["🚀 実行・予約", "📋 予約リスト", "📊 ログ概要", "📝 ログ詳細"])

    with tab3:
        st.subheader("実行履歴 (概要)")
        log_file_path = f"{log_dir}/app.log"
        if os.path.exists(log_file_path):
            with open(log_file_path, "r") as f:
                lines = f.readlines()
            
            # ログ集約: ジョブ開始 -> ジョブ完了/失敗
            # 可能ならスレッド/コンテキストで実行中ジョブを追跡する辞書を使うべきだが、
            # ここでは線形実行または近接マッチングを仮定する。
            # 簡易ロジック: "Started" を反復し、次の "Completed/Failed" と結合する
            
            history_data = []
            current_job = {}
            
            for line in lines:
                ts_str = line.split("[")[0].strip()
                # ソート用にタイムスタンプをパース
                try:
                    ts = datetime.strptime(ts_str.split(',')[0], "%Y-%m-%d %H:%M:%S")
                except:
                    continue

                if "Job Started" in line:
                    # 新規エントリ
                    # 前のジョブが未完了なら、実行中/不明としてプッシュ
                    if current_job:
                        history_data.append(current_job)
                    
                    parts = line.split("Job Started:")
                    desc = parts[1].strip()
                    
                    # Mode判定
                    if "Dry=True" in desc:
                        mode_str = "🧪 Test"
                    elif "Dry=False" in desc:
                        mode_str = "🔴 Live"
                    else:
                        mode_str = "-"
                    
                    clean_desc = desc.replace(" (Dry=True)", "").replace(" (Dry=False)", "")
                    
                    current_job = {
                        "Date": ts.strftime('%Y-%m-%d'),
                        "Start Time": ts.strftime('%H:%M:%S'),
                        "End Time": "-",
                        "Mode": mode_str,
                        "Detail": clean_desc,
                        "Status": "Running..." 
                    }
                
                elif "Job Completed Successfully" in line:
                    if current_job:
                        current_job["End Time"] = ts.strftime('%H:%M:%S')
                        current_job["Status"] = "✅ Success"
                        history_data.append(current_job)
                        current_job = {} # リセット
                
                elif "Job Failed" in line:
                    if current_job:
                        parts = line.split("Job Failed:")
                        err = parts[1].strip() if len(parts) > 1 else "Error"
                        current_job["End Time"] = ts.strftime('%H:%M:%S')
                        current_job["Status"] = f"❌ Error: {err}"
                        history_data.append(current_job)
                        current_job = {} # リセット

            # まだ実行中なら最後のジョブを追加
            if current_job:
                 history_data.append(current_job)

            if history_data:
                # 最新を最初に表示
                df = pd.DataFrame(history_data[::-1])
                st.dataframe(df, use_container_width=True)
                if st.button("ログ削除 (リセット)", key="clear_logs"):
                    open(log_file_path, 'w').close()
                    st.rerun()
            else:
                st.info("ログデータがまだありません。")
        else:
            st.info("ログファイルはまだ作成されていません。")

    with tab4:
        st.subheader("実行ログ (詳細)")
        log_file_path = f"{log_dir}/app.log"
        if os.path.exists(log_file_path):
            with open(log_file_path, "r") as f:
                raw_logs = f.read()
            st.text_area("Log Output", raw_logs, height=400)
            # 自動更新ボタン
            if st.button("最新の情報に更新"):
                st.rerun()
        else:
            st.info("ログファイルなし")

    with tab1:
        st.subheader("Action")
        
        col1, col2 = st.columns(2)
        with col1:
            clock_type = st.radio("Type", [LBL_TYPE_IN, LBL_TYPE_OUT])
            type_code = "in" if "IN" in clock_type else "out"
        with col2:
            mode = st.radio("Mode", [LBL_MODE_TEST, LBL_MODE_LIVE])
            is_dry = "Dry" in mode
            
            # ヘッドレストグル
            is_headless = st.checkbox("Headless Mode (ブラウザ非表示)", value=True)

        st.subheader("Schedule")
        # 日付/時間ロジック (安定したデフォルト)
        # レイアウト調整: 日付と時間を等しいカラム幅に
        dc1, dc2 = st.columns(2)
        
        with dc1:
            d_val = st.date_input(LBL_DATE, date.today())
        
        with dc2:
            # チェックボックスの状態に基づく時間ステップのロジック (下に配置するためにsession_state経由で処理)
            use_minute_step_key = "use_minute_step"
            # デフォルトはTrue (1分刻み)
            current_step_mode = st.session_state.get(use_minute_step_key, True)
            step_val = 60 if current_step_mode else 300

            # タイプに基づいてデフォルト時間を定義
            if type_code == "in":
                def_t = datetime.strptime("08:55", "%H:%M").time()
            else:
                def_t = datetime.strptime("18:05", "%H:%M").time()

            # 時間入力 (日付入力と整列)
            t_val = st.time_input(LBL_TIME, value=def_t, step=step_val)
            
            st.checkbox(LBL_DETAIL, key=use_minute_step_key, value=True)

        run_dt = datetime.combine(d_val, t_val)

        # Actions
        st.divider()
        ac1, ac2 = st.columns(2)
        
        mp = st.session_state['master_password']

        with ac1:
            if st.button(LBL_RUN, type="primary"):
                with st.status("実行プロセス起動...", expanded=True) as status:
                    st.write("認証 & 同期中...")
                    # Streamlitスレッド内で実行（UIにログが出せる利点）
                    try:
                        # JobServiceに委譲
                        svc = JobService()
                        svc.run_job(type_code, is_dry, mp, headless=is_headless)
                            
                        status.update(label="完了！", state="complete")
                        st.success("成功しました")
                    except Exception as e:
                        status.update(label="失敗", state="error")
                        st.error(f"{e}")

        with ac2:
            if st.button(LBL_SCHEDULE):
                if run_dt <= datetime.now():
                    st.error("未来の日時を指定してください")
                else:
                    job_id = f"{type_code}_{run_dt.strftime('%Y%m%d%H%M%S')}"
                    job = scheduler.add_job(
                        JobService().run_job,
                        trigger='date',
                        run_date=run_dt,
                        args=[type_code, is_dry, mp, is_headless], # MP, Headlessを渡す
                        id=job_id,
                        name=f"{clock_type} ({mode})",
                        misfire_grace_time=3600 # 1時間の遅延まで許容(これがないと少し過ぎただけで実行されない)
                    )
                    st.success(f"予約しました: {run_dt}")
                    logging.info(f"Job Scheduled: {run_dt} id={job_id}")

    with tab2:
        st.subheader("Jobs")
        jobs = scheduler.get_jobs()
        if not jobs:
            st.caption("No active jobs")
        else:
            for j in jobs:
                c1, c2, c3 = st.columns([3,2,1])
                c1.write(f"**{j.name}**")
                c2.write(f"{j.next_run_time.strftime('%Y-%m-%d %H:%M')}")
                if c3.button("Drop", key=j.id):
                    j.remove()
                    st.rerun()
                st.divider()

else:
    # --- 未認証状態 ---
    # トップブロックですでに処理済み
    pass
    # レイアウトシフトのアーティファクトを防ぐために st.stop() を削除

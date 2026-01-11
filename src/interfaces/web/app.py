import streamlit as st
import streamlit.components.v1 as components
import logging
import time
import pandas as pd
from datetime import datetime, date, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from src.core.usecase import run_process
from src.core.bitwarden import BitwardenClient
from src.core.credentials import CredentialManager
from src.config import settings as config

# -----------------------------------------------------------------------------
# Constants & UI Labels (Single Source of Truth)
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
# Configuration & Setup
# -----------------------------------------------------------------------------
st.set_page_config(page_title="TouchOnTime Automator", page_icon="⏰")
# Logging Setup
log_dir = "logs"
import os
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

logging.basicConfig(
    filename=f"{log_dir}/app.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    force=True
)
logger = logging.getLogger("app")

# Scheduler (Singleton)
@st.cache_resource
def get_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.start()
    return scheduler

scheduler = get_scheduler()

# Global Persistence (Singleton)
# ブラウザを閉じてもサーバーが生きている限り値を保持する
@st.cache_resource
class GlobalSession:
    def __init__(self):
        self.master_password = None

global_session = GlobalSession()

# -----------------------------------------------------------------------------
# Helper Functions (Background Logic)
# -----------------------------------------------------------------------------
def robust_job_runner(clock_type, is_dry_run, master_password, headless=False):
    """
    堅牢化された実行ランナー
    常に Unlock -> Sync -> Run の順序で実行する
    """
    log_prefix = f"[{datetime.now().strftime('%H:%M:%S')}]"
    msg_start = f"Job Started: {clock_type} (Dry={is_dry_run})"
    print(f"{log_prefix} {msg_start}")
    logging.info(msg_start)

    try:
        # Check Cache first
        cm = CredentialManager()
        if cm.is_cached(config.BITWARDEN_ITEM_NAME):
            # Cache Hit: No master password needed
            logging.info("Cache hit: Starting job without Bitwarden unlock.")
            run_process(clock_type, is_dry_run, session_key=None, headless=headless)
        else:
            # Cache Miss: Unlock & Sync
            # 1. Unlock (Always fresh)
            bw = BitwardenClient()
            session_key = bw.unlock(master_password)
            if not session_key:
                raise RuntimeError("Unlock failed (Session key is empty)")
            
            # 2. Sync (最新化)
            bw.sync()
            
            # 3. Automation Run
            run_process(clock_type, is_dry_run, session_key, headless=headless)
        
        msg_end = "Job Completed Successfully."
        print(f"{log_prefix} {msg_end}")
        logging.info(msg_end)
        
    except Exception as e:
        msg_err = f"Job Failed: {e}"
        print(f"{log_prefix} {msg_err}")
        logging.error(msg_err)

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
    /* Hide the anchor link (chain icon) in headers */
    a.anchor-link {
        display: none !important;
    }
    /* For newer Streamlit versions where anchors might have different classes */
    .stHeading a {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("⏰ Touch On Time Automator")

# === Shortcuts & Attribute Injection ===
def add_keyboard_shortcuts():
    # Pass Python constants to JS
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
    
    // --- 1. Attribute Injection Helper ---
    function assignTestIds() {{
        // Buttons
        assignIdByText(SEARCH_KEYS.RUN, 'btn-run-now');
        assignIdByText(SEARCH_KEYS.SCHEDULE, 'btn-add-schedule');
        
        // Radio Labels
        assignIdByText(SEARCH_KEYS.TYPE_IN, 'radio-in', 'label');
        assignIdByText(SEARCH_KEYS.TYPE_OUT, 'radio-out', 'label');
        assignIdByText(SEARCH_KEYS.MODE_TEST, 'radio-dry', 'label');
        assignIdByText(SEARCH_KEYS.MODE_LIVE, 'radio-live', 'label');
        assignIdByText(SEARCH_KEYS.DETAIL, 'chk-detail', 'label');

        // Inputs
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
            
            // Heuristic: Skip if text is too long (likely a container, not the button/label itself)
            if (el.innerText && el.innerText.length > text.length + 50) continue;

            if (testId.startsWith('btn') || testId.startsWith('radio') || testId.startsWith('chk')) {{
                 let current = el;
                 let found = false;
                 // Traverse up to find the clickable element
                 while(current && current !== doc.body) {{
                    if (current.tagName === 'BUTTON' || current.tagName === 'LABEL' || current.getAttribute('role') === 'button') {{
                        // Avoid overwriting if possible, but ensure priority
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
        // 1. Password Special Case
        if (isPassword) {{
           const inputs = Array.from(doc.getElementsByTagName('input'));
           const pw = inputs.find(i => i.type === 'password');
           if (pw) {{ pw.setAttribute('data-testid', testId); return; }}
        }}

        const lowerLabel = labelText.toLowerCase();

        // 2. Try find by aria-label (Case Insensitive)
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

        // 3. Robust Search: Label with 'for' attribute
        const translate = "translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')";
        const xpathLabel = `//label[contains(${{translate}}, '${{lowerLabel}}')]`;
        const labelResult = doc.evaluate(xpathLabel, doc, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
        
        for (let i = 0; i < labelResult.snapshotLength; i++) {{
             const label = labelResult.snapshotItem(i);
             // Skip if label text is huge
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

        // 4. Fallback: Proximity Search
        // Look for any element containing the text
        const xpathGeneric = `//*[self::p or self::div or self::span or self::label][contains(${{translate}}, '${{lowerLabel}}')]`;
        const result = doc.evaluate(xpathGeneric, doc, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
        
        for (let i = 0; i < result.snapshotLength; i++) {{
             let labelEl = result.snapshotItem(i);
             if (labelEl.innerText && labelEl.innerText.length > labelText.length + 50) continue;
             
             let parent = labelEl.parentElement;
             let levels = 0;
             while(parent && levels < 5) {{
                 // Try to find input, select, or textarea
                 const input = parent.querySelector('input');
                 if (input) {{ 
                     // Only assign if not already assigned different ID
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
    
    // --- 2. Event Handler using IDs ---
    if (window.parent._clockInKeyHandler) {{
        doc.removeEventListener('keydown', window.parent._clockInKeyHandler);
    }}

    window.parent._clockInKeyHandler = function(e) {{
        assignTestIds(); // Re-check IDs

        const activeTag = doc.activeElement ? doc.activeElement.tagName.toLowerCase() : "";
        const activeType = doc.activeElement ? doc.activeElement.type : "";
        const isTypingSensitive = (activeType === 'password' || activeTag === 'textarea');

        if (e.altKey && e.shiftKey) {{
             console.log(`Key Detected: Alt+Shift+${{e.key}}`); // DEBUG Log
        }}

        // Actions
        if (e.shiftKey && e.key === 'Enter') {{
            clickById('btn-run-now'); e.preventDefault();
        }}
        if (e.shiftKey && (e.key === 's' || e.key === 'S')) {{
            if (!isTypingSensitive) {{ clickById('btn-add-schedule'); e.preventDefault(); }}
        }}

        // Toggles & Focus
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
    
    // Initial run to set IDs
    assignTestIds();
    // Observer to handle DOM changes (Streamlit Re-renders)
    const observer = new MutationObserver(() => {{
        assignTestIds();
    }});
    observer.observe(doc.body, {{ childList: true, subtree: true }});


    // Helpers
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

# === Credential Management (Main Area) ===
# Sync Global -> Local (Initialize State)
if 'master_password' not in st.session_state:
    st.session_state['master_password'] = global_session.master_password if global_session.master_password else ""

# Logic for Authentication (Reusable for button and Enter key)
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
                # No manual rerun needed if called from callback, but state update triggers rerun
            else:
                st.error("ロック解除に失敗しました")
        except Exception as e:
            st.error(f"エラー: {e}")

# Check for Local Cache
cm = CredentialManager()
has_cache = cm.is_cached(config.BITWARDEN_ITEM_NAME)

# Authentication State Logic
# Authenticated if:
# 1. Master Password is in session (Manual Login)
# OR
# 2. Local Cache exists (Auto Login)
is_manual_auth = bool(st.session_state.get('master_password') and global_session.master_password)
is_authenticated = is_manual_auth or has_cache

# 認証されていない場合のみ入力フォームを表示
if not is_authenticated:
    add_keyboard_shortcuts()
    st.info(f"👇 Master Passwordを入力して、接続を開始してください。 (Alt+Shift+M)")
    
    # CSS for vertical alignment of button to match text input height
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
        # on_change=authenticate triggers the logic when Enter is pressed
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
        # type="secondary" (default) is neutral color. 
        # on_click=authenticate triggers same logic.
        st.button("接続確認", use_container_width=True, on_click=authenticate)

# Callback function for logout
def logout_callback():
    st.session_state['master_password'] = ""
    global_session.master_password = None
    # Note: Logout currently only clears memory session. 
    # It does NOT remove the local file cache (User can remove it via file system if needed)
    # If we wanted "Log out" to mean "Clear Cache", we would call cm.clear_cache() here.
    # For now, we assume "Logout" just resets the UI state, but if Cache exists, 
    # the page reload will just auto-login again.
    # To truly "Logout" in a cached world, we might need a "Forget Device" button.
    # For this fix, we simply reload to let the state logic decide.

# ステータス表示 & メインコンテンツ制御
if is_authenticated:
    # ログイン済みヘッダー
    add_keyboard_shortcuts()
    # st.successの高さに合わせるため、少しCSSで調整するか、あるいはシンプルに並べる
    # Vertical alignment for logout button
    st.markdown("""
    <style>
    /* Align logout button with the success message */
    div[data-testid="stHorizontalBlock"] > div:nth-child(2) button {
        height: 3rem; /* Match st.success default height approx */
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
        # If cached, "Logout" is a bit ambiguous. Maybe "Reload"? 
        # But keeping "Logout" for consistency.
        st.button("ログアウト", on_click=logout_callback, type="secondary", use_container_width=True)
    
    # === Main: Execution Console (Authenticated) ===
    tab1, tab2, tab3, tab4 = st.tabs(["🚀 実行・予約", "📋 予約リスト", "📊 ログ概要", "📝 ログ詳細"])

    with tab3:
        st.subheader("実行履歴 (概要)")
        log_file_path = f"{log_dir}/app.log"
        if os.path.exists(log_file_path):
            with open(log_file_path, "r") as f:
                lines = f.readlines()
            
            # Aggregate logs: Job Started -> Job Completed/Failed
            # Use a dictionary to track running jobs by thread/context if possible, 
            # but here we'll assume linear execution or close proximity matching.
            # Simplified Logic: Iterate and combine "Started" with next "Completed/Failed"
            
            history_data = []
            current_job = {}
            
            for line in lines:
                ts_str = line.split("[")[0].strip()
                # Parse timestamp for sorting
                # 2026-01-04 12:00:00,123
                try:
                    ts = datetime.strptime(ts_str.split(',')[0], "%Y-%m-%d %H:%M:%S")
                except:
                    continue

                if "Job Started" in line:
                    # New Entry
                    # If previous job incomplete, push it as running/unknown
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
                        current_job = {} # Reset
                
                elif "Job Failed" in line:
                    if current_job:
                        parts = line.split("Job Failed:")
                        err = parts[1].strip() if len(parts) > 1 else "Error"
                        current_job["End Time"] = ts.strftime('%H:%M:%S')
                        current_job["Status"] = f"❌ Error: {err}"
                        history_data.append(current_job)
                        current_job = {} # Reset

            # Append last job if still running
            if current_job:
                 history_data.append(current_job)

            if history_data:
                # Show newest first
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
            
            # Headless Toggle
            is_headless = st.checkbox("Headless Mode (ブラウザ非表示)", value=True)

        st.subheader("Schedule")
        # Date/Time Logic (Stable Defaults)
        # Layout adjustment: Equal columns for Date and Time
        dc1, dc2 = st.columns(2)
        
        with dc1:
            d_val = st.date_input(LBL_DATE, date.today())
        
        with dc2:
            # Logic for time step based on checkbox state (handled via session_state to allow placement below)
            use_minute_step_key = "use_minute_step"
            # Default to True (1 minute step)
            current_step_mode = st.session_state.get(use_minute_step_key, True)
            step_val = 60 if current_step_mode else 300

            # Define default time based on type
            if type_code == "in":
                def_t = datetime.strptime("08:55", "%H:%M").time()
            else:
                def_t = datetime.strptime("18:05", "%H:%M").time()

            # Time Input (aligned with Date Input now)
            t_val = st.time_input(LBL_TIME, value=def_t, step=step_val)
            
            # Checkbox placed BELOW Time input
            # Changing this will trigger rerun, updating 'step' in next pass
            st.checkbox(LBL_DETAIL, key=use_minute_step_key)

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
                        cm = CredentialManager()
                        if cm.is_cached(config.BITWARDEN_ITEM_NAME):
                            st.write("キャッシュ検出: ロック解除をスキップします。")
                            st.write("自動操作実行中...")
                            run_process(type_code, is_dry, session_key=None, headless=is_headless)
                        else:
                            bw = BitwardenClient()
                            key = bw.unlock(mp)
                            bw.sync()
                            st.write("自動操作実行中...")
                            run_process(type_code, is_dry, key, headless=is_headless)
                            
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
                    scheduler.add_job(
                        robust_job_runner, # 堅牢版ランナーを指定
                        'date',
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
    # --- Not Authenticated State ---
    # Already handled by top block
    pass
    # st.stop() is removed to prevent layout shift artifacts

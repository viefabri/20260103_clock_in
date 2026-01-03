import streamlit as st
import logging
import time
from datetime import datetime, date, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from src.bitwarden import BitwardenClient
from main import run_process

# -----------------------------------------------------------------------------
# Configuration & Setup
# -----------------------------------------------------------------------------
st.set_page_config(page_title="TouchOnTime Automator", page_icon="⏰")
logger = logging.getLogger("app")

# セッション状態の初期化
if 'bw_session' not in st.session_state:
    st.session_state['bw_session'] = None

# Schedulerの初期化 (シングルトン)
@st.cache_resource
def get_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.start()
    return scheduler

scheduler = get_scheduler()

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
def job_function(clock_type, is_dry_run, session_key, master_password=None):
    """APSchedulerから呼び出されるラッパー"""
    print(f"[{datetime.now()}] Job started: {clock_type}, DryRun={is_dry_run}")
    
    # マスターパスワードがある場合、念のため再取得(Unlock)を試みる
    current_key = session_key
    if master_password:
        try:
            print(f"[{datetime.now()}] Refreshing session using Master Password...")
            # ここで都度BitwardenClientを作ってUnlock
            # ※ 注意: 並列実行時にロックファイルの競合等の可能性はあるが、頻度は低い想定
            bw_temp = BitwardenClient()
            new_key = bw_temp.unlock(master_password)
            if new_key:
                current_key = new_key
                print(f"[{datetime.now()}] Session Refreshed.")
        except Exception as e:
            print(f"[{datetime.now()}] Failed to refresh session: {e}")
            # 失敗しても古いキーでリトライする (何もしない)

    try:
        run_process(clock_type, is_dry_run, current_key)
        print(f"[{datetime.now()}] Job completed successfully.")
    except Exception as e:
        print(f"[{datetime.now()}] Job failed: {e}")

@st.cache_data(ttl=5)
def get_cached_status():
    """Bitwardenのステータスを取得 (キャッシュ付き)"""
    # 頻繁なsubprocess呼び出しを防ぐ
    temp_bw = BitwardenClient()
    return temp_bw.get_status()

# -----------------------------------------------------------------------------
# UI Layout
# -----------------------------------------------------------------------------
st.title("⏰ Touch On Time Automator")

# === Sidebar: Bitwarden Status ===
st.sidebar.header("🔑 Bitwarden Status")

# セッションの永続化チェック
if 'master_password' not in st.session_state:
    st.session_state['master_password'] = None

# ステータス取得 (キャッシュ使用)
status = get_cached_status()
# 解除済みだがセッション変数がない場合、アンロック済みとみなせるがキーがないと動かない
# アプリ起動直後はここに来る

status_map = {
    "unlocked": "✅ Unlocked",
    "locked": "🔒 Locked",
    "unauthenticated": "❌ Unauthenticated",
    "unknown": "❓ Unknown",
    "error": "⚠️ Error"
}
st.sidebar.info(f"Status: **{status_map.get(status, status)}**")

if status != "unlocked":
    st.sidebar.warning("Bitwarden is locked. Please unlock to proceed.")
    mp_input = st.sidebar.text_input("Master Password", type="password")
    if st.sidebar.button("Unlock Vault"):
        if mp_input:
            with st.spinner("Unlocking..."):
                try:
                    # インスタンス作成
                    bw_auth = BitwardenClient()
                    session = bw_auth.unlock(mp_input)
                    if session:
                        st.session_state['bw_session'] = session
                        st.session_state['master_password'] = mp_input # 将来のJob実行用にメモリ保持
                        get_cached_status.clear() # キャッシュクリア
                        st.sidebar.success("Unlocked successfully!")
                        time.sleep(1) # 少し待ってからリロード
                        st.rerun()
                except Exception as e:
                    st.sidebar.error(f"Unlock failed: {e}")
else:
    if st.sidebar.button("Lock Vault"):
        st.session_state['bw_session'] = None
        st.session_state['master_password'] = None
        get_cached_status.clear()
        st.rerun()

# === Main: Scheduling & Execution ===

if status != "unlocked":
    st.warning("⚠️ Bitwardenがロックされています。サイドバーから解除してください。")
    st.stop()

# Tab Layout
tab1, tab2 = st.tabs(["🚀 実行・予約", "📋 予約リスト"])

with tab1:
    st.subheader("実行設定")
    
    col1, col2 = st.columns(2)
    with col1:
        clock_type = st.radio("打刻タイプ", ["出勤 (IN)", "退勤 (OUT)"], index=0)
        type_val = "in" if "IN" in clock_type else "out"
        
    with col2:
        mode = st.radio("モード", ["テスト (Dry Run)", "本番 (Live)"], index=0)
        is_dry = (mode == "テスト (Dry Run)")

    st.subheader("日時指定")
    d_col1, d_col2 = st.columns(2)
    with d_col1:
        target_date = st.date_input("日付", date.today())
    with d_col2:
        # デフォルト時刻の設定
        # datetime.now() を使うと再描画のたびに値が変わり、入力がリセットされる原因になるため、固定値を使用
        if type_val == "in":
            # 出勤推奨: 08:45-09:00 なので 08:55 をデフォルトに
            default_t = datetime.strptime("08:55", "%H:%M").time()
        else:
            # 退勤推奨: 18:00-20:00 なので 18:05 をデフォルトに
            default_t = datetime.strptime("18:05", "%H:%M").time()
            
        target_time = st.time_input("時刻", value=default_t)

    # 実行日時オブジェクト
    run_dt = datetime.combine(target_date, target_time)
    
    # Validation Warning 表示
    # 現在時刻と比較して警告を出すロジック (簡易連携)
    # Validatorロジックはimportして使えるが、UI上で動的に出すのが親切
    # ここではシンプルに
    if run_dt < datetime.now():
        st.caption("⚠️ 過去の日時が指定されています（即時実行扱いになります）")

    st.divider()

    action_col1, action_col2 = st.columns(2)
    
    with action_col1:
        if st.button("今すぐ実行", type="primary"):
            with st.status("実行中...", expanded=True) as status_box:
                st.write("Initializing...")
                try:
                    # 即時実行時も、MPがあればリフレッシュしてから...というロジックも入れられるが、
                    # 即時実行は「今」のセッションキーで動けばよいのでそのまま
                    success = run_process(type_val, is_dry, st.session_state['bw_session'])
                    if success:
                        status_box.update(label="完了しました！", state="complete", expanded=False)
                        st.success("処理が正常に完了しました。")
                except Exception as e:
                    status_box.update(label="エラーが発生しました", state="error")
                    st.error(f"Error: {e}")

    with action_col2:
        if st.button("予約リストに追加"):
            if run_dt < datetime.now():
                st.error("現在時刻より未来の日時を指定してください。")
            else:
                job_id = f"{type_val}_{run_dt.strftime('%Y%m%d%H%M%S')}"
                scheduler.add_job(
                    job_function, 
                    'date', 
                    run_date=run_dt, 
                    args=[type_val, is_dry, st.session_state['bw_session'], st.session_state.get('master_password')],
                    id=job_id,
                    name=f"{clock_type} ({mode})"
                )
                st.success(f"予約しました: {run_dt}")

with tab2:
    st.subheader("予約済みジョブ")
    
    jobs = scheduler.get_jobs()
    if not jobs:
        st.info("予約中のジョブはありません。")
    else:
        for job in jobs:
            with st.container():
                c1, c2, c3 = st.columns([3, 2, 1])
                c1.write(f"**{job.name}**")
                c2.write(f"{job.next_run_time.strftime('%Y-%m-%d %H:%M:%S')}")
                if c3.button("削除", key=job.id):
                    job.remove()
                    st.rerun()
                st.divider()

import streamlit as st
import json
import os
import pandas as pd
import datetime

# ==========================================
# ⚙️ 1. 頁面配置與 CSS 魔改 (UI 靈魂)
# ==========================================
st.set_page_config(
    page_title="SNIPER BETTING PRO",
    page_icon="🎯",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- 🎨 狙擊手戰術風格 CSS ---
st.markdown("""
<style>
    /* 全局背景色 - 深灰戰術黑 */
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    
    /* 頂部資金 HUD 儀表板 */
    .hud-container {
        background: linear-gradient(90deg, #1F2937 0%, #111827 100%);
        border: 1px solid #374151;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        text-align: center;
        border-left: 5px solid #00C853; /* 綠色能量條 */
    }
    .hud-title { font-size: 12px; color: #9CA3AF; letter-spacing: 1px; text-transform: uppercase; }
    .hud-value { font-size: 32px; font-weight: 800; color: #FFFFFF; font-family: 'Courier New', monospace; }
    .hud-sub { font-size: 14px; color: #34D399; font-weight: bold; }
    
    /* 輸入框優化 */
    .stSelectbox label, .stNumberInput label, .stRadio label {
        color: #E5E7EB !important;
        font-weight: bold;
    }
    
    /* 按鈕樣式重寫 */
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        height: 50px;
        font-weight: bold;
        border: none;
        transition: all 0.2s;
    }
    
    /* 主行動按鈕 (鎖定下注) - 戰術藍 */
    .primary-btn button {
        background-color: #2563EB !important;
        color: white !important;
        box-shadow: 0 4px 14px 0 rgba(37, 99, 235, 0.39);
    }
    
    /* 贏按鈕 - 螢光綠 */
    .win-btn button { background-color: #059669 !important; color: white !important; }
    
    /* 輸按鈕 - 警示紅 */
    .lose-btn button { background-color: #DC2626 !important; color: white !important; }
    
    /* 分頁 Tabs 優化 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1F2937;
        border-radius: 5px;
        padding: 10px 20px;
        color: #9CA3AF;
    }
    .stTabs [aria-selected="true"] {
        background-color: #374151 !important;
        color: #60A5FA !important;
        border-bottom: 2px solid #60A5FA;
    }
    
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🌍 2. 資料庫 (簡化顯示，請保持你的完整名單)
# ==========================================
# 請將你之前那個完整的 GLOBAL_DB 放在這裡
GLOBAL_DB = {
    "英超": ["曼城", "兵工廠", "利物浦", "阿斯頓維拉", "熱刺", "切爾西", "曼聯", "紐卡索聯"],
    "西甲": ["皇家馬德里", "巴塞隆納", "赫羅納", "馬德里競技", "畢爾包"],
    "德甲": ["勒沃庫森", "拜仁慕尼黑", "多特蒙德"],
    "義甲": ["國際米蘭", "AC米蘭", "尤文圖斯"],
    "法甲": ["巴黎聖日耳曼", "摩納哥", "里爾"],
    "中超": ["上海海港", "上海申花", "成都蓉城", "北京國安", "山東泰山"],
    "美職聯": ["邁阿密國際", "洛杉磯銀河", "LAFC"],
    "日職": ["神戶勝利船", "橫濱水手", "浦和紅鑽"],
    "英冠": ["里茲聯", "伯恩利", "盧頓"],
    "澳職": ["中央海岸水手", "威靈頓鳳凰", "墨爾本勝利"]
    # ... (請確保這裡放入你完整的資料庫)
}

# ==========================================
# 🧠 3. 邏輯核心
# ==========================================
if 'records' not in st.session_state:
    st.session_state.records = []
if 'bankroll' not in st.session_state:
    st.session_state.bankroll = 10000.0

def add_bet(league, home, away, bet_str, stake, odds):
    new_rec = {
        "id": int(datetime.datetime.now().timestamp()),
        "date": datetime.datetime.now().strftime("%m/%d %H:%M"),
        "match": f"[{league}] {home} vs {away}",
        "type": bet_str, "stake": stake, "odds": odds,
        "status": "待定", "profit": 0
    }
    st.session_state.records.append(new_rec)

def settle_bet(bid, res_code):
    for r in st.session_state.records:
        if r['id'] == bid:
            s, o = r['stake'], r['odds']
            p = 0
            if res_code == "贏": p = s * (o - 1)
            elif res_code == "贏半": p = (s * (o - 1)) / 2
            elif res_code == "輸": p = -s
            elif res_code == "輸半": p = -s / 2
            r['status'] = res_code
            r['profit'] = p
            st.session_state.bankroll += p
            return p
    return 0

# ==========================================
# 📱 4. App 介面佈局
# ==========================================

# --- 頂部 HUD (Head-Up Display) ---
total_profit = st.session_state.bankroll - 10000
p_color = "#34D399" if total_profit >= 0 else "#EF4444"
p_sign = "+" if total_profit >= 0 else ""

st.markdown(f"""
<div class="hud-container">
    <div class="hud-title">CURRENT BANKROLL</div>
    <div class="hud-value">${st.session_state.bankroll:,.0f}</div>
    <div class="hud-sub" style="color: {p_color};">TOTAL P/L: {p_sign}${total_profit:,.0f}</div>
</div>
""", unsafe_allow_html=True)

# --- 分頁導航 ---
tab1, tab2, tab3 = st.tabs(["📝 鎖定目標", "⚖️ 確認戰果", "📊 戰情室"])

# === TAB 1: 下注 ===
with tab1:
    # 聯賽與隊伍區塊
    with st.container():
        league = st.selectbox("賽事區域 (League)", list(GLOBAL_DB.keys()))
        teams = GLOBAL_DB[league]
        
        col1, col2 = st.columns(2)
        with col1:
            home = st.selectbox("主隊 (Home)", teams)
        with col2:
            # 自動過濾主隊
            away_opts = [t for t in teams if t != home]
            away = st.selectbox("客隊 (Away)", away_opts)

    st.markdown("---")

    # 玩法區塊 (動態介面)
    m_type = st.radio("戰術選擇", ['獨贏 (1x2)', '讓分 (Handicap)', '大小 (O/U)'], horizontal=True)
    
    bet_content = ""
    
    if m_type == '獨贏 (1x2)':
        sel = st.selectbox("預測方向", ['主勝', '和局', '客勝'])
        bet_content = f"獨贏 [{sel}]"
        
    elif m_type == '讓分 (Handicap)':
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1: target = st.selectbox("對象", ['主隊', '客隊'])
        with c2: sign = st.selectbox("讓/受", ['讓 (-)', '受讓 (+)'])
        with c3: val = st.selectbox("盤口", ['0', '0/0.5', '0.5', '0.5/1', '1', '1.5', '2'])
        bet_content = f"讓分 [{target} {sign} {val}]"
        
    elif m_type == '大小 (O/U)':
        c1, c2 = st.columns(2)
        with c1: side = st.selectbox("方向", ['大 (Over)', '小 (Under)'])
        with c2: val = st.selectbox("球數", ['0.5', '1.5', '2.5', '3.5', '4.5'])
        bet_content = f"大小 [{side} {val}]"

    st.markdown("---")

    # 資金區塊
    c1, c2 = st.columns(2)
    with c1: stake = st.number_input("投入金額", value=1000, step=100)
    with c2: odds = st.number_input("賠率 (Odds)", value=1.90, step=0.01)

    # 送出按鈕 (自定義 Class)
    st.markdown('<div class="primary-btn">', unsafe_allow_html=True)
    if st.button("🚀 LOCK IN BET (鎖定注單)"):
        add_bet(league, home, away, bet_content, stake, odds)
        st.success(f"TARGET ACQUIRED: {home} vs {away}")
    st.markdown('</div>', unsafe_allow_html=True)

# === TAB 2: 結算 ===
with tab2:
    pending = [r for r in st.session_state.records if r['status'] == '待定']
    
    if not pending:
        st.info("NO ACTIVE TARGETS (無進行中賽事)")
    else:
        # 下拉選單選單號
        opts = {f"{r['match']} ({r['type']}) ${r['stake']}": r['id'] for r in pending}
        sel_label = st.selectbox("選擇結算目標", list(opts.keys()))
        bid = opts[sel_label]
        
        st.markdown("### MISSION OUTCOME (賽果)")
        
        # 第一排按鈕
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="win-btn">', unsafe_allow_html=True)
            if st.button("✅ WIN (全贏)"):
                p = settle_bet(bid, "贏")
                st.toast(f"MISSION SUCCESS! +${p}")
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="lose-btn">', unsafe_allow_html=True)
            if st.button("❌ LOSS (全輸)"):
                p = settle_bet(bid, "輸")
                st.toast(f"MISSION FAILED. ${p}")
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            
        # 第二排特殊按鈕
        c3, c4, c5 = st.columns(3)
        if c3.button("💵 贏半"):
            settle_bet(bid, "贏半"); st.rerun()
        if c4.button("🔄 走水"):
            settle_bet(bid, "走水"); st.rerun()
        if c5.button("💸 輸半"):
            settle_bet(bid, "輸半"); st.rerun()

# === TAB 3: 報表 ===
with tab3:
    if len(st.session_state.records) > 0:
        # 計算數據
        equity = [10000]
        dates = ["Start"]
        curr = 10000
        wins = 0
        total_settled = 0
        
        for r in st.session_state.records:
            if r['status'] != '待定':
                curr += r['profit']
                equity.append(curr)
                dates.append(r['date'])
                total_settled += 1
                if r['profit'] > 0: wins += 1
        
        win_rate = (wins / total_settled * 100) if total_settled > 0 else 0
        
        # 顯示指標
        c1, c2, c3 = st.columns(3)
        c1.metric("Win Rate", f"{win_rate:.1f}%")
        c2.metric("Total Trades", f"{total_settled}")
        c3.metric("ROI", f"{(curr-10000)/10000*100:.1f}%")
        
        # 圖表
        chart_data = pd.DataFrame({'Equity': equity}, index=dates)
        st.line_chart(chart_data)
        
        # 歷史表格
        st.markdown("### 📜 Mission Log")
        df = pd.DataFrame(st.session_state.records)
        st.dataframe(df[['date', 'match', 'type', 'status', 'profit']], use_container_width=True)
    else:
        st.write("Awaiting Data...")


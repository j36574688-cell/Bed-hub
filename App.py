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
    initial_sidebar_state="collapsed" # 預設摺疊側邊欄，保持主畫面乾淨
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
    
    /* 側邊欄樣式 */
    [data-testid="stSidebar"] {
        background-color: #111827;
        border-right: 1px solid #374151;
    }
    
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🌍 2. 資料庫 (完整版)
# ==========================================
GLOBAL_DB = {
    "英超 (Premier League)": ["曼城", "兵工廠", "利物浦", "阿斯頓維拉", "熱刺", "切爾西", "紐卡索聯", "曼聯", "西漢姆聯", "布萊頓", "伯恩茅斯", "富勒姆", "狼隊", "艾佛頓", "布倫特福德", "諾丁漢森林", "萊斯特城", "伊普斯維奇", "南安普頓", "水晶宮"],
    "西甲 (La Liga)": ["皇家馬德里", "巴塞隆納", "赫羅納", "馬德里競技", "畢爾包", "皇家社會", "皇家貝提斯", "維拉利爾", "瓦倫西亞", "阿拉維斯", "奧薩蘇納", "赫塔費", "塞爾塔", "塞維亞", "馬約卡", "拉斯帕爾馬斯", "巴列卡諾", "萊加內斯", "瓦拉多利德", "西班牙人"],
    "德甲 (Bundesliga)": ["勒沃庫森", "斯圖加特", "拜仁慕尼黑", "萊比錫RB", "多特蒙德", "法蘭克福", "霍芬海姆", "海登海姆", "不萊梅", "弗萊堡", "奧格斯堡", "沃夫斯堡", "美因茨", "慕尼黑格拉德巴赫", "柏林聯", "波鴻", "聖保利", "基爾霍爾斯泰因"],
    "義甲 (Serie A)": ["國際米蘭", "AC米蘭", "尤文圖斯", "亞特蘭大", "波隆那", "羅馬", "拉齊奧", "佛羅倫提那", "拿坡里", "都靈", "熱那亞", "蒙扎", "維羅納", "萊切", "烏迪內斯", "卡利亞里", "恩波利", "帕爾馬", "科莫", "威尼斯"],
    "法甲 (Ligue 1)": ["巴黎聖日耳曼", "摩納哥", "布雷斯特", "里爾", "尼斯", "里昂", "朗斯", "馬賽", "蘭斯", "雷恩", "土魯斯", "蒙彼利埃", "史特拉斯堡", "南特", "勒阿弗爾", "歐塞爾", "昂熱", "聖艾蒂安"],
    "中超 (CSL)": ["上海海港", "上海申花", "成都蓉城", "北京國安", "山東泰山", "天津津門虎", "浙江隊", "河南隊", "長春亞泰", "青島西海岸", "青島海牛", "深圳新鵬城", "武漢三鎮", "滄州雄獅", "雲南玉昆", "大連英博"],
    "日職 (J1 League)": ["神戶勝利船", "橫濱水手", "廣島三箭", "浦和紅鑽", "鹿島鹿角", "名古屋鯨魚", "福岡黃蜂", "川崎前鋒", "大阪櫻花", "新潟天鵝", "FC東京", "札幌岡薩多", "京都不死鳥", "鳥栖砂岩", "湘南比馬", "大阪飛腳", "柏雷素爾", "町田澤維亞", "磐田喜悅", "東京綠茵"],
    "美職聯 (MLS)": ["邁阿密國際", "洛杉磯銀河", "LAFC", "哥倫布機員", "辛辛那提", "紐約紅牛", "西雅圖海灣人", "亞特蘭大聯", "奧蘭多城", "多倫多FC", "聖路易城", "費城聯", "休士頓迪納摩", "皇家鹽湖城", "紐約城", "聖地牙哥FC"],
    "英冠 (Championship)": ["里茲聯", "伯恩利", "盧頓", "謝菲爾德聯", "西布朗", "諾維奇", "考文垂", "米德斯堡", "赫爾城", "桑德蘭", "沃特福德", "斯旺西", "普雷斯頓", "布里斯托城", "卡迪夫城", "米爾沃", "QPR", "布萊克本", "斯托克城", "謝週三", "普利茅斯", "樸茨茅斯", "德比郡", "牛津聯"],
    "沙烏地職": ["利雅德新月", "利雅德勝利", "吉達國民", "吉達聯合", "達曼協作"],
    "澳職 (A-League)": ["中央海岸水手", "威靈頓鳳凰", "墨爾本勝利", "雪梨FC", "麥克阿瑟FC", "墨爾本城", "西雪梨流浪者", "阿德萊德聯", "布里斯本獅吼", "紐卡索噴射機", "西部聯", "柏斯光榮", "奧克蘭FC"],
    "台甲 (企甲)": ["南市台鋼", "台灣電力", "台中FUTURO", "航源FC", "新北航源", "銘傳大學", "台北維京人", "陽信北競"],
    "葡超": ["體育里斯本", "本菲卡", "波爾圖", "布拉加"],
    "荷甲": ["PSV恩霍芬", "飛耶諾德", "阿賈克斯", "阿爾克馬爾"],
    "土超": ["加拉塔薩雷", "費內巴切", "貝西克塔斯"],
    "英甲": ["伯明翰城", "雷克斯漢姆", "博爾頓"],
    "英乙": ["米爾頓凱恩斯", "唐卡斯特"],
    "西乙": ["卡迪斯", "格拉納達", "希洪競技"],
    "德乙": ["科隆", "漢堡", "杜塞爾多夫"]
}

# ==========================================
# 🧠 3. 邏輯核心
# ==========================================
if 'records' not in st.session_state:
    st.session_state.records = []
if 'bankroll' not in st.session_state:
    st.session_state.bankroll = 10000.0
if 'initial_capital' not in st.session_state:
    st.session_state.initial_capital = 10000.0

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
# ⚙️ 4. 側邊欄設定 (Sidebar) - 新增功能
# ==========================================
with st.sidebar:
    st.header("⚙️ 系統設定 (System)")
    
    st.markdown("### 💰 資金管理")
    new_capital = st.number_input("設定目前本金", value=float(st.session_state.bankroll), step=1000.0)
    
    if st.button("💾 更新本金"):
        st.session_state.bankroll = new_capital
        st.session_state.initial_capital = new_capital # 重設基準
        st.toast(f"本金已更新為 ${new_capital:,.0f}", icon="✅")
        st.rerun()
        
    st.divider()
    
    st.markdown("### 🗑️ 資料管理")
    if st.button("⚠️ 清空所有紀錄", type="primary"):
        st.session_state.records = []
        st.session_state.bankroll = 10000.0
        st.toast("系統已重置", icon="🔄")
        st.rerun()
    
    st.caption("Sniper Bet Pro v3.0")

# ==========================================
# 📱 5. App 主介面佈局
# ==========================================

# --- 頂部 HUD ---
# 計算相對於初始本金的盈虧
total_profit = st.session_state.bankroll - st.session_state.initial_capital
p_color = "#34D399" if total_profit >= 0 else "#EF4444"
p_sign = "+" if total_profit >= 0 else ""

st.markdown(f"""
<div class="hud-container">
    <div class="hud-title">CURRENT BANKROLL</div>
    <div class="hud-value">${st.session_state.bankroll:,.0f}</div>
    <div class="hud-sub" style="color: {p_color};">PROFIT: {p_sign}${total_profit:,.0f}</div>
</div>
""", unsafe_allow_html=True)

# --- 分頁導航 ---
tab1, tab2, tab3 = st.tabs(["📝 鎖定目標", "⚖️ 確認戰果", "📊 戰情室"])

# === TAB 1: 下注 ===
with tab1:
    with st.container():
        league = st.selectbox("賽事區域 (League)", list(GLOBAL_DB.keys()))
        teams = GLOBAL_DB[league]
        
        col1, col2 = st.columns(2)
        with col1: home = st.selectbox("主隊 (Home)", teams)
        with col2: 
            away_opts = [t for t in teams if t != home]
            away = st.selectbox("客隊 (Away)", away_opts)

    st.markdown("---")

    m_type = st.radio("戰術選擇", ['獨贏 (1x2)', '讓分 (Handicap)', '大小 (O/U)'], horizontal=True)
    
    bet_content = ""
    if m_type == '獨贏 (1x2)':
        sel = st.selectbox("預測方向", ['主勝', '和局', '客勝'])
        bet_content = f"獨贏 [{sel}]"
    elif m_type == '讓分 (Handicap)':
        c1, c2, c3 = st.columns([1, 1, 1])
        with c1: target = st.selectbox("對象", ['主隊', '客隊'])
        with c2: sign = st.selectbox("讓/受", ['讓 (-)', '受讓 (+)'])
        with c3: val = st.selectbox("盤口", ['0', '0/0.5', '0.5', '0.5/1', '1', '1.5', '2', '2.5', '3'])
        bet_content = f"讓分 [{target} {sign} {val}]"
    elif m_type == '大小 (O/U)':
        c1, c2 = st.columns(2)
        with c1: side = st.selectbox("方向", ['大 (Over)', '小 (Under)'])
        with c2: val = st.selectbox("球數", ['0.5', '1.5', '2.5', '3.5', '4.5', '5.5', '6.5'])
        bet_content = f"大小 [{side} {val}]"

    st.markdown("---")

    c1, c2 = st.columns(2)
    with c1: stake = st.number_input("投入金額", value=1000, step=100)
    with c2: odds = st.number_input("賠率 (Odds)", value=1.90, step=0.01)

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
        opts = {f"{r['match']} ({r['type']}) ${r['stake']}": r['id'] for r in pending}
        sel_label = st.selectbox("選擇結算目標", list(opts.keys()))
        bid = opts[sel_label]
        
        st.markdown("### MISSION OUTCOME (賽果)")
        
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
        equity = [st.session_state.initial_capital] # 使用設定的本金為起點
        dates = ["Start"]
        curr = st.session_state.initial_capital
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
        roi = ((curr - st.session_state.initial_capital) / st.session_state.initial_capital * 100)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Win Rate", f"{win_rate:.1f}%")
        c2.metric("Total Trades", f"{total_settled}")
        c3.metric("ROI", f"{roi:.1f}%")
        
        chart_data = pd.DataFrame({'Equity': equity}, index=dates)
        st.line_chart(chart_data)
        
        st.markdown("### 📜 Mission Log")
        df = pd.DataFrame(st.session_state.records)
        st.dataframe(df[['date', 'match', 'type', 'status', 'profit']], use_container_width=True)
    else:
        st.write("Awaiting Data...")

import streamlit as st
import json
import os
import pandas as pd
import datetime
import uuid

# ==========================================
# ⚙️ 1. 頁面配置與戰術風格 CSS
# ==========================================
st.set_page_config(
    page_title="SNIPER BETTING PRO",
    page_icon="🎯",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    /* 全局背景色 - 深灰戰術黑 */
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    
    /* 頂部 HUD 儀表板 */
    .hud-container {
        background: linear-gradient(90deg, #1F2937 0%, #111827 100%);
        border: 1px solid #374151;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        text-align: center;
        border-left: 5px solid #00C853;
    }
    .hud-title { font-size: 12px; color: #9CA3AF; letter-spacing: 1px; text-transform: uppercase; }
    .hud-value { font-size: 32px; font-weight: 800; color: #FFFFFF; font-family: 'Courier New', monospace; }
    .hud-sub { font-size: 14px; color: #34D399; font-weight: bold; }
    
    /* 介面優化 */
    .stSelectbox label, .stNumberInput label, .stRadio label, .stTextInput label { color: #E5E7EB !important; font-weight: bold; }
    .stButton > button { width: 100%; border-radius: 8px; height: 50px; font-weight: bold; border: none; transition: all 0.2s; }
    
    /* 按鈕色系 */
    .primary-btn button { background-color: #2563EB !important; color: white !important; box-shadow: 0 4px 14px 0 rgba(37, 99, 235, 0.39); }
    .win-btn button { background-color: #059669 !important; color: white !important; }
    .lose-btn button { background-color: #DC2626 !important; color: white !important; }
    .push-btn button { background-color: #D97706 !important; color: white !important; }
    
    /* 側邊欄 */
    [data-testid="stSidebar"] { background-color: #111827; border-right: 1px solid #374151; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔒 2. GLOBAL_DB 資料庫 (定版不更動)
# ==========================================
GLOBAL_DB = {
    "[英] 英超 (Premier League)": ["曼城", "兵工廠", "利物浦", "阿斯頓維拉", "熱刺", "切爾西", "紐卡索聯", "曼聯", "西漢姆聯", "水晶宮", "布萊頓", "伯恩茅斯", "富勒姆", "狼隊", "艾佛頓", "布倫特福德", "諾丁漢森林", "萊斯特城", "伊普斯維奇", "南安普頓"],
    "[英] 英冠 (Championship)": ["里茲聯", "伯恩利", "盧頓", "謝菲爾德聯", "西布朗", "諾維奇", "考文垂", "米德斯堡", "赫爾城", "桑德蘭", "沃特福德", "斯旺西", "普雷斯頓", "布里斯托城", "卡迪夫城", "米爾沃", "QPR (女王公園)", "布萊克本", "斯托克城", "謝週三", "普利茅斯", "樸茨茅斯", "德比郡", "牛津聯"],
    "[英] 英甲 (League One)": ["伯明翰城", "雷克斯漢姆", "博爾頓", "彼得堡聯", "哈德斯菲爾德", "羅瑟漢姆", "巴恩斯利", "林肯城", "布萊克浦", "斯蒂文尼奇", "雷丁", "維根競技", "韋康比流浪者", "雷頓東方", "布里斯托流浪", "北安普頓", "埃克塞特城", "什魯斯伯里", "克勞利鎮", "劍橋聯", "柏頓", "曼斯菲爾德", "斯托克港", "伯頓"],
    "[英] 英乙 (League Two)": ["米爾頓凱恩斯 (MK Dons)", "唐卡斯特", "克魯", "維爾港", "卡萊爾聯", "切爾滕漢姆", "福利特伍德", "布拉德福德", "吉林漢姆", "沃爾索爾", "AFC溫布頓", "哈洛格特", "特蘭米爾", "阿克寧頓", "索爾福德城", "史雲頓", "紐波特郡", "莫克姆", "科爾切斯特", "格里姆斯比", "切斯特菲爾德", "布羅姆利", "哈特柏爾", "瑟頓聯"],
    "[歐] 西甲 (La Liga)": ["皇家馬德里", "巴塞隆納", "赫羅納", "馬德里競技", "畢爾包", "皇家社會", "皇家貝提斯", "維拉利爾", "瓦倫西亞", "阿拉維斯", "奧薩蘇納", "赫塔費", "塞爾塔", "塞維亞", "馬約卡", "拉斯帕爾馬斯", "巴列卡諾", "萊加內斯", "瓦拉多利德", "西班牙人"],
    "[歐] 德甲 (Bundesliga)": ["勒沃庫森", "斯圖加特", "拜仁慕尼黑", "萊比錫RB", "多特蒙德", "法蘭克福", "霍芬海姆", "海登海姆", "不萊梅", "弗萊堡", "奧格斯堡", "沃夫斯堡", "美因茨", "慕尼黑格拉德巴赫", "柏林聯", "波鴻", "聖保利", "基爾霍爾斯泰因"],
    "[歐] 義甲 (Serie A)": ["國際米蘭", "AC米蘭", "尤文圖斯", "亞特蘭大", "波隆那", "羅馬", "拉齊奧", "佛羅倫提那", "拿坡里", "都靈", "熱那亞", "蒙扎", "維羅納", "萊切", "烏迪內斯", "卡利亞里", "恩波利", "帕爾馬", "科莫", "威尼斯"],
    "[歐] 法甲 (Ligue 1)": ["巴黎聖日耳曼", "摩納哥", "布雷斯特", "里爾", "尼斯", "里昂", "朗斯", "馬賽", "蘭斯", "雷恩", "土魯斯", "蒙彼利埃", "史特拉斯堡", "南特", "勒阿弗爾", "歐塞爾", "昂熱", "聖艾蒂安"],
    "[美] 巴西甲 (Série A)": ["博塔弗戈", "帕梅拉斯", "弗拉門戈", "福塔雷薩", "國際體育會", "聖保羅", "科林蒂安", "巴伊亞", "克魯塞羅", "華斯科", "維多利亞", "米內羅競技", "佛魯米嫩塞", "格雷米奧", "尤文圖德", "布拉甘蒂諾", "巴拉納競技", "克里西烏馬", "桑托斯 (Santos)", "米拉索爾 (Mirassol)"],
    "[美] 阿甲 (Primera)": ["河床", "博卡青年", "競賽會", "獨立隊", "聖洛倫索", "薩斯菲爾德", "塔勒瑞斯", "學生隊", "防衛者", "颶風", "阿根廷青年", "紐維爾舊生", "羅薩里奧中央", "拉努斯", "班菲爾德", "老虎競技", "普拉滕斯", "圖庫曼競技", "科爾多瓦", "貝爾格拉諾", "高多爾", "聯合隊", "巴拉卡斯", "利斯特拉", "里瓦達維亞", "薩蘭迪兵工廠", "科隆", "阿爾多希維"],
    "[美] 美職聯 (MLS)": ["邁阿密國際", "洛杉磯銀河", "LAFC", "哥倫布機員", "辛辛那提", "紐約紅牛", "西雅圖海灣人", "亞特蘭大聯", "奧蘭多城", "多倫多FC", "聖路易城", "費城聯", "休士頓迪納摩", "皇家鹽湖城", "紐約城", "納什維爾", "新英格蘭革命", "溫哥華白浪", "FC達拉斯", "堪薩斯城", "明尼蘇達聯", "波特蘭伐木者", "聖荷西地震", "科羅拉多急流", "奧斯汀FC", "夏洛特FC", "芝加哥火焰", "蒙特婁衝擊", "DC United (華盛頓聯)", "聖地牙哥FC"],
    "[歐] 葡超 (Primeira)": ["體育里斯本", "本菲卡", "波爾圖", "布拉加", "吉馬良斯", "莫雷拉人", "阿羅卡", "法馬利康", "卡薩皮亞", "法倫斯", "里奧艾維", "吉爾維森特", "艾斯托里爾", "艾馬泰", "博阿維斯塔", "聖克拉拉", "馬德拉國民", "AVS"],
    "[歐] 荷甲 (Eredivisie)": ["PSV恩霍芬", "飛耶諾德", "特溫特", "阿爾克馬爾", "阿賈克斯", "奈梅亨", "烏德勒支", "鹿特丹斯巴達", "前進之鷹", "幸運薛達", "海倫芬", "茲沃勒", "阿梅爾城", "荷拉克勒斯", "華域克", "威廉二世", "格羅寧根", "布雷達"],
    "[歐] 土超 (Süper Lig)": ["加拉塔薩雷", "費內巴切", "特拉布宗", "貝西克塔斯", "卡斯帕薩", "錫瓦斯", "阿蘭亞", "里澤", "巴沙克舒希", "安塔利亞", "加濟安泰普", "阿達納", "薩姆松", "凱塞利", "哈塔伊", "科尼亞", "安卡拉古庫", "伊尤斯堡", "哥茲塔比"],
    "[歐] 德乙 (2. Bundesliga)": ["科隆", "達姆施塔特", "杜塞爾多夫", "漢堡", "卡爾斯魯厄", "漢諾威96", "帕德博恩", "菲爾特", "柏林赫塔", "沙爾克04", "埃弗斯堡", "紐倫堡", "馬格德堡", "布倫瑞克", "凱澤斯勞滕", "烏爾姆", "明斯特普魯士", "雷根斯堡"],
    "[歐] 西乙 (Segunda)": ["卡迪斯", "格拉納達", "阿爾梅里亞", "奧維耶多", "桑坦德競技", "希洪競技", "埃瓦爾", "萊萬特", "布爾戈斯", "費羅爾", "埃爾切", "特內里費", "阿爾巴塞特", "卡塔赫納", "薩拉戈薩", "埃登斯", "韋斯卡", "米蘭德斯", "拉科魯尼亞", "卡斯特利翁", "馬拉加", "科爾多瓦"],
    "[亞] 中超 (CSL)": ["上海海港", "上海申花", "成都蓉城", "北京國安", "山東泰山", "天津津門虎", "浙江隊", "河南隊", "長春亞泰", "青島西海岸", "青島海牛", "深圳新鵬城", "武漢三鎮", "滄州雄獅", "雲南玉昆", "大連英博"],
    "[亞] 日職 (J1 League)": ["神戶勝利船", "橫濱水手", "廣島三箭", "浦和紅鑽", "鹿島鹿角", "名古屋鯨魚", "福岡黃蜂", "川崎前鋒", "大阪櫻花", "新潟天鵝", "FC東京", "札幌岡薩多", "京都不死鳥", "鳥栖砂岩", "湘南比馬", "大阪飛腳", "柏雷素爾", "町田澤維亞", "磐田喜悅", "東京綠茵"],
    "[亞] 韓職 (K League 1)": ["蔚山HD", "浦項製鐵", "光州FC", "全北現代", "仁川聯", "大邱FC", "FC首爾", "大田韓亞市民", "濟州聯", "江原FC", "水原FC", "金泉尚武"],
    "[亞] 沙烏地職 (Saudi Pro)": ["利雅德新月", "利雅德勝利", "吉達國民", "吉達聯合", "達曼協作", "利雅德青年", "阿爾法特", "阿爾費哈", "達馬克", "阿爾卡利傑", "阿爾拉德", "阿爾瓦赫達", "阿爾阿赫杜德", "阿爾利雅德", "卡迪西亞", "阿爾奧魯巴", "阿爾科洛", "阿爾泰"],
    "[亞] 澳職 (A-League)": ["中央海岸水手", "威靈頓鳳凰", "墨爾本勝利", "雪梨FC", "麥克阿瑟FC", "墨爾本城", "西雪梨流浪者", "阿德萊德聯", "布里斯本獅吼", "紐卡索噴射機", "西部聯", "柏斯光榮", "奧克蘭FC"],
    "[亞] 台甲 (企甲)": ["南市台鋼", "台灣電力", "台中FUTURO", "航源FC", "新北航源", "銘傳大學", "台北維京人", "陽信北競"]
}

# ==========================================
# 💾 3. 永續資料管理 (Persistence)
# ==========================================
DATA_FILE = "bets.json"

def load_data():
    """啟動時載入資料"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('records', []), data.get('bankroll', 10000.0), data.get('initial', 10000.0)
        except:
            pass
    return [], 10000.0, 10000.0

def save_data():
    """變更時存入硬碟"""
    data = {
        'records': st.session_state.records,
        'bankroll': st.session_state.bankroll,
        'initial': st.session_state.initial_capital
    }
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 初始化 Session State
if 'records' not in st.session_state:
    recs, bank, init_cap = load_data()
    st.session_state.records = recs
    st.session_state.bankroll = bank
    st.session_state.initial_capital = init_cap

# ==========================================
# 🧠 4. 核心邏輯 (Logic)
# ==========================================

def add_bet(league, home, away, bet_str, stake, odds):
    clean_league = league.split('] ')[1].split(' (')[0] if ']' in league else league
    
    # [NEW] 使用 UUID 確保唯一性
    # [NEW] 使用 isoformat 儲存標準時間
    new_rec = {
        "id": str(uuid.uuid4()), 
        "date": datetime.datetime.now().isoformat(),
        "match": f"[{clean_league}] {home} vs {away}",
        "type": bet_str,
        "stake": stake,
        "odds": odds,
        "status": "待定",
        "profit": 0
    }
    st.session_state.records.append(new_rec)
    save_data() # [NEW] 自動存檔

def settle_bet(bid, res_code):
    for r in st.session_state.records:
        if r['id'] == bid:
            s, o = float(r['stake']), float(r['odds'])
            p = 0.0
            
            # [NEW] 走水邏輯 (Push)
            if res_code == "贏": p = s * (o - 1)
            elif res_code == "贏半": p = (s * (o - 1)) / 2
            elif res_code == "輸": p = -s
            elif res_code == "輸半": p = -s / 2
            elif res_code == "走水": p = 0.0 
            
            r['status'] = res_code
            r['profit'] = p
            # [NEW] 記錄結算時間，用於報表排序
            r['settled_at'] = datetime.datetime.now().isoformat()
            
            st.session_state.bankroll += p
            save_data() # [NEW] 自動存檔
            return p
    return 0.0

# ==========================================
# ⚙️ 5. 側邊欄 (資料管理)
# ==========================================
with st.sidebar:
    st.header("⚙️ 總部指令 (HQ)")
    
    st.markdown("### 💰 資金修正")
    new_capital = st.number_input("校正本金", value=float(st.session_state.bankroll), step=1000.0)
    if st.button("💾 更新水位"):
        st.session_state.bankroll = new_capital
        st.session_state.initial_capital = new_capital
        save_data()
        st.toast(f"本金已更新為 ${new_capital:,.0f}", icon="✅")
        st.rerun()

    st.divider()

    st.markdown("### 📂 資料傳輸")
    
    # [NEW] 匯出功能
    st.download_button(
        label="📥 匯出備份 (JSON)",
        data=json.dumps({'records': st.session_state.records, 'bankroll': st.session_state.bankroll}, ensure_ascii=False, indent=2),
        file_name=f"sniper_backup_{datetime.datetime.now().strftime('%Y%m%d')}.json",
        mime="application/json"
    )

    # [NEW] 匯入功能
    uploaded_file = st.file_uploader("📤 匯入紀錄", type=['json'])
    if uploaded_file is not None:
        try:
            data = json.load(uploaded_file)
            st.session_state.records = data.get('records', [])
            st.session_state.bankroll = data.get('bankroll', 10000.0)
            save_data()
            st.success("資料匯入成功！")
            st.rerun()
        except:
            st.error("檔案格式錯誤")

    st.divider()

    # [NEW] 安全重置 (需勾選確認)
    st.markdown("### 🚨 危險區域")
    confirm_reset = st.checkbox("我確認要清除所有資料")
    if st.button("⚠️ 初始化系統", type="primary", disabled=not confirm_reset):
        # [NEW] 備份機制 (Undo)
        st.session_state.last_backup = st.session_state.records.copy()
        
        st.session_state.records = []
        st.session_state.bankroll = 10000.0
        st.session_state.initial_capital = 10000.0
        save_data()
        st.toast("系統已重置", icon="💥")
        st.rerun()
        
    # [NEW] 還原按鈕
    if 'last_backup' in st.session_state and st.session_state.last_backup:
        if st.button("↩️ 復原刪除"):
            st.session_state.records = st.session_state.last_backup
            save_data()
            del st.session_state.last_backup
            st.success("資料已復原")
            st.rerun()

# ==========================================
# 📱 6. 主畫面 (HUD & Tabs)
# ==========================================
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

    # [NEW] 即時預覽 & 驗證
    potential_win = stake * (odds - 1)
    st.caption(f"預估獲利: :green[+${potential_win:,.0f}]")

    st.markdown('<div class="primary-btn">', unsafe_allow_html=True)
    
    if stake <= 0 or odds <= 1.0:
        st.error("⚠️ 請輸入有效的金額與賠率")
    else:
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
        # [NEW] 顯示優化：加入日期
        opts = {}
        for r in pending:
            d_str = pd.to_datetime(r['date']).strftime("%m/%d")
            label = f"[{d_str}] {r['match']} ({r['type']}) ${r['stake']}"
            opts[label] = r['id']
            
        sel_label = st.selectbox("選擇結算目標", list(opts.keys()))
        bid = opts[sel_label]
        
        st.markdown("### MISSION OUTCOME")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="win-btn">', unsafe_allow_html=True)
            if st.button("✅ WIN (全贏)"):
                settle_bet(bid, "贏"); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="lose-btn">', unsafe_allow_html=True)
            if st.button("❌ LOSS (全輸)"):
                settle_bet(bid, "輸"); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        
        # [NEW] 加入走水按鈕
        c3, c4, c5 = st.columns(3)
        if c3.button("💵 贏半"): settle_bet(bid, "贏半"); st.rerun()
        with c4:
             st.markdown('<div class="push-btn">', unsafe_allow_html=True)
             if st.button("🔄 走水"): settle_bet(bid, "走水"); st.rerun()
             st.markdown('</div>', unsafe_allow_html=True)
        if c5.button("💸 輸半"): settle_bet(bid, "輸半"); st.rerun()

# === TAB 3: 報表 ===
with tab3:
    # [NEW] 篩選器
    all_leagues = sorted(list(set([r['match'].split(']')[0].replace('[', '') for r in st.session_state.records]))) if st.session_state.records else []
    filter_lg = st.selectbox("Filter League", ["All"] + all_leagues)
    
    filtered_records = st.session_state.records
    if filter_lg != "All":
        filtered_records = [r for r in filtered_records if filter_lg in r['match']]

    if len(filtered_records) > 0:
        # [NEW] 時間序列修正邏輯
        settled_recs = [r for r in filtered_records if r['status'] != '待定']
        
        if settled_recs:
            df_settled = pd.DataFrame(settled_recs)
            # 優先使用結算時間，若無則用下注時間
            time_col = 'settled_at' if 'settled_at' in df_settled.columns else 'date'
            df_settled[time_col] = pd.to_datetime(df_settled[time_col])
            df_settled = df_settled.sort_values(time_col)
            
            equity = [st.session_state.initial_capital]
            dates = ["Start"]
            
            for _, row in df_settled.iterrows():
                equity.append(equity[-1] + row['profit'])
                # 簡化日期顯示
                dates.append(row[time_col].strftime("%m/%d"))
            
            chart_data = pd.DataFrame({'Equity': equity}, index=dates)
            st.line_chart(chart_data)
            
            # 計算數據
            wins = (df_settled['profit'] > 0).sum()
            total = len(df_settled)
            win_rate = (wins / total * 100) if total > 0 else 0
            curr_equity = equity[-1]
            roi = ((curr_equity - st.session_state.initial_capital) / st.session_state.initial_capital * 100)

            c1, c2, c3 = st.columns(3)
            c1.metric("Win Rate", f"{win_rate:.1f}%")
            c2.metric("Trades", f"{total}")
            c3.metric("ROI", f"{roi:.1f}%")
        else:
            st.info("尚未有結算紀錄")

        st.markdown("### 📜 Mission Log")
        # 顯示所有紀錄 (含待定)
        df_all = pd.DataFrame(filtered_records)
        # 格式化顯示
        df_show = df_all[['date', 'match', 'type', 'status', 'profit']].copy()
        df_show['date'] = pd.to_datetime(df_show['date']).dt.strftime("%m/%d %H:%M")
        st.dataframe(df_show, use_container_width=True)
    else:
        st.write("Awaiting Data...")

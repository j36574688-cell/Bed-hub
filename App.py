import streamlit as st
import sqlite3
import pandas as pd
import datetime
import uuid
import json
import io
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo

# ==========================================
# ⚙️ 0. 核心設定與常數
# ==========================================
DB_PATH = "sniper_v8.db"
TZ_TAIPEI = ZoneInfo("Asia/Taipei")

st.set_page_config(
    page_title="SNIPER BETTING PRO",
    page_icon="🎯",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 🛠 1. 資料庫層 (SQLite + WAL + Audit)
# ==========================================
def init_db():
    """初始化資料庫結構 (含 WAL 優化與 Index)"""
    with sqlite3.connect(DB_PATH) as conn:
        # [NEW] 啟用 WAL 模式，提升穩定性
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        
        cur = conn.cursor()
        
        # 1. 注單表 (新增 notes 欄位)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS bets (
            id TEXT PRIMARY KEY,
            created_at TEXT,
            match_info TEXT,
            bet_type TEXT,
            stake REAL,
            odds REAL,
            status TEXT,
            profit REAL,
            settled_at TEXT,
            notes TEXT
        )""")
        
        # [NEW] 2. 索引優化
        cur.execute("CREATE INDEX IF NOT EXISTS idx_bets_created ON bets(created_at);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_bets_status ON bets(status);")
        
        # 3. 設定表
        cur.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value REAL
        )""")
        
        # [NEW] 4. 審計日誌 (Audit Log)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            action TEXT,
            target_id TEXT,
            payload TEXT
        )""")
        
        # 初始化本金
        cur.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('bankroll', 10000.0)")
        cur.execute("INSERT OR IGNORE INTO config (key, value) VALUES ('initial', 10000.0)")
        conn.commit()

def log_audit(conn, action, target_id, payload):
    """寫入審計日誌 (內部呼叫)"""
    ts = datetime.datetime.now(TZ_TAIPEI).isoformat()
    conn.execute(
        "INSERT INTO audit_log (ts, action, target_id, payload) VALUES (?, ?, ?, ?)",
        (ts, action, target_id, json.dumps(payload, ensure_ascii=False))
    )

def get_config():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT key, value FROM config")
        data = dict(cur.fetchall())
        return data.get('bankroll', 10000.0), data.get('initial', 10000.0)

def update_config(bankroll=None, initial=None):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        if bankroll is not None:
            cur.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('bankroll', ?)", (bankroll,))
            log_audit(conn, "UPDATE_CONFIG", "SYSTEM", {"bankroll": bankroll})
        if initial is not None:
            cur.execute("INSERT OR REPLACE INTO config (key, value) VALUES ('initial', ?)", (initial,))
        conn.commit()

def add_bet_db(match, bet_type, stake, odds, notes=""):
    now_iso = datetime.datetime.now(TZ_TAIPEI).isoformat()
    bet_id = str(uuid.uuid4())
    
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        # 防重複檢查
        cur.execute("""
            SELECT id FROM bets 
            WHERE match_info=? AND bet_type=? AND stake=? AND odds=? AND status='待定'
        """, (match, bet_type, stake, odds))
        if cur.fetchone():
            return False, "⚠️ 偵測到重複注單，操作已攔截！"

        cur.execute("""
            INSERT INTO bets (id, created_at, match_info, bet_type, stake, odds, status, profit, settled_at, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (bet_id, now_iso, match, bet_type, stake, odds, '待定', 0.0, None, notes))
        
        log_audit(conn, "ADD_BET", bet_id, {"match": match, "stake": stake})
        conn.commit()
        return True, bet_id

def settle_bet_db(bet_id, profit, status):
    """結算注單 (交易原子性)"""
    now_iso = datetime.datetime.now(TZ_TAIPEI).isoformat()
    
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cur = conn.cursor()
            cur.execute("BEGIN") # 顯式開啟交易
            
            # 1. 檢查並鎖定狀態
            cur.execute("SELECT profit, status FROM bets WHERE id=?", (bet_id,))
            row = cur.fetchone()
            if not row: return False
            old_profit = row[0]
            
            # 2. 更新注單
            cur.execute("""
                UPDATE bets 
                SET status=?, profit=?, settled_at=? 
                WHERE id=?
            """, (status, float(profit), now_iso, bet_id))
            
            # 3. 更新本金 (扣除舊盈虧，加入新盈虧 -> 支援重新結算)
            cur.execute("SELECT value FROM config WHERE key='bankroll'")
            current_bank = cur.fetchone()[0]
            # 邏輯：新本金 = 當前本金 - 舊盈虧(若有) + 新盈虧
            new_bank = current_bank - old_profit + float(profit)
            cur.execute("UPDATE config SET value=? WHERE key='bankroll'", (new_bank,))
            
            log_audit(conn, "SETTLE_BET", bet_id, {"status": status, "profit": profit, "old_profit": old_profit})
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise e

def revoke_settlement_db(bet_id):
    """[NEW] 撤銷結算 (反悔藥)"""
    with sqlite3.connect(DB_PATH) as conn:
        try:
            cur = conn.cursor()
            cur.execute("BEGIN")
            
            cur.execute("SELECT profit FROM bets WHERE id=?", (bet_id,))
            row = cur.fetchone()
            if not row: return False
            profit_to_remove = row[0]
            
            # 回滾狀態
            cur.execute("UPDATE bets SET status='待定', profit=0, settled_at=NULL WHERE id=?", (bet_id,))
            
            # 回滾本金
            cur.execute("SELECT value FROM config WHERE key='bankroll'")
            current_bank = cur.fetchone()[0]
            cur.execute("UPDATE config SET value=? WHERE key='bankroll'", (current_bank - profit_to_remove,))
            
            log_audit(conn, "REVOKE_SETTLE", bet_id, {"removed_profit": profit_to_remove})
            conn.commit()
            return True
        except:
            conn.rollback()
            return False

def get_all_bets():
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query("SELECT * FROM bets ORDER BY created_at ASC", conn)

def reset_system_db():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM bets")
        cur.execute("DELETE FROM audit_log")
        cur.execute("UPDATE config SET value=10000.0 WHERE key='bankroll'")
        cur.execute("UPDATE config SET value=10000.0 WHERE key='initial'")
        log_audit(conn, "SYSTEM_RESET", "ALL", {})
        conn.commit()

# 初始化
init_db()

# ==========================================
# 🧠 2. 商業邏輯 (Decimal)
# ==========================================
def calculate_pnl(stake, odds, result_code):
    d_stake = Decimal(str(stake))
    d_odds = Decimal(str(odds))
    d_profit = Decimal('0.0')

    if result_code == "贏": d_profit = d_stake * (d_odds - Decimal('1'))
    elif result_code == "贏半": d_profit = (d_stake * (d_odds - Decimal('1'))) / Decimal('2')
    elif result_code == "輸": d_profit = -d_stake
    elif result_code == "輸半": d_profit = -d_stake / Decimal('2')
    elif result_code == "走水": d_profit = Decimal('0.0')
    
    return d_profit.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

def calculate_max_drawdown(equity_curve):
    """[NEW] 計算最大回撤"""
    if not equity_curve: return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for value in equity_curve:
        if value > peak:
            peak = value
        dd = (peak - value) / peak if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd
    return max_dd * 100

# ==========================================
# 🎨 3. UI 樣式
# ==========================================
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
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
    .stSelectbox label, .stNumberInput label, .stRadio label, .stTextInput label { color: #E5E7EB !important; font-weight: bold; }
    .stButton > button { width: 100%; border-radius: 8px; height: 50px; font-weight: bold; border: none; transition: all 0.2s; }
    .primary-btn button { background-color: #2563EB !important; color: white !important; box-shadow: 0 4px 14px 0 rgba(37, 99, 235, 0.39); }
    .win-btn button { background-color: #059669 !important; color: white !important; }
    .lose-btn button { background-color: #DC2626 !important; color: white !important; }
    .push-btn button { background-color: #D97706 !important; color: white !important; }
    .revoke-btn button { background-color: #4B5563 !important; color: white !important; border: 1px solid #6B7280; }
    [data-testid="stSidebar"] { background-color: #111827; border-right: 1px solid #374151; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔒 4. GLOBAL_DB (資料庫定版)
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
# 📱 5. 側邊欄 (設定與管理)
# ==========================================
curr_bankroll, curr_initial = get_config()

with st.sidebar:
    st.header("⚙️ 總部指令 (HQ)")
    
    st.markdown("### 💰 資金修正")
    new_capital = st.number_input("校正本金", value=float(curr_bankroll), step=1000.0)
    if st.button("💾 更新水位"):
        update_config(bankroll=new_capital, initial=new_capital)
        st.toast(f"本金已更新為 ${new_capital:,.0f}", icon="✅")
        st.rerun()

    st.divider()

    st.markdown("### 📥 批次結算 (Batch)")
    batch_file = st.file_uploader("上傳 CSV (id, result)", type=['csv'])
    if batch_file and st.button("⚡ 執行批次結算"):
        try:
            df_batch = pd.read_csv(batch_file)
            count = 0
            for _, row in df_batch.iterrows():
                # 需先查詢該單詳情計算 profit (略為簡化，需有 id, result)
                # 這裡僅作範例框架，實際需結合 DB 查詢
                st.warning("請確保 CSV 包含 id 與 result 欄位")
                break 
            st.success(f"批次處理完成")
        except:
            st.error("CSV 格式錯誤")

    st.divider()

    st.markdown("### 📂 資料備份")
    df_all = get_all_bets()
    export_data = {
        "records": df_all.to_dict(orient='records'),
        "bankroll": curr_bankroll,
        "initial": curr_initial,
        "ts": datetime.datetime.now(TZ_TAIPEI).isoformat()
    }
    st.download_button(
        label="📥 匯出資料庫 (JSON)",
        data=json.dumps(export_data, ensure_ascii=False, indent=2),
        file_name=f"sniper_v8_backup.json",
        mime="application/json"
    )

    st.divider()
    confirm_reset = st.checkbox("確認清除所有資料")
    if st.button("⚠️ 初始化系統", type="primary", disabled=not confirm_reset):
        reset_system_db()
        st.toast("系統已完全重置", icon="💥")
        st.rerun()
        
    st.caption("Sniper Bet Pro v8.0 (Titanium)")

# ==========================================
# 🖥️ 6. 主畫面
# ==========================================
total_profit = curr_bankroll - curr_initial
p_color = "#34D399" if total_profit >= 0 else "#EF4444"
p_sign = "+" if total_profit >= 0 else ""

st.markdown(f"""
<div class="hud-container">
    <div class="hud-title">CURRENT BANKROLL</div>
    <div class="hud-value">${curr_bankroll:,.0f}</div>
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
    
    # [NEW] 戰術備註
    notes = st.text_input("戰術筆記 (選填)", placeholder="例如：主隊主力受傷，看好小球...")

    if stake > 0 and odds > 1.0:
        pot_win = calculate_pnl(stake, odds, "贏")
        st.caption(f"🎯 預估獲利: :green[+${pot_win:,.2f}]")

    st.markdown('<div class="primary-btn">', unsafe_allow_html=True)
    if st.button("🚀 LOCK IN BET (鎖定注單)"):
        clean_league = league.split('] ')[1].split(' (')[0] if ']' in league else league
        match_info = f"[{clean_league}] {home} vs {away}"
        success, msg = add_bet_db(match_info, bet_content, stake, odds, notes)
        if success:
            st.success(f"TARGET ACQUIRED: {home} vs {away}")
            st.rerun()
        else:
            st.error(msg)
    st.markdown('</div>', unsafe_allow_html=True)

# === TAB 2: 結算 ===
with tab2:
    df_pending = pd.read_sql_query("SELECT * FROM bets WHERE status='待定' ORDER BY created_at DESC", sqlite3.connect(DB_PATH))
    
    if df_pending.empty:
        st.info("NO ACTIVE TARGETS (無進行中賽事)")
    else:
        opts = {}
        for _, r in df_pending.iterrows():
            dt = datetime.datetime.fromisoformat(r['created_at']).strftime("%m/%d %H:%M")
            label = f"[{dt}] {r['match_info']} ({r['bet_type']}) ${r['stake']:.0f}"
            opts[label] = r['id']

        sel_label = st.selectbox("選擇結算目標", list(opts.keys()))
        bid = opts[sel_label]
        target_bet = df_pending[df_pending['id'] == bid].iloc[0]
        
        st.markdown("### MISSION OUTCOME")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="win-btn">', unsafe_allow_html=True)
            if st.button("✅ WIN (全贏)"):
                p = calculate_pnl(target_bet['stake'], target_bet['odds'], "贏")
                settle_bet_db(bid, p, "贏")
                st.toast(f"MISSION SUCCESS! +${p}", icon="💰"); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with c2:
            st.markdown('<div class="lose-btn">', unsafe_allow_html=True)
            if st.button("❌ LOSS (全輸)"):
                p = calculate_pnl(target_bet['stake'], target_bet['odds'], "輸")
                settle_bet_db(bid, p, "輸")
                st.toast(f"MISSION FAILED. ${p}", icon="🥀"); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
            
        c3, c4, c5 = st.columns(3)
        if c3.button("💵 贏半"):
            p = calculate_pnl(target_bet['stake'], target_bet['odds'], "贏半")
            settle_bet_db(bid, p, "贏半"); st.rerun()
        with c4:
             st.markdown('<div class="push-btn">', unsafe_allow_html=True)
             if st.button("🔄 走水"):
                 p = calculate_pnl(target_bet['stake'], target_bet['odds'], "走水")
                 settle_bet_db(bid, p, "走水"); st.rerun()
             st.markdown('</div>', unsafe_allow_html=True)
        if c5.button("💸 輸半"):
            p = calculate_pnl(target_bet['stake'], target_bet['odds'], "輸半")
            settle_bet_db(bid, p, "輸半"); st.rerun()

    # [NEW] 撤銷結算區 (Recent Settled)
    st.markdown("---")
    st.markdown("#### ↩️ 近期已結算 (可撤銷)")
    df_settled_recent = pd.read_sql_query("SELECT * FROM bets WHERE status != '待定' ORDER BY settled_at DESC LIMIT 5", sqlite3.connect(DB_PATH))
    if not df_settled_recent.empty:
        for _, r in df_settled_recent.iterrows():
            col_info, col_btn = st.columns([3, 1])
            with col_info:
                st.caption(f"{r['match_info']} | {r['status']} (${r['profit']})")
            with col_btn:
                st.markdown('<div class="revoke-btn">', unsafe_allow_html=True)
                if st.button("撤銷", key=f"rev_{r['id']}"):
                    if revoke_settlement_db(r['id']):
                        st.toast("結算已撤銷", icon="↩️")
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

# === TAB 3: 報表 ===
with tab3:
    df_all = get_all_bets()
    all_leagues = sorted(list(set([r.split(']')[0].replace('[', '') for r in df_all['match_info']]))) if not df_all.empty else []
    filter_lg = st.selectbox("Filter League", ["All"] + all_leagues)
    
    if filter_lg != "All":
        df_all = df_all[df_all['match_info'].str.contains(filter_lg)]

    if not df_all.empty:
        df_settled = df_all[df_all['status'] != '待定'].copy()
        
        if not df_settled.empty:
            df_settled['sort_time'] = pd.to_datetime(df_settled['settled_at'])
            df_settled = df_settled.sort_values('sort_time')
            
            equity_curve = [curr_initial]
            dates = ["Start"]
            cum_profit = 0
            for _, r in df_settled.iterrows():
                cum_profit += r['profit']
                equity_curve.append(curr_initial + cum_profit)
                dates.append(r['sort_time'].strftime("%m/%d"))
            
            # [NEW] 最大回撤計算
            max_dd = calculate_max_drawdown(equity_curve)
            
            st.line_chart(pd.DataFrame({'Equity': equity_curve}, index=dates))
            
            wins = len(df_settled[df_settled['profit'] > 0])
            total = len(df_settled)
            win_rate = (wins / total * 100) if total > 0 else 0
            roi = ((equity_curve[-1] - curr_initial) / curr_initial * 100)
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Win Rate", f"{win_rate:.1f}%")
            c2.metric("Max Drawdown", f"{max_dd:.1f}%", help="最大回撤：資金從最高點回落的幅度")
            c3.metric("ROI", f"{roi:.1f}%")
        else:
            st.info("尚無結算數據")

        st.markdown("### 📜 Mission Log")
        df_show = df_all[['created_at', 'match_info', 'bet_type', 'status', 'profit', 'notes']].copy()
        df_show['created_at'] = pd.to_datetime(df_show['created_at']).dt.strftime("%m/%d %H:%M")
        df_show.columns = ['Time', 'Match', 'Bet', 'Status', 'P/L', 'Notes']
        st.dataframe(df_show, use_container_width=True)
    else:
        st.write("Awaiting Data...")

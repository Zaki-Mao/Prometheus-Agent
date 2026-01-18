import streamlit as st
import requests
import json
import google.generativeai as genai
import time

# ================= 🕵️‍♂️ 1. 基础配置 =================
st.set_page_config(
    page_title="Be Holmes | Alpha Hunter",
    page_icon="🕵️‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= 🎨 2. 五行风水 UI (Fire & Wood Edition) =================
st.markdown("""
<style>
    /* --- 全局背景：深海玄水 (Abyss Blue/Black) --- */
    .stApp { background-color: #050505; font-family: 'Roboto Mono', monospace; }
    [data-testid="stSidebar"] { background-color: #000000; border-right: 1px solid #1a1a1a; }
    
    /* --- 标题：金火相生 (Gold & Red) --- */
    h1 { 
        background: -webkit-linear-gradient(45deg, #D4AF37, #FF4500);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Georgia', serif; 
        border-bottom: 2px solid #333; 
        padding-bottom: 15px;
    }
    
    /* --- 文本色调 --- */
    h3 { color: #E0C097 !important; }
    p, label, .stMarkdown, .stText, li, div, span { color: #A0A0A0 !important; }
    strong { color: #FFF !important; font-weight: 600; } 
    a { text-decoration: none !important; border-bottom: none !important; }

    /* --- 输入框：木火通明 (Focus时发光) --- */
    .stTextArea textarea, .stNumberInput input, .stTextInput input, .stSelectbox div[data-baseweb="select"] { 
        background-color: #0F0F0F !important; 
        color: #D4AF37 !important; 
        border: 1px solid #333 !important; 
        border-radius: 8px;
    }
    .stTextArea textarea:focus, .stTextInput input:focus { 
        border: 1px solid #FF4500 !important; /* 火红聚焦 */
        box-shadow: 0 0 15px rgba(255, 69, 0, 0.2); 
    }
    
    /* --- 按钮：火炼金 (Magma Style) --- */
    div.stButton > button { 
        background-color: #111; 
        color: #FF4500; 
        border: 1px solid #333; 
        font-weight: bold;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover { 
        background-color: #FF4500; 
        color: #FFF; 
        border-color: #FF4500;
        box-shadow: 0 0 20px rgba(255, 69, 0, 0.4);
    }

    /* --- 核心执行按钮 (Action Green/Gold) --- */
    .execute-btn {
        background: linear-gradient(90deg, #D4AF37, #FF4500); 
        border: none;
        color: #000;
        width: 100%;
        padding: 15px;
        font-weight: 900;
        font-size: 16px;
        cursor: pointer;
        border-radius: 6px;
        text-transform: uppercase;
        letter-spacing: 2px;
        box-shadow: 0 5px 15px rgba(255, 69, 0, 0.3);
        margin-top: 20px;
        transition: transform 0.2s;
    }
    .execute-btn:hover { 
        transform: scale(1.02); 
        box-shadow: 0 8px 25px rgba(255, 69, 0, 0.5); 
    }

    /* --- 实时盘口框 (Cyberpunk HUD) --- */
    .ticker-box {
        background-color: #080808;
        border: 1px solid #222;
        border-left: 4px solid #00FF99; /* 极光绿：代表生机/信号 */
        color: #00FF99;
        font-family: 'Courier New', monospace;
        padding: 15px;
        margin: 15px 0;
        font-size: 1.05em;
        font-weight: bold;
        box-shadow: 0 0 10px rgba(0, 255, 153, 0.05);
        display: flex;
        align-items: center;
    }
    
    /* --- 呼吸灯动画 --- */
    @keyframes pulse-red {
        0% { box-shadow: 0 0 0 0 rgba(255, 69, 0, 0.7); }
        70% { box-shadow: 0 0 0 10px rgba(255, 69, 0, 0); }
        100% { box-shadow: 0 0 0 0 rgba(255, 69, 0, 0); }
    }

    /* ============== 悬浮按钮 (Easter Egg) ============== */
    .stMainBlockContainer > div:last-of-type button {
        position: fixed;
        bottom: 30px;
        right: 30px;
        z-index: 9999;
        width: 50px;
        height: 50px;
        border-radius: 50% !important;
        background-color: #000 !important; 
        border: 2px solid #FF4500 !important; 
        color: #FF4500 !important;
        font-size: 20px !important;
        box-shadow: 0 0 15px rgba(255, 69, 0, 0.3);
        animation: pulse-red 2s infinite; /* 呼吸效果 */
    }
    .stMainBlockContainer > div:last-of-type button:hover {
        transform: scale(1.2) rotate(360deg);
        background-color: #FF4500 !important;
        color: #000 !important;
    }
</style>
""", unsafe_allow_html=True)

# ================= 🔐 3. 安全层 =================
try:
    if "GEMINI_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_KEY"]
    else:
        st.error("⚠️ KEY ERROR: Please configure .streamlit/secrets.toml")
        st.stop()
except Exception as e:
    st.error(f"⚠️ SYSTEM ERROR: {e}")
    st.stop()

# ================= 📡 4. 深海声纳系统 (The Sonar Engine) =================

def parse_market_data(data):
    """标准数据清洗器"""
    markets_clean = []
    if not data: return []
    
    for event in data:
        title = event.get('title', 'Unknown')
        slug = event.get('slug', '')
        all_markets = event.get('markets', [])
        
        if not all_markets: continue

        # 逻辑：找Volume最大的那个具体的Market
        best_market = None
        max_volume = -1
        for m in all_markets:
            if m.get('closed') is True: continue    
            try:
                vol = float(m.get('volume', 0))
                if vol > max_volume:
                    max_volume = vol
                    best_market = m
            except: continue
        
        if not best_market: best_market = all_markets[0]

        # 逻辑：解析赔率字符串
        odds_display = "N/A"
        try:
            raw_outcomes = best_market.get('outcomes', '["Yes", "No"]')
            outcomes = json.loads(raw_outcomes) if isinstance(raw_outcomes, str) else raw_outcomes
            raw_prices = best_market.get('outcomePrices', '[]')
            prices = json.loads(raw_prices) if isinstance(raw_prices, str) else raw_prices

            odds_list = []
            if prices and len(prices) == len(outcomes):
                for o, p in zip(outcomes, prices):
                    val = float(p) * 100
                    if val > 0.5: # 忽略极小概率
                        odds_list.append(f"{o}: {val:.1f}%")
                odds_display = " | ".join(odds_list)
            else:
                odds_display = f"Price: {float(prices[0])*100:.1f}%"
        except:
            odds_display = "No Data"
        
        markets_clean.append({
            "title": title,
            "odds": odds_display,
            "slug": slug,
            "volume": max_volume
        })
    return markets_clean

@st.cache_data(ttl=300) 
def fetch_top_markets():
    """获取 Top 100 热门市场 (守株待兔)"""
    url = "https://gamma-api.polymarket.com/events?limit=50&active=true&closed=false&sort=volume"
    try:
        response = requests.get(url, headers={"User-Agent": "BeHolmes/1.0"}, timeout=5)
        if response.status_code == 200:
            return parse_market_data(response.json())
        return []
    except: return []

def deep_sonar_search(keyword):
    """主动声纳：根据关键词强制搜索 (主动出击)"""
    if not keyword: return []
    # 使用 q 参数进行全文检索
    url = f"https://gamma-api.polymarket.com/events?limit=20&active=true&closed=false&q={keyword}"
    try:
        response = requests.get(url, headers={"User-Agent": "BeHolmes/1.0"}, timeout=5)
        if response.status_code == 200:
            return parse_market_data(response.json())
        return []
    except: return []

def extract_keywords_with_ai(user_text, key):
    """AI 关键词萃取器：把长新闻变成搜索词"""
    if not user_text: return None
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        # 简单粗暴的 Prompt
        prompt = f"""
        Extract 1-2 most important English keywords for a search engine from this text.
        Text: "{user_text}"
        Output strictly in this format: keyword1
        (If multiple, just space them. Example: iPhone Apple)
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return None

# ================= 🧠 5. 核心推理引擎 =================

def consult_holmes(user_evidence, market_list, key):
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # 格式化市场数据
        markets_text = "\n".join([f"- {m['title']} [Odds: {m['odds']}]" for m in market_list[:50]])
        
        prompt = f"""
        Role: **Be Holmes**, The Prediction Market Detective.
        Goal: Find Alpha by connecting news to market odds.
        
        [Evidence]: "{user_evidence}"
        [Available Markets]: 
        {markets_text}

        **LANGUAGE PROTOCOL:**
        - Input Chinese -> Output CHINESE report.
        - Input English -> Output ENGLISH report.

        **OUTPUT FORMAT (Strict HTML/Markdown):**
        
        ---
        ### 🕵️‍♂️ Case File: [Most Relevant Market Title]
        
        <div class="ticker-box">
        🟢 LIVE SIGNAL: [Insert Odds Here]
        </div>
        
        **1. ⚖️ The Verdict (结论)**
        - **Signal:** 🔥 STRONG BUY / 🧊 AVOID / 🌲 LONG HOLD
        - **Confidence:** **[0-100]%**
        - **Prediction:** Market implies [Current %], I calculate [Target %].
        
        **2. ⛓️ The Deduction (因果推理)**
        > *[Mandatory: Write a deep, 100-word analysis. Start with the extracted keyword facts, explain the causal chain, and state why the current odds are mispriced.]*
        
        **3. ⏳ Strategy (执行)**
        - **Timeframe:** [e.g. 48 Hours / Until Official Announcement]
        - **Risk:** [Main Risk Factor]
        ---
        """
        
        response = model.generate_content(prompt)
        
        # 注入底部实心按钮
        btn_html = """
<br>
<a href='https://polymarket.com/' target='_blank' style='text-decoration:none;'>
<button class='execute-btn'>🚀 EXECUTE TRADE ON POLYMARKET</button>
</a>
"""
        return response.text + btn_html

    except Exception as e:
        return f"❌ Deduction Error: {str(e)}"

# ================= 🚀 6. 悬浮彩蛋 (Project MARS) =================

@st.dialog("🚀 PROJECT MARS: ELON RADAR", width="large")
def open_mars_radar():
    st.markdown("---")
    # 状态初始化
    if 'mars_markets' not in st.session_state: st.session_state['mars_markets'] = []

    # 1. 引导区
    st.info("💡 Data Source: Manual calibration required due to X API limits.")
    st.markdown("""
        <div style='text-align: center; margin-bottom: 15px;'>
        👉 <a href='https://xtracker.polymarket.com/user/elonmusk' target='_blank' style='color:#FF4500; font-weight:bold; border-bottom:1px dashed #FF4500;'>
        [ OPEN POLYMARKET X-TRACKER ]
        </a>
        </div>""", unsafe_allow_html=True)

    # 2. 市场搜索 (Deep Scan)
    col_s, col_b = st.columns([3, 1])
    with col_s: 
        kw = st.text_input("Target Keyword", value="Elon Tweet")
    with col_b: 
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("📡 SCAN", use_container_width=True):
            with st.spinner("Pinging Sonar..."):
                st.session_state['mars_markets'] = deep_sonar_search(kw) # 复用深海搜索

    # 3. 选择与计算
    if st.session_state['mars_markets']:
        opts = [m['title'] for m in st.session_state['mars_markets']]
        sel = st.selectbox("Select Market", opts)
        
        target = next((m for m in st.session_state['mars_markets'] if m['title'] == sel), None)
        odds = target['odds'] if target else "N/A"
        
        st.markdown(f"<div style='background:#000; border:1px solid #333; color:#00FF99; padding:10px; font-family:monospace;'>📊 ODDS: {odds}</div>", unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1: count = st.number_input("Current Count", min_value=0)
        with c2: hrs = st.number_input("Hours Left", min_value=1, value=24)
        
        if st.button("👽 CALCULATE", use_container_width=True) and count > 0:
            with st.spinner("Processing..."):
                try:
                    genai.configure(api_key=api_key)
                    m = genai.GenerativeModel('gemini-2.5-flash')
                    p = f"Predict Elon Tweet count. Context: {sel}. Odds: {odds}. Current: {count}. Time: {hrs}h. Output: Short sci-fi analysis."
                    r = m.generate_content(p)
                    st.markdown(f"<div style='border:1px solid #FF4500; background:#111; padding:15px; margin-top:10px; color:#ddd;'>{r.text}</div>", unsafe_allow_html=True)
                except: st.error("Link Failed")

# ================= 🖥️ 7. 主界面布局 (The Main Stage) =================

with st.sidebar:
    st.markdown("## 💼 DETECTIVE'S TOOLKIT")
    st.markdown("`CORE: GEMINI-2.5-FLASH`")
    st.success("🔒 System: Online")
    st.markdown("---")
    st.markdown("### 🌊 Market Sonar (Top 5)")
    
    # 默认加载 Top 市场
    with st.spinner("Initializing Sonar..."):
        top_markets = fetch_top_markets()
    
    if top_markets:
        for m in top_markets[:5]:
            st.caption(f"📅 {m['title']}")
            st.code(f"{m['odds']}") 
    else:
        st.error("⚠️ Data Stream Offline")

# 标题区
st.title("🕵️‍♂️ Be Holmes")
st.caption("EVENT-DRIVEN INTELLIGENCE | SECOND-ORDER CAUSAL REASONING") 
st.markdown("---")

col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("### 📁 EVIDENCE INPUT")
    user_news = st.text_area(
        "Input News / Rumors / X Links...", 
        height=150, 
        placeholder="Try searching specifically: 'iPhone 18 rumors' or 'Trump tariffs'...", 
        label_visibility="collapsed"
    )

with col2:
    st.markdown("<br><br>", unsafe_allow_html=True)
    ignite_btn = st.button("🔍 INVESTIGATE", use_container_width=True)

if ignite_btn:
    if not user_news:
        st.warning("⚠️ Evidence required to initiate investigation.")
    else:
        # --- 🔥 V8.0 核心逻辑：双引擎搜索 (Dual Engine) ---
        
        # 1. 启动声纳：AI 提取关键词
        with st.status("🚀 Initiating Deep Scan...", expanded=True) as status:
            st.write("🧠 Analyzing intent (Gemini 2.5)...")
            search_keywords = extract_keywords_with_ai(user_news, api_key)
            
            # 2. 发射声纳：如果提取出了关键词，就去深挖
            sonar_markets = []
            if search_keywords:
                st.write(f"🌊 Active Sonar Ping: '{search_keywords}'...")
                sonar_markets = deep_sonar_search(search_keywords)
                st.write(f"✅ Found {len(sonar_markets)} specific markets in the deep web.")
            
            # 3. 数据融合：合并 Top 100 和 声纳结果
            combined_markets = sonar_markets + top_markets
            # 去重逻辑 (根据 slug)
            seen_slugs = set()
            unique_markets = []
            for m in combined_markets:
                if m['slug'] not in seen_slugs:
                    unique_markets.append(m)
                    seen_slugs.add(m['slug'])
            
            st.write("⚖️ Cross-referencing odds data...")
            status.update(label="✅ Investigation Complete", state="complete", expanded=False)

        # 4. 生成最终报告
        if not unique_markets:
            st.error("⚠️ No relevant markets found anywhere.")
        else:
            with st.spinner(">> Deducing Alpha..."):
                # 将融合后的数据喂给 AI，并优先把 声纳结果 放在前面 (更相关)
                result = consult_holmes(user_news, unique_markets, api_key)
                st.markdown("---")
                st.markdown("### 📝 INVESTIGATION REPORT")
                st.markdown(result, unsafe_allow_html=True)

# ================= 👽 8. 悬浮按钮 (必须在最后) =================
st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True) 
if st.button("👽", key="mars_fab", help="Project MARS: Elon Radar"):
    open_mars_radar()

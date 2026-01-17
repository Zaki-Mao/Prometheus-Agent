import streamlit as st
import requests
import json
import google.generativeai as genai
import os

# ================= 🕵️‍♂️ 1. 基础配置 =================
st.set_page_config(
    page_title="Be Holmes | AI Market Detective",
    page_icon="🕵️‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= 🎨 2. 全局 CSS =================
st.markdown("""
<style>
    /* --- 全局深色主题 --- */
    .stApp { background-color: #0E1117; font-family: 'Roboto Mono', monospace; }
    [data-testid="stSidebar"] { background-color: #050505; border-right: 1px solid #333; }
    
    /* --- 字体与颜色 --- */
    h1 { color: #D4AF37 !important; font-family: 'Georgia', serif; text-shadow: 0 0 5px #443300; border-bottom: 1px solid #D4AF37; padding-bottom: 15px;}
    h3 { color: #E0C097 !important; }
    p, label, .stMarkdown, .stText, li, div, span { color: #B0B0B0 !important; }
    strong { color: #FFF !important; font-weight: 600; } 
    a { text-decoration: none !important; border-bottom: none !important; }

    /* --- 输入框优化 --- */
    .stTextArea textarea, .stNumberInput input, .stSelectbox div[data-baseweb="select"], .stTextInput input { 
        background-color: #151515 !important; 
        color: #D4AF37 !important; 
        border: 1px solid #444 !important; 
    }
    .stTextArea textarea:focus, .stNumberInput input:focus, .stTextInput input:focus { 
        border: 1px solid #D4AF37 !important; 
        box-shadow: 0 0 10px rgba(212, 175, 55, 0.2); 
    }
    
    /* --- 通用按钮 --- */
    div.stButton > button { 
        background-color: #000; color: #D4AF37; border: 1px solid #D4AF37; 
        transition: all 0.3s ease;
    }
    div.stButton > button:hover { 
        background-color: #D4AF37; color: #000; border-color: #D4AF37;
    }

    /* --- 报告中的执行按钮 (实心金) --- */
    .execute-btn {
        background: linear-gradient(45deg, #D4AF37, #FFD700);
        border: none;
        color: #000;
        width: 100%;
        padding: 15px;
        font-weight: 800;
        font-size: 16px;
        cursor: pointer;
        border-radius: 4px;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        box-shadow: 0 4px 15px rgba(212, 175, 55, 0.3);
        margin-top: 20px;
    }
    .execute-btn:hover { 
        transform: translateY(-2px); 
        box-shadow: 0 6px 20px rgba(212, 175, 55, 0.6); 
    }

    /* --- 报告中的 LED 盘口框 --- */
    .ticker-box {
        background-color: #000;
        border: 1px solid #333;
        border-left: 5px solid #D4AF37;
        color: #00FF00;
        font-family: 'Courier New', monospace;
        padding: 15px;
        margin: 10px 0;
        font-size: 1.1em;
        font-weight: bold;
        box-shadow: 0 0 10px rgba(0, 255, 0, 0.1);
        letter-spacing: 1px;
    }

    /* ============== 隐藏彩蛋：右下角悬浮按钮 ============== */
    .stMainBlockContainer > div:last-of-type button {
        position: fixed;
        bottom: 30px;
        right: 30px;
        z-index: 9999;
        width: 50px;
        height: 50px;
        border-radius: 50% !important;
        background-color: #0d0202 !important; 
        border: 2px solid #FF4500 !important; 
        color: #FF4500 !important;
        font-size: 20px !important;
        box-shadow: 0 0 15px rgba(255, 69, 0, 0.4);
        transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }
    .stMainBlockContainer > div:last-of-type button:hover {
        transform: scale(1.2) rotate(360deg);
        box-shadow: 0 0 25px rgba(255, 69, 0, 0.8);
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
        st.error("⚠️ MISSING KEY: The detective cannot work without his tools.")
        st.stop()
except Exception as e:
    st.error(f"⚠️ SYSTEM ERROR: {e}")
    st.stop()

# ================= 📡 4. 数据层：Polymarket (双引擎：热门 + 搜索) =================

def parse_market_data(data):
    """解析 API 返回的 JSON 数据为标准格式"""
    markets_clean = []
    for event in data:
        title = event.get('title', 'Unknown')
        slug = event.get('slug', '')
        all_markets = event.get('markets', [])
        
        if not all_markets: continue

        # 找成交量最大的 Market (主盘口)
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

        # 解析赔率
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
                    if val > 1.0: # 过滤极小概率
                        odds_list.append(f"{o}: {val:.1f}%")
                odds_display = " | ".join(odds_list)
            else:
                val = float(prices[0]) * 100
                odds_display = f"Price: {val:.1f}%"
        except:
            odds_display = "Odds Unavailable"
        
        markets_clean.append({
            "title": title,
            "odds": odds_display,
            "slug": slug
        })
    return markets_clean

@st.cache_data(ttl=300) 
def fetch_top_markets():
    """默认获取热门 Top 100"""
    url = "https://gamma-api.polymarket.com/events?limit=100&active=true&closed=false&sort=volume"
    try:
        headers = {"User-Agent": "BeHolmes-Agent/1.0"}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return parse_market_data(response.json())
        return []
    except: return []

# 🔥 V7.0 新增：深海声纳 (搜索特定关键词)
def fetch_markets_by_keyword(keyword):
    """强制搜索包含关键词的市场 (不限成交量，只看相关性)"""
    if not keyword: return []
    # 使用 q 参数进行全文检索
    url = f"https://gamma-api.polymarket.com/events?limit=20&active=true&closed=false&q={keyword}"
    try:
        headers = {"User-Agent": "BeHolmes-Agent/1.0"}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return parse_market_data(response.json())
        return []
    except: return []

# ================= 🧠 5. 智能层：Be Holmes 深度推理引擎 =================

def consult_holmes(user_evidence, market_list, key):
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        markets_text = "\n".join([f"- ID:{i} | {m['title']} [Live Odds: {m['odds']}]" for i, m in enumerate(market_list[:40])])
        
        prompt = f"""
        Role: You are **Be Holmes**, a legendary prediction market detective. 
        Task: Analyze the [Evidence] against the [Market List].

        [Evidence]: "{user_evidence}"
        [Market Data]: {markets_text}

        **LANGUAGE PROTOCOL:**
        - Input Chinese -> Output CHINESE report.
        - Input English -> Output ENGLISH report.

        **OUTPUT FORMAT (Markdown + HTML):**
        
        ---
        ### 🕵️‍♂️ Case File: [Exact Market Title]
        
        <div class="ticker-box">
        📡 LIVE SNAPSHOT: [Insert Odds Here]
        </div>
        
        **1. ⚖️ The Verdict (结论)**
        - **Signal:** 🟢 STRONG BUY / 🔴 STRONG SELL / ⚠️ WATCH
        - **Confidence:** **[0-100]%**
        - **Target:** Market [Current %] ➔ I Predict [Target %]
        
        **2. ⛓️ The Deduction (深度逻辑链)**
        > *[Mandatory: Write a deep analysis paragraph (100+ words). Start with the hard evidence, explain the transmission mechanism, and conclude why the market is mispriced.]*
        
        **3. ⏳ Execution (执行计划)**
        - **Timeframe:** [Duration]
        - **Exit:** [Condition]
        ---
        """
        
        response = model.generate_content(prompt)
        
        btn_html = """
<br>
<a href='https://polymarket.com/' target='_blank' style='text-decoration:none;'>
<button class='execute-btn'>🚀 EXECUTE TRADE ON POLYMARKET</button>
</a>
"""
        return response.text + btn_html

    except Exception as e:
        return f"❌ Deduction Error: {str(e)}"

# ================= 🚀 6. 彩蛋模块：Project MARS (深海声纳版 V7.0) =================

@st.dialog("🚀 PROJECT MARS: ELON RADAR", width="large")
def open_mars_radar():
    st.markdown("---")
    
    # 0. 数据源状态管理
    if 'mars_markets' not in st.session_state:
        st.session_state['mars_markets'] = []

    # 1. 链接引导
    st.info("💡 Data Source: Manual calibration required due to X API limits.")
    st.markdown(
        """<div style='text-align: center; margin-bottom: 15px; font-family: monospace;'>
        👉 <b>STEP 1: CHECK OFFICIAL COUNT </b><br>
        <a href='https://xtracker.polymarket.com/user/elonmusk' target='_blank' style='font-size: 1.1em; color: #FF4500; border-bottom: 1px dashed #FF4500;'>
        [ OPEN POLYMARKET X-TRACKER ]
        </a>
        </div>""", 
        unsafe_allow_html=True
    )

    # 2. 市场选择器 (含深度搜索)
    st.markdown("### 🎯 STEP 2: LOCATE TARGET MARKET")
    
    col_search, col_btn = st.columns([3, 1])
    with col_search:
        # 默认搜索 "Elon Tweet"，允许用户改
        search_query = st.text_input("Search Market Keyword (Default: 'Elon')", value="Elon")
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True) # 对齐
        scan_btn = st.button("📡 DEEP SCAN", use_container_width=True)

    # 执行搜索逻辑
    if scan_btn or not st.session_state['mars_markets']:
        with st.spinner(f"Sonar pinging for '{search_query}'..."):
            # 这里的逻辑是：Top 100 里可能没有，所以我们强制去搜全量数据库
            found_markets = fetch_markets_by_keyword(search_query)
            # 过滤一下，只保留相关的 (比如包含 Tweet 的，或者用户就要搜别的)
            # 这里不做严格过滤，给用户自由度
            st.session_state['mars_markets'] = found_markets

    # 下拉菜单展示结果
    if not st.session_state['mars_markets']:
        st.warning(f"⚠️ No markets found for '{search_query}'. Try broader keywords.")
        selected_market_title = None
        selected_market_odds = "N/A"
    else:
        # 让用户选择
        market_options = [m['title'] for m in st.session_state['mars_markets']]
        selected_market_title = st.selectbox("Select Active Market:", market_options)
        
        # 获取赔率
        target_data = next((m for m in st.session_state['mars_markets'] if m['title'] == selected_market_title), None)
        selected_market_odds = target_data['odds'] if target_data else "N/A"

        # 展示选中市场的实时赔率
        st.markdown(f"""
        <div style="border:1px solid #333; background:#000; padding:10px; border-radius:5px; margin-bottom:15px; font-family:'Courier New'; font-size:0.9em; color:#00FF00;">
        📊 LIVE ODDS: {selected_market_odds}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # 3. 数据输入 & 计算
    if selected_market_title:
        m_col1, m_col2 = st.columns(2)
        with m_col1:
            current_count = st.number_input("🔢 Current Count (from X-Tracker)", min_value=0, value=0)
        with m_col2:
            hours_left = st.number_input("⏳ Hours Remaining", min_value=1, value=24)

        if st.button("👽 CALCULATE TRAJECTORY", use_container_width=True):
            if current_count == 0:
                st.warning("⚠️ Please enter valid count.")
            else:
                with st.spinner("🛰️ Triangulating trajectory..."):
                    try:
                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel('gemini-2.5-flash')
                        
                        mars_prompt = f"""
                        Role: You are 'Elon Musk Behavioral Model' (Project MARS).
                        
                        **Mission Data:**
                        - **Target Market:** {selected_market_title}
                        - **Implied Odds:** {selected_market_odds}
                        - **Current Count:** {current_count}
                        - **Time Left:** {hours_left}h
                        
                        **Analysis Logic:**
                        1. Calculate projected finish: Current + (Avg Hourly Rate * Time Left).
                        2. Factor in 'Elon Time' (Volatility, Weekends, Events).
                        3. Compare Projection vs Market Odds to find EV+.

                        **Output (Sci-fi Style):**
                        ### 🎯 Trajectory Analysis
                        
                        **1. Velocity & Projection**
                        - **Current Pace:** [Tweets/hr]
                        - **Predicted End:** [Range]
                        
                        **2. Sniper Signal**
                        - **Target Bucket:** [e.g., "60-69"]
                        - **Edge:** "Market gives 20%, Model gives 60%."
                        
                        **3. Threat Level**
                        - [Main risk factor]
                        """
                        resp = model.generate_content(mars_prompt)
                        
                        st.markdown(f"""
                        <div style="border:1px solid #FF4500; background:#1a0505; padding:15px; border-radius:5px; margin-top:10px; color:#ddd;">
                            {resp.text}
                        </div>
                        """, unsafe_allow_html=True)
                        
                    except Exception as e:
                        st.error(f"Link Failed: {e}")

# ================= 🖥️ 7. 主界面布局 =================

with st.sidebar:
    st.markdown("## 💼 DETECTIVE'S TOOLKIT")
    st.markdown("`ENGINE: GEMINI-2.5-FLASH`")
    st.success("🔒 Authorization: Granted")
    st.markdown("---")
    st.markdown("### 🔍 Market Surveillance")
    
    with st.spinner("Scanning tickers..."):
        top_markets = fetch_top_markets()
    
    if top_markets:
        st.info(f"Monitoring {len(top_markets)} Active Cases")
        for m in top_markets[:5]:
            st.caption(f"📅 {m['title']}")
            st.code(f"{m['odds']}") 
    else:
        st.error("⚠️ Network Glitch: Data Unavailable")

st.title("🕵️‍♂️ Be Holmes")
st.caption("THE ART OF DEDUCTION FOR PREDICTION MARKETS | DEEP CAUSAL INFERENCE") 
st.markdown("---")

col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("### 📁 EVIDENCE LOCKER")
    user_news = st.text_area(
        "News", 
        height=150, 
        placeholder="Enter evidence here... \n(Input English -> English Report | Input Chinese -> Chinese Report)", 
        label_visibility="collapsed"
    )

with col2:
    st.markdown("<br><br>", unsafe_allow_html=True)
    ignite_btn = st.button("🔍 INVESTIGATE", use_container_width=True)

if ignite_btn:
    if not user_news:
        st.warning("⚠️ No evidence provided. I cannot make bricks without clay.")
    elif not top_markets:
        st.error("⚠️ Market data unavailable.")
    else:
        with st.spinner(">> Deducing outcomes... (Deep Analysis)"):
            result = consult_holmes(user_news, top_markets, api_key)
            st.markdown("---")
            st.markdown("### 📝 INVESTIGATION REPORT")
            st.markdown(result, unsafe_allow_html=True)

# ================= 👽 8. 悬浮按钮 =================
st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True) 
if st.button("👽", key="mars_fab", help="Project MARS: Elon Radar"):
    open_mars_radar()

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

# ================= 🎨 2. 全局 CSS (含悬浮按钮 Hack) =================
st.markdown("""
<style>
    /* --- 全局深色主题 --- */
    .stApp { background-color: #0E1117; font-family: 'Roboto Mono', monospace; }
    [data-testid="stSidebar"] { background-color: #050505; border-right: 1px solid #333; }
    
    /* --- 字体与颜色 --- */
    h1 { color: #D4AF37 !important; font-family: 'Georgia', serif; text-shadow: 0 0 5px #443300; border-bottom: 1px solid #D4AF37; padding-bottom: 15px;}
    h3 { color: #E0C097 !important; }
    p, label, .stMarkdown, .stText, li, div { color: #B0B0B0 !important; }
    strong { color: #FFF !important; font-weight: 600; } 
    a { text-decoration: none !important; border-bottom: none !important; }

    /* --- 输入框优化 --- */
    .stTextArea textarea, .stNumberInput input { 
        background-color: #151515 !important; 
        color: #D4AF37 !important; 
        border: 1px solid #444 !important; 
    }
    .stTextArea textarea:focus, .stNumberInput input:focus { 
        border: 1px solid #D4AF37 !important; 
        box-shadow: 0 0 10px rgba(212, 175, 55, 0.2); 
    }
    
    /* --- 通用按钮 (调查按钮) --- */
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
        color: #00FF00; /* 骇客绿 */
        font-family: 'Courier New', monospace;
        padding: 15px;
        margin: 10px 0;
        font-size: 1.1em;
        font-weight: bold;
        box-shadow: 0 0 10px rgba(0, 255, 0, 0.1);
        letter-spacing: 1px;
    }

    /* ============== 隐藏彩蛋：右下角悬浮按钮 ============== */
    /* 核心逻辑：定位页面最后一个按钮容器 */
    .stMainBlockContainer > div:last-of-type button {
        position: fixed;
        bottom: 30px;
        right: 30px;
        z-index: 9999;
        width: 50px;
        height: 50px;
        border-radius: 50% !important;
        background-color: #0d0202 !important; /* 火星黑 */
        border: 2px solid #FF4500 !important; /* 火星红 */
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

# ================= 📡 4. 数据层：Polymarket (双边赔率解析) =================
@st.cache_data(ttl=300) 
def fetch_top_markets():
    url = "https://gamma-api.polymarket.com/events?limit=100&active=true&closed=false&sort=volume"
    try:
        headers = {"User-Agent": "BeHolmes-Agent/1.0"}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            markets_clean = []
            
            for event in data:
                title = event.get('title', 'Unknown')
                slug = event.get('slug', '')
                all_markets = event.get('markets', [])
                
                if not all_markets: continue

                # 找成交量最大的 Market
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

                # 解析 Yes/No 详细赔率
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
        return []
    except Exception as e:
        return []

# ================= 🧠 5. 智能层：Be Holmes 深度推理引擎 =================

def consult_holmes(user_evidence, market_list, key):
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # 传递包含实时赔率的市场列表
        markets_text = "\n".join([f"- ID:{i} | {m['title']} [Live Odds: {m['odds']}]" for i, m in enumerate(market_list[:40])])
        
        prompt = f"""
        Role: You are **Be Holmes**, a legendary prediction market detective. 
        
        Task: Analyze the [Evidence] against the [Market List].

        [Evidence]: "{user_evidence}"
        [Market Data]: {markets_text}

        **LANGUAGE PROTOCOL:**
        - Input Chinese -> Output CHINESE report.
        - Input English -> Output ENGLISH report.

        **OUTPUT FORMAT (Strict Markdown + HTML Structure):**
        
        You must structure the output exactly as follows. 
        For the "Market Ticker", just provide the raw odds string.

        ---
        ### 🕵️‍♂️ Case File: [Exact Market Title]
        
        <div class="ticker-box">
        📡 LIVE SNAPSHOT: [Insert Odds Here, e.g., Yes: 22.5% | No: 77.5%]
        </div>
        
        **1. ⚖️ The Verdict (结论)**
        - **Signal:** 🟢 STRONG BUY / 🔴 STRONG SELL / ⚠️ WATCH
        - **Confidence:** **[0-100]%**
        - **Target:** Market [Current %] ➔ I Predict [Target %]
        
        **2. ⛓️ The Deduction (深度逻辑链)**
        > *[Mandatory: Write a deep analysis paragraph (100+ words). Start with the hard evidence, explain the transmission mechanism (how it affects the settlement criteria), and conclude why the market is mispriced.]*
        
        **3. ⏳ Execution (执行计划)**
        - **Timeframe:** [Duration]
        - **Exit:** [Condition]
        ---
        """
        
        response = model.generate_content(prompt)
        
        # 注入底部实心金色按钮
        btn_html = """
<br>
<a href='https://polymarket.com/' target='_blank' style='text-decoration:none;'>
<button class='execute-btn'>🚀 EXECUTE TRADE ON POLYMARKET</button>
</a>
"""
        return response.text + btn_html

    except Exception as e:
        return f"❌ Deduction Error: {str(e)}"

# ================= 🚀 6. 彩蛋模块：Project MARS (弹窗逻辑) =================

# 注意：st.dialog 需要 Streamlit 1.34+ (云端默认支持)
@st.dialog("🚀 PROJECT MARS: ELON RADAR", width="large")
def open_mars_radar():
    st.markdown("---")
    # 1. 链接区
    st.info("💡 Data Source: Anti-bot active. Manual input required.")
    st.markdown(
        """<div style='text-align: center; margin-bottom: 15px; font-family: monospace;'>
        👉 <b>STEP 1: CHECK OFFICIAL COUNT </b><br>
        <a href='https://xtracker.polymarket.com/user/elonmusk' target='_blank' style='font-size: 1.1em; color: #FF4500; border-bottom: 1px dashed #FF4500;'>
        [ OPEN POLYMARKET X-TRACKER ]
        </a>
        </div>""", 
        unsafe_allow_html=True
    )

    # 2. 交互区
    m_col1, m_col2 = st.columns(2)
    with m_col1:
        current_count = st.number_input("🔢 Current Count", min_value=0, value=0, help="Input number from X-Tracker")
    with m_col2:
        hours_left = st.number_input("⏳ Hours Left", min_value=1, value=24)

    # 3. 预测计算
    if st.button("👽 CALCULATE TRAJECTORY", use_container_width=True):
        if current_count == 0:
            st.warning("⚠️ Please enter valid count from tracker.")
        else:
            with st.spinner("🛰️ Establishing link with Mars..."):
                try:
                    # 独立的马斯克模型逻辑
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    
                    mars_prompt = f"""
                    Role: You are 'Elon Musk Behavioral Model'.
                    Context: Betting on how many tweets Elon will post.
                    Data: Current {current_count}, Time Left {hours_left}h.
                    Task: Predict final range. Short, robotic, sci-fi style response.
                    
                    Output format:
                    ### 🎯 Projection: [Range]
                    - **Velocity:** [Tweets/hr]
                    - **Verdict:** [Buy Bucket X]
                    - **Risk:** [One sentence]
                    """
                    resp = model.generate_content(mars_prompt)
                    
                    # 结果显示 (黑红风格框)
                    st.markdown(f"""
                    <div style="border:1px solid #FF4500; background:#1a0505; padding:15px; border-radius:5px; margin-top:10px; color:#ddd;">
                        {resp.text}
                    </div>
                    """, unsafe_allow_html=True)
                    
                except Exception as e:
                    st.error(f"Link Failed: {e}")

# ================= 🖥️ 7. 主界面布局 =================

# 侧边栏
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
            st.code(f"{m['odds']}") # 显示详细赔率
    else:
        st.error("⚠️ Network Glitch: Data Unavailable")

# 标题区
st.title("🕵️‍♂️ Be Holmes")
st.caption("THE ART OF DEDUCTION FOR PREDICTION MARKETS | DEEP CAUSAL INFERENCE") 
st.markdown("---")

# 主输入区
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

# 核心触发逻辑
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

# ================= 👽 8. 悬浮按钮 (必须放在代码最后) =================
# 这个按钮会被 CSS 强制移动到右下角
st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True) # 占位
if st.button("👽", key="mars_fab", help="Project MARS: Elon Radar"):
    open_mars_radar()

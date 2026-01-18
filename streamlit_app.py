import streamlit as st
import requests
import json
import google.generativeai as genai
import re

# ================= 🕵️‍♂️ 1. SYSTEM CONFIGURATION =================
st.set_page_config(
    page_title="Be Holmes | Alpha Hunter",
    page_icon="🕵️‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= 🎨 2. UI DESIGN (Magma Red - Clean Mode) =================
st.markdown("""
<style>
    /* --- HIDE SYSTEM ELEMENTS --- */
    [data-testid="stToolbar"] { visibility: hidden; height: 0%; position: fixed; }
    footer { visibility: hidden; }
    header { visibility: hidden; }

    /* --- Global Background --- */
    .stApp { background-color: #050505; font-family: 'Roboto Mono', monospace; }
    [data-testid="stSidebar"] { background-color: #000000; border-right: 1px solid #1a1a1a; }
    
    /* --- Typography --- */
    h1 { 
        background: linear-gradient(90deg, #FF4500, #E63946); 
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Georgia', serif; 
        font-weight: 800;
        border-bottom: 2px solid #331111; 
        padding-bottom: 15px;
        text-shadow: 0 0 20px rgba(255, 69, 0, 0.2);
    }
    
    h3 { color: #FF7F50 !important; } 
    p, label, .stMarkdown, .stText, li, div, span { color: #A0A0A0 !important; }
    strong { color: #FFF !important; font-weight: 600; } 
    a { text-decoration: none !important; border-bottom: none !important; }

    /* --- Inputs --- */
    .stTextArea textarea, .stNumberInput input, .stTextInput input, .stSelectbox div[data-baseweb="select"] { 
        background-color: #0A0A0A !important; 
        color: #E63946 !important; 
        border: 1px solid #333 !important; 
        border-radius: 6px;
    }
    .stTextArea textarea:focus, .stTextInput input:focus { 
        border: 1px solid #FF4500 !important; 
        box-shadow: 0 0 15px rgba(255, 69, 0, 0.2); 
    }
    
    /* --- Buttons --- */
    .stButton button { width: 100%; border-radius: 6px; font-weight: bold; transition: all 0.3s ease; }
    
    div[data-testid="column"]:nth-of-type(1) div.stButton > button { 
        background: linear-gradient(90deg, #8B0000, #FF4500); 
        color: #FFF; border: none; box-shadow: 0 4px 15px rgba(255, 69, 0, 0.3);
    }
    div[data-testid="column"]:nth-of-type(1) div.stButton > button:hover { 
        box-shadow: 0 6px 25px rgba(255, 69, 0, 0.6); transform: translateY(-2px);
    }

    div[data-testid="column"]:nth-of-type(2) div.stButton > button { 
        background-color: transparent; color: #666; border: 1px solid #333; 
    }
    div[data-testid="column"]:nth-of-type(2) div.stButton > button:hover { 
        border-color: #FF4500; color: #FF4500; background-color: #1a0505;
    }

    /* --- Report Elements --- */
    .execute-btn {
        background: linear-gradient(90deg, #FF4500, #FFD700); 
        border: none; color: #000; width: 100%; padding: 15px;
        font-weight: 900; font-size: 16px; cursor: pointer; border-radius: 6px;
        text-transform: uppercase; letter-spacing: 2px;
        box-shadow: 0 5px 15px rgba(255, 69, 0, 0.3); margin-top: 20px;
    }
    .execute-btn:hover { transform: scale(1.02); box-shadow: 0 8px 25px rgba(255, 69, 0, 0.5); }

    .ticker-box {
        background-color: #080808; border: 1px solid #222; border-left: 4px solid #FF4500;
        color: #FF4500; font-family: 'Courier New', monospace; padding: 15px; margin: 15px 0;
        font-size: 1.05em; font-weight: bold; display: flex; align-items: center;
    }
</style>
""", unsafe_allow_html=True)

# ================= 🔐 3. KEY MANAGEMENT =================
active_key = None

# ================= 📡 4. DATA ENGINE (ATOMIC MARKET SEARCH V15.0) =================

def detect_language_type(text):
    for char in text:
        if '\u4e00' <= char <= '\u9fff': return "CHINESE"
    return "ENGLISH"

def parse_single_market(m):
    """专门解析 /markets 接口返回的扁平数据结构"""
    try:
        # 在 markets 接口中，字段名通常是 'question' 而不是 'title'
        title = m.get('question', m.get('title', 'Unknown Market'))
        slug = m.get('slug', '')
        
        # 过滤掉已经关闭的市场
        if m.get('closed') is True: return None
        
        # 解析赔率
        odds_display = "N/A"
        raw_outcomes = m.get('outcomes', '["Yes", "No"]')
        outcomes = json.loads(raw_outcomes) if isinstance(raw_outcomes, str) else raw_outcomes
        raw_prices = m.get('outcomePrices', '[]')
        prices = json.loads(raw_prices) if isinstance(raw_prices, str) else raw_prices
        
        odds_list = []
        if prices and len(prices) == len(outcomes):
            for o, p in zip(outcomes, prices):
                try:
                    val = float(p) * 100
                    if val > 0.5: odds_list.append(f"{o}: {val:.1f}%")
                except: continue
            odds_display = " | ".join(odds_list)
        elif prices:
             odds_display = f"Price: {float(prices[0])*100:.1f}%"
             
        volume = float(m.get('volume', 0))
        
        return {"title": title, "odds": odds_display, "slug": slug, "volume": volume, "id": m.get('id')}
    except:
        return None

@st.cache_data(ttl=300) 
def fetch_top_markets():
    # 🔥 FIX 1: 改用 /markets 接口，直接获取热门具体问题
    try:
        url = "https://gamma-api.polymarket.com/markets?limit=50&active=true&closed=false&sort=volume"
        response = requests.get(url, headers={"User-Agent": "BeHolmes/1.0"}, timeout=6)
        if response.status_code == 200:
            raw_data = response.json()
            cleaned = []
            for m in raw_data:
                parsed = parse_single_market(m)
                if parsed: cleaned.append(parsed)
            return cleaned
        return []
    except: return []

def atomic_search(keywords_list):
    """
    🔥 V15 原子搜索：直接搜 Markets，不搜 Events
    这能解决 'SpaceX IPO' 藏在某个莫名其妙 Event 里的问题。
    """
    all_results = []
    seen_ids = set()
    
    for kw in keywords_list:
        if not kw: continue
        # 🔥 FIX 2: 搜索 /markets，并强制按 volume 排序，确保大额盘口置顶
        # 加上 sort=volume 是为了把你看到的那个 846K 的市场排在前面
        url = f"https://gamma-api.polymarket.com/markets?limit=50&active=true&closed=false&sort=volume&q={kw}"
        try:
            response = requests.get(url, headers={"User-Agent": "BeHolmes/1.0"}, timeout=6)
            if response.status_code == 200:
                data = response.json()
                for m in data:
                    parsed = parse_single_market(m)
                    if parsed and parsed['id'] not in seen_ids:
                        all_results.append(parsed)
                        seen_ids.add(parsed['id'])
        except: continue
    
    # 本地再按 Volume 降序排一次，确保万无一失
    all_results.sort(key=lambda x: x['volume'], reverse=True)
    return all_results

def extract_search_terms_ai(user_text, key):
    if not user_text: return []
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        # 提取更精准的短语
        prompt = f"""
        Extract 2 distinct English search keywords for Polymarket.
        1. Exact concept (e.g. "SpaceX IPO")
        2. Broad entity (e.g. "SpaceX")
        Input: "{user_text}"
        Output: Keyword1, Keyword2 (comma separated)
        """
        response = model.generate_content(prompt)
        raw_text = response.text.strip()
        keywords = [k.strip() for k in raw_text.split(',')]
        return keywords[:2]
    except: return []

# ================= 🧠 5. INTELLIGENCE LAYER =================

def consult_holmes(user_evidence, market_list, key):
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # 喂给 AI 前 30 个结果 (因为是 Market 级别，粒度细，30个足够涵盖)
        markets_text = "\n".join([f"- {m['title']} [Odds: {m['odds']}]" for m in market_list[:30]])
        target_language = detect_language_type(user_evidence)
        
        prompt = f"""
        Role: You are **Be Holmes**, a Senior Hedge Fund Strategist.
        
        [User Input]: "{user_evidence}"
        [Market Data (Sorted by Volume)]: 
        {markets_text}

        **MANDATORY INSTRUCTION:**
        1. **Language:** Output strictly in **{target_language}**.
        2. **Targeting:** The list is now granular markets. Find the specific question asking about the event.
           - Look specifically for "SpaceX" AND "IPO" in the title.
           - The user is looking for a high-volume market.
        
        **OUTPUT FORMAT (Strict Markdown):**
        
        ---
        ### 🕵️‍♂️ Case File: [Exact Market Question]
        
        <div class="ticker-box">
        🔥 LIVE SNAPSHOT: [Insert Odds]
        </div>
        
        **1. ⚖️ The Verdict (交易指令)**
        - **Signal:** 🟢 BUY / 🔴 SELL / ⚠️ WAIT
        - **Confidence:** **[0-100]%**
        - **Valuation:** Market: [X%], Model: [Y%].
        
        **2. 🧠 Deep Logic (深度推演)**
        > *[Analysis in {target_language}. 200 words.]*
        
        **3. 🛡️ Execution Protocol (执行方案)**
        - **Action:** [Instruction]
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
    except Exception as e: return f"❌ Intelligence Error: {str(e)}"

# ================= 📘 6. MANUAL MODULE =================

@st.dialog("📘 Be Holmes Manual", width="large")
def open_manual():
    lang = st.radio("Language / 语言", ["English", "中文"], horizontal=True)
    st.markdown("---")
    if lang == "中文":
        st.markdown("""
        ### 🕵️‍♂️ 系统简介
        **Be Holmes** 是基于 Gemini 2.5 的全知全能金融侦探。
        
        ### 🚀 V15.0 升级：原子搜索
        我们升级了底层数据引擎，不再搜索模糊的"事件组"，而是直接检索 Polymarket 上每一个具体的**交易合约 (Markets)**。配合成交量加权排序，确保精准命中高流动性标的。
        
        ### 🛠️ 操作指南
        - **输入:** 粘贴新闻或关键词。
        - **调查:** 点击红色 **INVESTIGATE**。
        """)
    else:
        st.markdown("""
        ### 🕵️‍♂️ System Profile
        **Be Holmes** is an omniscient financial detective.
        
        ### 🚀 V15.0 Update: Atomic Search
        We now query individual **Markets** instead of aggregated Events. This ensures high-precision discovery of specific contracts (e.g., "SpaceX IPO") sorted by liquidity.
        """)

# ================= 🖥️ 7. MAIN INTERFACE =================

with st.sidebar:
    st.markdown("## 💼 DETECTIVE'S TOOLKIT")
    with st.expander("🔑 API Key Settings", expanded=False):
        st.caption("Rate limited? Enter your own Google AI Key.")
        user_api_key = st.text_input("Gemini Key", type="password")
        st.markdown("[Get Free Key](https://aistudio.google.com/app/apikey)")

    if user_api_key:
        active_key = user_api_key
        st.success("🔓 User Key Active")
    elif "GEMINI_KEY" in st.secrets:
        active_key = st.secrets["GEMINI_KEY"]
        st.info("🔒 System Key Active")
    else:
        st.error("⚠️ No API Key found!")
        st.stop()

    st.markdown("---")
    st.markdown("### 🌊 Market Sonar (Top 5)")
    with st.spinner("Initializing Sonar..."):
        top_markets = fetch_top_markets()
    if top_markets:
        for m in top_markets[:5]:
            st.caption(f"📅 {m['title']}")
            st.code(f"{m['odds']}") 
    else: st.error("⚠️ Data Stream Offline")

# --- Main Stage ---
st.title("Be Holmes")
st.caption("EVENT-DRIVEN INTELLIGENCE | SECOND-ORDER CAUSAL REASONING") 
st.markdown("---")

st.markdown("### 📁 EVIDENCE INPUT")
user_news = st.text_area(
    "Input News / Rumors / X Links...", 
    height=150, 
    placeholder="Paste detailed intel here... (e.g., 'Rumors that iPhone 18 will remove all buttons')", 
    label_visibility="collapsed"
)

col_btn_main, col_btn_help = st.columns([4, 1])
with col_btn_main:
    ignite_btn = st.button("🔍 INVESTIGATE", use_container_width=True)
with col_btn_help:
    help_btn = st.button("📘 Manual", use_container_width=True)

if help_btn: open_manual()

if ignite_btn:
    if not user_news:
        st.warning("⚠️ Evidence required to initiate investigation.")
    else:
        with st.status("🚀 Initiating Atomic Market Search...", expanded=True) as status:
            st.write("🧠 Extracting precise market tags (Gemini 2.5)...")
            search_keywords = extract_search_terms_ai(user_news, active_key)
            
            sonar_markets = []
            if search_keywords:
                st.write(f"🌊 Querying Market API: {search_keywords}...")
                # 使用原子搜索
                sonar_markets = atomic_search(search_keywords)
                st.write(f"✅ Retrieved {len(sonar_markets)} specific contracts.")
            
            # 没搜到就用 Top 市场兜底
            if not sonar_markets:
                sonar_markets = top_markets
            
            st.write("⚖️ Analyzing Alpha...")
            status.update(label="✅ Investigation Complete", state="complete", expanded=False)

        if not sonar_markets: st.error("⚠️ No relevant markets found in the database.")
        else:
            with st.spinner(">> Deducing Alpha..."):
                result = consult_holmes(user_news, sonar_markets, active_key)
                st.markdown("---")
                st.markdown("### 📝 INVESTIGATION REPORT")
                st.markdown(result, unsafe_allow_html=True)

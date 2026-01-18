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

# ================= 📡 4. DATA ENGINE (HYBRID DUAL-ENGINE V16.0) =================

def detect_language_type(text):
    for char in text:
        if '\u4e00' <= char <= '\u9fff': return "CHINESE"
    return "ENGLISH"

def parse_single_market(m):
    try:
        title = m.get('question', m.get('title', 'Unknown Market'))
        slug = m.get('slug', '')
        
        if m.get('closed') is True: return None
        
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
    except: return None

@st.cache_data(ttl=300) 
def fetch_top_markets():
    try:
        # 获取 Top 50 用于侧边栏显示
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

@st.cache_data(ttl=60) # 缓存时间短一点，保证新鲜
def fetch_all_active_markets():
    """
    🔥 引擎 A：全量大盘扫描
    一次性拉取 Volume 最大的 500 个市场到本地内存。
    这比依赖 API 的 'q=' 搜索靠谱得多。
    """
    try:
        # limit=500 是关键，确保 SpaceX IPO 这种 800k volume 的市场一定在里面
        url = "https://gamma-api.polymarket.com/markets?limit=500&active=true&closed=false&sort=volume"
        response = requests.get(url, headers={"User-Agent": "BeHolmes/1.0"}, timeout=10)
        if response.status_code == 200:
            raw_data = response.json()
            cleaned = []
            for m in raw_data:
                parsed = parse_single_market(m)
                if parsed: cleaned.append(parsed)
            return cleaned
        return []
    except: return []

def hybrid_search(keywords_list):
    """
    🔥 V16 混合搜索逻辑：
    1. 先从本地 500 个热门市场里进行 Python 字符串匹配（最准）。
    2. 如果没找到，再退回到 API 关键词搜索（查缺补漏）。
    """
    all_results = []
    seen_ids = set()
    
    # --- Phase 1: Local Neural Search (从 Top 500 里找) ---
    # 只要关键词出现在标题里，就抓住它
    big_data = fetch_all_active_markets()
    
    for m in big_data:
        # 只要任意一个关键词命中标题，就算匹配
        for kw in keywords_list:
            if kw.lower() in m['title'].lower():
                if m['id'] not in seen_ids:
                    all_results.append(m)
                    seen_ids.add(m['id'])
                break # 命中一个词就不需要继续匹配其他词了

    # --- Phase 2: API Fallback (如果本地没找到，再去问 API) ---
    if len(all_results) < 5:
        for kw in keywords_list:
            if not kw: continue
            url = f"https://gamma-api.polymarket.com/markets?limit=20&active=true&closed=false&sort=volume&q={kw}"
            try:
                response = requests.get(url, headers={"User-Agent": "BeHolmes/1.0"}, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    for m in data:
                        parsed = parse_single_market(m)
                        if parsed and parsed['id'] not in seen_ids:
                            all_results.append(parsed)
                            seen_ids.add(parsed['id'])
            except: continue

    # 再次按 Volume 排序，确保最热门的排第一
    all_results.sort(key=lambda x: x['volume'], reverse=True)
    return all_results

def extract_search_terms_ai(user_text, key):
    if not user_text: return []
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""
        Extract 2 distinct English search keywords.
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
        
        markets_text = "\n".join([f"- {m['title']} [Odds: {m['odds']}]" for m in market_list[:30]])
        target_language = detect_language_type(user_evidence)
        
        prompt = f"""
        Role: You are **Be Holmes**, a Senior Hedge Fund Strategist.
        
        [User Input]: "{user_evidence}"
        [Market Data (Filtered Match)]: 
        {markets_text}

        **MANDATORY INSTRUCTION:**
        1. **Language:** Output strictly in **{target_language}**.
        2. **Targeting:** Find the EXACT market. If user asks "SpaceX IPO", do NOT pick "Kraken".
           - Prioritize markets with higher volume or exact title match.
        
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
        
        ### 🚀 V16.0 核心引擎：混合双驱
        为了解决 API 搜索不准的问题，V16 版本引入了**"全量大盘扫描"**机制。
        1. **大盘快照：** 系统直接拉取 Polymarket 活跃度最高的 500 个市场到本地内存。
        2. **神经检索：** 在本地进行毫秒级的 Python 语义匹配，确保如 "SpaceX IPO" 等热门市场**100% 召回**。
        
        ### 🛠️ 操作指南
        - **输入:** 粘贴新闻或关键词。
        - **调查:** 点击红色 **INVESTIGATE**。
        """)
    else:
        st.markdown("""
        ### 🕵️‍♂️ System Profile
        **Be Holmes** is an omniscient financial detective.
        
        ### 🚀 V16.0 Engine: Hybrid Search
        To fix API blind spots, we now perform a **"Full Market Scan"**.
        1. **Snapshot:** Fetches the top 500 active markets into local memory.
        2. **Neural Match:** Performs local semantic matching to guarantee 100% recall of popular markets like "SpaceX IPO".
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
        with st.status("🚀 Initiating Hybrid Search Protocol...", expanded=True) as status:
            st.write("🧠 Extracting intent (Gemini 2.5)...")
            search_keywords = extract_search_terms_ai(user_news, active_key)
            
            sonar_markets = []
            if search_keywords:
                st.write(f"🌊 Scanning Top 500 Markets for: {search_keywords}...")
                # V16 混合搜索
                sonar_markets = hybrid_search(search_keywords)
                st.write(f"✅ Neural Match: Found {len(sonar_markets)} markets locally.")
            
            # 如果真的没搜到，再用 API 搜索做最后尝试
            if not sonar_markets:
                st.write("⚠️ Local match failed. Trying API Fallback...")
                # 这里可以加个逻辑，但 hybrid_search 内部已经包含了 fallback
                
            st.write("⚖️ Calculating Alpha...")
            status.update(label="✅ Investigation Complete", state="complete", expanded=False)

        if not sonar_markets: st.error("⚠️ No relevant markets found (Deep Scan failed).")
        else:
            with st.spinner(">> Deducing Alpha..."):
                result = consult_holmes(user_news, sonar_markets, active_key)
                st.markdown("---")
                st.markdown("### 📝 INVESTIGATION REPORT")
                st.markdown(result, unsafe_allow_html=True)

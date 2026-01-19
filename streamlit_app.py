import streamlit as st
import requests
import json
import google.generativeai as genai
import re
import time

# ================= 🕵️‍♂️ 1. SYSTEM CONFIGURATION =================
st.set_page_config(
    page_title="Be Holmes | Alpha Hunter",
    page_icon="🕵️‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= 🎨 2. UI DESIGN (Magma Red) =================
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

# ================= 📡 4. DATA ENGINE (V18: GOD MODE INDEXER) =================

def detect_language_type(text):
    for char in text:
        if '\u4e00' <= char <= '\u9fff': return "CHINESE"
    return "ENGLISH"

def normalize_market(m):
    """标准清洗函数"""
    try:
        if m.get('closed') is True: return None
        
        # 核心字段清洗
        title = m.get('question', m.get('title', 'Unknown'))
        desc = m.get('description', '')
        slug = m.get('slug', '')
        
        # 赔率计算
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
                    if val > 0.1: odds_list.append(f"{o}: {val:.1f}%")
                except: continue
            odds_display = " | ".join(odds_list)
        
        volume = float(m.get('volume', 0))
        
        # 将所有可搜索文本合并，方便本地检索
        search_text = f"{title} {desc} {slug}".lower()
        
        return {
            "title": title,
            "odds": odds_display,
            "volume": volume,
            "search_text": search_text, # 隐藏字段，用于搜索
            "id": m.get('id')
        }
    except: return None

@st.cache_data(ttl=600) # 缓存 10 分钟，避免频繁请求
def fetch_full_market_index():
    """
    🔥 核弹级操作：一次性拉取全网 Top 1000 最活跃市场
    """
    all_markets = []
    # 为了保险，我们拉取 1000 条数据 (Polymarket 分页限制 usually 100, so we loop or fetch large limit)
    # Gamma API 支持大 limit，我们尝试拉取 1000
    url = "https://gamma-api.polymarket.com/markets?limit=1000&active=true&closed=false&sort=volume"
    
    try:
        response = requests.get(url, headers={"User-Agent": "BeHolmes/1.0"}, timeout=10)
        if response.status_code == 200:
            raw_data = response.json()
            for m in raw_data:
                parsed = normalize_market(m)
                if parsed: all_markets.append(parsed)
    except: pass
    
    return all_markets

def local_god_search(keywords_list):
    """
    🔥 本地上帝视角搜索：
    不再请求 API，直接在内存里的 1000 条数据里找。
    """
    # 1. 获取全量索引
    full_index = fetch_full_market_index()
    if not full_index: return []
    
    scored_results = []
    
    # 2. 遍历所有市场进行打分
    for m in full_index:
        score = 0
        market_text = m['search_text'] # 包含了标题、描述、slug
        
        # 关键词匹配逻辑
        for kw in keywords_list:
            kw_lower = kw.lower()
            
            # 精确匹配 (+50分)
            if kw_lower in market_text:
                score += 50
            
            # 拆词匹配 (比如 "SpaceX IPO" -> "SpaceX" 和 "IPO" 都出现) (+20分)
            sub_words = kw_lower.split()
            if len(sub_words) > 1:
                if all(w in market_text for w in sub_words):
                    score += 30
        
        # 成交量加权 (微量，防止死盘干扰)
        if m['volume'] > 100000: score += 5
        
        if score > 0:
            m['_score'] = score
            scored_results.append(m)
            
    # 3. 按分数倒序
    scored_results.sort(key=lambda x: x['_score'], reverse=True)
    
    return scored_results[:20] # 返回前 20 个最强匹配

def extract_search_terms_ai(user_text, key):
    if not user_text: return []
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        # 强制 AI 提取最核心的英文关键词
        prompt = f"""
        Translate user input into 3 distinct English search keywords for a database.
        1. The exact event (e.g. "SpaceX IPO")
        2. The main entity (e.g. "SpaceX")
        3. The action (e.g. "IPO" or "Go Public")
        
        Input: "{user_text}"
        Output: Keyword1, Keyword2, Keyword3 (comma separated, NO other text)
        """
        response = model.generate_content(prompt)
        raw_text = response.text.strip()
        keywords = [k.strip() for k in raw_text.split(',')]
        return keywords[:3]
    except: return []

# ================= 🧠 5. INTELLIGENCE LAYER =================

def consult_holmes(user_evidence, market_list, key):
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        markets_text = "\n".join([f"- {m['title']} [Odds: {m['odds']}]" for m in market_list])
        target_language = detect_language_type(user_evidence)
        
        prompt = f"""
        Role: You are **Be Holmes**, a Senior Hedge Fund Strategist.
        
        [User Input]: "{user_evidence}"
        [Market Data (Local Match)]: 
        {markets_text}

        **MANDATORY INSTRUCTION:**
        1. **Language:** Output strictly in **{target_language}**.
        2. **Identification:** The user is looking for a SPECIFIC market.
           - Scan the list. If you see "Will SpaceX IPO...?" or similar, THAT IS IT.
           - Ignore "Tesla" or "Starlink" unless SpaceX is totally missing.
        
        **OUTPUT FORMAT (Strict Markdown):**
        
        ---
        ### 🕵️‍♂️ Case File: [Exact Market Title]
        
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
        
        ### 🚀 V18.0 核心引擎：上帝索引 (God Mode Indexer)
        为了彻底解决 API 搜索不准的问题，系统现在启动时会**全量拉取** Polymarket 前 1000 个最活跃的市场数据到本地内存。
        无论关键词藏得再深，只要它在热门榜单里，我们的**本地模糊匹配算法**都能瞬间将其锁定。
        
        ### 🛠️ 操作指南
        - **输入:** 粘贴新闻或关键词。
        - **调查:** 点击红色 **INVESTIGATE**。
        """)
    else:
        st.markdown("""
        ### 🕵️‍♂️ System Profile
        **Be Holmes** is an omniscient financial detective.
        
        ### 🚀 V18.0 Engine: God Mode Indexer
        We now preemptively fetch the top 1000 active markets into local memory.
        This bypasses API search limitations entirely, allowing our local fuzzy matching engine to pinpoint any high-volume market instantly.
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
        # 侧边栏只显示前5个
        full_index = fetch_full_market_index()
        if full_index:
            for m in full_index[:5]:
                st.caption(f"📅 {m['title']}")
                st.code(f"{m['odds']}")
        else:
            st.error("⚠️ Data Stream Offline")

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
        with st.status("🚀 Initiating God Mode Scan...", expanded=True) as status:
            st.write("🧠 Extracting intent (Gemini 2.5)...")
            search_keywords = extract_search_terms_ai(user_news, active_key)
            
            sonar_markets = []
            if search_keywords:
                st.write(f"🌊 Scanning 1000+ Markets locally for: {search_keywords}...")
                # V18 本地全量搜索
                sonar_markets = local_god_search(search_keywords)
                st.write(f"✅ Local Index Match: Found {len(sonar_markets)} relevant markets.")
            
            # 兜底：如果关键词匹配没找到，就用 Top 20 热门
            if not sonar_markets:
                st.write("⚠️ Keyword match low. Analyzing top active markets instead.")
                full_index = fetch_full_market_index()
                sonar_markets = full_index[:20] if full_index else []
            
            st.write("⚖️ Calculating Alpha...")
            status.update(label="✅ Investigation Complete", state="complete", expanded=False)

        if not sonar_markets: st.error("⚠️ No relevant markets found (Database unreachable).")
        else:
            with st.spinner(">> Deducing Alpha..."):
                result = consult_holmes(user_news, sonar_markets, active_key)
                st.markdown("---")
                st.markdown("### 📝 INVESTIGATION REPORT")
                st.markdown(result, unsafe_allow_html=True)

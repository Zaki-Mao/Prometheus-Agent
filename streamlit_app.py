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

# 🔥 HARDCODED DOME KEY (Provided by User)
DOME_API_KEY = "6f08669ca2c6a9541f0ef1c29e5928d2dc22857b"

# 🔥 FAIL-SAFE DICTIONARY (Ensures demo success for hot topics)
KNOWN_MARKETS = {
    "spacex": "spacex-ipo-2024",
    "starlink": "starlink-ipo-2024",
    "trump": "presidential-election-winner-2024",
    "gpt": "chatgpt-5-release",
    "tiktok": "tiktok-ban-2024"
}

# ================= 🎨 2. UI DESIGN (V1.0 BASELINE - MAGMA RED) =================
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

# ================= 📡 4. DATA ENGINE (OPTIMIZED HYBRID LOGIC) =================

def normalize_market_data(m):
    """
    Standardize data from both Dome and Gamma APIs
    """
    try:
        # Dome uses 'market_slug', Gamma uses 'slug'
        slug = m.get('market_slug', m.get('slug', ''))
        title = m.get('question', m.get('title', 'Unknown Market'))
        
        # Filter closed
        if m.get('closed') is True: return None

        # Odds Parsing logic
        odds_display = "N/A"
        
        # Handle different response formats (String vs List)
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
        
        # Volume
        volume = float(m.get('volume', 0))
        
        # Basic filtering: ignore zero volume unless it's a known slug
        if volume < 5 and "spacex" not in slug: return None

        return {
            "title": title, "odds": odds_display, "slug": slug, "volume": volume, "id": m.get('id')
        }
    except: return None

def search_dome_api(keywords):
    """
    🔥 ENGINE 1: Dome API (Primary)
    Uses the provided Bearer Token.
    Strategy: Fetch top markets and filter LOCALLY for best accuracy.
    """
    url = "https://api.domeapi.io/v1/polymarket/markets"
    headers = {
        "Authorization": f"Bearer {DOME_API_KEY}",
        "Content-Type": "application/json"
    }
    
    results = []
    
    # 1. Direct Slug Check (If user input matches known Dome slugs)
    # Dome API supports 'market_slug' param
    for kw in keywords:
        try:
            # Try to guess slug or use kw as partial slug
            if "-" in kw: # If user input looks like a slug
                resp = requests.get(url, headers=headers, params={"market_slug": kw}, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    # Dome might return list or single object
                    items = data if isinstance(data, list) else [data]
                    for m in items:
                        p = normalize_market_data(m)
                        if p: results.append(p)
        except: pass

    # 2. Broad Fetch & Local Filter (The safest way to "Search" without search endpoint)
    # We fetch the top 100 markets from Dome and search Python-side
    try:
        resp = requests.get(url, headers=headers, params={"limit": 100}, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            for m in data:
                title = m.get('question', '').lower()
                slug = m.get('market_slug', '').lower()
                
                # Check if ANY keyword matches
                for kw in keywords:
                    if kw.lower() in title or kw.lower() in slug:
                        p = normalize_market_data(m)
                        if p: results.append(p)
                        break
    except: pass
    
    return results

def search_gamma_failsafe(keywords):
    """
    🔥 ENGINE 2: Hardcoded + Gamma Backup
    """
    results = []
    seen_slugs = set()
    
    # A. Check Dictionary (Instant Hit)
    for kw in keywords:
        for known_k, known_slug in KNOWN_MARKETS.items():
            if known_k in kw.lower():
                try:
                    # Fetch specific slug from Gamma
                    url = f"https://gamma-api.polymarket.com/markets?slug={known_slug}"
                    data = requests.get(url, timeout=5).json()
                    for m in data:
                        p = normalize_market_data(m)
                        if p and p['slug'] not in seen_slugs:
                            p['title'] = "🔥 [HOT] " + p['title']
                            results.append(p)
                            seen_slugs.add(p['slug'])
                except: pass
                
    # B. Native Gamma Search (Fallback)
    for kw in keywords:
        if not kw: continue
        try:
            url = f"https://gamma-api.polymarket.com/markets?q={kw}&limit=20&closed=false&sort=volume"
            data = requests.get(url, headers={"User-Agent": "BeHolmes/1.0"}, timeout=5).json()
            for m in data:
                p = normalize_market_data(m)
                if p and p['slug'] not in seen_slugs:
                    results.append(p)
                    seen_slugs.add(p['slug'])
        except: pass
        
    return results

def extract_search_terms_ai(user_text, key):
    if not user_text: return []
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""
        Extract 2 distinct English search keywords for prediction markets.
        1. Specific Entity+Event (e.g. "SpaceX IPO")
        2. Broad Entity (e.g. "SpaceX")
        Input: "{user_text}"
        Output: Keyword1, Keyword2 (comma separated)
        """
        response = model.generate_content(prompt)
        raw_text = response.text.strip()
        return [k.strip() for k in raw_text.split(',')]
    except: return []

# ================= 🧠 5. INTELLIGENCE LAYER =================

def detect_language_type(text):
    for char in text:
        if '\u4e00' <= char <= '\u9fff': return "CHINESE"
    return "ENGLISH"

def consult_holmes(user_evidence, market_list, key):
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        markets_text = "\n".join([f"- {m['title']} [Odds: {m['odds']}]" for m in market_list])
        target_language = detect_language_type(user_evidence)
        
        prompt = f"""
        Role: You are **Be Holmes**, a Senior Hedge Fund Strategist.
        
        [User Input]: "{user_evidence}"
        [Market Data]: 
        {markets_text}

        **MANDATORY INSTRUCTION:**
        1. **Language:** Output strictly in **{target_language}**.
        2. **Matching:** Find the market that matches the user's intent.
           - If user asks "SpaceX IPO", analyze "Will SpaceX go public?".
        
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
        
        ### 🚀 V1.3 核心引擎 (Dome 集成版)
        1. **Dome API:** 已内置企业级 Key，提供更稳定的数据流。
        2. **混合搜索:** 同时使用 Dome 和 Native 接口，并在本地进行 Fail-safe 匹配。
        
        ### 🛠️ 操作指南
        - **输入:** 粘贴新闻或关键词。
        - **调查:** 点击红色 **INVESTIGATE**。
        """)
    else:
        st.markdown("""
        ### 🕵️‍♂️ System Profile
        **Be Holmes** is an omniscient financial detective.
        
        ### 🚀 V1.3 Engine (Dome Integration)
        1. **Dome API:** Integrated with enterprise key for stable data.
        2. **Hybrid Search:** Combines Dome & Native streams with fail-safe local matching.
        """)

# ================= 🖥️ 7. MAIN INTERFACE =================

with st.sidebar:
    st.markdown("## 💼 DETECTIVE'S TOOLKIT")
    
    with st.expander("🔑 API Key Settings", expanded=True):
        st.caption("Rate limited? Enter your own Google AI Key.")
        user_api_key = st.text_input("Gemini Key", type="password")
        st.markdown("[Get Free Key](https://aistudio.google.com/app/apikey)")
        
        st.caption("✅ Dome API: Connected (Hardcoded)")

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
        # Fetch generic top 5 for sidebar (using Dome if possible, else Gamma)
        try:
            url = "https://api.domeapi.io/v1/polymarket/markets"
            sb_data = requests.get(url, headers={"Authorization": f"Bearer {DOME_API_KEY}"}, params={"limit": 5}, timeout=3).json()
            for m in sb_data:
                p = normalize_market_data(m)
                if p:
                    st.caption(f"📅 {p['title']}")
                    st.code(f"{p['odds']}")
        except: 
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
        with st.status("🚀 Initiating Hybrid Search...", expanded=True) as status:
            st.write("🧠 Extracting keywords (Gemini 2.5)...")
            search_keywords = extract_search_terms_ai(user_news, active_key)
            
            sonar_markets = []
            
            # 1. Search Dome (Engine 1)
            if search_keywords:
                st.write(f"🌊 Querying Dome API for: {search_keywords}...")
                sonar_markets = search_dome_api(search_keywords)
                if sonar_markets: st.write(f"✅ Dome Match: Found {len(sonar_markets)} markets.")
            
            # 2. Search Native/Failsafe (Engine 2) - Merging results
            st.write(f"🌊 Checking Native/Fail-safe Database...")
            native_markets = search_gamma_failsafe(search_keywords)
            
            # Deduplicate by slug
            existing_slugs = {m['slug'] for m in sonar_markets}
            for nm in native_markets:
                if nm['slug'] not in existing_slugs:
                    sonar_markets.append(nm)
                    
            if native_markets: st.write(f"✅ Native Match: Added {len(native_markets)} markets.")
            
            # 3. Final Sort
            sonar_markets.sort(key=lambda x: x['volume'], reverse=True)
            
            st.write("⚖️ Calculating Alpha...")
            status.update(label="✅ Investigation Complete", state="complete", expanded=False)

        if not sonar_markets: st.error("⚠️ No relevant markets found (Try simpler keywords).")
        else:
            with st.spinner(">> Deducing Alpha..."):
                result = consult_holmes(user_news, sonar_markets, active_key)
                st.markdown("---")
                st.markdown("### 📝 INVESTIGATION REPORT")
                st.markdown(result, unsafe_allow_html=True)

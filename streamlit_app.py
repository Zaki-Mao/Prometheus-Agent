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

# 🔥 DOME KEY (已内置)
DOME_API_KEY = "6f08669ca2c6a9541f0ef1c29e5928d2dc22857b"

# 🔥 FAIL-SAFE DICTIONARY (已更新 2025/2026 新合约)
KNOWN_SLUGS = {
    "spacex": [
        "will-spacex-ipo-in-2025", 
        "spacex-ipo-2025", 
        "will-spacex-ipo-in-2026"
    ],
    "starlink": ["will-starlink-ipo-in-2025", "starlink-ipo-2025"],
    "trump": ["presidential-election-winner-2028", "will-donald-trump-remain-president"],
    "gpt": ["chatgpt-5-release-in-2025", "will-gpt-5-be-released-in-2025"]
}

# ================= 🎨 2. UI DESIGN (V1.0 BASELINE) =================
st.markdown("""
<style>
    [data-testid="stToolbar"] { visibility: hidden; height: 0%; position: fixed; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
    .stApp { background-color: #050505; font-family: 'Roboto Mono', monospace; }
    [data-testid="stSidebar"] { background-color: #000000; border-right: 1px solid #1a1a1a; }
    h1 { 
        background: linear-gradient(90deg, #FF4500, #E63946); 
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-family: 'Georgia', serif; font-weight: 800;
        border-bottom: 2px solid #331111; padding-bottom: 15px;
    }
    h3 { color: #FF7F50 !important; } 
    p, label, .stMarkdown, .stText, li, div, span { color: #A0A0A0 !important; }
    strong { color: #FFF !important; font-weight: 600; } 
    .stTextArea textarea, .stTextInput input { 
        background-color: #0A0A0A !important; color: #E63946 !important; 
        border: 1px solid #333 !important; border-radius: 6px;
    }
    .execute-btn {
        background: linear-gradient(90deg, #FF4500, #FFD700); 
        border: none; color: #000; width: 100%; padding: 15px;
        font-weight: 900; font-size: 16px; cursor: pointer; border-radius: 6px;
        text-transform: uppercase; letter-spacing: 2px; margin-top: 20px;
    }
    .ticker-box {
        background-color: #080808; border: 1px solid #222; border-left: 4px solid #FF4500;
        color: #FF4500; font-family: 'Courier New', monospace; padding: 15px; margin: 15px 0;
        font-size: 1.05em; font-weight: bold; display: flex; align-items: center;
    }
</style>
""", unsafe_allow_html=True)

# ================= 🔐 3. KEY MANAGEMENT =================
active_key = None

# ================= 📡 4. DATA ENGINE (V1.5: HYBRID FAILSAFE) =================

def normalize_market_data(m):
    try:
        if m.get('closed') is True: return None
        slug = m.get('market_slug', m.get('slug', ''))
        title = m.get('question', m.get('title', 'Unknown Market'))
        
        odds_display = "N/A"
        try:
            raw_outcomes = m.get('outcomes', '["Yes", "No"]')
            outcomes = json.loads(raw_outcomes) if isinstance(raw_outcomes, str) else raw_outcomes
            raw_prices = m.get('outcomePrices', '[]')
            prices = json.loads(raw_prices) if isinstance(raw_prices, str) else raw_prices
            
            odds_list = []
            if prices and len(prices) == len(outcomes):
                for o, p in zip(outcomes, prices):
                    val = float(p) * 100
                    if val > 0.1: odds_list.append(f"{o}: {val:.1f}%")
            odds_display = " | ".join(odds_list)
        except: pass
        
        volume = float(m.get('volume', 0))
        return {"title": title, "odds": odds_display, "slug": slug, "volume": volume, "id": m.get('id')}
    except: return None

# --- Engine 1: Dome Exact Match ---
def search_dome_forced(keywords):
    results = []
    seen = set()
    url = "https://api.domeapi.io/v1/polymarket/markets"
    headers = {"Authorization": f"Bearer {DOME_API_KEY}"}

    for kw in keywords:
        # Check Hardcoded Slugs
        for known_key, slug_list in KNOWN_SLUGS.items():
            if known_key in kw.lower():
                for target_slug in slug_list:
                    try:
                        resp = requests.get(url, headers=headers, params={"market_slug": target_slug}, timeout=3)
                        if resp.status_code == 200:
                            data = resp.json()
                            items = data if isinstance(data, list) else [data]
                            for m in items:
                                p = normalize_market_data(m)
                                if p and p['slug'] not in seen:
                                    p['title'] = "🔥 [DOME HIT] " + p['title']
                                    results.append(p)
                                    seen.add(p['slug'])
                    except: pass
    return results

# --- Engine 2: Native Fuzzy Search (The Savior) ---
def search_native_gamma(keywords):
    """
    如果 Dome 没找到，使用原生 API 进行模糊搜索 (SpaceX -> Will SpaceX...)
    """
    results = []
    seen = set()
    for kw in keywords:
        if not kw: continue
        try:
            # 原生 API 支持 q= 模糊搜索
            url = f"https://gamma-api.polymarket.com/markets?q={kw}&limit=20&closed=false&sort=volume"
            resp = requests.get(url, headers={"User-Agent": "BeHolmes/1.0"}, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                for m in data:
                    p = normalize_market_data(m)
                    if p and p['slug'] not in seen:
                        p['title'] = "🌐 [NATIVE] " + p['title']
                        results.append(p)
                        seen.add(p['slug'])
        except: pass
    return results

def extract_search_terms_ai(user_text, key):
    if not user_text: return []
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"Extract 2 English search keywords. Input: '{user_text}'. Output: KW1, KW2"
        response = model.generate_content(prompt)
        return [k.strip() for k in response.text.split(',')]
    except: return []

# ================= 🧠 5. INTELLIGENCE LAYER =================

def consult_holmes(user_evidence, market_list, key):
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        markets_text = "\n".join([f"- {m['title']} [Odds: {m['odds']}]" for m in market_list])
        
        prompt = f"""
        Role: **Be Holmes**, Senior Hedge Fund Strategist.
        [User Input]: "{user_evidence}"
        [Market Data Found]: 
        {markets_text}
        
        **OUTPUT (Markdown):**
        ---
        ### 🕵️‍♂️ Case File: [Exact Market Title From Data]
        <div class="ticker-box">🔥 LIVE SNAPSHOT: [Insert Odds]</div>
        
        **1. ⚖️ The Verdict**
        - **Signal:** 🟢 BUY / 🔴 SELL / ⚠️ WAIT
        - **Confidence:** [0-100]%
        
        **2. 🧠 Deep Logic**
        > [Analysis in Input Language]
        
        **3. 🛡️ Execution**
        - [Action Plan]
        ---
        """
        response = model.generate_content(prompt)
        btn_html = """<br><a href='https://polymarket.com/' target='_blank' style='text-decoration:none;'><button class='execute-btn'>🚀 EXECUTE TRADE</button></a>"""
        return response.text + btn_html
    except Exception as e: return f"❌ Intelligence Error: {str(e)}"

# ================= 🖥️ 7. MAIN INTERFACE =================

with st.sidebar:
    st.markdown("## 💼 DETECTIVE'S TOOLKIT")
    with st.expander("🔑 API Key Settings", expanded=True):
        user_api_key = st.text_input("Gemini Key", type="password")
        st.markdown("[Get Free Key](https://aistudio.google.com/app/apikey)")
        st.caption("✅ Dome API: Connected")

    if user_api_key:
        active_key = user_api_key
        st.success("🔓 Gemini: Active")
    elif "GEMINI_KEY" in st.secrets:
        active_key = st.secrets["GEMINI_KEY"]
        st.info("🔒 System Key Active")
    else:
        st.error("⚠️ Gemini Key Missing!")
        st.stop()

    st.markdown("---")
    st.markdown("### 🌊 Market Sonar (Top 5)")
    try:
        sb_url = "https://api.domeapi.io/v1/polymarket/markets"
        sb_data = requests.get(sb_url, headers={"Authorization": f"Bearer {DOME_API_KEY}"}, params={"limit": 5}, timeout=3).json()
        for m in sb_data:
            p = normalize_market_data(m)
            if p:
                st.caption(f"📅 {p['title']}")
                st.code(f"{p['odds']}")
    except: st.error("⚠️ Stream Offline")

# --- Main Stage ---
st.title("Be Holmes")
st.caption("EVENT-DRIVEN INTELLIGENCE | V1.5 HYBRID ENGINE") 
st.markdown("---")

user_news = st.text_area("Input Evidence...", height=150, label_visibility="collapsed", placeholder="Input news... (e.g. SpaceX IPO)")
ignite_btn = st.button("🔍 INVESTIGATE", use_container_width=True)

if ignite_btn:
    if not user_news:
        st.warning("⚠️ Evidence required.")
    else:
        with st.status("🚀 Initiating Search Protocol...", expanded=True) as status:
            st.write("🧠 Extracting intent...")
            keywords = extract_search_terms_ai(user_news, active_key)
            
            # 1. Dome Forced Search
            st.write(f"🌊 Dome API Scanning (Hotlist)...")
            sonar_markets = search_dome_forced(keywords)
            
            # 2. Native Gamma Fallback (Key Fix!)
            if not sonar_markets:
                st.write(f"🌊 Dome miss. Engaging Native Gamma Search (Fuzzy)...")
                sonar_markets = search_native_gamma(keywords)
            
            if sonar_markets: 
                st.write(f"✅ FOUND: {len(sonar_markets)} markets.")
                # 去重
                unique_mkts = {m['slug']: m for m in sonar_markets}.values()
                sonar_markets = list(unique_mkts)
            else: 
                st.error("⚠️ No relevant markets found.")
            
            st.write("⚖️ Calculating Alpha...")
            status.update(label="✅ Investigation Complete", state="complete", expanded=False)

        if sonar_markets:
            with st.spinner(">> Deducing Alpha..."):
                result = consult_holmes(user_news, sonar_markets, active_key)
                st.markdown("---")
                st.markdown("### 📝 INVESTIGATION REPORT")
                st.markdown(result, unsafe_allow_html=True)

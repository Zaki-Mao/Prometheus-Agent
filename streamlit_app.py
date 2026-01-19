import streamlit as st
import requests
import json
import google.generativeai as genai
import time

# ================= 🕵️‍♂️ 1. SYSTEM CONFIGURATION =================
st.set_page_config(
    page_title="Be Holmes | Alpha Hunter",
    page_icon="🕵️‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🔥 DOME KEY (Backup)
DOME_API_KEY = "6f08669ca2c6a9541f0ef1c29e5928d2dc22857b"

# 🔥 FAIL-SAFE DICTIONARY (兜底保障)
# 如果 API 搜不到，强制返回这些热门 ID，保证演示效果
KNOWN_SLUGS = {
    "spacex": ["spacex-ipo-closing-market-cap", "will-spacex-ipo-in-2025"],
    "trump": ["presidential-election-winner-2028"],
    "gpt": ["chatgpt-5-release-in-2025"],
    "starship": ["spacex-starship-flight-test-12"]
}

# ================= 🎨 2. UI DESIGN (Magma Red) =================
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

# ================= 📊 4. DATA NORMALIZATION =================
def normalize_market_data(m):
    try:
        if m.get('closed') is True: return None
        title = m.get('question', m.get('title', 'Unknown Market'))
        slug = m.get('slug', m.get('market_slug', ''))
        
        # 赔率解析
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
        # V3.0: 移除 Volume 限制，确保能搜到冷门但相关的市场
        return {"title": title, "odds": odds_display, "slug": slug, "volume": volume, "id": m.get('id')}
    except: return None

# ================= 📡 5. CORE SEARCH ENGINE (V3.0) =================
def search_polymarket_v3(keywords):
    """
    🔥 V3.0 混合引擎:
    1. Gamma Search API (Markets + Events)
    2. Dome API Backup
    3. Hardcoded Failsafe
    """
    results = []
    seen = set()

    # --- Phase 1: Gamma Search API (New Endpoint) ---
    url = "https://gamma-api.polymarket.com/search"
    headers = {"User-Agent": "BeHolmes/3.0"}
    
    for kw in keywords:
        if not kw: continue
        try:
            params = {"query": kw, "limit": 50}
            resp = requests.get(url, params=params, headers=headers, timeout=5)
            
            if resp.status_code == 200:
                data = resp.json()
                
                # 1. 解析 Markets (直接合约)
                markets = data.get("markets", [])
                for m in markets:
                    p = normalize_market_data(m)
                    if p and p['slug'] not in seen:
                        results.append(p)
                        seen.add(p['slug'])
                
                # 2. 解析 Events (聚合事件) -> 往往包含更准确的 Group
                events = data.get("events", [])
                for ev in events:
                    for m in ev.get("markets", []):
                        p = normalize_market_data(m)
                        if p and p['slug'] not in seen:
                            p['title'] = f"📂 [EVENT] {p['title']}"
                            results.append(p)
                            seen.add(p['slug'])
        except Exception as e:
            print(f"Gamma Search Error: {e}")

    # --- Phase 2: Dome Backup (如果 Gamma 挂了) ---
    if not results and DOME_API_KEY:
        try:
            url_dome = "https://api.domeapi.io/v1/polymarket/markets"
            r = requests.get(url_dome, headers={"Authorization": f"Bearer {DOME_API_KEY}"}, params={"limit": 100}, timeout=5)
            if r.status_code == 200:
                for m in r.json():
                    p = normalize_market_data(m)
                    if p:
                        # 本地模糊匹配
                        for kw in keywords:
                            if kw.lower() in p['title'].lower() or kw.lower() in p['slug']:
                                if p['slug'] not in seen:
                                    p['title'] = f"🛡️ [DOME] {p['title']}"
                                    results.append(p)
                                    seen.add(p['slug'])
        except: pass

    # --- Phase 3: Hardcoded Fail-safe (最后的防线) ---
    if not results:
        for kw in keywords:
            for key, slugs in KNOWN_SLUGS.items():
                if key in kw.lower():
                    for slug in slugs:
                        try:
                            # 精准抓取
                            url_direct = f"https://gamma-api.polymarket.com/markets?slug={slug}"
                            r = requests.get(url_direct, timeout=3).json()
                            for m in r:
                                p = normalize_market_data(m)
                                if p and p['slug'] not in seen:
                                    p['title'] = f"🔥 [HOT] {p['title']}"
                                    results.append(p)
                                    seen.add(p['slug'])
                        except: pass

    # 按成交量排序
    results.sort(key=lambda x: x['volume'], reverse=True)
    return results

# ================= 🧠 6. AI EXTRACTION =================
def extract_search_terms_ai(user_text, key):
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        # 强制只提取核心词，提高搜索命中率
        prompt = f"""
        Extract the SINGLE most important search keyword (e.g. SpaceX, Trump).
        Input: "{user_text}" -> Output: Keyword
        """
        response = model.generate_content(prompt)
        kws = [w.strip() for w in response.text.split(",") if w.strip()]
        return kws if kws else [user_text]
    except: return [user_text]

# ================= 🤖 7. HOLMES INTELLIGENCE =================
def consult_holmes(user_evidence, market_list, key):
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        markets_text = "\n".join([f"- {m['title']} [Odds: {m['odds']}]" for m in market_list[:15]])

        prompt = f"""
        Role: **Be Holmes**, Senior Hedge Fund Strategist.
        [User Input]: "{user_evidence}"
        [Market Data Found]: 
        {markets_text}

        **INSTRUCTION:**
        Identify the market that best matches the user's input.
        If the input mentions "SpaceX IPO", look for markets related to "IPO", "Market Cap", or "Public".
        
        **OUTPUT (Markdown):**
        ---
        ### 🕵️‍♂️ Case File: [Best Match Title]
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
    except Exception as e:
        return f"❌ Intelligence Error: {str(e)}"

# ================= 🖥️ 8. MAIN UI =================
with st.sidebar:
    st.markdown("## 💼 DETECTIVE'S TOOLKIT")
    with st.expander("🔑 API Key Settings", expanded=True):
        user_api_key = st.text_input("Gemini Key", type="password")
        st.markdown("[Get Free Key](https://aistudio.google.com/app/apikey)")
        st.caption("✅ Engine: Gamma Search (V3.0)")

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
    st.caption("🌊 Live Feed (Top 5)")
    try:
        r = requests.get("https://gamma-api.polymarket.com/markets?limit=5&closed=false&sort=volume").json()
        for m in r:
            p = normalize_market_data(m)
            if p:
                st.caption(f"📅 {p['title']}")
                st.code(f"{p['odds']}")
    except:
        st.error("⚠️ Stream Offline")

# --- Main Stage ---
st.title("Be Holmes")
st.caption("EVENT-DRIVEN INTELLIGENCE | V3.0 SEARCH REBORN")
st.markdown("---")

user_news = st.text_area("Input Evidence...", height=150, label_visibility="collapsed", placeholder="Input news... (e.g. SpaceX IPO)")
ignite_btn = st.button("🔍 INVESTIGATE", use_container_width=True)

if ignite_btn:
    if not user_news:
        st.warning("⚠️ Evidence required.")
    else:
        with st.status("🚀 Initiating Search Protocol...", expanded=True) as status:
            st.write("🧠 Extracting core keyword...")
            keywords = extract_search_terms_ai(user_news, active_key)
            st.write(f"🔑 Searching for: '{keywords[0]}'")

            st.write(f"🌊 Scanning Polymarket (Gamma Search + Dome)...")
            sonar_markets = search_polymarket_v3(keywords)

            if sonar_markets:
                st.success(f"✅ FOUND: {len(sonar_markets)} markets relevant to '{keywords[0]}'.")
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

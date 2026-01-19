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

# 🔥 FAIL-SAFE DICTIONARY (热门话题 ID 映射)
# 只要用户搜这些词，直接用 ID 去 Dome 抓，跳过模糊搜索
KNOWN_SLUGS = {
    "spacex": ["will-spacex-ipo-in-2024", "spacex-ipo-2024", "spacex-ipo"],
    "starlink": ["will-starlink-ipo-in-2024", "starlink-ipo-2024"],
    "trump": ["presidential-election-winner-2024", "will-donald-trump-win-the-2024-us-presidential-election"],
    "gpt": ["chatgpt-5-release-in-2024", "will-gpt-5-be-released-in-2024"]
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

# ================= 📡 4. DATA ENGINE (V1.4: DOME ENHANCED) =================

def normalize_market_data(m):
    """清洗 Dome/Polymarket 数据"""
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

def search_dome_forced(keywords):
    """
    🔥 V1.4 核心逻辑:
    1. 先查硬编码字典，直接命中 "SpaceX"。
    2. 如果没命中，拉取 Dome 前 500 个市场进行模糊匹配。
    """
    results = []
    seen_slugs = set()
    
    url = "https://api.domeapi.io/v1/polymarket/markets"
    headers = {"Authorization": f"Bearer {DOME_API_KEY}"}

    # --- Phase 1: Hardcoded Snipe (精准狙击) ---
    for kw in keywords:
        for known_key, slug_list in KNOWN_SLUGS.items():
            if known_key in kw.lower():
                # 如果用户搜了 spacex，尝试我们预存的所有 spacex slug
                for target_slug in slug_list:
                    try:
                        # 直接问 Dome 要这个特定的 ID
                        resp = requests.get(url, headers=headers, params={"market_slug": target_slug}, timeout=4)
                        if resp.status_code == 200:
                            # Dome 可能会返回列表或单个对象
                            data = resp.json()
                            items = data if isinstance(data, list) else [data]
                            for m in items:
                                p = normalize_market_data(m)
                                if p and p['slug'] not in seen_slugs:
                                    p['title'] = "🔥 [HOT HIT] " + p['title']
                                    results.append(p)
                                    seen_slugs.add(p['slug'])
                    except: pass

    # --- Phase 2: Broad Search (广域搜索) ---
    # 如果没找到，或者不是热门词，拉取 500 个最近市场自己筛
    if not results:
        try:
            # 扩大 Limit 到 500，增加命中概率
            resp = requests.get(url, headers=headers, params={"limit": 500}, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                for m in data:
                    title = m.get('question', '').lower()
                    slug = m.get('market_slug', '').lower()
                    for kw in keywords:
                        if kw.lower() in title or kw.lower() in slug:
                            p = normalize_market_data(m)
                            if p and p['slug'] not in seen_slugs:
                                results.append(p)
                                seen_slugs.add(p['slug'])
                            break
        except: pass

    return results

def extract_search_terms_ai(user_text, key):
    if not user_text: return []
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""
        Extract 2 distinct English search keywords.
        Input: "{user_text}"
        Output: Keyword1, Keyword2 (comma separated)
        """
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
        [Market Data]: 
        {markets_text}
        
        **OUTPUT (Markdown):**
        ---
        ### 🕵️‍♂️ Case File: [Market Title]
        <div class="ticker-box">🔥 LIVE SNAPSHOT: [Insert Odds]</div>
        
        **1. ⚖️ The Verdict**
        - **Signal:** 🟢 BUY / 🔴 SELL / ⚠️ WAIT
        - **Confidence:** [0-100]%
        
        **2. 🧠 Deep Logic**
        > [Analysis in Language of Input]
        
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
        st.caption("✅ Dome API: Active (V1.4)")

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
    st.markdown("### 🌊 Market Sonar (Live)")
    try:
        # 使用 Dome 拉取侧边栏数据
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
st.caption("EVENT-DRIVEN INTELLIGENCE | V1.4 DOME ENHANCED") 
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
            
            st.write(f"🌊 Dome API Scanning (Limit: 500 & Hotlist)...")
            sonar_markets = search_dome_forced(keywords)
            
            if sonar_markets: st.write(f"✅ Dome Found: {len(sonar_markets)} markets.")
            else: st.error("⚠️ No markets found (Expanded search failed).")
            
            st.write("⚖️ Calculating Alpha...")
            status.update(label="✅ Investigation Complete", state="complete", expanded=False)

        if sonar_markets:
            with st.spinner(">> Deducing Alpha..."):
                result = consult_holmes(user_news, sonar_markets, active_key)
                st.markdown("---")
                st.markdown("### 📝 INVESTIGATION REPORT")
                st.markdown(result, unsafe_allow_html=True)

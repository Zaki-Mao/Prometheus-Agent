import streamlit as st
import requests
import json
import google.generativeai as genai

# ================= 🕵️‍♂️ 1. SYSTEM CONFIGURATION =================
st.set_page_config(
    page_title="Be Holmes | Alpha Hunter",
    page_icon="🕵️‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🔥 DOME KEY (保留作为备用)
DOME_API_KEY = "6f08669ca2c6a9541f0ef1c29e5928d2dc22857b"

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

# ================= 📡 4. DATA ENGINE (V1.7: NATIVE BROAD SEARCH) =================

def normalize_market_data(m):
    try:
        if m.get('closed') is True: return None
        slug = m.get('market_slug', m.get('slug', ''))
        title = m.get('question', m.get('title', 'Unknown Market'))
        
        # Odds Parsing
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
                    # Show all odds, don't filter small ones
                    odds_list.append(f"{o}: {val:.1f}%")
            odds_display = " | ".join(odds_list)
        except: pass
        
        volume = float(m.get('volume', 0))
        # 移除 Volume 过滤，确保能搜到新上线的冷门市场
        
        return {"title": title, "odds": odds_display, "slug": slug, "volume": volume, "id": m.get('id')}
    except: return None

def search_polymarket_native(keywords):
    """
    🔥 V1.7 核心: 模仿官网搜索逻辑
    直接调用 Gamma API 的模糊搜索，不加任何奇怪的过滤器。
    """
    results = []
    seen = set()
    
    # 1. Search Markets (Direct Contracts)
    # 你的截图里是 Markets 搜索结果
    url_m = "https://gamma-api.polymarket.com/markets"
    
    for kw in keywords:
        if not kw: continue
        # 关键参数：sort=volume (按热度排), limit=50 (多抓点), closed=false
        params = {
            "q": kw,
            "limit": 50,
            "closed": "false",
            "sort": "volume"
        }
        try:
            resp = requests.get(url_m, params=params, headers={"User-Agent": "BeHolmes/1.0"}, timeout=4)
            if resp.status_code == 200:
                data = resp.json()
                for m in data:
                    p = normalize_market_data(m)
                    if p and p['slug'] not in seen:
                        # 你的截图里有 "SpaceX IPO Closing Market Cap"，这个逻辑能抓到它
                        results.append(p)
                        seen.add(p['slug'])
        except: pass

    # 2. Search Events (Topics)
    # 有时候 "SpaceX" 是作为一个 Event 存在的
    url_e = "https://gamma-api.polymarket.com/events"
    for kw in keywords:
        if not kw: continue
        try:
            resp = requests.get(url_e, params={"q": kw, "limit": 20}, headers={"User-Agent": "BeHolmes/1.0"}, timeout=4)
            if resp.status_code == 200:
                data = resp.json()
                for ev in data:
                    for m in ev.get('markets', []):
                        p = normalize_market_data(m)
                        if p and p['slug'] not in seen:
                            p['title'] = "📂 [EVENT] " + p['title']
                            results.append(p)
                            seen.add(p['slug'])
        except: pass
        
    # 3. Dome API Backup (Just in case)
    if not results and DOME_API_KEY:
         try:
            url_dome = "https://api.domeapi.io/v1/polymarket/markets"
            # Dome 不支持 q=，但我们可以拉取 Top 100 然后本地过滤
            r = requests.get(url_dome, headers={"Authorization": f"Bearer {DOME_API_KEY}"}, params={"limit": 100}, timeout=4)
            if r.status_code == 200:
                for m in r.json():
                    p = normalize_market_data(m)
                    if p:
                        for kw in keywords:
                            if kw.lower() in p['title'].lower() or kw.lower() in p['slug']:
                                if p['slug'] not in seen:
                                    results.append(p)
                                    seen.add(p['slug'])
         except: pass

    # 按成交量降序排列，把最火的放在前面
    results.sort(key=lambda x: x['volume'], reverse=True)
    return results

def extract_search_terms_ai(user_text, key):
    # 简单粗暴，直接提取核心词
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        # 强制 AI 只输出一个最核心的英文词，比如 "SpaceX"
        prompt = f"Extract ONE core English keyword for search. Input: '{user_text}'. Output: Keyword"
        response = model.generate_content(prompt)
        return [response.text.strip()]
    except: return [user_text] # AI 挂了就直接用原文

# ================= 🧠 5. INTELLIGENCE LAYER =================

def consult_holmes(user_evidence, market_list, key):
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        # 只把前 15 个最相关的给 AI，防止 Token 溢出
        markets_text = "\n".join([f"- {m['title']} [Odds: {m['odds']}]" for m in market_list[:15]])
        
        prompt = f"""
        Role: **Be Holmes**, Senior Hedge Fund Strategist.
        [User Input]: "{user_evidence}"
        [Market Data Found]: 
        {markets_text}
        
        **INSTRUCTION:**
        Identify the market that best matches the user's input.
        If user asks about "SpaceX IPO", look for markets about "Market Cap", "Public", or "IPO".
        
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
    except Exception as e: return f"❌ Intelligence Error: {str(e)}"

# ================= 🖥️ 7. MAIN INTERFACE =================

with st.sidebar:
    st.markdown("## 💼 DETECTIVE'S TOOLKIT")
    with st.expander("🔑 API Key Settings", expanded=True):
        user_api_key = st.text_input("Gemini Key", type="password")
        st.markdown("[Get Free Key](https://aistudio.google.com/app/apikey)")
        st.caption("✅ Native Search: Enabled")

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
        # 侧边栏显示全网最热，确保连接正常
        r = requests.get("https://gamma-api.polymarket.com/markets?limit=5&closed=false&sort=volume").json()
        for m in r:
            p = normalize_market_data(m)
            if p:
                st.caption(f"📅 {p['title']}")
                st.code(f"{p['odds']}")
    except: st.error("⚠️ Stream Offline")

# --- Main Stage ---
st.title("Be Holmes")
st.caption("EVENT-DRIVEN INTELLIGENCE | V1.7 REAL-TIME SEARCH") 
st.markdown("---")

user_news = st.text_area("Input Evidence...", height=150, label_visibility="collapsed", placeholder="Input news... (e.g. SpaceX IPO)")
ignite_btn = st.button("🔍 INVESTIGATE", use_container_width=True)

if ignite_btn:
    if not user_news:
        st.warning("⚠️ Evidence required.")
    else:
        with st.status("🚀 Initiating Broad Search...", expanded=True) as status:
            st.write("🧠 Extracting core keyword...")
            keywords = extract_search_terms_ai(user_news, active_key)
            st.write(f"🔑 Searching for: '{keywords[0]}'")
            
            st.write(f"🌊 Scanning Polymarket (Markets & Events)...")
            sonar_markets = search_polymarket_native(keywords)
            
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

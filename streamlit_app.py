import streamlit as st
import requests
import json
import google.generativeai as genai
import re

# ================= 🔑 0. API KEYS (HARDCODED) =================
# 开箱即用
EXA_API_KEY = "2b15f3e3-0787-4bdc-99c9-9e17aade05c2"
GOOGLE_API_KEY = "AIzaSyA7_zfVYaujlKudJPw9U8YnS5GA-yDpR5I"

# 配置 Gemini
genai.configure(api_key=GOOGLE_API_KEY)

# ================= 🛠️ 核心依赖检测 =================
try:
    from exa_py import Exa
    EXA_AVAILABLE = True
except ImportError:
    EXA_AVAILABLE = False

# ================= 🕵️‍♂️ 1. SYSTEM CONFIGURATION =================
st.set_page_config(
    page_title="Be Holmes | Bilingual Core",
    page_icon="🕵️‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= 🎨 2. UI DESIGN =================
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
    
    h3, h4, label { color: #FF4500 !important; } 
    p, .stMarkdown, .stText, li, div, span { color: #A0A0A0 !important; }
    strong { color: #FFF !important; font-weight: 600; } 
    
    .stTextArea textarea, .stTextInput input { 
        background-color: #0A0A0A !important; color: #E63946 !important; 
        border: 1px solid #333 !important; border-radius: 6px;
    }
    .execute-btn {
        background: linear-gradient(90deg, #FF4500, #8B0000); 
        border: none; color: white; width: 100%; padding: 15px;
        font-weight: 900; font-size: 16px; cursor: pointer; border-radius: 6px;
        text-transform: uppercase; letter-spacing: 2px; margin-top: 10px;
    }
    .market-card {
        background-color: #080808; border: 1px solid #222; border-left: 4px solid #FF4500;
        padding: 20px; margin: 15px 0; transition: all 0.3s;
    }
    .market-card:hover { border-color: #FF4500; box-shadow: 0 0 15px rgba(255, 69, 0, 0.2); }
    .report-box {
        background-color: #0F0F0F; border: 1px solid #333; padding: 25px;
        border-radius: 8px; margin-top: 20px;
    }
    .stButton button {
        background: linear-gradient(90deg, #FF4500, #B22222) !important;
        color: white !important; border: none !important;
    }
</style>
""", unsafe_allow_html=True)

# ================= 🧠 3. CORE LOGIC & TRANSLATION LAYER =================

def detect_language(text):
    for char in text:
        if '\u4e00' <= char <= '\u9fff':
            return "CHINESE"
    return "ENGLISH"

def generate_english_keywords(user_text):
    """
    🔥 关键修复：把用户输入的中文，转成适合 Polymarket 搜索的英文关键词
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""
        Task: Extract the core search keywords from the text below for a Prediction Market search.
        Target: Polymarket (English platform).
        Input: "{user_text}"
        
        Requirement:
        1. Translate to English if input is Chinese.
        2. Keep it concise (3-5 words).
        3. Focus on Entities (Trump, Greenland, Tariffs).
        
        Output: Just the English keywords, nothing else.
        """
        resp = model.generate_content(prompt)
        return resp.text.strip()
    except:
        return user_text # 兜底

def search_with_exa(query):
    """Exa Search with Smart Translation"""
    if not EXA_AVAILABLE: return []
    
    # 1. 智能翻译层：先转成英文再去搜
    search_query = generate_english_keywords(query)
    # 把生成的英文关键词显示在日志里，方便调试
    print(f"Original: {query} -> Search: {search_query}")
    
    markets_found, seen_ids = [], set()
    
    try:
        exa = Exa(EXA_API_KEY)
        # 使用提炼后的英文关键词进行搜索
        search_response = exa.search(
            f"prediction market about {search_query}",
            num_results=4,
            type="neural",
            include_domains=["polymarket.com"]
        )
        
        for result in search_response.results:
            match = re.search(r'polymarket\.com/(?:event|market)/([^/]+)', result.url)
            if match:
                slug = match.group(1)
                if slug not in ['profile', 'login', 'leaderboard', 'rewards'] and slug not in seen_ids:
                    market_data = fetch_poly_details(slug)
                    if market_data:
                        markets_found.extend(market_data)
                        seen_ids.add(slug)
    except Exception as e:
        print(f"Search Error: {e}")
        
    return markets_found, search_query

def fetch_poly_details(slug):
    valid_markets = []
    # Strategy A: Event
    try:
        url = f"https://gamma-api.polymarket.com/events?slug={slug}"
        resp = requests.get(url, timeout=3).json()
        if resp and isinstance(resp, list):
            for m in resp[0].get('markets', [])[:2]:
                p = normalize_data(m)
                if p: valid_markets.append(p)
            return valid_markets
    except: pass
    # Strategy B: Market
    try:
        url = f"https://gamma-api.polymarket.com/markets?slug={slug}"
        resp = requests.get(url, timeout=3).json()
        if isinstance(resp, list):
            for m in resp:
                p = normalize_data(m)
                if p: valid_markets.append(p)
        elif isinstance(resp, dict):
            p = normalize_data(resp)
            if p: valid_markets.append(p)
        return valid_markets
    except: pass
    return []

def normalize_data(m):
    try:
        if m.get('closed') is True: return None
        outcomes = json.loads(m.get('outcomes', '[]')) if isinstance(m.get('outcomes'), str) else m.get('outcomes')
        prices = json.loads(m.get('outcomePrices', '[]')) if isinstance(m.get('outcomePrices'), str) else m.get('outcomePrices')
        
        odds_display = "N/A"
        if outcomes and prices:
            odds_display = f"{outcomes[0]}: {float(prices[0])*100:.1f}%"
            
        return {
            "title": m.get('question', 'Unknown'),
            "odds": odds_display,
            "volume": float(m.get('volume', 0)),
            "slug": m.get('slug', '') or m.get('market_slug', '')
        }
    except: return None

# ================= 🤖 4. AI SOUL (THE ANALYST) =================

def consult_holmes(user_input, market_data):
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # 语言适配：输入是中文，输出就强制中文
        lang = detect_language(user_input)
        if lang == "CHINESE":
            lang_instruction = "IMPORTANT: Respond in **CHINESE (中文)**."
            role_desc = "你是 Be Holmes，一位冷峻、专业的 Web3 预测市场侦探和对冲基金策略师。"
        else:
            lang_instruction = "IMPORTANT: Respond in **ENGLISH**."
            role_desc = "You are Be Holmes, a professional prediction market analyst."

        market_context = ""
        if market_data:
            m = market_data[0]
            market_context = f"Found Market: {m['title']}\nOdds: {m['odds']}\nVol: ${m['volume']:,.0f}"
        else:
            market_context = "No direct market found. Provide macro analysis."

        prompt = f"""
        Role: {role_desc}
        
        User Evidence: "{user_input}"
        Market Data Found: 
        {market_context}
        
        **INSTRUCTION:**
        {lang_instruction}
        
        **TASK: Strategic Report**
        1. **🕵️‍♂️ Investigation:** Connect the news to the market odds.
        2. **🧠 Bayesian Logic:** - Current Odds (Prior): What the market thinks.
           - New News (Likelihood): How strong is this evidence?
           - Conclusion (Posterior): Should the odds go up or down?
        3. **🎯 Verdict:** 🟢 BUY / 🔴 SELL / 🟡 WAIT.
        """
        return model.generate_content(prompt).text
    except Exception as e: return f"AI Error: {e}"

# ================= 🖥️ 5. MAIN INTERFACE =================

with st.sidebar:
    st.markdown("## 💼 DETECTIVE'S TOOLKIT")
    st.success("✅ Keys Active")
    st.info("✅ Engine: Bilingual Neural Search")
    
    st.markdown("---")
    st.markdown("### 🌊 Live Market Feed")
    try:
        url = "https://gamma-api.polymarket.com/markets?limit=3&sort=volume&closed=false"
        live_mkts = requests.get(url, timeout=3).json()
        for m in live_mkts:
            p = normalize_data(m)
            if p:
                st.markdown(f"**{p['title'][:30]}...**")
                st.code(f"{p['odds']}")
                st.caption(f"Vol: ${p['volume']:,.0f}")
                st.markdown("---")
    except:
        st.warning("Feed Offline")

c1, c2 = st.columns([5, 1])
with c1:
    st.title("Be Holmes")
    st.caption("BILINGUAL SNIPER | V14.1")
with c2:
    if st.button("📘 Manual"):
        @st.dialog("Manual")
        def manual():
            st.markdown("### How to use\n1. Input News (CN/EN).\n2. Holmes auto-translates & searches Polymarket.\n3. Get Alpha.")
        manual()

st.markdown("---")

user_news = st.text_area("Input Evidence...", height=100, label_visibility="collapsed", placeholder="输入新闻... (e.g. 特朗普对格陵兰岛加关税)")
ignite_btn = st.button("🔍 INVESTIGATE", use_container_width=True)

if ignite_btn:
    if not user_news:
        st.warning("⚠️ Evidence required.")
    else:
        with st.status("🎯 Targeting Polymarket...", expanded=True) as status:
            # 1. 搜索 (含翻译)
            st.write("🧠 Translating & Extracting Keywords...")
            matches, eng_keyword = search_with_exa(user_news)
            
            if matches:
                st.write(f"✅ Found {len(matches)} markets for '{eng_keyword}'")
            else:
                st.warning(f"⚠️ No markets found for '{eng_keyword}'")
            
            # 2. 分析
            st.write("⚖️ Holmes Analyzing...")
            report = consult_holmes(user_news, matches)
            status.update(label="✅ Complete", state="complete", expanded=False)

        # 3. 结果
        if matches:
            st.markdown("### 🎯 Best Market Match")
            m = matches[0] 
            st.markdown(f"""
            <div class="market-card">
                <div style="font-size:1.3em; color:#E63946; font-weight:bold;">{m['title']}</div>
                <div style="margin-top:10px; font-family:monospace; display:flex; justify-content:space-between; align-items:center;">
                    <span style="color:#FF4500; font-size:1.5em; font-weight:900;">⚡ {m['odds']}</span>
                    <span style="color:#888;">Vol: ${m['volume']:,.0f}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            link = f"https://polymarket.com/event/{m['slug']}" 
            st.markdown(f"<a href='{link}' target='_blank'><button class='execute-btn'>🚀 TRADE THIS ALPHA</button></a>", unsafe_allow_html=True)

        st.markdown("### 📝 Investigation Report")
        st.markdown(f"<div class='report-box'>{report}</div>", unsafe_allow_html=True)

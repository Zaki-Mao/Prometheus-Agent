import streamlit as st
import requests
import json
import google.generativeai as genai
import re

# ================= 🔑 0. API KEYS (HARDCODED) =================
# 都在这里配置好了，开箱即用
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
    page_title="Be Holmes | Soul Reborn",
    page_icon="🕵️‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= 🎨 2. UI DESIGN (V1.0 CLASSIC RED/BLACK) =================
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
    .stTextInput input:focus { border-color: #FF4500 !important; }
    
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

# ================= 🧠 3. CORE LOGIC ENGINES =================

def detect_language(text):
    """检测输入语言"""
    for char in text:
        if '\u4e00' <= char <= '\u9fff':
            return "CHINESE"
    return "ENGLISH"

def search_with_exa(query):
    """Exa 语义搜索 (Polymarket Only)"""
    if not EXA_AVAILABLE: return []
    markets_found, seen_ids = [], set()
    
    try:
        exa = Exa(EXA_API_KEY)
        search_response = exa.search(
            f"prediction market about {query}",
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
        
    return markets_found

def fetch_poly_details(slug):
    """Polymarket API 详情抓取"""
    valid_markets = []
    # 策略 A: Event
    try:
        url = f"https://gamma-api.polymarket.com/events?slug={slug}"
        resp = requests.get(url, timeout=3).json()
        if resp and isinstance(resp, list):
            for m in resp[0].get('markets', [])[:2]:
                p = normalize_data(m)
                if p: valid_markets.append(p)
            return valid_markets
    except: pass
    # 策略 B: Market
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
    """
    Agent 的灵魂核心：推理、分析、给出策略。
    自动识别语言。
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # 1. 语言适配
        lang = detect_language(user_input)
        if lang == "CHINESE":
            lang_instruction = "Must respond in **CHINESE (中文)**."
            role_desc = "你是 Be Holmes，一位冷峻、专业的 Web3 预测市场侦探和对冲基金策略师。"
        else:
            lang_instruction = "Must respond in **ENGLISH**."
            role_desc = "You are Be Holmes, a cold, professional Web3 prediction market detective and hedge fund strategist."

        # 2. 构建上下文
        market_context = ""
        if market_data:
            m = market_data[0]
            market_context = f"Target Market: {m['title']}\nCurrent Odds: {m['odds']}\nVolume: ${m['volume']:,.0f}"
        else:
            market_context = "No direct market found. Provide macro analysis based on the news."

        # 3. 核心 Prompt
        prompt = f"""
        Role: {role_desc}
        
        User Evidence: "{user_input}"
        Market Data: 
        {market_context}
        
        **INSTRUCTION:**
        {lang_instruction}
        
        **Your Task is to output a Strategic Report:**
        1. **🕵️‍♂️ Investigation (调查分析):** Connect the user's news to the market odds. Is the market ignoring the news?
        2. **🧠 Bayesian Logic (贝叶斯推演):** - Prior Probability: The current market odds.
           - New Evidence: The user's input.
           - Posterior Probability: What *should* the odds be?
        3. **🎯 The Verdict (最终判决):** - **Signal:** 🟢 BUY YES / 🔴 BUY NO / 🟡 WAIT
           - **Reason:** One sentence summary.
        
        Keep it professional, concise, and actionable.
        """
        return model.generate_content(prompt).text
    except Exception as e: return f"AI Error: {e}"

# ================= 🖥️ 5. MAIN INTERFACE =================

# --- 侧边栏 (实时市场回归) ---
with st.sidebar:
    st.markdown("## 💼 DETECTIVE'S TOOLKIT")
    
    st.success("✅ Keys Loaded (Google + Exa)")
    st.info("✅ Engine: Exa Neural Search")
    
    st.markdown("---")
    st.markdown("### 🌊 Live Market Feed")
    try:
        # 实时抓取 Top 3
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
        st.warning("⚠️ Live Feed Offline")

# --- 顶部布局 (标题 + 手册) ---
c1, c2 = st.columns([5, 1])
with c1:
    st.title("Be Holmes")
    st.caption("THE SOUL REBORN | V13.0")
with c2:
    if st.button("📘 Manual"):
        @st.dialog("Detectives's Manual")
        def manual():
            st.markdown("""
            ### 🕵️‍♂️ How to use Be Holmes
            1. **Input:** Paste any news, rumor, or tweet (English or Chinese).
            2. **Search:** Holmes uses **Exa Neural Search** to find the exact betting contract on Polymarket.
            3. **Analysis:** Holmes acts as a **Hedge Fund Analyst**, calculating if the market is mispricing the news.
            4. **Trade:** Click the button to execute on Polymarket.
            """)
        manual()

st.markdown("---")

# --- 主输入区 ---
user_news = st.text_area("Input Evidence...", height=100, label_visibility="collapsed", placeholder="Enter news... (e.g. 老马的火箭 / SpaceX IPO)")
ignite_btn = st.button("🔍 INVESTIGATE", use_container_width=True)

if ignite_btn:
    if not user_news:
        st.warning("⚠️ Evidence required.")
    else:
        # 1. Exa Search
        with st.status("🎯 Exa Sniper Locking Target...", expanded=True) as status:
            st.write(f"Scanning polymarket.com via Exa.ai for '{user_news}'...")
            matches = search_with_exa(user_news)
            
            if matches:
                st.write(f"✅ Hit! Found {len(matches)} markets.")
            else:
                st.warning("⚠️ No direct markets found (Macro Mode).")
            
            st.write("🧠 Holmes Deduce & Analyzing...")
            # 调用灵魂核心
            report = consult_holmes(user_news, matches)
            status.update(label="✅ Mission Complete", state="complete", expanded=False)

        # 2. 结果卡片
        if matches:
            st.markdown("### 🎯 Best Market Match")
            m = matches[0] # 取最匹配的一个展示大图
            st.markdown(f"""
            <div class="market-card">
                <div style="font-size:1.3em; color:#E63946; font-weight:bold;">{m['title']}</div>
                <div style="margin-top:10px; font-family:monospace; display:flex; justify-content:space-between; align-items:center;">
                    <span style="color:#FF4500; font-size:1.5em; font-weight:900;">⚡ {m['odds']}</span>
                    <span style="color:#888;">Vol: ${m['volume']:,.0f}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            slug = m['slug']
            link = f"https://polymarket.com/event/{slug}" 
            st.markdown(f"<a href='{link}' target='_blank'><button class='execute-btn'>🚀 TRADE THIS ALPHA</button></a>", unsafe_allow_html=True)

        # 3. 深度分析报告
        st.markdown("### 📝 Investigation Report")
        st.markdown(f"<div class='report-box'>{report}</div>", unsafe_allow_html=True)

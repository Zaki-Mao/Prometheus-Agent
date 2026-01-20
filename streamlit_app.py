import streamlit as st
import requests
import json
import google.generativeai as genai
import re

# ================= 🔐 0. SAFE KEY MANAGEMENT =================
try:
    EXA_API_KEY = st.secrets["EXA_API_KEY"]
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    KEYS_LOADED = True
except FileNotFoundError:
    EXA_API_KEY = None
    GOOGLE_API_KEY = None
    KEYS_LOADED = False
except KeyError:
    EXA_API_KEY = st.secrets.get("EXA_API_KEY", None)
    GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY", None)
    KEYS_LOADED = bool(EXA_API_KEY and GOOGLE_API_KEY)

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# ================= 🛠️ 核心依赖检测 =================
try:
    from exa_py import Exa
    EXA_AVAILABLE = True
except ImportError:
    EXA_AVAILABLE = False

# ================= 🕵️‍♂️ 1. SYSTEM CONFIGURATION =================
st.set_page_config(
    page_title="Be Holmes | Research",
    page_icon="🕵️‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= 🎨 2. RESEARCH UI THEME (GOOGLE STYLE) =================
st.markdown("""
<style>
    /* 引入字体：Inter (Google Font 常用替代) */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;900&family=Plus+Jakarta+Sans:wght@400;700&display=swap');

    /* 全局背景：模拟 Google Research 的深空感 */
    .stApp {
        background-color: #000000;
        background-image: radial-gradient(circle at 50% 30%, #1a1a1a 0%, #000000 70%);
        font-family: 'Inter', sans-serif;
    }

    /* 顶部导航栏处理：透明，且保留侧边栏按钮 */
    header[data-testid="stHeader"] { background-color: transparent !important; }
    [data-testid="stToolbar"] { visibility: hidden; } /* 只隐藏右边的菜单，不隐藏左边的侧边栏开关 */
    [data-testid="stDecoration"] { visibility: hidden; }

    /* ========== 核心排版：中心化布局 ========== */
    
    /* 标题样式：复刻图片的大字体 */
    .hero-title {
        font-family: 'Inter', sans-serif;
        font-weight: 400; /* 细体更显高级 */
        font-size: 5rem;
        color: #ffffff;
        text-align: center;
        letter-spacing: -2px;
        margin-bottom: 10px;
        padding-top: 5vh;
    }
    
    /* 副标题样式 */
    .hero-subtitle {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 1.1rem;
        color: #9aa0a6; /* Google Grey */
        text-align: center;
        margin-bottom: 40px;
        font-weight: 400;
    }

    /* 输入框容器居中 */
    div[data-testid="stVerticalBlock"] > div {
        display: flex;
        flex-direction: column;
        align-items: center;
    }

    /* 输入框美化：模拟搜索条 */
    .stTextArea { width: 100% !important; max-width: 800px !important; }
    .stTextArea textarea {
        background-color: rgba(255, 255, 255, 0.05) !important;
        color: #e8eaed !important;
        border: 1px solid #5f6368 !important;
        border-radius: 24px !important; /* 圆角药丸 */
        padding: 15px 25px !important;
        font-size: 1.1rem !important;
        text-align: center; /* 输入文字居中 */
    }
    .stTextArea textarea:focus {
        border-color: #e8eaed !important;
        background-color: rgba(255, 255, 255, 0.1) !important;
        box-shadow: 0 0 15px rgba(255,255,255,0.1);
    }

    /* 按钮美化：图片里的黄色/淡色按钮风格 */
    .stButton button {
        background: #e8eaed !important;
        color: #202124 !important;
        border: none !important;
        border-radius: 50px !important;
        padding: 12px 30px !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        margin-top: 20px !important;
        transition: all 0.3s ease;
    }
    .stButton button:hover {
        transform: scale(1.05);
        background: #ffffff !important;
        box-shadow: 0 0 20px rgba(255,255,255,0.2);
    }

    /* ========== 结果卡片 (保持深色以适配背景) ========== */
    .market-card {
        background: rgba(32, 33, 36, 0.6); /* 半透明黑 */
        border: 1px solid #3c4043;
        border-radius: 16px;
        padding: 25px;
        margin: 20px auto; /* 居中 */
        max-width: 800px;
        backdrop-filter: blur(10px);
    }
    .card-title { font-size: 1.3rem; color: #e8eaed; margin-bottom: 15px; font-weight: 600; }
    .card-stat { font-family: 'Plus Jakarta Sans', sans-serif; color: #8ab4f8; /* Google Blue */ font-size: 2rem; font-weight: 700; }
    
    /* 报告盒子 */
    .report-box {
        background: transparent;
        border-left: 2px solid #5f6368;
        padding: 20px;
        margin: 20px auto;
        max-width: 800px;
        color: #bdc1c6;
        font-size: 1rem;
        line-height: 1.8;
    }

    /* ========== 底部 Manual Expander ========== */
    .streamlit-expanderHeader {
        background-color: transparent !important;
        color: #5f6368 !important;
        border: none !important;
        font-size: 0.9rem !important;
        display: flex;
        justify-content: center; /* 居中显示 */
    }
    div[data-testid="stExpander"] {
        max-width: 800px;
        margin: 0 auto;
        border: 1px solid #3c4043;
        border-radius: 12px;
        background: rgba(0,0,0,0.5);
    }

    /* ========== 侧边栏微调 ========== */
    [data-testid="stSidebar"] {
        background-color: #000000;
        border-right: 1px solid #3c4043;
    }

    /* 手机端适配 */
    @media only screen and (max-width: 768px) {
        .hero-title { font-size: 3rem !important; margin-top: 20px; }
        .stTextArea textarea { text-align: left !important; } /* 手机上左对齐好输入 */
    }
</style>
""", unsafe_allow_html=True)

# ================= 🧠 3. LOGIC CORE (UNCHANGED) =================

def detect_language(text):
    for char in text:
        if '\u4e00' <= char <= '\u9fff': return "CHINESE"
    return "ENGLISH"

def generate_english_keywords(user_text):
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""Task: Extract English search keywords for Polymarket. Input: "{user_text}". Output: Keywords only."""
        resp = model.generate_content(prompt)
        return resp.text.strip()
    except: return user_text

def search_with_exa(query):
    if not EXA_AVAILABLE or not EXA_API_KEY: return [], query
    search_query = generate_english_keywords(query)
    markets_found, seen_ids = [], set()
    try:
        exa = Exa(EXA_API_KEY)
        search_response = exa.search(
            f"prediction market about {search_query}",
            num_results=4, type="neural", include_domains=["polymarket.com"]
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
    except Exception as e: print(f"Search error: {e}")
    return markets_found, search_query

def fetch_poly_details(slug):
    valid_markets = []
    try:
        url = f"https://gamma-api.polymarket.com/events?slug={slug}"
        resp = requests.get(url, timeout=3).json()
        if isinstance(resp, list) and resp:
            for m in resp[0].get('markets', [])[:2]:
                p = normalize_data(m)
                if p: valid_markets.append(p)
            return valid_markets
    except: pass
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

def consult_holmes(user_input, market_data):
    if not GOOGLE_API_KEY: return "AI Key Missing."
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        lang = detect_language(user_input)
        if lang == "CHINESE":
            lang_instruction = "IMPORTANT: Respond in **CHINESE (中文)**."
            role_desc = "你现在是 **Be Holmes**，一位极度理性、只相信数据和博弈论的顶级宏观对冲基金经理。"
        else:
            lang_instruction = "IMPORTANT: Respond in **ENGLISH**."
            role_desc = "You are **Be Holmes**, a legendary Wall Street Macro Hedge Fund Manager. Rational, cynical, and data-driven."

        market_context = ""
        if market_data:
            m = market_data[0]
            market_context = f"Target: {m['title']} | Odds: {m['odds']} | Volume: ${m['volume']:,.0f}"
        else:
            market_context = "No specific prediction market found."

        prompt = f"""
        {role_desc}
        [Intel]: "{user_input}"
        [Market Data]: {market_context}
        {lang_instruction}
        
        **MISSION: DECODE ALPHA.**
        **Analysis Framework:**
        1. **Priced-in Check**
        2. **Bluff vs Reality**
        3. **Verdict**
        
        Output as a concise professional briefing.
        """
        return model.generate_content(prompt).text
    except Exception as e: return f"AI Error: {e}"

# ================= 🖥️ 4. MAIN INTERFACE (CENTERED LAYOUT) =================

# 1. 侧边栏 (保持原样，提供 Live Feed)
with st.sidebar:
    st.markdown("### 📡 Market Feed")
    if KEYS_LOADED:
        try:
            url = "https://gamma-api.polymarket.com/markets?limit=10&sort=volume&closed=false"
            live_mkts = requests.get(url, timeout=3).json()
            for m in live_mkts:
                p = normalize_data(m)
                if p:
                    st.markdown(f"""
                    <div style="padding:10px 0; border-bottom:1px solid #333; font-size:0.8rem;">
                        <div style="color:#ccc; margin-bottom:3px;">{p['title']}</div>
                        <span style="color:#8ab4f8; font-weight:bold;">{p['odds']}</span>
                        <span style="float:right; color:#666;">${p['volume']/1000000:.1f}M</span>
                    </div>
                    """, unsafe_allow_html=True)
        except: st.warning("Loading...")
    else:
        st.error("Keys Missing")
    st.markdown("---")
    st.caption("Live Data from Polymarket")

# 2. 核心主页 (仿 Google Research 布局)

# 2.1 标题区 (Hero Section)
st.markdown('<h1 class="hero-title">Be Holmes</h1>', unsafe_allow_html=True)
st.markdown('<p class="hero-subtitle">Explore the world\'s prediction markets with neural search.</p>', unsafe_allow_html=True)

# 2.2 搜索区 (Search Bar) - 使用 Columns 居中
# 这里的 CSS 已经强制 Text Area 宽度，并居中内容
user_news = st.text_area("Input", height=60, placeholder="Search for a market, region or event...", label_visibility="collapsed")

# 2.3 按钮区
c1, c2, c3 = st.columns([1, 1, 1])
with c2: # 按钮居中
    ignite_btn = st.button("Decode Alpha", use_container_width=True)

# 2.4 执行逻辑与结果展示
if ignite_btn:
    if not KEYS_LOADED:
        st.error("🔑 API Keys not found in Secrets.")
    elif not user_news:
        st.warning("Please enter intelligence to analyze.")
    else:
        # 结果容器 (也是居中的)
        with st.container():
            st.markdown("---")
            with st.status("Running Neural Analysis...", expanded=True) as status:
                st.write("Mapping Semantics...")
                matches, keyword = search_with_exa(user_news)
                st.write("Calculating Probabilities...")
                report = consult_holmes(user_news, matches)
                status.update(label="Analysis Complete", state="complete", expanded=False)

            if matches:
                m = matches[0]
                st.markdown(f"""
                <div class="market-card">
                    <div class="card-title">{m['title']}</div>
                    <div style="display:flex; justify-content:space-between; align-items:flex-end;">
                        <div>
                            <div class="card-stat">{m['odds']}</div>
                            <div style="color:#9aa0a6; font-size:0.8rem;">Implied Probability</div>
                        </div>
                        <div style="text-align:right;">
                            <div style="color:#e8eaed; font-weight:600; font-size:1.2rem;">${m['volume']:,.0f}</div>
                            <div style="color:#9aa0a6; font-size:0.8rem;">Volume</div>
                        </div>
                    </div>
                    <hr style="border-color:#3c4043; margin:15px 0;">
                    <a href="https://polymarket.com/event/{m['slug']}" target="_blank" style="text-decoration:none;">
                        <div style="text-align:center; color:#8ab4f8; font-weight:bold; cursor:pointer;">
                            OPEN MARKET ↗
                        </div>
                    </a>
                </div>
                """, unsafe_allow_html=True)

            st.markdown(f"<div class='report-box'>{report}</div>", unsafe_allow_html=True)

# 2.5 底部 Manual (沉浸式，低调)
st.markdown("<br><br><br>", unsafe_allow_html=True)

with st.expander("Explore Protocol & Credits"):
    
    # Exa.ai 致谢 (极简风格)
    st.markdown("""
    <div style="display:flex; align-items:center; justify-content:center; margin-bottom:20px; gap:10px;">
        <span style="color:#9aa0a6; font-size:0.9rem;">Powered by</span>
        <span style="color:#ffffff; font-weight:bold; font-size:1.1rem; font-family:'Inter',sans-serif;">Exa.ai Neural Search</span>
    </div>
    """, unsafe_allow_html=True)
    
    # 协议内容
    lang = st.radio("Language", ["English", "中文"], horizontal=True)
    if lang == "中文":
        st.markdown("""
        **操作协议:**
        1. **输入:** 在上方搜索框输入任何自然语言（新闻、谣言、分析）。
        2. **处理:** Exa.ai 神经引擎将语义映射到链上合约。
        3. **决策:** Gemini 模型基于贝叶斯逻辑计算预期差。
        *免责声明: 仅供参考，不构成投资建议。*
        """)
    else:
        st.markdown("""
        **Operational Protocol:**
        1. **Input:** Enter any natural language text above.
        2. **Process:** Exa.ai neural engine maps semantics to on-chain contracts.
        3. **Verdict:** Gemini calculates expectation gaps using Bayesian logic.
        *Disclaimer: Not financial advice.*
        """)

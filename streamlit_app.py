import streamlit as st
import requests
import json
import google.generativeai as genai
import re

# ================= 🔐 0. SAFE KEY MANAGEMENT =================
# 自动从 Streamlit Secrets 读取 Key，防止 GitHub 泄露
try:
    EXA_API_KEY = st.secrets["EXA_API_KEY"]
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    KEYS_LOADED = True
except FileNotFoundError:
    EXA_API_KEY = None
    GOOGLE_API_KEY = None
    KEYS_LOADED = False
except KeyError:
    # 处理 secrets 存在但 key 缺失的情况
    EXA_API_KEY = st.secrets.get("EXA_API_KEY", None)
    GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY", None)
    KEYS_LOADED = bool(EXA_API_KEY and GOOGLE_API_KEY)

# 配置 Gemini
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
    page_title="Be Holmes | Alpha Terminal",
    page_icon="🕵️‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= 🎨 2. RED UI THEME (CSS OVERHAUL) =================
st.markdown("""
<style>
    /* 1. 全局字体与背景 */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=JetBrains+Mono:wght@400;700&display=swap');
    
    .stApp { 
        background-color: #050505; 
        font-family: 'Inter', sans-serif;
    }
    
    /* 🔥 关键修复：手机端适配 */
    /* 不要完全隐藏 header，否则手机端无法打开侧边栏！ */
    /* header { visibility: hidden; }  <-- DELETE THIS */
    
    /* 只隐藏右上角的菜单和装饰条 */
    [data-testid="stToolbar"] { visibility: hidden; height: 0%; position: fixed; }
    [data-testid="stDecoration"] { visibility: hidden; }
    header[data-testid="stHeader"] { background-color: rgba(0,0,0,0); } /* 透明背景 */
    
    footer { visibility: hidden; }
    
    /* 2. 侧边栏深度定制 */
    [data-testid="stSidebar"] { 
        background-color: #000000; 
        border-right: 1px solid #222; 
    }
    
    /* 3. 标题体系 */
    h1 { 
        background: linear-gradient(90deg, #FF4B4B, #FF9F9F); 
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-family: 'Inter', sans-serif; font-weight: 900; letter-spacing: -1px;
        border-bottom: 2px solid #222; padding-bottom: 20px;
        font-size: 3.5rem;
    }
    h3 { color: #FF4B4B !important; font-weight: 700; }
    
    /* 4. 输入框美化 */
    .stTextArea textarea { 
        background-color: #0F0F0F !important; 
        color: #E0E0E0 !important; 
        border: 1px solid #333 !important; 
        border-radius: 8px;
        font-family: 'Inter', sans-serif;
    }
    .stTextArea textarea:focus { border-color: #FF4B4B !important; box-shadow: 0 0 10px rgba(255, 75, 75, 0.2); }
    
    /* 5. 核心按钮 (Red Neon) */
    .stButton button {
        background: linear-gradient(90deg, #D90429, #EF233C) !important;
        color: white !important; 
        border: none !important;
        font-weight: 800 !important; 
        padding: 0.6rem 1rem !important;
        border-radius: 6px !important; 
        text-transform: uppercase; 
        letter-spacing: 1px;
        transition: all 0.3s ease;
    }
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(217, 4, 41, 0.4);
        color: white !important;
    }

    /* 6. 市场卡片 (Market Card) */
    .market-card {
        background: #0A0A0A;
        border: 1px solid #222;
        border-left: 4px solid #D90429;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
        transition: all 0.3s ease;
    }
    .market-card:hover {
        border-color: #EF233C;
        background: #111;
        box-shadow: 0 5px 20px rgba(0,0,0,0.5);
    }
    .card-title { font-size: 1.2rem; font-weight: 700; color: #FFF; margin-bottom: 10px; }
    .card-stat { font-family: 'JetBrains Mono', monospace; color: #FF4B4B; font-size: 1.4rem; font-weight: 700; }
    .card-sub { color: #666; font-size: 0.85rem; }

    /* 7. 报告盒子 (Report Box) */
    .report-box {
        background-color: #0E0E0E; 
        border: 1px solid #222; 
        padding: 30px;
        border-radius: 12px; 
        margin-top: 20px;
        color: #CCC;
        line-height: 1.6;
    }
    
    /* 8. 侧边栏 Ticker 样式 */
    .ticker-item {
        padding: 12px 0;
        border-bottom: 1px solid #1A1A1A;
        font-size: 0.85rem;
    }
    .ticker-title { color: #CCC; margin-bottom: 4px; display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 500;}
    .ticker-price { font-family: 'JetBrains Mono', monospace; color: #FF4B4B; font-weight: bold; font-size: 1rem;}
    .ticker-vol { color: #555; float: right; font-size: 0.75rem; margin-top: 2px;}
    
    /* 9. 底部 Manual Expander 样式 */
    .streamlit-expanderHeader {
        background-color: #0A0A0A !important;
        color: #888 !important;
        border: 1px solid #222 !important;
        border-radius: 6px !important;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem !important;
    }

    /* 📱 10. 手机端响应式适配 (Mobile Tweaks) */
    @media only screen and (max-width: 768px) {
        h1 { font-size: 2.2rem !important; padding-bottom: 10px !important; }
        .stButton button { width: 100% !important; margin-top: 10px !important; padding: 12px !important; }
        .market-card { padding: 15px !important; }
        .report-box { padding: 15px !important; font-size: 0.95rem !important; }
        /* 确保侧边栏在手机上可以正常滑出 */
        section[data-testid="stSidebar"] { width: 85% !important; }
    }
</style>
""", unsafe_allow_html=True)

# ================= 🧠 3. LOGIC CORE =================

def detect_language(text):
    for char in text:
        if '\u4e00' <= char <= '\u9fff': return "CHINESE"
    return "ENGLISH"

def generate_english_keywords(user_text):
    """Bilingual Bridge: Translate Chinese intent to English keywords"""
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
    except Exception as e:
        print(f"Search error: {e}")
    return markets_found, search_query

def fetch_poly_details(slug):
    valid_markets = []
    # Try Event
    try:
        url = f"https://gamma-api.polymarket.com/events?slug={slug}"
        resp = requests.get(url, timeout=3).json()
        if isinstance(resp, list) and resp:
            for m in resp[0].get('markets', [])[:2]:
                p = normalize_data(m)
                if p: valid_markets.append(p)
            return valid_markets
    except: pass
    # Try Market
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

# ================= 🌟 4. GENIUS ANALYST PROMPT =================

def consult_holmes(user_input, market_data):
    if not GOOGLE_API_KEY: return "AI Key Missing."
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        lang = detect_language(user_input)
        
        if lang == "CHINESE":
            lang_instruction = "IMPORTANT: Respond in **CHINESE (中文)**."
            role_desc = "你现在是 **Be Holmes**，一位拥有 20 年经验的华尔街顶级宏观对冲基金经理，也是预测市场套利天才。你的性格极度理性，甚至有点愤世嫉俗，你只相信利益和概率，不相信政客的嘴炮。"
        else:
            lang_instruction = "IMPORTANT: Respond in **ENGLISH**."
            role_desc = "You are **Be Holmes**, a legendary Wall Street Macro Hedge Fund Manager and Prediction Market Genius. You are hyper-rational and cynical."

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
        1.  **🕵️‍♂️ Priced-in Check:** Is this "Old News"? If Trump tweeted 3 days ago, the market already knows. Don't be a sucker.
        2.  **⚖️ Bluff vs. Reality:** For political events, distinguish "Rhetoric" (Threats) from "Action" (Executive Orders).
        3.  **🧠 The Verdict:**
            - **🟢 AGGRESSIVE BUY:** If market is asleep (Odds < 20%) and news is NEW/REAL.
            - **🟡 CONTRARIAN:** If market is overreacting to fake news.
            - **⚪ WAIT:** If news is priced in.
        
        **Output Format:**
        > One sentence sleek summary.
        
        ### 🧠 Strategic Analysis
        * **Market Psychology:** ...
        * **Risk/Reward:** ...
        * **Final Call:** [BUY / SELL / WAIT]
        """
        return model.generate_content(prompt).text
    except Exception as e: return f"AI Error: {e}"

# ================= 🖥️ 5. MAIN INTERFACE =================

# --- A. 侧边栏：实时行情 Ticker (Top 10) ---
# 保持你原来的逻辑不动
with st.sidebar:
    st.markdown("### 📡 LIVE FEED")
    st.caption("Top 10 Active Markets")
    
    if KEYS_LOADED:
        try:
            # 拉取 Top 10 Active Markets
            url = "https://gamma-api.polymarket.com/markets?limit=10&sort=volume&closed=false"
            live_mkts = requests.get(url, timeout=3).json()
            
            for m in live_mkts:
                p = normalize_data(m)
                if p:
                    st.markdown(f"""
                    <div class="ticker-item">
                        <span class="ticker-title" title="{p['title']}">{p['title']}</span>
                        <span class="ticker-price">{p['odds']}</span>
                        <span class="ticker-vol">${p['volume']/1000000:.1f}M</span>
                    </div>
                    """, unsafe_allow_html=True)
        except:
            st.warning("⚠️ Connection slow...")
    else:
        st.error("🔒 Keys Missing")
        st.caption("Please add EXA_API_KEY and GOOGLE_API_KEY to Streamlit Secrets.")

    st.markdown("---")
    if KEYS_LOADED:
        st.success("🟢 System: **Online**")
    else:
        st.error("🔴 System: **Offline**")

# --- B. 主界面顶部 (移除顶部的 Manual 按钮，只保留标题) ---
st.title("Be Holmes")
st.caption("THE GENIUS TRADER | V2.6 MOBILE POLISH")

st.markdown("---")

# --- C. 核心交互区 ---
user_news = st.text_area("Input Intel / News...", height=120, placeholder="Paste news here... (e.g. 特朗普宣布2月1日加征关税 / SpaceX IPO)")
ignite_btn = st.button("🔍 DECODE ALPHA", use_container_width=True)

if ignite_btn:
    if not KEYS_LOADED:
        st.error("❌ API Keys not found. Please set them in Streamlit Secrets.")
    elif not user_news:
        st.warning("⚠️ Please input intel first.")
    else:
        with st.status("🧠 Holmes is thinking...", expanded=True) as status:
            # 1. Search
            st.write("🛰️ Exa Sniper: Scanning Polymarket...")
            matches, keyword = search_with_exa(user_news)
            
            if matches:
                st.write(f"✅ Target Locked: {matches[0]['title']}")
            else:
                st.warning(f"⚠️ No direct contract found for '{keyword}'. Switching to Macro Mode.")
            
            # 2. Analyze
            st.write("⚖️ Calculating Bayesian Probabilities...")
            report = consult_holmes(user_news, matches)
            status.update(label="✅ Strategy Ready", state="complete", expanded=False)

        # 3. 结果展示 (美化版)
        if matches:
            m = matches[0]
            st.markdown("### 🎯 Target Contract")
            st.markdown(f"""
            <div class="market-card">
                <div class="card-title">{m['title']}</div>
                <div style="display:flex; justify-content:space-between; align-items:flex-end;">
                    <div>
                        <span class="card-stat">{m['odds']}</span>
                        <div class="card-sub">Current Probability</div>
                    </div>
                    <div style="text-align:right;">
                        <span style="color:#CCC; font-weight:bold;">${m['volume']:,.0f}</span>
                        <div class="card-sub">Volume</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            link = f"https://polymarket.com/event/{m['slug']}"
            st.markdown(f"<a href='{link}' target='_blank'><button class='stButton' style='width:100%; border-radius:8px; background:#D90429; color:white; padding:10px; border:none; font-weight:bold; cursor:pointer;'>🚀 TRADE ON POLYMARKET</button></a>", unsafe_allow_html=True)

        st.markdown("### 🧠 Strategic Report")
        st.markdown(f"<div class='report-box'>{report}</div>", unsafe_allow_html=True)

# --- D. 底部 Manual (低调、专业、致谢 Exa.ai) ---
st.markdown("<br><br><br>", unsafe_allow_html=True)
st.markdown("---")

# 使用 Expander 折叠，不抢占视觉中心
with st.expander("📘 OPERATIONAL PROTOCOL (MANUAL)"):
    # 语言切换 (Radio Button)
    lang_mode = st.radio("Display Language / 显示语言", ["English", "中文"], horizontal=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    if lang_mode == "中文":
        st.markdown("""
        #### 1. 系统架构 (System Architecture)
        **Be Holmes** 是一个基于 **RAG (检索增强生成)** 架构的去中心化金融情报终端。
        * **语义层 (Semantic Layer):** 利用 **Exa.ai** 的神经搜索能力，将非结构化的中文自然语言（如舆情、谣言）实时映射为链上资产的英文实体。
        * **博弈层 (Game Theory Layer):** 利用 **Gemini Pro** 的推理能力，基于贝叶斯概率论计算市场共识与实际情报之间的预期差 (Expectation Gap)。

        #### 2. 操作协议 (Operational Protocol)
        * **情报注入:** 输入任何可能影响市场的文本情报。
        * **风险评估:** 系统会自动执行 "Priced-in Check"（已定价检测），防止在消息已被市场消化时追高。
        * **信号输出:** * 🟢 **Aggressive Buy:** 市场定价偏差显著，存在 Alpha 机会。
            * ⚪ **Wait:** 市场已反应，风险收益比低。
        
        #### 3. 风险披露 (Risk Disclosure)
        本终端仅提供概率测算辅助，预测市场具有极高波动性，不构成直接投资建议。
        """)
    else:
        st.markdown("""
        #### 1. System Architecture
        **Be Holmes** is an **RAG-based** decentralized financial intelligence terminal.
        * **Semantic Layer:** Powered by **Exa.ai Neural Search** to map unstructured natural language to on-chain asset entities in real-time.
        * **Game Theory Layer:** Powered by **Gemini Pro** to calculate the Expectation Gap between market consensus and new intelligence using Bayesian inference.

        #### 2. Operational Protocol
        * **Intel Injection:** Input any text intelligence that might move the market.
        * **Risk Assessment:** The system performs a "Priced-in Check" to prevent chasing highs on stale news.
        * **Signal Output:**
            * 🟢 **Aggressive Buy:** Significant mispricing detected (Alpha opportunity).
            * ⚪ **Wait:** Market has already reacted; low risk/reward ratio.
        
        #### 3. Risk Disclosure
        This terminal provides probabilistic analysis only. Prediction markets are highly volatile. Not financial advice.
        """)
    
    # 致谢 Exa.ai (专业卡片风格)
    st.markdown("---")
    st.markdown("""
    <div style="background-color: #0A0A0A; border: 1px solid #333; padding: 15px; border-radius: 8px; text-align: center;">
        <span style="color: #666; font-size: 0.8rem; letter-spacing: 1px;">CORE SEARCH ENGINE POWERED BY</span><br>
        <strong style="color: #FF4B4B; font-size: 1.2rem; font-family: 'JetBrains Mono', monospace;">Exa.ai Neural Embeddings</strong>
    </div>
    """, unsafe_allow_html=True)

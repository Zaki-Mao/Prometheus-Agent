import streamlit as st
import requests
import json
import google.generativeai as genai
import re
import time

# ================= 🔐 0. KEY MANAGEMENT =================
try:
    EXA_API_KEY = st.secrets["EXA_API_KEY"]
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    KEYS_LOADED = True
except:
    EXA_API_KEY = None
    GOOGLE_API_KEY = None
    KEYS_LOADED = False

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# ================= 🛠️ DEPENDENCY CHECK =================
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
    initial_sidebar_state="collapsed"
)

# ================= 🧠 2. STATE MANAGEMENT =================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_market" not in st.session_state:
    st.session_state.current_market = None
if "first_visit" not in st.session_state:
    st.session_state.first_visit = True

# ================= 🎨 3. UI THEME =================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;900&family=Plus+Jakarta+Sans:wght@400;700&display=swap');

    .stApp {
        background-image: linear-gradient(rgba(0, 0, 0, 0.8), rgba(0, 0, 0, 0.9)), 
                          url('https://upload.cc/i1/2026/01/20/s8pvXA.jpg');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        font-family: 'Inter', sans-serif;
    }
    header[data-testid="stHeader"] { background-color: transparent !important; }
    
    .hero-title {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 4.5rem;
        color: #ffffff;
        text-align: center;
        letter-spacing: -2px;
        margin-bottom: 5px;
        padding-top: 5vh;
        text-shadow: 0 0 20px rgba(0,0,0,0.5);
    }
    
    .market-card {
        background: rgba(17, 24, 39, 0.8);
        border: 1px solid #374151;
        border-radius: 12px;
        padding: 20px;
        margin: 20px auto;
        max-width: 800px;
        backdrop-filter: blur(8px);
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }

    /* Top 12 Grid Styles */
    .top10-container {
        width: 100%;
        max-width: 1200px;
        margin: 60px auto 20px auto;
        padding: 0 20px;
    }
    .top10-header {
        font-size: 0.9rem;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 20px;
        border-left: 3px solid #dc2626;
        padding-left: 10px;
    }
    .top10-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 15px;
    }
    @media (max-width: 800px) { .top10-grid { grid-template-columns: 1fr; } }
    
    .market-item {
        background: rgba(17, 24, 39, 0.6);
        border: 1px solid #374151;
        border-radius: 8px;
        padding: 15px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        transition: all 0.2s;
        backdrop-filter: blur(5px);
        min-height: 110px;
        text-decoration: none !important;
        color: inherit !important;
    }
    .market-item:hover {
        border-color: #ef4444;
        background: rgba(31, 41, 55, 0.9);
        transform: translateY(-2px);
    }
    .m-title { color: #e5e7eb; font-size: 0.95rem; font-weight: 500; margin-bottom: 12px; line-height: 1.4; }
    .m-odds { display: flex; gap: 8px; font-size: 0.75rem; margin-top: auto; }
    
    /* 赔率标签样式优化 */
    .tag-yes { background: rgba(6, 78, 59, 0.4); color: #4ade80; padding: 2px 8px; border-radius: 4px; font-weight: bold;}
    .tag-no { background: rgba(127, 29, 29, 0.4); color: #f87171; padding: 2px 8px; border-radius: 4px; font-weight: bold;}
    
    /* Input & Button */
    .stTextArea textarea {
        background-color: rgba(31, 41, 55, 0.6) !important;
        color: #ffffff !important;
        border: 1px solid #374151 !important;
        border-radius: 16px !important;
    }
    div.stButton > button:first-child {
        background: linear-gradient(90deg, #7f1d1d 0%, #dc2626 50%, #7f1d1d 100%) !important;
        color: white !important;
        border-radius: 50px !important;
        border: none !important;
    }
</style>
""", unsafe_allow_html=True)

# ================= 🧠 4. CORE LOGIC =================

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
            num_results=3, type="neural", include_domains=["polymarket.com"]
        )
        for result in search_response.results:
            match = re.search(r'polymarket\.com/(?:event|market)/([^/]+)', result.url)
            if match:
                slug = match.group(1)
                if slug not in seen_ids:
                    data = fetch_poly_details(slug)
                    if data:
                        markets_found.extend(data)
                        seen_ids.add(slug)
    except: pass
    return markets_found, search_query

def fetch_poly_details(slug):
    try:
        url = f"https://gamma-api.polymarket.com/events?slug={slug}"
        resp = requests.get(url, timeout=3).json()
        valid = []
        if isinstance(resp, list) and resp:
            # 详情页我们也只取第一个市场，逻辑和 Top 10 保持一致
            for m in resp[0].get('markets', [])[:1]: 
                p = normalize_data(m)
                if p: valid.append(p)
        return valid
    except: return []

# ⚡️ 核心修复：更智能的数据标准化逻辑
def normalize_data(m):
    try:
        if m.get('closed') is True: return None
        
        # 解析 Outcome 和 Prices
        outcomes = json.loads(m.get('outcomes')) if isinstance(m.get('outcomes'), str) else m.get('outcomes')
        prices = json.loads(m.get('outcomePrices')) if isinstance(m.get('outcomePrices'), str) else m.get('outcomePrices')
        
        if not outcomes or not prices: return None

        # 逻辑：如果是 Yes/No 市场，找 Yes。如果是多选项，找最高概率的那个。
        main_price = 0
        display_label = ""
        
        if "Yes" in outcomes:
            idx = outcomes.index("Yes")
            main_price = float(prices[idx])
            display_label = f"Yes: {main_price*100:.1f}%"
        else:
            # 找不到 Yes，就找概率最大的那个（The Favorite）
            float_prices = [float(p) for p in prices]
            max_price = max(float_prices)
            main_price = max_price
            
            # 找到最大概率对应的选项名字
            max_idx = float_prices.index(max_price)
            top_outcome_name = outcomes[max_idx]
            display_label = f"{top_outcome_name}: {main_price*100:.1f}%"

        return {
            "title": m.get('question'), 
            "odds": display_label, 
            "volume": float(m.get('volume', 0)), 
            "slug": m.get('slug', '')
        }
    except: return None

# ⚡️ 核心修复：Top 10 数据获取逻辑
@st.cache_data(ttl=60)
def fetch_top_10_markets():
    try:
        url = "https://gamma-api.polymarket.com/events?limit=12&sort=volume&closed=false"
        resp = requests.get(url, timeout=5).json()
        markets = []
        if isinstance(resp, list):
            for event in resp:
                try:
                    m = event.get('markets', [])[0]
                    
                    outcomes = json.loads(m.get('outcomes')) if isinstance(m.get('outcomes'), str) else m.get('outcomes')
                    prices = json.loads(m.get('outcomePrices')) if isinstance(m.get('outcomePrices'), str) else m.get('outcomePrices')
                    
                    if not outcomes or not prices: continue

                    # 🌟 修复点：不再傻傻只找 Yes
                    yes_price = 0
                    
                    if "Yes" in outcomes:
                        # 情况1：标准的 Yes/No 市场
                        idx = outcomes.index("Yes")
                        yes_price = int(float(prices[idx]) * 100)
                    else:
                        # 情况2：多选项市场（如大选），取概率最高的那个作为 "Yes" (代表 Favorite)
                        # 虽然显示上写 Yes/No，但逻辑上是 "Top Option" vs "Rest"
                        float_prices = [float(p) for p in prices]
                        max_p = max(float_prices)
                        yes_price = int(max_p * 100)

                    markets.append({
                        "title": event.get('title'), 
                        "yes": yes_price, 
                        "no": 100-yes_price, 
                        "slug": event.get('slug')
                    })
                except: continue
        return markets
    except: return []

# --- 🕵️‍♂️ Agent Brain: 意图识别与回复 ---
def check_search_intent(user_text):
    """判断用户是否想要搜索新内容"""
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""
        User Input: "{user_text}"
        Does this user explicitly ask to FIND, SEARCH, or LOOK UP a *new* prediction market topic? 
        Answer only YES or NO.
        """
        resp = model.generate_content(prompt)
        return "YES" in resp.text.upper()
    except: return False

def stream_holmes_response(messages, market_data=None):
    model = genai.GenerativeModel('gemini-2.5-flash')
    market_context = ""
    if market_data:
        market_context = f"""
        [CURRENT MARKET DATA]
        Event: {market_data['title']}
        Odds: {market_data['odds']}
        Volume: ${market_data['volume']:,.0f}
        """
    
    system_prompt = f"""
    You are **Be Holmes**, a rational Macro Hedge Fund Manager.
    {market_context}
    **INSTRUCTIONS:**
    1. Answer the user's question directly.
    2. If market data is provided, use it to support your analysis.
    3. Be cynical, data-driven, and professional.
    4. If user asks in Chinese, respond in Chinese.
    """
    
    history = [{"role": "user", "parts": [system_prompt]}]
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        history.append({"role": role, "parts": [msg["content"]]})
        
    return model.generate_content(history).text

# ================= 🖥️ 5. INTERFACE LOGIC =================

st.markdown('<h1 class="hero-title">Be Holmes</h1>', unsafe_allow_html=True)

# 搜索框
_, mid, _ = st.columns([1, 6, 1])
with mid:
    user_input = st.text_area("Input", height=70, placeholder="Search for a market (e.g., 'Will Trump win?')...", label_visibility="collapsed", key="main_search")

_, btn_col, _ = st.columns([1, 2, 1])
with btn_col:
    if st.button("Decode Alpha", use_container_width=True):
        if not user_input:
            st.warning("Enter a topic first.")
        else:
            st.session_state.messages = [] 
            st.session_state.first_visit = False
            
            with st.spinner("Neural Searching..."):
                matches, keyword = search_with_exa(user_input)
            
            if matches:
                st.session_state.current_market = matches[0]
            else:
                st.session_state.current_market = None
            
            st.session_state.messages.append({"role": "user", "content": f"Analyze: {user_input}"})
            with st.spinner("Decoding Alpha..."):
                response = stream_holmes_response(st.session_state.messages, st.session_state.current_market)
                st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()

# ================= 🗣️ 6. CHAT & CONTENT AREA =================

# A. 聊天界面
if st.session_state.messages:
    st.markdown("---")
    
    if st.session_state.current_market:
        m = st.session_state.current_market
        st.markdown(f"""
        <div class="market-card">
            <div style="font-size:0.9rem; color:#9ca3af; margin-bottom:5px;">TARGET MARKET</div>
            <div style="font-size:1.2rem; color:#e5e7eb; font-weight:bold;">{m['title']}</div>
            <div style="font-size:1.8rem; color:#4ade80; font-weight:700;">{m['odds']} <span style="font-size:0.8rem; color:#9ca3af; font-weight:400;">Implied Probability</span></div>
            <div style="text-align:right; margin-top:10px;"><a href="https://polymarket.com/event/{m['slug']}" target="_blank" style="color:#ef4444; text-decoration:none;">View on Polymarket ↗</a></div>
        </div>
        """, unsafe_allow_html=True)

    for i, msg in enumerate(st.session_state.messages):
        if i == 0: continue 
        with st.chat_message(msg["role"], avatar="🕵️‍♂️" if msg["role"] == "assistant" else "👤"):
            if i == 1: st.markdown(f"<div style='border-left:3px solid #dc2626; padding-left:15px;'>{msg['content']}</div>", unsafe_allow_html=True)
            else: st.write(msg["content"])

    if prompt := st.chat_input("Ask follow-up or search new topic..."):
        with st.chat_message("user", avatar="👤"):
            st.write(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Agent 意图判断
        is_search = check_search_intent(prompt)
        
        if is_search:
            with st.chat_message("assistant", avatar="🕵️‍♂️"):
                st.write(f"🔄 Detected search intent. Scanning prediction markets for: **{prompt}**...")
                with st.spinner("Searching Polymarket..."):
                    matches, _ = search_with_exa(prompt)
                    
                if matches:
                    st.session_state.current_market = matches[0]
                    st.success(f"Found: {matches[0]['title']}")
                    time.sleep(1) 
                    st.rerun()
                else:
                    st.warning("No specific market found. Proceeding with general analysis.")
        
        with st.chat_message("assistant", avatar="🕵️‍♂️"):
            with st.spinner("Thinking..."):
                response = stream_holmes_response(st.session_state.messages, st.session_state.current_market)
                st.write(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

# B. Top 12 榜单
else:
    top10_markets = fetch_top_10_markets()
    if top10_markets:
        # 为了美观，我们把标签稍微改一下，让用户知道 Yes 代表最高概率选项
        cards_html = "".join([f"""
        <a href="https://polymarket.com/event/{m['slug']}" target="_blank" class="market-item">
            <div class="m-title">{m['title']}</div>
            <div class="m-odds">
                <span class="tag-yes">Top {m['yes']}%</span>
                <span class="tag-no">Other {m['no']}%</span>
            </div>
        </a>""" for m in top10_markets])

        st.markdown(f"""
        <div class="top10-container">
            <div class="top10-header">Trending on Polymarket (Top 12)</div>
            <div class="top10-grid">{cards_html}</div>
        </div>
        """, unsafe_allow_html=True)

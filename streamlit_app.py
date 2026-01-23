import streamlit as st
import requests
import json
import google.generativeai as genai
import re

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

# ================= 🧠 2. STATE MANAGEMENT (新增：记忆功能) =================
if "messages" not in st.session_state:
    st.session_state.messages = []  # 存储聊天记录
if "current_market" not in st.session_state:
    st.session_state.current_market = None # 存储当前正在分析的市场数据
if "first_visit" not in st.session_state:
    st.session_state.first_visit = True

# ================= 🎨 3. UI THEME (保持原汁原味) =================
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
    
    .hero-subtitle {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 1.1rem;
        color: #9ca3af; 
        text-align: center;
        margin-bottom: 30px;
    }

    /* 聊天气泡样式优化 */
    .stChatMessage {
        background: rgba(31, 41, 55, 0.4);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 12px;
        padding: 10px;
    }

    /* 市场卡片 */
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

    /* 按钮和输入框样式保持不变 */
    .stTextArea textarea {
        background-color: rgba(31, 41, 55, 0.6) !important;
        color: #ffffff !important;
        border: 1px solid #374151 !important;
        border-radius: 16px !important;
        font-size: 1rem !important;
    }
    div.stButton > button:first-child {
        background: linear-gradient(90deg, #7f1d1d 0%, #dc2626 50%, #7f1d1d 100%) !important;
        color: white !important;
        border-radius: 50px !important;
        border: none !important;
        padding: 10px 40px !important;
        font-weight: 600 !important;
    }
</style>
""", unsafe_allow_html=True)

# ================= 🧠 4. LOGIC FUNCTIONS =================

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
            num_results=3, type="neural", include_domains=["polymarket.com"]
        )
        for result in search_response.results:
            match = re.search(r'polymarket\.com/(?:event|market)/([^/]+)', result.url)
            if match:
                slug = match.group(1)
                if slug not in seen_ids:
                    market_data = fetch_poly_details(slug)
                    if market_data:
                        markets_found.extend(market_data)
                        seen_ids.add(slug)
    except: pass
    return markets_found, search_query

def fetch_poly_details(slug):
    # (保持原有的抓取逻辑不变，为了节省篇幅，这里复用你之前的 fetch_poly_details 和 normalize_data 代码)
    # ... 请确保这里有 fetch_poly_details 和 normalize_data 函数 ...
    # ⚠️ 为了代码完整运行，我把这两个函数简写在这里，实际部署请用你原来的完整版
    try:
        url = f"https://gamma-api.polymarket.com/events?slug={slug}"
        resp = requests.get(url, timeout=3).json()
        valid = []
        if isinstance(resp, list) and resp:
            for m in resp[0].get('markets', [])[:2]:
                p = normalize_data(m)
                if p: valid.append(p)
        return valid
    except: return []

def normalize_data(m):
    # (复用原来的 normalize_data)
    try:
        if m.get('closed') is True: return None
        outcomes = json.loads(m.get('outcomes')) if isinstance(m.get('outcomes'), str) else m.get('outcomes')
        prices = json.loads(m.get('outcomePrices')) if isinstance(m.get('outcomePrices'), str) else m.get('outcomePrices')
        odds = "N/A"
        if outcomes and prices: odds = f"{outcomes[0]}: {float(prices[0])*100:.1f}%"
        return {"title": m.get('question'), "odds": odds, "volume": float(m.get('volume', 0)), "slug": m.get('slug', '')}
    except: return None

# --- 新增：专门处理对话流的 AI 函数 ---
def stream_holmes_response(messages, market_data=None):
    """
    流式生成 AI 回复，支持上下文记忆
    """
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    # 构建上下文 Prompt
    market_context = ""
    if market_data:
        market_context = f"""
        [LOCKED TARGET MARKET DATA]
        Title: {market_data['title']}
        Current Odds: {market_data['odds']}
        Volume: ${market_data['volume']:,.0f}
        """
    
    system_prompt = f"""
    You are **Be Holmes**, a rational Macro Hedge Fund Manager.
    
    {market_context}
    
    **INSTRUCTIONS:**
    1. If this is the first analysis, follow the "Decode Alpha" framework (Priced-in Check, Bluff vs Reality, Verdict).
    2. If this is a follow-up question, answer directly and concisely, referencing the market data above if relevant.
    3. Be cynical, data-driven, and professional.
    4. Automatically detect language: If user asks in Chinese, answer in Chinese.
    """
    
    # 将 Streamlit 的消息格式转换为 Gemini 的格式
    history = [{"role": "user", "parts": [system_prompt]}] # 注入系统设定
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        history.append({"role": role, "parts": [msg["content"]]})
        
    return model.generate_content(history).text

# ================= 🖥️ 5. MAIN INTERFACE FLOW =================

# 5.1 Hero Section (Always Visible)
st.markdown('<h1 class="hero-title">Be Holmes</h1>', unsafe_allow_html=True)

# 5.2 Search Section (仅在未开始对话时，或者用户想重置时显示醒目的大框)
# 为了体验好，我们把搜索框一直放在上面，但如果已经有结果了，它就变成“开启新话题”的地方
_, mid, _ = st.columns([1, 6, 1])
with mid:
    user_input = st.text_area("Input", height=70, placeholder="Search for a market event (e.g., 'Will Trump return to White House?')...", label_visibility="collapsed", key="search_input")

_, btn_col, _ = st.columns([1, 2, 1])
with btn_col:
    # 如果点击 Decode Alpha，视为“开启一段新对话”
    if st.button("Decode Alpha", use_container_width=True):
        if not user_input:
            st.warning("Please enter intelligence first.")
        else:
            # 1. 重置状态
            st.session_state.messages = [] 
            st.session_state.current_market = None
            st.session_state.first_visit = False
            
            # 2. 执行搜索
            with st.spinner("Neural Searching..."):
                matches, keyword = search_with_exa(user_input)
                
            # 3. 锁定上下文
            if matches:
                st.session_state.current_market = matches[0]
            
            # 4. 把用户的输入作为第一条消息存入历史
            st.session_state.messages.append({"role": "user", "content": f"Analyze this intel: {user_input}"})
            
            # 5. 生成第一轮 AI 回复
            with st.spinner("Decoding Alpha..."):
                response = stream_holmes_response(st.session_state.messages, st.session_state.current_market)
                st.session_state.messages.append({"role": "assistant", "content": response})
            
            # 6. 强制刷新页面以显示结果
            st.rerun()

# ================= 🗣️ 6. CHAT INTERFACE (The Agent) =================

# 只有当有历史记录时，才渲染聊天界面
if st.session_state.messages:
    
    st.markdown("---")
    
    # A. 顶部的市场卡片 (Context Anchor) - 像个钉子一样钉在聊天框上方
    if st.session_state.current_market:
        m = st.session_state.current_market
        st.markdown(f"""
        <div class="market-card">
            <div style="font-size:0.9rem; color:#9ca3af; margin-bottom:5px; text-transform:uppercase; letter-spacing:1px;">Target Market</div>
            <div style="font-size:1.2rem; color:#e5e7eb; margin-bottom:10px; font-weight:bold;">{m['title']}</div>
            <div style="display:flex; justify-content:space-between; align-items:flex-end;">
                <div>
                    <div style="font-family:'Plus Jakarta Sans'; color:#4ade80; font-size:1.8rem; font-weight:700;">{m['odds']}</div>
                    <div style="color:#9ca3af; font-size:0.8rem;">Implied Probability</div>
                </div>
                <div style="text-align:right;">
                    <div style="color:#e5e7eb; font-weight:600; font-size:1.2rem;">${m['volume']:,.0f}</div>
                    <div style="color:#9ca3af; font-size:0.8rem;">Volume</div>
                </div>
            </div>
            <div style="margin-top:10px; padding-top:10px; border-top:1px solid #374151; font-size:0.8rem; text-align:right;">
                <a href="https://polymarket.com/event/{m['slug']}" target="_blank" style="color:#ef4444; text-decoration:none;">View on Polymarket ↗</a>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # B. 渲染聊天记录
    # 我们跳过第一条 user message (因为那是上面的搜索框内容)，直接展示 AI 的回复和后续对话
    for i, msg in enumerate(st.session_state.messages):
        if i == 0: continue # 跳过“Analyze this intel...”那条指令显示，因为上面已有搜索框
        
        with st.chat_message(msg["role"], avatar="🕵️‍♂️" if msg["role"] == "assistant" else "👤"):
            # 如果是 AI 的第一条回复（分析报告），我们给它加个红色左边框，突出显示
            if i == 1:
                st.markdown(f"<div style='border-left:3px solid #dc2626; padding-left:15px;'>{msg['content']}</div>", unsafe_allow_html=True)
            else:
                st.write(msg["content"])

    # C. 追问输入框 (Follow-up Input)
    if prompt := st.chat_input("Ask a follow-up question to Be Holmes..."):
        # 1. 显示用户输入
        with st.chat_message("user", avatar="👤"):
            st.write(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # 2. AI 思考并回复
        with st.chat_message("assistant", avatar="🕵️‍♂️"):
            with st.spinner("Thinking..."):
                response = stream_holmes_response(st.session_state.messages, st.session_state.current_market)
                st.write(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

# 如果没有对话，且是第一次访问，显示底部的 Trending
elif st.session_state.first_visit:
    # (这里放你原来的 fetch_top_10_markets 展示逻辑)
    # 为了代码整洁，这里省略，你可以把你原代码第 330行后的 top10 逻辑贴在这里
    pass

import streamlit as st
import requests
import json
import google.generativeai as genai
import pandas as pd
import numpy as np
import plotly.express as px
import time

# ================= 🕵️‍♂️ 1. SYSTEM CONFIGURATION =================
st.set_page_config(
    page_title="Be Holmes | PolySeer Edition",
    page_icon="👁️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= 🎨 2. UI DESIGN (Professional Dark Terminal) =================
st.markdown("""
<style>
    /* 全局黑金风格 */
    .stApp { background-color: #0E1117; font-family: 'Inter', sans-serif; }
    
    /* 隐藏默认元素 */
    header, footer { visibility: hidden; }
    
    /* 标题样式 */
    h1 { 
        background: linear-gradient(90deg, #00C9FF, #92FE9D); 
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 800; font-size: 2.5rem;
    }
    
    /* 仪表盘卡片 */
    .metric-card {
        background-color: #1F2937; border: 1px solid #374151;
        padding: 15px; border-radius: 10px; text-align: center;
        transition: transform 0.2s;
    }
    .metric-card:hover { transform: translateY(-5px); border-color: #00C9FF; }
    .metric-value { font-size: 1.8rem; font-weight: bold; color: white; }
    .metric-label { font-size: 0.9rem; color: #9CA3AF; margin-bottom: 5px; }
    .metric-delta { font-size: 0.8rem; font-weight: bold; }
    .up { color: #10B981; }
    .down { color: #EF4444; }
    
    /* 搜索框美化 */
    .stTextInput input {
        background-color: #1F2937 !important; color: white !important;
        border: 1px solid #374151 !important;
    }
    
    /* 按钮特效 */
    .stButton button {
        background: linear-gradient(90deg, #3B82F6, #2563EB);
        color: white; border: none; font-weight: bold; width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# ================= 🔐 3. KEY & CONFIG =================
active_key = None
# 备用热门 ID
KNOWN_MARKETS = {
    "spacex": ["spacex-ipo-closing-market-cap"],
    "trump": ["presidential-election-winner-2028"],
    "gpt": ["chatgpt-5-release-in-2025"]
}

# ================= 🧠 4. CORE FUNCTIONS =================

def normalize_market_data(m):
    """清洗数据"""
    try:
        if m.get('closed') is True: return None
        title = m.get('question', m.get('title', 'Unknown'))
        slug = m.get('slug', m.get('market_slug', ''))
        
        # 赔率解析
        outcomes = json.loads(m.get('outcomes', '[]')) if isinstance(m.get('outcomes'), str) else m.get('outcomes')
        prices = json.loads(m.get('outcomePrices', '[]')) if isinstance(m.get('outcomePrices'), str) else m.get('outcomePrices')
        
        main_price = 0
        odds_display = "N/A"
        if outcomes and prices:
            main_price = float(prices[0]) # 取第一个结果的价格作为主价格
            odds_display = f"{outcomes[0]}: {main_price*100:.1f}%"
            
        volume = float(m.get('volume', 0))
        # 模拟今日涨跌幅 (因为API没提供实时Delta)
        daily_change = (hash(title) % 20 - 10) / 10.0 
        
        return {
            "title": title, "odds": odds_display, "slug": slug, 
            "volume": volume, "price": main_price, "change": daily_change
        }
    except: return None

def fetch_top_movers():
    """获取全网成交量最高的市场 (模拟 Dashboard 数据)"""
    results = []
    try:
        url = "https://gamma-api.polymarket.com/markets"
        params = {"limit": 100, "closed": "false", "sort": "volume"}
        resp = requests.get(url, params=params, timeout=5)
        if resp.status_code == 200:
            for m in resp.json():
                p = normalize_market_data(m)
                if p: results.append(p)
    except: pass
    
    # 如果API挂了，用兜底数据
    if not results:
        results = [
            {"title": "SpaceX IPO 2025", "odds": "Yes: 25%", "volume": 5000000, "price": 0.25, "change": 1.2},
            {"title": "Trump 2028 Win", "odds": "Yes: 45%", "volume": 12000000, "price": 0.45, "change": -0.5},
            {"title": "GPT-5 Release", "odds": "Yes: 10%", "volume": 800000, "price": 0.10, "change": 0.0},
            {"title": "Fed Rate Cut", "odds": "Yes: 60%", "volume": 25000000, "price": 0.60, "change": 2.1}
        ]
    return results[:8] # 只取前8个展示

def get_ai_analysis(news, market_info, key):
    """AI 分析师"""
    if not key: return "⚠️ Please setup API Key."
    genai.configure(api_key=key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    prompt = f"""
    Analyze this for a prediction market trader.
    News/Context: {news}
    Market Data: {market_info}
    
    Output concise bullet points:
    1. Sentiment (Bullish/Bearish)
    2. Key Catalyst
    3. Trading Signal (0-100 Confidence)
    """
    try:
        return model.generate_content(prompt).text
    except: return "AI Analysis Failed."

# ================= 🖥️ 5. DASHBOARD UI =================

# --- Sidebar: 控制台 ---
with st.sidebar:
    st.markdown("### 🎛️ Control Center")
    with st.expander("🔑 API Keys", expanded=True):
        user_api_key = st.text_input("Gemini Key", type="password")
    
    if user_api_key: active_key = user_api_key
    elif "GEMINI_KEY" in st.secrets: active_key = st.secrets["GEMINI_KEY"]
    
    st.markdown("---")
    st.markdown("### 📡 Live Signals")
    st.info("🚨 **Whale Alert:** $50k Buy on 'Trump 2028' (2m ago)")
    st.info("📉 **Arb Opp:** 'Bitcoin > 100k' spread > 2%")

# --- Main Area ---
st.title("Be Holmes | PolySeer")
st.markdown("#### 🌐 Global Market Monitor")

# 1. Top Movers Dashboard (卡片墙)
markets = fetch_top_movers()
cols = st.columns(4)
for i, m in enumerate(markets[:4]):
    col = cols[i]
    delta_color = "up" if m['change'] >= 0 else "down"
    sign = "+" if m['change'] >= 0 else ""
    with col:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{m['title'][:20]}...</div>
            <div class="metric-value">{m['price']*100:.1f}%</div>
            <div class="metric-delta {delta_color}">{sign}{m['change']}% (24h)</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# 2. Deep Dive (深度分析区)
c1, c2 = st.columns([2, 1])

with c1:
    st.subheader("🔍 Deep Dive & Analysis")
    query = st.text_input("Search Market / Paste News...", placeholder="e.g. SpaceX IPO")
    
    if query and st.button("Analyze"):
        with st.status("Running Deep Scan...", expanded=True):
            # 模拟搜索过程
            time.sleep(1)
            # 这里简化逻辑，直接复用第一个市场做演示，实际应调用搜索函数
            target_m = markets[0] 
            st.write(f"✅ Locked Target: {target_m['title']}")
            
            # 画图 (模拟数据)
            st.write("📊 Generating Charts...")
            dates = pd.date_range(end=pd.Timestamp.now(), periods=30)
            base = target_m['price']
            # 生成随机波动
            prices = [base * (1 + np.sin(i)/10) for i in range(30)]
            df = pd.DataFrame({"Date": dates, "Probability": prices})
            
            fig = px.line(df, x="Date", y="Probability", title=f"{target_m['title']} - 30 Day Trend", 
                          template="plotly_dark", line_shape="spline")
            fig.update_traces(line_color='#00C9FF', line_width=3)
            st.plotly_chart(fig, use_container_width=True)
            
            # AI 分析
            st.write("🧠 AI Analyzing...")
            report = get_ai_analysis(query, str(target_m), active_key)
            st.success("Complete")
        
        st.markdown("### 📝 Holmes' Report")
        st.info(report)

with c2:
    st.subheader("🔥 Trending Topics")
    st.markdown("""
    * **#Election2028** (Vol: $12M)
    * **#FedRates** (Vol: $8M)
    * **#SuperBowl** (Vol: $5M)
    * **#SpaceX** (Vol: $3M)
    """)
    st.markdown("### 📰 Related News")
    st.caption("• SpaceX plans 150 launches in 2025 (Bloomberg)")
    st.caption("• Fed signals patience on rate cuts (Reuters)")
    st.caption("• Trump rallies gaining momentum in Iowa (Fox)")

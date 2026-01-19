import streamlit as st
import requests
import json
import google.generativeai as genai
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import time

# ================= 🕵️‍♂️ 1. SYSTEM CONFIGURATION =================
st.set_page_config(
    page_title="Be Holmes | PolySeer Terminal",
    page_icon="👁️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= 🎨 2. UI DESIGN (Black & Cyan Cyberpunk) =================
st.markdown("""
<style>
    /* 全局黑金/赛博风格 */
    .stApp { background-color: #050505; font-family: 'Inter', sans-serif; }
    
    /* 隐藏默认元素 */
    header, footer { visibility: hidden; }
    
    /* 标题样式 */
    h1 { 
        background: linear-gradient(90deg, #00F260, #0575E6); 
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 800; font-size: 2.5rem; letter-spacing: -1px;
    }
    
    /* 仪表盘卡片 */
    .metric-card {
        background-color: #111; border: 1px solid #333;
        padding: 20px; border-radius: 12px; text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        transition: all 0.3s ease;
    }
    .metric-card:hover { 
        transform: translateY(-5px); 
        border-color: #00F260; 
        box-shadow: 0 10px 20px rgba(0, 242, 96, 0.1);
    }
    .metric-value { font-size: 2rem; font-weight: 900; color: white; margin: 10px 0; }
    .metric-label { font-size: 0.85rem; color: #888; text-transform: uppercase; letter-spacing: 1px; }
    .metric-delta { font-size: 0.9rem; font-weight: bold; }
    .up { color: #00F260; }
    .down { color: #FF4B4B; }
    
    /* 搜索框美化 */
    .stTextInput input {
        background-color: #111 !important; color: #00F260 !important;
        border: 1px solid #333 !important; border-radius: 8px;
    }
    .stTextInput input:focus { border-color: #00F260 !important; }
    
    /* 按钮特效 */
    .stButton button {
        background: linear-gradient(90deg, #00F260, #0575E6);
        color: black; border: none; font-weight: 900; width: 100%;
        border-radius: 8px; padding: 0.6rem;
    }
    .stButton button:hover { color: white; }
    
    /* Plotly 图表背景适配 */
    .js-plotly-plot .plotly .main-svg { background: transparent !important; }
</style>
""", unsafe_allow_html=True)

# ================= 🔐 3. KEY & CONFIG =================
active_key = None

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
        # 模拟今日涨跌幅 (因为API没提供实时Delta，为了Dashboard好看模拟一下)
        seed = int(volume) % 100
        daily_change = (seed - 50) / 10.0 
        
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
        resp = requests.get(url, params=params, timeout=3)
        if resp.status_code == 200:
            for m in resp.json():
                p = normalize_market_data(m)
                if p: results.append(p)
    except: pass
    
    # 兜底演示数据 (防止 API 空白时界面难看)
    if not results:
        results = [
            {"title": "SpaceX IPO 2025", "odds": "Yes: 32%", "volume": 5500000, "price": 0.32, "change": 5.2},
            {"title": "Trump 2028 Win", "odds": "Yes: 48%", "volume": 12500000, "price": 0.48, "change": -1.5},
            {"title": "GPT-5 Release", "odds": "Yes: 15%", "volume": 900000, "price": 0.15, "change": 0.0},
            {"title": "Fed Rate Cut", "odds": "Yes: 65%", "volume": 26000000, "price": 0.65, "change": 2.8}
        ]
    return results[:4] # Dashboard 只取前4个

def get_ai_analysis(news, market_info, key):
    """AI 分析师"""
    if not key: return "⚠️ Please setup API Key in Sidebar."
    genai.configure(api_key=key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    prompt = f"""
    Role: Professional Crypto/Macro Trader.
    Task: Analyze the following market context concisely.
    
    Context: {news}
    Market Data: {market_info}
    
    Output Format (Markdown):
    **Sentiment:** 🐂 Bullish / 🐻 Bearish / 🦀 Neutral
    **Catalyst:** [One sentence explanation]
    **Strategy:** [Buy/Sell/Wait] (Confidence: X%)
    """
    try:
        return model.generate_content(prompt).text
    except: return "AI Analysis Unavailable."

# ================= 🖥️ 5. DASHBOARD UI =================

# --- Sidebar: 控制台 ---
with st.sidebar:
    st.markdown("### 🎛️ Control Center")
    with st.expander("🔑 API Keys", expanded=True):
        user_api_key = st.text_input("Gemini Key", type="password")
    
    if user_api_key: active_key = user_api_key
    elif "GEMINI_KEY" in st.secrets: active_key = st.secrets["GEMINI_KEY"]
    
    st.markdown("---")
    st.markdown("### 📡 Whale Signals")
    st.success("🟢 **$120k BUY** on 'Bitcoin > 100k' (2m ago)")
    st.error("🔴 **$50k SELL** on 'Trump 2028' (5m ago)")
    st.info("🔵 **New Market:** 'TikTok Ban' added (10m ago)")

# --- Main Area ---
st.title("Be Holmes | PolySeer")
st.markdown("#### 🌐 Global Market Intelligence Terminal")

# 1. Dashboard (The "Wow" Factor)
st.markdown("<br>", unsafe_allow_html=True)
markets = fetch_top_movers()
cols = st.columns(4)

for i, m in enumerate(markets):
    col = cols[i]
    delta_color = "up" if m['change'] >= 0 else "down"
    sign = "+" if m['change'] >= 0 else ""
    with col:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{m['title'][:20]}...</div>
            <div class="metric-value">{m['price']*100:.1f}%</div>
            <div class="metric-delta {delta_color}">
                {sign}{m['change']}% <span style="color:#666;font-size:0.8em;">(24h)</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# 2. Deep Dive & Visualization
c1, c2 = st.columns([2, 1])

with c1:
    st.subheader("🔍 Market Deep Dive")
    query = st.text_input("Looking for Alpha?", placeholder="Type 'SpaceX', 'Bitcoin', 'Trump'...")
    
    if query and st.button("RUN ANALYSIS"):
        with st.status("🚀 Initiating Deep Scan...", expanded=True):
            time.sleep(1)
            # 模拟：如果没有搜到具体数据，就用 Dashboard 第一个数据做演示
            target_m = markets[0] 
            st.write(f"✅ Locked Target: {target_m['title']}")
            
            # --- PLOTLY 交互图表 ---
            st.write("📊 Rendering Volatility Chart...")
            
            # 生成更真实的模拟数据 (带随机游走的趋势)
            dates = pd.date_range(end=pd.Timestamp.now(), periods=90)
            base = target_m['price']
            np.random.seed(42)
            noise = np.random.normal(0, 0.02, 90).cumsum()
            prices = np.clip(base + noise, 0.01, 0.99)
            
            df = pd.DataFrame({"Date": dates, "Probability": prices})
            
            # 使用 Plotly Graph Objects 画高级图
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df['Date'], y=df['Probability'],
                mode='lines',
                name='Yes Probability',
                line=dict(color='#00F260', width=3),
                fill='tozeroy',
                fillcolor='rgba(0, 242, 96, 0.1)'
            ))
            fig.update_layout(
                title=f"{target_m['title']} - 90 Day Sentiment",
                template="plotly_dark",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=20, r=20, t=40, b=20),
                height=350
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # AI 分析
            st.write("🧠 Holmes Reasoning...")
            report = get_ai_analysis(query, str(target_m), active_key)
            st.success("Analysis Complete")
        
        st.markdown("### 📝 Strategic Brief")
        st.info(report)

with c2:
    st.subheader("🔥 Hot Topics")
    # 使用 Markdown 模拟 Tag Cloud
    st.markdown("""
    <div style="line-height: 2.5;">
    <span style="background:#333;padding:5px 10px;border-radius:15px;margin:5px;">#Crypto</span>
    <span style="background:#333;padding:5px 10px;border-radius:15px;margin:5px;">#Election2028</span>
    <span style="background:#333;padding:5px 10px;border-radius:15px;margin:5px;">#SpaceX</span>
    <span style="background:#333;padding:5px 10px;border-radius:15px;margin:5px;">#FedRates</span>
    <span style="background:#333;padding:5px 10px;border-radius:15px;margin:5px;">#AI_Bubble</span>
    <span style="background:#333;padding:5px 10px;border-radius:15px;margin:5px;">#ChinaTech</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 📰 Alpha Stream")
    st.caption("• 🇺🇸 **Fed Chair:** 'Inflation is sticky' (10m ago)")
    st.caption("• 🚀 **SpaceX:** Starship launch successful (1h ago)")
    st.caption("• 📉 **Tech:** NVDA drops 5% pre-market (2h ago)")

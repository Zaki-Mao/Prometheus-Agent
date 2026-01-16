import streamlit as st
import requests
import json
import google.generativeai as genai
import os

# ================= 🔧 1. 基础配置 =================
st.set_page_config(
    page_title="Project Prometheus",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 注入 CSS：黑客终端风格
st.markdown("""
<style>
    .stApp { background-color: #000000; font-family: 'Courier New', monospace; }
    [data-testid="stSidebar"] { background-color: #0a0a0a; border-right: 1px solid #333; }
    h1 { color: #FF4500 !important; text-shadow: 0 0 10px #FF4500; border-bottom: 2px solid #FF4500; padding-bottom: 10px;}
    p, label, .stMarkdown, .stText, li, div { color: #e0e0e0 !important; }
    strong { color: #FFD700 !important; } 
    .stTextArea textarea { background-color: #111; color: #FFD700; border: 1px solid #333; }
    div.stButton > button { background-color: #000; color: #FF4500; border: 1px solid #FF4500; font-weight: bold; }
    div.stButton > button:hover { background-color: #FF4500; color: #000; }
    a { color: #FFD700 !important; text-decoration: none; }
</style>
""", unsafe_allow_html=True)

# ================= 🔐 2. 安全层：静默加载密钥 =================
try:
    if "GEMINI_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_KEY"]
    else:
        st.error("⚠️ SYSTEM ERROR: 密钥未配置 (Missing Secrets)")
        st.stop()
except Exception as e:
    st.error(f"⚠️ SYSTEM ERROR: {e}")
    st.stop()

# ================= 📡 3. 数据层：抓取 Polymarket (修复版) =================

@st.cache_data(ttl=300) 
def fetch_top_markets():
    """最终修复版：恢复Top100，按交易量排序，增强价格解析"""
    # 🔴 改回 limit=100 和 sort=volume (交易量大的市场价格波动才精彩)
    url = "https://gamma-api.polymarket.com/events?limit=100&active=true&closed=false&sort=volume"
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            markets_clean = []
            for event in data:
                title = event.get('title', 'Unknown')
                slug = event.get('slug', '')
                markets = event.get('markets', [])
                
                # 🔴 价格解析逻辑增强：兼容不同数据格式
                price_str = "N/A"
                if markets:
                    main_market = markets[0]
                    try:
                        # 1. 尝试获取 Outcome Prices
                        raw_prices = main_market.get('outcomePrices', [])
                        
                        # 2. 如果是字符串(旧API格式)，转成列表；如果是列表(新API格式)，直接用
                        if isinstance(raw_prices, str):
                            prices = json.loads(raw_prices)
                        else:
                            prices = raw_prices
                        
                        # 3. 尝试找到 "Yes" 的价格
                        # 大多数二元市场，索引 0 或 1 是 Yes。通常取最大的那个或者第一个非零的作为展示
                        if prices and len(prices) > 0:
                            # 简单策略：取第一个价格 (通常是 Yes 或主要选项)
                            val = float(prices[0])
                            
                            # 格式化
                            if val < 0.01 and val > 0:
                                price_str = f"{val * 100:.2f}%"
                            else:
                                price_str = f"{val * 100:.1f}%"
                    except Exception as e: 
                        price_str = "N/A"
                
                markets_clean.append({
                    "title": title,
                    "price": price_str,
                    "slug": slug
                })
            return markets_clean
        return []
    except Exception as e:
        return []

# ================= 🧠 4. 智能层：Gemini 2.5 引擎 =================

def ignite_prometheus(user_news, market_list, key):
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # 只取前 50 个市场给 AI，避免 Token 过多溢出
        markets_text = "\n".join([f"- ID:{i} | {m['title']} (Price: {m['price']})" for i, m in enumerate(market_list[:50])])
        
        prompt = f"""
        角色: Prometheus (Polymarket Alpha Hunter).
        任务: 分析【新闻】，从【市场列表】中寻找交易机会。

        [Top Markets]:
        {markets_text}

        [News]:
        "{user_news}"

        要求:
        1. 必须用中文输出。
        2. 挑选 3 个最相关的市场。
        3. 解释二阶因果逻辑 (Second-order thinking)。
        4. 给出 Signal (Long/Short).

        输出格式(Markdown):
        ### 市场英文标题
        - **信号:** 🟢 买入 (Yes) / 🔴 卖出 (No)
        - **逻辑:** (中文深度分析...)
        """
        
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        return f"❌ AI Error: {str(e)}"

# ================= 🖥️ 5. 前端交互层 =================

with st.sidebar:
    st.markdown("## ⚙️ SYSTEM CONFIG")
    st.markdown("`CORE: GEMINI-2.5-FLASH`")
    st.success("🔒 Secure Key Loaded")
    
    st.markdown("---")
    st.markdown("### 🔥 Top Market Monitor")
    
    with st.spinner("Syncing Polymarket..."):
        top_markets = fetch_top_markets()
    
    if top_markets:
        st.info(f"已连接: 监控 {len(top_markets)} 个热门市场")
        # 滚动展示前3个
        for m in top_markets[:3]:
            st.caption(f"📈 {m['title']}")
            st.code(f"Price: {m['price']}")
    else:
        st.error("⚠️ Connection Failed")

st.title("PROMETHEUS PROTOCOL")
st.caption("THE EVENT-DRIVEN INTELLIGENCE ENGINE")
st.markdown("---")

col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("### 📡 INTELLIGENCE INPUT")
    user_news = st.text_area("News", height=150, placeholder="输入突发新闻... (例如: OpenAI 发布会推迟)", label_visibility="collapsed")

with col2:
    st.markdown("<br><br>", unsafe_allow_html=True)
    ignite_btn = st.button("🔥 IGNITE", use_container_width=True)

if ignite_btn:
    if not user_news:
        st.warning("⚠️ 请输入情报")
    elif not top_markets:
        st.error("⚠️ 数据流离线")
    else:
        with st.spinner(">> Analyzing Alpha..."):
            result = ignite_prometheus(user_news, top_markets, api_key)
            st.markdown("---")
            st.markdown(result)
            st.markdown("<br><a href='https://polymarket.com/' target='_blank'><button style='background:transparent;border:1px solid #FFD700;color:#FFD700;width:100%;padding:10px;'>🚀 EXECUTE</button></a>", unsafe_allow_html=True)

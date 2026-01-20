import streamlit as st
import requests
import json
import google.generativeai as genai
import re

# ================= 🔐 0. 密钥管理 =================
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

try:
    from exa_py import Exa
    EXA_AVAILABLE = True
except ImportError:
    EXA_AVAILABLE = False

# ================= 🕵️‍♂️ 1. 系统配置 =================
st.set_page_config(
    page_title="Be Holmes",
    page_icon="🕵️‍♂️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ================= 🎨 2. UI 强力修复 (CSS) =================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');

    /* 1. 背景：地球 + 黑色遮罩 */
    .stApp {
        background-image: linear-gradient(rgba(0, 0, 0, 0.7), rgba(0, 0, 0, 0.9)), 
                          url('https://images.unsplash.com/photo-1451187580459-43490279c0fa?q=80&w=2072&auto=format&fit=crop');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        font-family: 'Inter', sans-serif;
    }

    /* 隐藏顶部默认导航 */
    header[data-testid="stHeader"] { background: transparent !important; }

    /* 标题样式 */
    .hero-title {
        font-size: 4rem;
        font-weight: 800;
        color: white;
        text-align: center;
        margin-top: 60px;
        text-shadow: 0 0 30px rgba(0,0,0,0.8);
    }
    .hero-subtitle {
        text-align: center;
        color: #9ca3af;
        margin-bottom: 40px;
        font-size: 1.1rem;
    }

    /* 输入框样式 */
    .stTextArea textarea {
        background-color: rgba(30, 41, 59, 0.7) !important;
        color: white !important;
        border: 1px solid #475569 !important;
        border-radius: 12px !important;
        text-align: center;
        font-size: 1.1rem !important;
    }
    .stTextArea textarea:focus {
        border-color: #ef4444 !important; /* Red Focus */
        box-shadow: 0 0 15px rgba(239, 68, 68, 0.3) !important;
    }

    /* 🔴 核心修复：红色渐变按钮 */
    /* 强制覆盖 Streamlit 默认按钮样式 */
    div.stButton > button {
        width: 100%;
        background: linear-gradient(90deg, #7f1d1d 0%, #ef4444 50%, #7f1d1d 100%) !important;
        background-size: 200% auto !important;
        color: white !important;
        border: none !important;
        border-radius: 50px !important;
        padding: 15px 30px !important;
        font-size: 1.2rem !important;
        font-weight: 600 !important;
        transition: all 0.5s ease !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3) !important;
    }
    div.stButton > button:hover {
        background-position: right center !important;
        transform: scale(1.02) !important;
        box-shadow: 0 0 25px rgba(239, 68, 68, 0.6) !important;
    }

    /* 👇 核心修复：防止底部列表乱码的 CSS */
    .market-container {
        width: 100%;
        max-width: 900px;
        margin: 50px auto;
        padding: 0 20px;
    }
    .market-header {
        color: #9ca3af;
        font-size: 0.9rem;
        border-left: 3px solid #ef4444;
        padding-left: 10px;
        margin-bottom: 20px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .market-grid {
        display: flex;
        flex-direction: column;
        gap: 12px;
    }
    .market-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: rgba(17, 24, 39, 0.8); /* 深色半透明背景 */
        border: 1px solid #374151;
        padding: 15px 20px;
        border-radius: 10px;
        transition: transform 0.2s;
        backdrop-filter: blur(5px);
    }
    .market-item:hover {
        border-color: #6b7280;
        transform: translateX(5px);
    }
    .m-title {
        color: #e5e7eb;
        font-size: 0.95rem;
        font-weight: 500;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 65%;
    }
    .m-odds {
        display: flex;
        gap: 10px;
        font-family: monospace;
        font-size: 0.85rem;
    }
    .tag-yes {
        color: #4ade80;
        background: rgba(74, 222, 128, 0.1);
        padding: 4px 8px;
        border-radius: 6px;
        border: 1px solid rgba(74, 222, 128, 0.2);
    }
    .tag-no {
        color: #f87171;
        background: rgba(248, 113, 113, 0.1);
        padding: 4px 8px;
        border-radius: 6px;
        border: 1px solid rgba(248, 113, 113, 0.2);
    }
</style>
""", unsafe_allow_html=True)

# ================= 🧠 3. 逻辑函数 =================

def search_with_exa(query):
    # (保持原有逻辑简化版)
    if not EXA_AVAILABLE or not EXA_API_KEY: return [], query
    try:
        exa = Exa(EXA_API_KEY)
        resp = exa.search(f"prediction market {query}", num_results=2, include_domains=["polymarket.com"])
        return [{"title": r.title, "url": r.url} for r in resp.results], query
    except: return [], query

def consult_holmes(query, data):
    # (保持原有逻辑简化版)
    if not GOOGLE_API_KEY: return "Error: API Key Missing"
    model = genai.GenerativeModel('gemini-2.5-flash')
    prompt = f"Act as a hedge fund manager. Analyze this user query: {query}. Context: {data}. Give a 3-line verdict."
    try: return model.generate_content(prompt).text
    except: return "Analysis Failed."

@st.cache_data(ttl=60)
def get_polymarket_top10():
    try:
        url = "https://gamma-api.polymarket.com/markets?limit=10&sort=volume&closed=false"
        data = requests.get(url, timeout=5).json()
        clean_data = []
        for m in data:
            try:
                # 解析 Yes/No 价格
                outcomes = json.loads(m.get('outcomes', '[]'))
                prices = json.loads(m.get('outcomePrices', '[]'))
                if len(prices) >= 2:
                    clean_data.append({
                        "title": m.get('question', 'Unknown'),
                        "yes": int(float(prices[0])*100),
                        "no": int(float(prices[1])*100)
                    })
            except: continue
        return clean_data
    except: return []

# ================= 🖥️ 4. 主界面构建 =================

# 4.1 顶部
st.markdown('<div class="hero-title">Be Holmes</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">Explore the world\'s prediction markets with neural search.</div>', unsafe_allow_html=True)

# 4.2 搜索框 (居中布局)
col1, col2, col3 = st.columns([1, 6, 1])
with col2:
    query = st.text_area("Search", height=60, placeholder="Search for a market, region or event...", label_visibility="collapsed")

# 4.3 按钮 (红色渐变)
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    btn = st.button("Decode Alpha")

# 4.4 结果显示
if btn and query:
    st.markdown("---")
    with st.spinner("Decoding Alpha..."):
        markets, _ = search_with_exa(query)
        report = consult_holmes(query, markets)
        st.success("Analysis Complete")
        st.markdown(f"**Holmes Verdict:**\n\n{report}")

# ================= 👇 5. 底部 TOP 10 (核心修复) =================

top10 = get_polymarket_top10()

if top10:
    # 🌟 关键修复：直接构建纯 HTML 字符串，不要有缩进
    # 我们使用 list comprehension 生成内部 HTML，然后 join 起来
    
    items_html = "".join([
        f"""
        <div class="market-item">
            <div class="m-title" title="{m['title']}">{m['title']}</div>
            <div class="m-odds">
                <span class="tag-yes">Yes {m['yes']}¢</span>
                <span class="tag-no">No {m['no']}¢</span>
            </div>
        </div>
        """ for m in top10
    ])

    # 包装在外层容器中
    final_html = f"""
    <div class="market-container">
        <div class="market-header">Trending on Polymarket (Top 10)</div>
        <div class="market-grid">
            {items_html}
        </div>
    </div>
    """

    # ❗❗❗ 最重要的一步：unsafe_allow_html=True ❗❗❗
    st.markdown(final_html, unsafe_allow_html=True)

else:
    # 如果加载失败，显示简单的提示，避免报错
    st.markdown("<p style='text-align:center;color:#666;'>Loading live markets...</p>", unsafe_allow_html=True)

# 底部版权
st.markdown("<br><br>", unsafe_allow_html=True)
with st.expander("Explore Protocol & Credits"):
    st.write("Powered by Exa.ai & Gemini 2.5")

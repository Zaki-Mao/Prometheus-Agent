import streamlit as st
import requests
import json
import google.generativeai as genai
import time
import re

# ================= 🛠️ 核心依赖检测 =================
try:
    from duckduckgo_search import DDGS
    SEARCH_AVAILABLE = True
except ImportError:
    SEARCH_AVAILABLE = False

# ================= 🕵️‍♂️ 1. SYSTEM CONFIGURATION =================
st.set_page_config(
    page_title="Be Holmes | Web Hunter",
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
    
    .stButton button {
        background: linear-gradient(90deg, #FF4500, #B22222) !important;
        color: white !important; border: none !important;
    }
</style>
""", unsafe_allow_html=True)

# ================= 🧠 3. WEB SEARCH ENGINE =================

def search_polymarket_web(query):
    """
    核心策略：利用 DuckDuckGo 搜索 site:polymarket.com
    这比任何 API 搜索都准，因为它利用了搜索引擎的语义能力。
    """
    if not SEARCH_AVAILABLE: return []
    
    markets_found = []
    seen_slugs = set()
    
    # 构造搜索词：限制在 polymarket 域名内
    search_query = f"site:polymarket.com {query}"
    
    try:
        with DDGS() as ddgs:
            # 抓取前 5 条结果
            results = list(ddgs.text(search_query, max_results=5))
            
            for res in results:
                url = res['href']
                # 解析 URL 提取 slug (ID)
                # URL 格式通常是 polymarket.com/event/slug 或 polymarket.com/market/slug
                match = re.search(r'polymarket\.com/(?:event|market)/([^/]+)', url)
                
                if match:
                    slug = match.group(1)
                    if slug not in seen_slugs:
                        # 拿到 slug 后，去 Gamma API 查详细数据
                        market_data = fetch_market_details(slug)
                        if market_data:
                            markets_found.extend(market_data)
                            seen_slugs.add(slug)
                            
    except Exception as e:
        print(f"Web Search Error: {e}")
        
    return markets_found

def fetch_market_details(slug):
    """根据 Slug 去官方 API 拉取实时赔率"""
    # 尝试作为 Event 查询
    try:
        url = f"https://gamma-api.polymarket.com/events?slug={slug}"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data:
                # Event 里面可能包含多个 Markets，我们取第一个最有代表性的
                markets = data[0].get('markets', [])
                valid_markets = []
                for m in markets[:2]: # 只取前两个
                    p = normalize_data(m)
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
            "slug": m.get('slug', '')
        }
    except: return None

# ================= 🤖 4. AI ANALYST =================

def consult_holmes(user_input, market_data, key):
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        market_context = ""
        if market_data:
            m = market_data[0]
            market_context = f"Found Market: {m['title']} | Odds: {m['odds']} | Volume: ${m['volume']:,.0f}"
        else:
            market_context = "No direct market found via Web Search."
            
        prompt = f"""
        Role: **Be Holmes**, The Web Detective.
        User Input: "{user_input}"
        Web Evidence: {market_context}
        
        Task:
        1. **Connection:** How does the found market relate to the user's news?
        2. **Verdict:** Based on the news, is the market Odds LOW or HIGH?
        3. **Strategy:** Buy Yes / Buy No / Wait.
        
        Output in concise Markdown.
        """
        return model.generate_content(prompt).text
    except Exception as e: return f"AI Error: {e}"

# ================= 🖥️ 5. MAIN INTERFACE =================

active_key = None

with st.sidebar:
    st.markdown("## 💼 DETECTIVE'S TOOLKIT")
    with st.expander("🔑 API Key Settings", expanded=True):
        user_api_key = st.text_input("Gemini Key", type="password")
        if not SEARCH_AVAILABLE:
            st.error("❌ 'duckduckgo-search' missing. Please update requirements.txt")
        else:
            st.caption("✅ Engine: Web Search (DuckDuckGo)")
            
        if user_api_key: active_key = user_api_key
        elif "GEMINI_KEY" in st.secrets: active_key = st.secrets["GEMINI_KEY"]
    
    st.markdown("---")
    st.info("💡 **Tip:** This version searches the entire web for Polymarket links.")

st.title("Be Holmes")
st.caption("WEB SEARCH EDITION | V9.0")
st.markdown("---")

user_news = st.text_area("Input News / Event...", height=100, label_visibility="collapsed", placeholder="e.g. SpaceX IPO rumours, Trump polls...")
ignite_btn = st.button("🔍 WEB INVESTIGATE", use_container_width=True)

if ignite_btn:
    if not user_news:
        st.warning("⚠️ Input required.")
    elif not active_key:
        st.error("⚠️ API Key required.")
    else:
        # 1. Web Search
        with st.status("🌐 Scouring the Deep Web...", expanded=True) as status:
            st.write(f"Searching site:polymarket.com for '{user_news}'...")
            matches = search_polymarket_web(user_news)
            
            if matches:
                st.write(f"✅ Found {len(matches)} related markets via Search Engine.")
            else:
                st.warning("⚠️ No direct Polymarket links found on Google/DDG.")
            
            st.write("⚖️ Holmes Analyzing...")
            report = consult_holmes(user_news, matches, active_key)
            status.update(label="✅ Investigation Complete", state="complete", expanded=False)

        # 2. Results
        if matches:
            st.markdown("### 🎯 Web Search Hits")
            for m in matches:
                st.markdown(f"""
                <div class="market-card">
                    <div style="font-size:1.1em; color:#E63946; font-weight:bold;">{m['title']}</div>
                    <div style="margin-top:5px; font-family:monospace;">
                        <span style="color:#FF4500;">⚡ {m['odds']}</span>
                        <span style="color:#666; margin-left:15px;">Vol: ${m['volume']:,.0f}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            slug = matches[0]['slug']
            st.markdown(f"<a href='https://polymarket.com/event/{slug}' target='_blank'><button class='execute-btn'>🚀 GO TO MARKET</button></a>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 📝 Holmes' Verdict")
        st.info(report)

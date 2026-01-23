import streamlit as st
import requests
import json
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import re
import time
import datetime

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

# ================= 🧠 1.1 STATE MANAGEMENT =================
# 初始化所有session state变量
default_state = {
    "messages": [],
    "current_market": None,
    "first_visit": True,
    "last_search_query": "",
    "chat_history_context": [],
    "search_results": [],
    "show_market_selection": False,
    "selected_market_index": -1,
    "direct_analysis_mode": False,
    "user_news_text": "",
    "is_processing": False,  # 新增：防止重复处理
    "last_user_input": ""  # 新增：记录最后一次用户输入
}

for key, value in default_state.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ================= 🎨 2. UI THEME (优化聊天框) =================
st.markdown("""
<style>
    /* Import Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;900&family=Plus+Jakarta+Sans:wght@400;700&display=swap');

    /* 1. Global Background */
    .stApp {
        background-image: linear-gradient(rgba(0, 0, 0, 0.8), rgba(0, 0, 0, 0.9)), 
                          url('https://upload.cc/i1/2026/01/20/s8pvXA.jpg');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        font-family: 'Inter', sans-serif;
    }

    /* Transparent Header */
    header[data-testid="stHeader"] { background-color: transparent !important; }
    [data-testid="stToolbar"] { visibility: hidden; }
    [data-testid="stDecoration"] { visibility: hidden; }

    /* Hero Title */
    .hero-title {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 4.5rem;
        color: #ffffff;
        text-align: center;
        letter-spacing: -2px;
        margin-bottom: 5px;
        padding-top: 8vh;
        text-shadow: 0 0 20px rgba(0,0,0,0.5);
    }
    
    .hero-subtitle {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 1.1rem;
        color: #9ca3af; 
        text-align: center;
        margin-bottom: 50px;
        font-weight: 400;
    }

    /* 4. Input Field Styling */
    div[data-testid="stVerticalBlock"] > div {
        display: flex;
        flex-direction: column;
        align-items: center;
    }
    .stTextArea { width: 100% !important; max-width: 800px !important; }
    
    .stTextArea textarea {
        background-color: rgba(31, 41, 55, 0.6) !important;
        color: #ffffff !important;
        border: 1px solid #374151 !important;
        border-radius: 16px !important;
        padding: 15px 20px !important; 
        font-size: 1rem !important;
        text-align: left !important;
        line-height: 1.6 !important;
        backdrop-filter: blur(10px);
        transition: all 0.3s ease;
    }
    
    .stTextArea textarea:focus {
        border-color: rgba(239, 68, 68, 0.8) !important;
        box-shadow: 0 0 15px rgba(220, 38, 38, 0.3) !important;
        background-color: rgba(31, 41, 55, 0.9) !important;
    }

    /* 3. Button Styling */
    div.stButton > button:first-child {
        background: linear-gradient(90deg, #7f1d1d 0%, #dc2626 50%, #7f1d1d 100%) !important;
        background-size: 200% auto !important;
        color: #ffffff !important;
        border: 1px solid rgba(239, 68, 68, 0.5) !important;
        border-radius: 50px !important;
        padding: 12px 50px !important;
        font-weight: 600 !important;
        font-size: 1.1rem !important;
        margin-top: 10px !important;
        transition: 0.5s !important;
        box-shadow: 0 0 20px rgba(0,0,0,0.5) !important;
    }
    
    div.stButton > button:first-child:hover {
        background-position: right center !important;
        transform: scale(1.05) !important;
        box-shadow: 0 0 30px rgba(220, 38, 38, 0.6) !important;
        border-color: #fca5a5 !important;
    }
    
    div.stButton > button:first-child:active {
        transform: scale(0.98) !important;
    }

    /* Result Card */
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
    
    /* Market Selection Card */
    .market-selection-card {
        background: rgba(17, 24, 39, 0.7);
        border: 1px solid #374151;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        transition: all 0.3s ease;
        backdrop-filter: blur(5px);
    }
    
    .market-selection-card:hover {
        border-color: #ef4444;
        background: rgba(31, 41, 55, 0.9);
        transform: translateY(-2px);
    }
    
    .market-selection-card.selected {
        border: 2px solid #ef4444;
        background: rgba(31, 41, 55, 0.95);
        box-shadow: 0 0 15px rgba(239, 68, 68, 0.3);
    }
    
    .select-market-btn {
        background: linear-gradient(90deg, #7f1d1d 0%, #dc2626 100%) !important;
        color: white !important;
        border: none !important;
        padding: 8px 20px !important;
        border-radius: 6px !important;
        font-size: 0.9rem !important;
        font-weight: 600 !important;
        transition: all 0.3s !important;
    }
    
    .select-market-btn:hover {
        transform: scale(1.05) !important;
        box-shadow: 0 0 10px rgba(220, 38, 38, 0.5) !important;
    }
    
    /* Direct Analysis Button */
    .direct-analysis-btn {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%) !important;
        color: white !important;
        border: none !important;
        padding: 10px 25px !important;
        border-radius: 8px !important;
        font-size: 1rem !important;
        font-weight: 600 !important;
        transition: all 0.3s !important;
        margin-top: 20px !important;
        width: 100% !important;
        max-width: 300px !important;
    }
    
    .direct-analysis-btn:hover {
        transform: scale(1.05) !important;
        box-shadow: 0 0 15px rgba(59, 130, 246, 0.5) !important;
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
        cursor: pointer;
    }
    .market-item:hover {
        border-color: #ef4444;
        background: rgba(31, 41, 55, 0.9);
        transform: translateY(-2px);
    }
    .m-title {
        color: #e5e7eb;
        font-size: 0.95rem;
        font-weight: 500;
        margin-bottom: 12px;
        line-height: 1.4;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    .m-odds { display: flex; gap: 8px; font-size: 0.75rem; margin-top: auto; }
    .tag-yes { background: rgba(6, 78, 59, 0.4); color: #4ade80; padding: 2px 8px; border-radius: 4px; font-weight: bold;}
    .tag-no { background: rgba(127, 29, 29, 0.4); color: #f87171; padding: 2px 8px; border-radius: 4px; font-weight: bold;}
    
    /* 优化聊天消息样式 */
    .stChatMessage {
        background: rgba(31, 41, 55, 0.6) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 16px !important;
        margin-bottom: 20px !important;
        padding: 20px !important;
        backdrop-filter: blur(8px) !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3) !important;
        max-width: 90% !important;
    }
    
    /* 用户消息样式 */
    .stChatMessage[data-testid="stChatMessage"][data-message-author="user"] {
        background: rgba(17, 24, 39, 0.8) !important;
        border-left: 4px solid #ef4444 !important;
        margin-left: auto !important;
        margin-right: 0 !important;
        width: fit-content !important;
        min-width: 200px !important;
        max-width: 700px !important;
    }
    
    /* 助手消息样式 */
    .stChatMessage[data-testid="stChatMessage"][data-message-author="assistant"] {
        background: rgba(17, 24, 39, 0.8) !important;
        border-left: 4px solid #3b82f6 !important;
        margin-left: 0 !important;
        margin-right: auto !important;
        width: fit-content !important;
        min-width: 200px !important;
        max-width: 700px !important;
    }
    
    /* 聊天消息内容 */
    .stChatMessageContent {
        font-family: 'Inter', sans-serif !important;
        font-size: 1.05rem !important;
        line-height: 1.7 !important;
        color: #f3f4f6 !important;
        padding: 5px !important;
    }
    
    /* 聊天输入框 */
    .stChatInput {
        background: rgba(31, 41, 55, 0.8) !important;
        border: 1px solid #374151 !important;
        border-radius: 16px !important;
        padding: 15px !important;
        backdrop-filter: blur(10px) !important;
        margin-top: 20px !important;
    }
    
    .stChatInput textarea {
        background: transparent !important;
        color: white !important;
        font-size: 1.1rem !important;
        min-height: 60px !important;
        padding: 12px !important;
    }
    
    .stChatInput button {
        background: linear-gradient(90deg, #7f1d1d 0%, #dc2626 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 25px !important;
        font-weight: 600 !important;
        margin-top: 10px !important;
    }
    
    /* Market Selection Container */
    .selection-container {
        background: rgba(17, 24, 39, 0.6);
        border: 1px solid #374151;
        border-radius: 12px;
        padding: 25px;
        margin: 30px auto;
        max-width: 900px;
        backdrop-filter: blur(8px);
    }
    
    /* Relevance Indicator */
    .relevance-badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.7rem;
        font-weight: 600;
        margin-left: 10px;
    }
    .relevance-high {
        background: rgba(6, 78, 59, 0.4);
        color: #4ade80;
        border: 1px solid rgba(6, 78, 59, 0.6);
    }
    .relevance-medium {
        background: rgba(146, 64, 14, 0.4);
        color: #fdba74;
        border: 1px solid rgba(146, 64, 14, 0.6);
    }
    .relevance-low {
        background: rgba(127, 29, 29, 0.4);
        color: #f87171;
        border: 1px solid rgba(127, 29, 29, 0.6);
    }
    
    /* No Market Found Container */
    .no-market-container {
        background: rgba(17, 24, 39, 0.6);
        border: 1px solid #374151;
        border-radius: 12px;
        padding: 30px;
        margin: 30px auto;
        max-width: 800px;
        backdrop-filter: blur(8px);
        text-align: center;
    }
    
    /* 修复Streamlit的全局样式冲突 */
    .main .block-container {
        padding-top: 2rem !important;
        padding-bottom: 5rem !important;
    }
    
    /* 隐藏Streamlit的默认滚动条 */
    .stApp [data-testid="stVerticalBlock"] {
        gap: 0.5rem !important;
    }
</style>
""", unsafe_allow_html=True)

# ================= 🧠 3. LOGIC CORE =================

def detect_language(text):
    """检测文本的主要语言"""
    # 简单检测：如果有中文字符就认为是中文
    if re.search(r'[\u4e00-\u9fff]', text):
        return 'chinese'
    else:
        return 'english'

def extract_entities_and_keywords(user_text):
    """使用Gemini提取新闻中的核心实体和关键词，优先排序"""
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # 根据输入语言调整提示词
        user_lang = detect_language(user_text)
        if user_lang == 'chinese':
            prompt = f"""
            分析以下新闻，提取用于搜索预测市场的关键词。请按重要性排序：
            
            新闻原文："{user_text}"
            
            要求：
            1. 识别核心主体（公司、人物、产品）
            2. 识别核心事件/主题
            3. 识别次要信息：如地点、时间等
            4. 按以下格式输出（请用英文输出关键词）：
            
            核心实体: [实体1], [实体2], [实体3]
            事件关键词: [关键词1], [关键词2], [关键词3]
            搜索优先级: 
            1. [最高优先级搜索词]
            2. [中优先级搜索词]
            3. [低优先级搜索词]
            """
        else:
            prompt = f"""
            Analyze the following news and extract keywords for searching prediction markets. Sort by importance:
            
            News: "{user_text}"
            
            Requirements:
            1. Identify core entities (companies, people, products)
            2. Identify core events/themes
            3. Identify secondary information: location, time, etc.
            4. Output in the following format:
            
            Core Entities: [entity1], [entity2], [entity3]
            Event Keywords: [keyword1], [keyword2], [keyword3]
            Search Priority: 
            1. [Highest priority search term]
            2. [Medium priority search term]
            3. [Low priority search term]
            """
        
        resp = model.generate_content(prompt)
        text = resp.text.strip()
        
        # 解析响应
        entities = []
        events = []
        search_queries = []
        
        lines = text.split('\n')
        for line in lines:
            if line.startswith('核心实体:') or line.startswith('Core Entities:'):
                content = line.replace('核心实体:', '').replace('Core Entities:', '')
                entities = [e.strip() for e in content.split(',')]
            elif line.startswith('事件关键词:') or line.startswith('Event Keywords:'):
                content = line.replace('事件关键词:', '').replace('Event Keywords:', '')
                events = [e.strip() for e in content.split(',')]
            elif line.startswith('1.'):
                search_queries.append(line.split('. ', 1)[1].strip())
            elif line.startswith('2.'):
                search_queries.append(line.split('. ', 1)[1].strip())
            elif line.startswith('3.'):
                search_queries.append(line.split('. ', 1)[1].strip())
        
        # 如果没有提取到搜索查询，使用备用策略
        if not search_queries:
            # 组合实体和事件
            if entities and events:
                search_queries = [
                    f"{entities[0]} {events[0]} prediction market",
                    f"{' '.join(entities[:2])} market",
                    f"{' '.join(entities)} Polymarket"
                ]
            else:
                # 最后备选：简单清理文本
                cleaned = re.sub(r'[^a-zA-Z0-9\s]', ' ', user_text)
                words = cleaned.lower().split()
                stop_words = ["the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were", "be", "been", "being"]
                keywords = [w for w in words if w not in stop_words][:6]
                search_queries = [' '.join(keywords)]
        
        return {
            'entities': entities,
            'events': events,
            'search_queries': search_queries
        }
        
    except Exception as e:
        print(f"Entity extraction error: {e}")
        # 回退策略
        cleaned = re.sub(r'[^a-zA-Z0-9\s]', ' ', user_text)
        return {
            'entities': [],
            'events': [],
            'search_queries': [cleaned[:100]]
        }

def calculate_relevance_score(market_title, entities, events):
    """计算市场标题与新闻的相关性分数"""
    title_lower = market_title.lower()
    
    # 初始化分数
    score = 0
    
    # 检查核心实体
    for entity in entities:
        entity_lower = entity.lower()
        if entity_lower in title_lower:
            score += 10  # 核心实体匹配高分
            # 如果实体在开头，额外加分
            if title_lower.startswith(entity_lower):
                score += 5
    
    # 检查事件关键词
    for event in events:
        event_lower = event.lower()
        if event_lower in title_lower:
            score += 5  # 事件匹配中分
    
    # 特殊关键词加分
    special_keywords = ['tesla', 'elon', 'musk', 'fsd', 'full self-driving', 'autonomous']
    for keyword in special_keywords:
        if keyword in title_lower:
            score += 3
    
    # 减分项：过度强调中国（如果核心实体不是中国公司）
    if 'china' in title_lower or 'chinese' in title_lower:
        if not any(e.lower() in ['alibaba', 'tencent', 'baidu', 'xiaomi'] for e in entities):
            score -= 2  # 如果不是中国公司，中国相关减分
    
    return score

def search_with_exa_optimized(user_text):
    """优化的语义搜索，聚焦核心实体"""
    if not EXA_AVAILABLE or not EXA_API_KEY: 
        return [], []
    
    # 提取实体和搜索查询
    extraction_result = extract_entities_and_keywords(user_text)
    entities = extraction_result['entities']
    events = extraction_result['events']
    search_queries = extraction_result['search_queries']
    
    print(f"提取的实体: {entities}")
    print(f"提取的事件: {events}")
    print(f"搜索查询: {search_queries}")
    
    markets_found = []
    seen_titles = set()
    
    try:
        exa = Exa(EXA_API_KEY)
        
        # 按优先级顺序尝试搜索
        for query in search_queries:
            if len(markets_found) >= 15:  # 最多收集15个结果
                break
                
            try:
                # 尝试不同的搜索格式
                search_formats = [
                    f"{query} prediction market Polymarket",
                    f"Polymarket market {query}",
                    f"{query} market odds",
                    f"prediction market {query}"
                ]
                
                for search_str in search_formats:
                    print(f"尝试搜索: {search_str}")
                    
                    search_response = exa.search(
                        search_str,
                        num_results=8, 
                        type="neural",
                        include_domains=["polymarket.com"]
                    )
                    
                    for result in search_response.results:
                        match = re.search(r'polymarket\.com/(?:event|market)/([^/]+)', result.url)
                        if match:
                            slug = match.group(1)
                            # 过滤无关页面
                            if slug not in ['profile', 'login', 'leaderboard', 'rewards', 'orders', 'activity']:
                                market_data = fetch_poly_details(slug)
                                if market_data:
                                    for market in market_data:
                                        title = market.get('title', '')
                                        
                                        # 去重
                                        if title and title not in seen_titles:
                                            # 计算相关性分数
                                            relevance = calculate_relevance_score(title, entities, events)
                                            market['relevance_score'] = relevance
                                            market['slug'] = slug
                                            markets_found.append(market)
                                            seen_titles.add(title)
                                            
            except Exception as e:
                print(f"搜索查询 '{query}' 错误: {e}")
                continue
                        
    except Exception as e: 
        print(f"搜索主错误: {e}")
    
    # 按相关性排序
    markets_found.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
    
    # 过滤掉相关性太低的结果
    filtered_markets = [m for m in markets_found if m.get('relevance_score', 0) > 5]
    
    return filtered_markets[:10], search_queries[0] if search_queries else ""

@st.cache_data(ttl=60)
def fetch_top_10_markets():
    try:
        url = "https://gamma-api.polymarket.com/events?limit=12&sort=volume&closed=false"
        resp = requests.get(url, timeout=5).json()
        markets = []
        if isinstance(resp, list):
            for event in resp:
                try:
                    title = event.get('title', 'Unknown Event')
                    event_markets = event.get('markets', [])
                    if not event_markets or not isinstance(event_markets, list): continue
                    
                    active_markets = []
                    for m in event_markets:
                        if m.get('closed') is True: continue
                        if not m.get('outcomePrices'): continue
                        active_markets.append(m)
                    if not active_markets: continue

                    active_markets.sort(key=lambda x: float(x.get('volume', 0) or 0), reverse=True)
                    m = active_markets[0]

                    outcomes = m.get('outcomes')
                    if isinstance(outcomes, str): outcomes = json.loads(outcomes)
                    prices = m.get('outcomePrices')
                    if isinstance(prices, str): prices = json.loads(prices)
                    if not outcomes or not prices or len(prices) != len(outcomes): continue

                    yes_price = 0
                    no_price = 0
                    
                    if "Yes" in outcomes and "No" in outcomes:
                        try:
                            yes_index = outcomes.index("Yes")
                            yes_raw = float(prices[yes_index])
                            yes_price = int(yes_raw * 100)
                            no_price = 100 - yes_price
                        except:
                            yes_price = int(float(prices[0]) * 100)
                            no_price = 100 - yes_price
                    else:
                        float_prices = [float(p) for p in prices]
                        max_price = max(float_prices)
                        yes_price = int(max_price * 100)
                        no_price = 100 - yes_price

                    markets.append({
                        "title": title,
                        "yes": yes_price,
                        "no": no_price,
                        "slug": event.get('slug', '')
                    })
                except Exception: continue
        return markets
    except Exception: return []

def fetch_poly_details(slug):
    valid_markets = []
    try:
        url = f"https://gamma-api.polymarket.com/events?slug={slug}"
        resp = requests.get(url, timeout=3).json()
        if isinstance(resp, list) and resp:
            for m in resp[0].get('markets', [])[:1]: 
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
        outcomes = m.get('outcomes')
        if isinstance(outcomes, str): outcomes = json.loads(outcomes)
        prices = m.get('outcomePrices')
        if isinstance(prices, str): prices = json.loads(prices)
        
        if not outcomes or not prices: return None

        display_label = ""
        if "Yes" in outcomes:
            idx = outcomes.index("Yes")
            price = float(prices[idx])
            display_label = f"Yes: {price*100:.1f}%"
        else:
            float_prices = [float(p) for p in prices]
            max_p = max(float_prices)
            max_idx = float_prices.index(max_p)
            top_name = outcomes[max_idx]
            display_label = f"{top_name}: {max_p*100:.1f}%"

        return {
            "title": m.get('question', 'Unknown'),
            "odds": display_label,
            "volume": float(m.get('volume', 0)),
            "slug": m.get('slug', '') or m.get('market_slug', '')
        }
    except: return None

# ================= 🧠 3.1 AGENT BRAIN =================

safety_config = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

def check_search_intent(user_text, current_market=None):
    """判断用户是否想要搜索新主题"""
    # 防止重复处理同一个输入
    if user_text == st.session_state.get("last_user_input", ""):
        return False
        
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        context = {
            'current_market': current_market['title'] if current_market else None,
            'last_search': st.session_state.last_search_query,
            'is_follow_up': len(st.session_state.messages) > 1
        }
        
        # 根据用户语言调整提示
        user_lang = detect_language(user_text)
        if user_lang == 'chinese':
            prompt = f"""
            分析用户是否想要搜索新的预测市场主题。
            
            上下文：
            - 当前主题：{context['current_market']}
            - 上次搜索：{context['last_search']}
            - 是否是后续对话：{context['is_follow_up']}
            
            用户输入："{user_text}"
            
            规则：
            1. 如果用户明确说"搜索"、"查找"、"找找"、"看看"等 → 是
            2. 如果用户提到完全不同的实体/主题 → 是
            3. 如果用户询问当前主题的细节/分析/意见 → 否
            4. 如果查询很短（1-3个词）且不明显是新主题 → 否
            
            输出只包含"YES"或"NO"。
            """
        else:
            prompt = f"""
            Analyze if the user wants to search for a NEW prediction market topic.
            
            CONTEXT:
            - Current topic: {context['current_market']}
            - Last search: {context['last_search']}
            - Is follow-up conversation: {context['is_follow_up']}
            
            USER INPUT: "{user_text}"
            
            RULES:
            1. If user explicitly says "search", "find", "look for", "show me" → YES
            2. If user mentions a completely different entity/topic → YES
            3. If user asks about details/analysis/opinion of current topic → NO
            4. If query is very short (1-3 words) and not obviously new → NO
            
            Output only "YES" or "NO".
            """
        
        resp = model.generate_content(prompt, safety_settings=safety_config)
        result = resp.text.strip().upper()
        
        # 记录最后一次处理
        st.session_state.last_user_input = user_text
        
        if "YES" in result:
            return True
        elif "NO" in result:
            return False
        else:
            # 使用简单规则作为回退
            if user_lang == 'chinese':
                search_triggers = ["搜索", "查找", "找找", "看看", "新", "其他", "不同的"]
            else:
                search_triggers = ["search", "find", "look for", "show me", "new", "different"]
            
            if any(trigger.lower() in user_text.lower() for trigger in search_triggers):
                return True
            if current_market and len(user_text.split()) <= 3:
                return False
            return False
            
    except Exception as e:
        print(f"Intent check error: {e}")
        return False

def stream_chat_response(messages, market_data=None, user_query="", direct_analysis=False):
    """生成分析响应，自动匹配用户语言"""
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # 检测用户语言
    user_lang = detect_language(user_query)
    if not user_query and messages:
        # 从消息中检测语言
        for msg in reversed(messages):
            if msg["role"] == "user":
                user_lang = detect_language(msg["content"])
                break
    
    # 构建对话历史上下文
    recent_history = "\n".join([
        f"{'User' if msg['role']=='user' else 'Assistant'}: {msg['content'][:100]}..."
        for msg in messages[-3:]
    ]) if len(messages) > 0 else "No previous conversation."
    
    # 根据分析模式构建不同的上下文
    if direct_analysis:
        # 直接分析模式：不依赖市场数据
        if user_lang == 'chinese':
            market_context = """
            模式：直接新闻分析（未找到或选择特定预测市场）
            
            重要提示：您正在直接分析新闻，不依赖具体市场数据。
            重点分析：
            1. 新闻的广泛影响
            2. 此新闻可能存在的潜在预测市场
            3. 为决策者提供战略见解
            """
        else:
            market_context = """
            MODE: DIRECT NEWS ANALYSIS (No specific prediction market found or selected)
            
            IMPORTANT: You are analyzing the news directly without specific market data.
            Focus on:
            1. Analyzing the news implications broadly
            2. Identifying potential prediction markets that COULD exist for this news
            3. Providing strategic insights for decision-makers
            """
    elif market_data:
        # 基于市场的分析模式
        if user_lang == 'chinese':
            market_context = f"""
            选择的市场数据：
            - 事件/问题："{market_data['title']}"
            - 当前赔率：{market_data['odds']}
            - 交易量：${market_data['volume']:,.0f}
            - 相关性分数：{market_data.get('relevance_score', 'N/A')}
            """
        else:
            market_context = f"""
            SELECTED MARKET DATA:
            - Event/Question: "{market_data['title']}"
            - Current Odds: {market_data['odds']}
            - Trading Volume: ${market_data['volume']:,.0f}
            - Relevance Score: {market_data.get('relevance_score', 'N/A')}
            """
    else:
        # 无市场数据的一般分析
        if user_lang == 'chinese':
            market_context = """
            模式：一般新闻分析
            注意：此分析没有可用的具体预测市场数据。
            """
        else:
            market_context = """
            MODE: GENERAL NEWS ANALYSIS
            Note: No specific prediction market data available for this analysis.
            """
    
    user_intel = user_query if user_query else "the provided intelligence"
    
    # 根据用户语言构建系统提示
    if user_lang == 'chinese':
        system_prompt = f"""
        你是Be Holmes，一位愤世嫉俗但理性的宏观对冲基金经理和地缘政治风险分析师。
        当前日期：{current_date}
        
        用户情报/查询：{user_intel}
        
        {market_context}
        
        最近对话：
        {recent_history}
        
        {'='*60}
        分析框架：
        """
        
        if direct_analysis or not market_data:
            system_prompt += f"""
            1. **新闻解构**：分解新闻中的关键事实和主张
            2. **来源可信度**：评估信息来源的可靠性
            3. **地缘政治背景**：将此新闻置于更广泛的地缘政治格局中
            4. **经济影响**：分析潜在的经济后果
            5. **市场创造机会**：为此新闻应该存在哪些预测市场？
            6. **风险评估**：识别关键风险及其概率
            7. **战略建议**：为决策者提供可操作的见解
            
            关键要求（直接分析模式）：
            - 像对冲基金经理一样思考，不仅仅是分析师
            - 识别第二和第三阶后果
            - 建议具体的交易/投资想法（即使不在Polymarket上）
            - 尽可能量化概率（例如，"有60%的可能性..."）
            - 考虑事件的时间和顺序
            - 突出不对称的风险/回报机会
            """
        else:
            system_prompt += f"""
            1. **市场背景**：解释这个预测市场是关于什么的
            2. **当前情绪**：分析当前赔率及其含义
            3. **新闻影响**：用户的情报/新闻如何影响这个市场？
            4. **市场无效性**：识别任何定价错误或机会
            5. **风险评估**：关键风险是什么？
            6. **交易建议**：明确的买入/卖出/持有建议及理由
            7. **头寸规模**：建议适当的头寸规模
            
            关键要求（市场分析模式）：
            - 尽可能数据驱动和量化
            - 保持怀疑、逆向思维的心态
            - 提供具体的概率估计
            - 如果提出建议，建议头寸规模
            - 突出上行和下行场景
            """
        
        system_prompt += f"""
        
        格式：
        以简短的执行摘要（1-2句话）开始，然后进行详细分析。
        对关键点使用粗体，对细微观察使用斜体。
        请使用中文回复。
        """
    else:
        system_prompt = f"""
        You are Be Holmes, a cynical but rational Macro Hedge Fund Manager and geopolitical risk analyst.
        Current Date: {current_date}
        
        USER'S INTELLIGENCE/QUERY: {user_intel}
        
        {market_context}
        
        RECENT CONVERSATION:
        {recent_history}
        
        {'='*60}
        ANALYSIS FRAMEWORK:
        """
        
        if direct_analysis or not market_data:
            system_prompt += f"""
            1. **News Deconstruction**: Break down the key facts and claims in the news
            2. **Source Credibility**: Assess the reliability of the information source
            3. **Geopolitical Context**: Place this news in the broader geopolitical landscape
            4. **Economic Implications**: Analyze potential economic consequences
            5. **Market Creation Opportunity**: What prediction markets SHOULD exist for this?
            6. **Risk Assessment**: Identify key risks and their probabilities
            7. **Strategic Recommendations**: Actionable insights for decision-makers
            
            CRITICAL REQUIREMENTS (Direct Analysis Mode):
            - Think like a hedge fund manager, not just an analyst
            - Identify second and third-order consequences
            - Suggest concrete trading/investment ideas (even if not on Polymarket)
            - Quantify probabilities where possible (e.g., "60% chance that...")
            - Consider timing and sequencing of events
            - Highlight asymmetrical risk/reward opportunities
            """
        else:
            system_prompt += f"""
            1. **Market Context**: Explain what this prediction market is about
            2. **Current Sentiment**: Analyze the current odds and what they imply
            3. **News Impact**: How does the user's intelligence/news affect this market?
            4. **Market Inefficiencies**: Identify any mispricings or opportunities
            5. **Risk Assessment**: What are the key risks?
            6. **Trading Recommendation**: Clear buy/sell/hold recommendation with reasoning
            7. **Position Sizing**: Suggest appropriate position sizing
            
            CRITICAL REQUIREMENTS (Market Analysis Mode):
            - Be data-driven and quantitative where possible
            - Maintain a skeptical, contrarian mindset
            - Provide specific probability estimates
            - Suggest position sizing if making a recommendation
            - Highlight both upside and downside scenarios
            """
        
        system_prompt += f"""
        
        FORMAT:
        Start with a brief executive summary (1-2 sentences), then detailed analysis.
        Use bold for key points and italic for nuanced observations.
        Please respond in English.
        """
    
    history = [{"role": "user", "parts": [system_prompt]}]
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        history.append({"role": role, "parts": [msg["content"]]})
    
    try:
        response = model.generate_content(history, safety_settings=safety_config)
        return response.text
    except ValueError:
        if user_lang == 'chinese':
            return "⚠️ 安全过滤器触发。请重新表达您的查询。"
        else:
            return "⚠️ Safety filter triggered. Please rephrase your query."
    except Exception as e:
        if user_lang == 'chinese':
            return f"⚠️ 错误：{str(e)}"
        else:
            return f"⚠️ Error: {str(e)}"

def analyze_selected_market(market_index, user_query):
    """分析用户选择的市场"""
    if 0 <= market_index < len(st.session_state.search_results):
        selected_market = st.session_state.search_results[market_index]
        st.session_state.current_market = selected_market
        st.session_state.selected_market_index = market_index
        st.session_state.direct_analysis_mode = False
        
        st.session_state.messages = []
        st.session_state.messages.append({"role": "user", "content": f"Analyze this intel in relation to the selected market: {user_query}"})
        
        with st.spinner("🧠 Decoding Alpha..."):
            response = stream_chat_response(
                st.session_state.messages, 
                selected_market,
                user_query,
                direct_analysis=False
            )
            st.session_state.messages.append({"role": "assistant", "content": response})
        
        st.session_state.show_market_selection = False
        return True
    return False

def analyze_directly(user_query):
    """直接分析新闻（不基于特定市场）"""
    st.session_state.current_market = None
    st.session_state.selected_market_index = -1
    st.session_state.direct_analysis_mode = True
    
    st.session_state.messages = []
    st.session_state.messages.append({"role": "user", "content": f"Analyze this news directly without specific market data: {user_query}"})
    
    with st.spinner("🧠 Conducting deep analysis..."):
        response = stream_chat_response(
            st.session_state.messages, 
            None,
            user_query,
            direct_analysis=True
        )
        st.session_state.messages.append({"role": "assistant", "content": response})
    
    st.session_state.show_market_selection = False
    return True

# ================= 🖥️ 4. MAIN INTERFACE =================

# 4.1 Hero Section
st.markdown('<h1 class="hero-title">Be Holmes</h1>', unsafe_allow_html=True)
st.markdown('<p class="hero-subtitle">Expert news analysis & prediction market intelligence</p>', unsafe_allow_html=True)

# 4.2 Search Section
_, mid, _ = st.columns([1, 6, 1])
with mid:
    user_news = st.text_area("Input", height=100, placeholder="Paste news, intelligence, or event description for analysis...", label_visibility="collapsed", key="main_search_input")

# 4.3 Button Section
_, btn_col, _ = st.columns([1, 2, 1])
with btn_col:
    ignite_btn = st.button("🔍 Search & Analyze", use_container_width=True)

# 4.4 触发搜索逻辑（修复bug：防止重复处理）
if ignite_btn and not st.session_state.is_processing:
    if not KEYS_LOADED:
        st.error("🔑 API Keys not found in Secrets.")
    elif not user_news:
        st.warning("Please enter intelligence to analyze.")
    else:
        # 设置处理状态
        st.session_state.is_processing = True
        
        # 保存用户新闻
        st.session_state.user_news_text = user_news
        
        # 重置状态
        st.session_state.messages = []
        st.session_state.current_market = None
        st.session_state.selected_market_index = -1
        st.session_state.direct_analysis_mode = False
        
        with st.spinner("🔍 Analyzing news and searching Polymarket..."):
            matches, keyword = search_with_exa_optimized(user_news)
        
        st.session_state.last_search_query = keyword
        st.session_state.search_results = matches
        
        if matches:
            # 找到市场：显示市场选择界面
            st.session_state.show_market_selection = True
        else:
            # 没有找到市场：直接进行分析
            st.session_state.show_market_selection = False
            analyze_directly(user_news)
        
        # 重置处理状态
        st.session_state.is_processing = False
        st.rerun()

# ================= 🗳️ 5. MARKET SELECTION INTERFACE =================

if st.session_state.show_market_selection and st.session_state.search_results:
    st.markdown("---")
    
    # 显示搜索摘要
    with st.expander("🔎 Search Summary", expanded=True):
        st.info(f"""
        **Search Query:** {st.session_state.last_search_query}
        
        **Found Markets:** {len(st.session_state.search_results)} relevant prediction markets
        
        **Relevance Scoring:**
        - 🟢 High (>15): Directly related to core entities
        - 🟡 Medium (10-15): Partially related
        - 🔴 Low (5-10): Weakly related
        """)
    
    st.markdown(f"""
    <div class="selection-container">
        <h3 style="color: #e5e7eb; margin-bottom: 5px;">📊 Select a Market for Analysis</h3>
        <p style="color: #9ca3af; margin-bottom: 25px;">Markets sorted by relevance to your news:</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 显示市场列表
    for idx, market in enumerate(st.session_state.search_results):
        relevance_score = market.get('relevance_score', 0)
        
        # 确定相关性标签
        if relevance_score > 15:
            relevance_class = "relevance-high"
            relevance_label = "🟢 High"
        elif relevance_score > 10:
            relevance_class = "relevance-medium"
            relevance_label = "🟡 Medium"
        else:
            relevance_class = "relevance-low"
            relevance_label = "🔴 Low"
        
        col1, col2 = st.columns([4, 1])
        
        with col1:
            is_selected = (st.session_state.selected_market_index == idx)
            card_class = "market-selection-card selected" if is_selected else "market-selection-card"
            
            st.markdown(f"""
            <div class="{card_class}">
                <div style="font-size: 1.1rem; color: #e5e7eb; font-weight: 500; margin-bottom: 8px;">
                    {market['title']}
                    <span class="relevance-badge {relevance_class}">{relevance_label}</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span style="color: #4ade80; font-weight: 600;">{market['odds']}</span>
                        <span style="color: #9ca3af; margin-left: 15px;">Volume: ${market['volume']:,.0f}</span>
                        <span style="color: #9ca3af; margin-left: 15px;">Score: {relevance_score}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            if st.button(f"Select", key=f"select_{idx}", use_container_width=True):
                analyze_selected_market(idx, st.session_state.user_news_text)
                st.rerun()
    
    # 添加"直接分析"按钮
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🧠 Direct News Analysis (No Market)", use_container_width=True, type="secondary"):
            analyze_directly(st.session_state.user_news_text)
            st.rerun()
    
    # 说明文字
    st.markdown("""
    <div style="text-align: center; margin-top: 30px; padding: 20px; background: rgba(255,255,255,0.03); border-radius: 10px;">
        <p style="color: #9ca3af; margin-bottom: 10px;">💡 <strong>Two Analysis Modes:</strong></p>
        <p style="color: #9ca3af; font-size: 0.9rem; margin-bottom: 5px;">
        <span style="color: #ef4444;">• Market-Based Analysis</span>: Select a market above for targeted trading insights
        </p>
        <p style="color: #9ca3af; font-size: 0.9rem;">
        <span style="color: #3b82f6;">• Direct News Analysis</span>: Click the blue button for broader strategic analysis without specific market data
        </p>
    </div>
    """, unsafe_allow_html=True)

# ================= 🗣️ 6. CHAT INTERFACE =================

if not st.session_state.show_market_selection and st.session_state.messages:
    st.markdown("---")
    
    # 显示当前分析模式
    if st.session_state.direct_analysis_mode:
        st.markdown(f"""
        <div class="market-card">
            <div style="font-size:0.9rem; color:#3b82f6; margin-bottom:5px;">
                📰 <strong>DIRECT NEWS ANALYSIS MODE</strong>
            </div>
            <div style="font-size:1.1rem; color:#e5e7eb; margin-bottom:10px; font-weight:bold;">
                Analyzing: "{st.session_state.user_news_text[:100]}..."
            </div>
            <div style="display:flex; justify-content:space-between; align-items:flex-end;">
                <div>
                    <div style="font-family:'Plus Jakarta Sans'; color:#3b82f6; font-size:1.5rem; font-weight:700;">
                        Strategic Intelligence
                    </div>
                    <div style="color:#9ca3af; font-size:0.8rem;">Geopolitical & Economic Analysis</div>
                </div>
                <div style="text-align:right;">
                    <div style="color:#e5e7eb; font-weight:600; font-size:1.1rem;">No Market Data</div>
                    <div style="color:#9ca3af; font-size:0.8rem;">Pure News Analysis</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    elif st.session_state.current_market:
        m = st.session_state.current_market
        relevance_score = m.get('relevance_score', 0)
        
        # 相关性指示器
        if relevance_score > 15:
            relevance_indicator = "🟢 Highly Relevant"
        elif relevance_score > 10:
            relevance_indicator = "🟡 Moderately Relevant"
        else:
            relevance_indicator = "🔴 Weakly Relevant"
        
        st.markdown(f"""
        <div class="market-card">
            <div style="font-size:0.9rem; color:#ef4444; margin-bottom:5px;">
                📊 <strong>MARKET-BASED ANALYSIS</strong> • {relevance_indicator}
            </div>
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
    
    # 显示消息历史（使用优化后的聊天框）
    for i, msg in enumerate(st.session_state.messages):
        if i == 0: continue 
        
        with st.chat_message(msg["role"], avatar="🕵️‍♂️" if msg["role"] == "assistant" else "👤"):
            # 使用st.markdown以确保正确渲染
            st.markdown(msg['content'])

    # 聊天输入（修复bug：防止重复处理）
    if prompt := st.chat_input("Ask a follow-up question or search for a new topic..."):
        # 检查是否正在处理中
        if st.session_state.is_processing:
            st.warning("Processing previous request, please wait...")
        else:
            # 设置处理状态
            st.session_state.is_processing = True
            
            # 添加用户消息
            with st.chat_message("user", avatar="👤"):
                st.write(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            is_search = check_search_intent(prompt, st.session_state.current_market)
            
            if is_search:
                # 新搜索逻辑
                st.session_state.show_market_selection = False
                st.session_state.current_market = None
                st.session_state.messages = []
                st.session_state.user_news_text = prompt  # 更新用户新闻
                
                with st.chat_message("assistant", avatar="🕵️‍♂️"):
                    st.write(f"🔍 Searching for new markets related to: **{prompt}**")
                    
                    with st.spinner("Scanning Polymarket..."):
                        matches, keyword = search_with_exa_optimized(prompt)
                    
                    if matches:
                        st.session_state.search_results = matches
                        st.session_state.last_search_query = keyword
                        st.session_state.show_market_selection = True
                        st.success(f"Found {len(matches)} markets. Please select one to analyze.")
                    else:
                        st.warning("No markets found. Switching to direct analysis mode...")
                        analyze_directly(prompt)
                
                # 重置处理状态
                st.session_state.is_processing = False
                st.rerun()
                
            else:
                # 追问逻辑
                with st.chat_message("assistant", avatar="🕵️‍♂️"):
                    with st.spinner("Analyzing follow-up..."):
                        response = stream_chat_response(
                            st.session_state.messages, 
                            st.session_state.current_market,
                            prompt,
                            direct_analysis=st.session_state.direct_analysis_mode
                        )
                        st.write(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
            
            # 重置处理状态
            st.session_state.is_processing = False
            st.rerun()

# ================= 📉 7. BOTTOM SECTION: TOP 12 MARKETS =================

st.markdown("---")
top10_markets = fetch_top_10_markets()

if top10_markets:
    cards_html = "".join([f"""
    <a href="https://polymarket.com/event/{m['slug']}" target="_blank" class="market-item">
        <div class="m-title" title="{m['title']}">{m['title']}</div>
        <div class="m-odds">
            <span class="tag-yes">Yes {m['yes']}¢</span>
            <span class="tag-no">No {m['no']}¢</span>
        </div>
    </a>""" for m in top10_markets])

    final_html = f"""
    <div class="top10-container">
        <div class="top10-header">Trending on Polymarket (Top 12)</div>
        <div class="top10-grid">{cards_html}</div>
    </div>
    """
    
    st.markdown(final_html, unsafe_allow_html=True)
else:
    st.markdown("""
    <div style="text-align:center; margin-top:50px; color:#666;">
        Connecting to Prediction Markets...
    </div>
    """, unsafe_allow_html=True)

# ================= 👇 8. 底部协议与说明 =================
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("""
<style>
    div.row-widget.stRadio > div { justify-content: center; }
    .protocol-container {
        font-family: 'Inter', sans-serif;
        color: #cbd5e1; font-size: 0.95rem; line-height: 1.8;
        margin-top: 20px; text-align: center; display: flex; flex-direction: column; align-items: center;
    }
    .protocol-step {
        margin-bottom: 25px; padding: 15px 20px; border-radius: 12px;
        background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.05);
        max-width: 700px; width: 100%; transition: all 0.3s;
    }
    .protocol-step:hover { background: rgba(255, 255, 255, 0.05); border-color: rgba(255, 255, 255, 0.1); }
    .protocol-title {
        font-weight: 700; color: #ef4444; font-size: 1rem; letter-spacing: 0.5px;
        text-transform: uppercase; display: block; margin-bottom: 8px;
    }
    .credits-section {
        text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #334155;
        color: #64748b; font-size: 0.85rem; font-family: monospace;
    }
    .credits-highlight { color: #94a3b8; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

with st.expander("Dual-Mode Analysis System"):
    lang_mode = st.radio("Language", ["EN", "CN"], horizontal=True, label_visibility="collapsed")
    st.markdown("<br>", unsafe_allow_html=True)
    if lang_mode == "EN":
        st.markdown("""
        <div class="protocol-container">
            <div class="protocol-step">
                <span class="protocol-title">1. Market-Based Analysis (Red Mode)</span>
                For traders and investors: Analyze news through the lens of specific prediction markets. Provides targeted trading insights, position sizing recommendations, and market inefficiency identification.
            </div>
            <div class="protocol-step">
                <span class="protocol-title">2. Direct News Analysis (Blue Mode)</span>
                For strategists and decision-makers: Pure news analysis without market constraints. Focuses on geopolitical implications, economic consequences, risk assessment, and strategic recommendations.
            </div>
            <div class="protocol-step">
                <span class="protocol-title">3. Intelligent Routing</span>
                System automatically switches to Direct Analysis when no relevant markets are found, ensuring all news receives professional analysis regardless of market availability.
            </div>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="protocol-container">
            <div class="protocol-step">
                <span class="protocol-title">1. 市场驱动分析 (红色模式)</span>
                针对交易员和投资者：通过特定预测市场分析新闻。提供针对性交易洞察、头寸规模建议和市场无效性识别。
            </div>
            <div class="protocol-step">
                <span class="protocol-title">2. 直接新闻分析 (蓝色模式)</span>
                针对战略家和决策者：无市场约束的纯粹新闻分析。专注于地缘政治影响、经济后果、风险评估和战略建议。
            </div>
            <div class="protocol-step">
                <span class="protocol-title">3. 智能路由系统</span>
                当未找到相关市场时，系统自动切换到直接分析模式，确保所有新闻都能获得专业分析，无论市场可用性如何。
            </div>
        </div>""", unsafe_allow_html=True)
    st.markdown("""
    <div class="credits-section">
        DUAL-MODE ANALYSIS SYSTEM<br>
        <span class="credits-highlight">Market Intelligence (Red)</span> & <span class="credits-highlight">Strategic Intelligence (Blue)</span><br><br>
        Powered by Gemini • Exa.ai • Polymarket API
    </div>""", unsafe_allow_html=True)

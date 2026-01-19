import streamlit as st
import google.generativeai as genai
import time

# 尝试导入搜索库，如果用户没装，不仅不报错，还自动降级为“知识库模式”
try:
    from duckduckgo_search import DDGS
    SEARCH_AVAILABLE = True
except ImportError:
    SEARCH_AVAILABLE = False

# ================= 🕵️‍♂️ 1. 系统配置 =================
st.set_page_config(
    page_title="Be Holmes | Market Detective",
    page_icon="🕵️‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= 🎨 2. UI 设计 (明亮商务风 + 品牌红) =================
st.markdown("""
<style>
    /* 全局背景设为干净的灰白色 */
    .stApp {
        background-color: #F8F9FA;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
    
    /* 隐藏顶部红条和页脚 */
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 标题样式：品牌红 */
    h1 {
        color: #D62828;
        font-weight: 800;
        letter-spacing: -1px;
    }
    
    /* 侧边栏样式 */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E9ECEF;
    }
    
    /* 输入框优化 */
    .stTextInput input {
        background-color: #FFFFFF;
        border: 1px solid #CED4DA;
        color: #495057;
        border-radius: 8px;
    }
    .stTextInput input:focus {
        border-color: #D62828;
        box-shadow: 0 0 0 2px rgba(214, 40, 40, 0.2);
    }
    
    /* 核心按钮：渐变红 */
    .stButton button {
        background: linear-gradient(135deg, #D62828 0%, #C1121F 100%);
        color: white;
        border: none;
        padding: 0.6rem 1rem;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(214, 40, 40, 0.2);
    }
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(214, 40, 40, 0.3);
        color: white;
    }
    
    /* 报告卡片风格 */
    .report-card {
        background-color: white;
        padding: 25px;
        border-radius: 12px;
        border-left: 5px solid #D62828;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        margin-top: 20px;
        color: #333;
    }
    
    /* 标签页样式 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px;
        color: #495057;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: rgba(214, 40, 40, 0.1);
        color: #D62828;
    }
</style>
""", unsafe_allow_html=True)

# ================= 🌐 3. 多语言字典 =================
LANG = {
    "CN": {
        "title": "Be Holmes",
        "subtitle": "海外发行情报侦探 | 竞品分析 & 舆情洞察",
        "sidebar_title": "侦探工具箱",
        "api_label": "Gemini API 密钥",
        "api_help": "必填，用于驱动 AI 大脑分析情报。",
        "input_label_1": "目标产品 / 竞品名称",
        "input_placeholder_1": "例如：原神 (Genshin Impact)",
        "input_label_2": "目标市场 / 国家",
        "input_placeholder_2": "例如：巴西 (Brazil)",
        "btn_start": "🔍 开始全网侦查",
        "btn_manual": "📘 使用手册",
        "status_searching": "正在全网搜集情报...",
        "status_analyzing": "Be Holmes 正在分析市场舆情...",
        "error_no_key": "❌ 请先在左侧输入 Gemini API Key",
        "error_no_input": "⚠️ 请输入完整的产品名和目标市场",
        "manual_title": "📘 使用手册",
        "manual_content": """
        ### 🕵️‍♂️ Be Holmes 是什么？
        这是一个专为**海外发行 PM** 打造的 AI 智能体。它模拟了一位资深市场分析师，能在 30 秒内帮你摸清竞品在海外的底细。
        
        ### 🚀 核心功能
        1. **舆情侦查：** 自动搜索 Reddit、Twitter、App Store 上的真实用户评价。
        2. **痛点挖掘：** 找出竞品在当地被吐槽最惨的地方（也就是你的机会）。
        3. **本地化分析：** 判断产品是否符合当地文化习俗。
        
        ### 🛠️ 如何使用
        1. 在左侧填入 API Key。
        2. 输入你想调研的**竞品**（如：Mobile Legends）。
        3. 输入**目标国家**（如：Indonesia）。
        4. 点击侦查，获取一份专业的全英文/全中文分析报告。
        """,
        "report_title": "📝 侦探档案：",
        "install_hint": "💡 提示：检测到未安装 duckduckgo-search，将使用 AI 知识库模式。建议 pip install duckduckgo-search 以开启联网能力。"
    },
    "EN": {
        "title": "Be Holmes",
        "subtitle": "Global Market Detective | Competitor Intelligence Agent",
        "sidebar_title": "Detective Toolkit",
        "api_label": "Gemini API Key",
        "api_help": "Required to power the AI reasoning engine.",
        "input_label_1": "Product / Competitor Name",
        "input_placeholder_1": "e.g. Genshin Impact",
        "input_label_2": "Target Market / Country",
        "input_placeholder_2": "e.g. Brazil",
        "btn_start": "🔍 Start Investigation",
        "btn_manual": "📘 User Manual",
        "status_searching": "Scouring the web for intelligence...",
        "status_analyzing": "Be Holmes is analyzing market sentiment...",
        "error_no_key": "❌ Please enter Gemini API Key in sidebar",
        "error_no_input": "⚠️ Please provide both Product Name and Market",
        "manual_title": "📘 User Manual",
        "manual_content": """
        ### 🕵️‍♂️ What is Be Holmes?
        An AI agent designed for **Overseas Publishing PMs**. It acts as a senior analyst, uncovering competitor insights in 30 seconds.
        
        ### 🚀 Core Features
        1. **Sentiment Recon:** Scans Reddit, Social Media, and Reviews.
        2. **Pain Point Detection:** Finds what local users hate about your competitor (your opportunity).
        3. **Localization Check:** Analyzes cultural fit and adaptation needs.
        
        ### 🛠️ How to Use
        1. Enter API Key on the left.
        2. Input **Competitor Name** (e.g., PUBG Mobile).
        3. Input **Target Country** (e.g., India).
        4. Click Investigate to get a professional strategy report.
        """,
        "report_title": "📝 Case File:",
        "install_hint": "💡 Note: Web search module missing. Running in Knowledge Mode. Run 'pip install duckduckgo-search' for live data."
    }
}

# ================= 🧠 4. 核心逻辑引擎 =================

def search_web_intelligence(product, market, lang_code):
    """
    搜索引擎：利用 DuckDuckGo 抓取实时网页快照
    """
    if not SEARCH_AVAILABLE:
        return None # 返回空，触发 AI 知识库模式
    
    results = []
    # 构造侦探搜索词 (Search Queries)
    queries = [
        f"{product} {market} user reviews reddit",
        f"{product} {market} biggest complaints problems",
        f"{product} {market} marketing strategy analysis",
        f"{product} {market} local cultural adaptation"
    ]
    
    try:
        with DDGS() as ddgs:
            for q in queries:
                # 每个词抓取 2 条最相关的结果
                r = list(ddgs.text(q, max_results=2))
                if r:
                    for item in r:
                        results.append(f"- Source: {item['title']}\n  Snippet: {item['body']}")
                time.sleep(0.5) # 防止请求过快
    except Exception as e:
        print(f"Search Error: {e}")
        return None
        
    return "\n".join(results)

def generate_agent_report(product, market, search_data, api_key, lang_mode):
    """
    AI 大脑：基于搜索结果生成专业报告
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # 根据用户选择的语言设定输出语言
        output_lang = "Chinese (Professional Business Tone)" if lang_mode == "CN" else "English (Professional Business Tone)"
        
        context_prompt = ""
        if search_data:
            context_prompt = f"Here is the collected LIVE WEB INTELLIGENCE:\n{search_data}\n"
        else:
            context_prompt = "Note: Live search is unavailable. Use your internal knowledge base to analyze this product deeply."

        prompt = f"""
        Role: You are **Be Holmes**, a Senior Strategy Consultant for Tencent Games/Apps Overseas Publishing.
        
        Task: Analyze the competitor **'{product}'** in the **'{market}'** market.
        
        {context_prompt}
        
        **Objective:**
        Produce a strategic "Competitor Analysis Report" in **{output_lang}**.
        
        **Report Structure (Strictly follow this Markdown format):**
        
        ## 🕵️‍♂️ Executive Summary (一句话核心结论)
        [Summarize the product's status in this market in 2 sentences.]
        
        ---
        
        ### 1. 📉 User Pain Points (致命弱点 - 我们的机会)
        * [Point 1]: [Detail based on Reddit/Review sentiment]
        * [Point 2]: [Detail]
        * [Point 3]: [Detail]
        
        ### 2. ❤️ Why They Succeed (竞品优势)
        * [Analysis of their localization or marketing strength]
        
        ### 3. 🗺️ Cultural & Localization Insights (本地化洞察)
        * [Cultural Fit Analysis]
        * [Payment/Device/Network constraints in {market}]
        
        ### 4. 💡 Strategic Advice for Us (给发行团队的建议)
        > [Actionable advice for a PM entering this market. Be specific.]
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ Analysis Failed: {str(e)}"

# ================= 🖥️ 5. 主界面布局 =================

# --- 侧边栏 ---
with st.sidebar:
    # 语言切换器 (放在最显眼的位置)
    lang_choice = st.radio("Language / 语言", ["CN", "EN"], horizontal=True)
    L = LANG[lang_choice] # 加载对应语言包
    
    st.markdown(f"## {L['sidebar_title']}")
    
    # API Key 输入
    with st.expander(f"🔑 {L['api_label']}", expanded=True):
        st.caption(L['api_help'])
        user_api_key = st.text_input("Gemini Key", type="password")
        if not SEARCH_AVAILABLE:
            st.warning(L['install_hint'])
    
    st.markdown("---")
    st.markdown("### 🌟 About")
    st.caption("Powered by Gemini 2.5 & DuckDuckGo")
    st.caption("Designed for Global Publishing PMs")

# --- 主舞台 ---
c1, c2 = st.columns([3, 1])
with c1:
    st.title(L['title'])
    st.markdown(f"**{L['subtitle']}**")

with c2:
    # 手册按钮
    if st.button(L['btn_manual']):
        @st.dialog(L['manual_title'])
        def show_manual():
            st.markdown(L['manual_content'])
        show_manual()

st.markdown("---")

# 输入表单区域
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        product_name = st.text_input(L['input_label_1'], placeholder=L['input_placeholder_1'])
    with col2:
        target_market = st.text_input(L['input_label_2'], placeholder=L['input_placeholder_2'])

    # 大号开始按钮
    start_btn = st.button(L['btn_start'], use_container_width=True)

# 逻辑处理
if start_btn:
    if not user_api_key:
        st.error(L['error_no_key'])
    elif not product_name or not target_market:
        st.warning(L['error_no_input'])
    else:
        # 1. 状态：搜索中
        with st.status(L['status_searching'], expanded=True) as status:
            st.write(f"🌐 Scouring the web for: {product_name} + {target_market}...")
            
            # 搜索步骤
            search_results = search_web_intelligence(product_name, target_market, lang_choice)
            
            if search_results:
                st.success("✅ Intelligence Acquired from Web.")
            else:
                if not SEARCH_AVAILABLE:
                    st.info("⚡ Using AI Internal Knowledge (Fast Mode).")
                else:
                    st.warning("⚠️ Web search timed out, relying on AI memory.")
            
            # 2. 状态：分析中
            st.write("🧠 Holmes is connecting the dots...")
            report = generate_agent_report(product_name, target_market, search_results, user_api_key, lang_choice)
            
            status.update(label="✅ Investigation Complete", state="complete", expanded=False)

        # 3. 结果展示
        st.markdown(f"### {L['report_title']} {product_name} @ {target_market}")
        st.markdown(f"""<div class="report-card">{report}</div>""", unsafe_allow_html=True)

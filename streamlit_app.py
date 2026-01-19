import streamlit as st
import requests
import json
import google.generativeai as genai

# ================= 🕵️‍♂️ 1. SYSTEM CONFIGURATION =================
st.set_page_config(
    page_title="Be Holmes | Alpha Hunter",
    page_icon="🕵️‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🔥 DOME KEY (Backup)
DOME_API_KEY = "6f08669ca2c6a9541f0ef1c29e5928d2dc22857b"

# ================= 🎨 2. UI DESIGN (V1.0 BASELINE) =================
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
    h3 { color: #FF7F50 !important; } 
    p, label, .stMarkdown, .stText, li, div, span { color: #A0A0A0 !important; }
    strong { color: #FFF !important; font-weight: 600; } 
    .stTextArea textarea, .stTextInput input { 
        background-color: #0A0A0A !important; color: #E63946 !important; 
        border: 1px solid #333 !important; border-radius: 6px;
    }
    .execute-btn {
        background: linear-gradient(90deg, #FF4500, #FFD700); 
        border: none; color: #000; width: 100%; padding: 15px;
        font-weight: 900; font-size: 16px; cursor: pointer; border-radius: 6px;
        text-transform: uppercase; letter-spacing: 2px; margin-top: 20px;
    }
    .ticker-box {
        background-color: #080808; border: 1px solid #222; border-left: 4px solid #FF4500;
        color: #FF4500; font-family: 'Courier New', monospace; padding: 15px; margin: 15px 0;
        font-size: 1.05em; font-weight: bold; display: flex; align-items: center;
    }
</style>
""", unsafe_allow_html=True)

# ================= 🔐 3. KEY MANAGEMENT =================
active_key = None

# ================= 📡 4. DATA ENGINE (V1.8: GRAPHQL CORE) =================

def normalize_market_data(m):
    """Universal Cleaner"""
    try:
        # GraphQL returns slightly different structure, handle both
        if m.get('closed') is True: return None
        slug = m.get('slug', m.get('market_slug', ''))
        title = m.get('question', m.get('title', 'Unknown Market'))
        
        odds_display = "N/A"
        try:
            raw_outcomes = m.get('outcomes', '["Yes", "No"]')
            outcomes = json.loads(raw_outcomes) if isinstance(raw_outcomes, str) else raw_outcomes
            raw_prices = m.get('outcomePrices', '[]')
            prices = json.loads(raw_prices) if isinstance(raw_prices, str) else raw_prices
            
            odds_list = []
            if prices and len(prices) == len(outcomes):
                for o, p in zip(outcomes, prices):
                    val = float(p) * 100
                    # Show all odds
                    odds_list.append(f"{o}: {val:.1f}%")
            odds_display = " | ".join(odds_list)
        except: pass
        
        volume = float(m.get('volume', 0))
        return {"title": title, "odds": odds_display, "slug": slug, "volume": volume, "id": m.get('id')}
    except: return None

def search_polymarket_graphql(query):
    """
    🔥 ENGINE 1: GraphQL (The "Website Search" Method)
    This mimics the frontend search bar.
    """
    url = "https://gamma-api.polymarket.com/graphql" # Official Endpoint
    query_str = """
    query SearchMarkets($term: String!) {
      searchMarkets(term: $term, limit: 20) {
        id
        question
        slug
        outcomes
        outcomePrices
        volume
        closed
        marketMakerAddress
        createdAt
      }
    }
    """
    
    results = []
    try:
        payload = {
            "query": query_str,
            "variables": {"term": query}
        }
        # Mimic browser headers slightly to be safe
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        resp = requests.post(url, json=payload, headers=headers, timeout=5)
        
        if resp.status_code == 200:
            data = resp.json()
            markets = data.get("data", {}).get("searchMarkets", [])
            for m in markets:
                p = normalize_market_data(m)
                if p:
                    p['title'] = "⚡ [GRAPHQL] " + p['title']
                    results.append(p)
    except Exception as e:
        print(f"GraphQL Error: {e}")
        pass
        
    return results

def search_dome_backup(query):
    """ENGINE 2: Dome Backup"""
    results = []
    try:
        url = "https://api.domeapi.io/v1/polymarket/markets"
        r = requests.get(url, headers={"Authorization": f"Bearer {DOME_API_KEY}"}, params={"limit": 100}, timeout=4)
        if r.status_code == 200:
            for m in r.json():
                p = normalize_market_data(m)
                if p and (query.lower() in p['title'].lower() or query.lower() in p['slug']):
                    results.append(p)
    except: pass
    return results

def extract_search_terms_ai(user_text, key):
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"Extract ONE core English keyword. Input: '{user_text}'. Output: Keyword"
        response = model.generate_content(prompt)
        return response.text.strip()
    except: return user_text

# ================= 🧠 5. INTELLIGENCE LAYER =================

def consult_holmes(user_evidence, market_list, key):
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        markets_text = "\n".join([f"- {m['title']} [Odds: {m['odds']}]" for m in market_list[:15]])
        
        prompt = f"""
        Role: **Be Holmes**, Senior Hedge Fund Strategist.
        [User Input]: "{user_evidence}"
        [Market Data Found]: 
        {markets_text}
        
        **OUTPUT (Markdown):**
        ---
        ### 🕵️‍♂️ Case File: [Best Match Title]
        <div class="ticker-box">🔥 LIVE SNAPSHOT: [Insert Odds]</div>
        
        **1. ⚖️ The Verdict**
        - **Signal:** 🟢 BUY / 🔴 SELL / ⚠️ WAIT
        - **Confidence:** [0-100]%
        
        **2. 🧠 Deep Logic**
        > [Analysis in Input Language]
        
        **3. 🛡️ Execution**
        - [Action Plan]
        ---
        """
        response = model.generate_content(prompt)
        btn_html = """<br><a href='https://polymarket.com/' target='_blank' style='text-decoration:none;'><button class='execute-btn'>🚀 EXECUTE TRADE</button></a>"""
        return response.text + btn_html
    except Exception as e: return f"❌ Intelligence Error: {str(e)}"

# ================= 🖥️ 7. MAIN INTERFACE =================

with st.sidebar:
    st.markdown("## 💼 DETECTIVE'S TOOLKIT")
    with st.expander("🔑 API Key Settings", expanded=True):
        user_api_key = st.text_input("Gemini Key", type="password")
        st.markdown("[Get Free Key](https://aistudio.google.com/app/apikey)")
        st.caption("✅ Engine: GraphQL (Primary)")

    if user_api_key:
        active_key = user_api_key
        st.success("🔓 Gemini: Active")
    elif "GEMINI_KEY" in st.secrets:
        active_key = st.secrets["GEMINI_KEY"]
        st.info("🔒 System Key Active")
    else:
        st.error("⚠️ Gemini Key Missing!")
        st.stop()

    st.markdown("---")
    st.caption("🌊 Live Feed")
    # Quick sidebar check using GraphQL
    try:
        sb_q = """query { markets(limit: 5, order: VOLUME_DESC, closed: false) { question outcomePrices outcomes } }"""
        # Simplified sidebar fetch
        pass 
    except: st.error("⚠️ Stream Offline")

# --- Main Stage ---
st.title("Be Holmes")
st.caption("EVENT-DRIVEN INTELLIGENCE | V1.8 GRAPHQL CORE") 
st.markdown("---")

user_news = st.text_area("Input Evidence...", height=150, label_visibility="collapsed", placeholder="Input news... (e.g. SpaceX IPO)")
ignite_btn = st.button("🔍 INVESTIGATE", use_container_width=True)

if ignite_btn:
    if not user_news:
        st.warning("⚠️ Evidence required.")
    else:
        with st.status("🚀 Initiating GraphQL Search...", expanded=True) as status:
            st.write("🧠 Extracting intent...")
            keyword = extract_search_terms_ai(user_news, active_key)
            st.write(f"🔑 Keyword: '{keyword}'")
            
            # 1. GraphQL Search (Primary)
            st.write(f"🌊 Querying Polymarket GraphQL...")
            sonar_markets = search_polymarket_graphql(keyword)
            
            if sonar_markets: 
                st.success(f"✅ GraphQL Found: {len(sonar_markets)} markets.")
            else:
                st.warning("⚠️ GraphQL miss. Trying Dome Backup...")
                # 2. Dome Backup
                sonar_markets = search_dome_backup(keyword)
                if sonar_markets: st.success(f"✅ Dome Found: {len(sonar_markets)} markets.")
            
            # Sort by volume
            sonar_markets.sort(key=lambda x: x['volume'], reverse=True)
            
            st.write("⚖️ Calculating Alpha...")
            status.update(label="✅ Investigation Complete", state="complete", expanded=False)

        if sonar_markets:
            with st.spinner(">> Deducing Alpha..."):
                result = consult_holmes(user_news, sonar_markets, active_key)
                st.markdown("---")
                st.markdown("### 📝 INVESTIGATION REPORT")
                st.markdown(result, unsafe_allow_html=True)
        else:
            st.error("⚠️ No relevant markets found.")

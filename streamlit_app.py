import streamlit as st
import requests
import json
import google.generativeai as genai
import re
import time

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

# ================= 📡 4. DATA ENGINE (DEEPSEEK ENHANCED) =================

def normalize_market_data(m):
    """DeepSeek's Robust Normalizer"""
    try:
        # Check closed status
        if m.get('closed') is True or m.get('status') == 'closed':
            return None
        
        # Robust Title Fetch
        title = m.get('question') or m.get('title') or m.get('market_title') or 'Unknown Market'
        slug = m.get('market_slug') or m.get('slug') or ''
        
        # Robust Volume Fetch
        volume = float(m.get('volume') or m.get('liquidity') or m.get('total_volume') or 0)
        
        # Robust Odds Parsing
        odds_display = "N/A"
        try:
            if 'outcomePrices' in m and m['outcomePrices']:
                prices = m['outcomePrices']
                outcomes = m.get('outcomes', ['Yes', 'No'])
                if isinstance(prices, str): prices = json.loads(prices)
                if isinstance(outcomes, str): outcomes = json.loads(outcomes)
                
                odds_list = []
                for i, (o, p) in enumerate(zip(outcomes, prices)):
                    val = float(p) * 100
                    odds_list.append(f"{o}: {val:.1f}%")
                odds_display = " | ".join(odds_list)
            elif 'prices' in m and m['prices']:
                prices = m['prices']
                odds_list = []
                for i, p in enumerate(prices):
                    val = float(p) * 100
                    label = 'Yes' if i == 0 else 'No'
                    odds_list.append(f"{label}: {val:.1f}%")
                odds_display = " | ".join(odds_list)
        except: 
            odds_display = "Odds parsing failed"
        
        return {
            "title": title, "odds": odds_display, "slug": slug, "volume": volume, "id": m.get('id') or m.get('market_id')
        }
    except Exception as e: return None

def extract_search_terms_ai(user_text, key):
    """DeepSeek's Strict Keyword Extractor"""
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""
        Extract the SINGLE most important English keyword.
        Remove quotes/punctuation. Only output the keyword.
        User input: '{user_text}'
        Examples: "SpaceX IPO" -> SpaceX, "Trump Win" -> Trump
        Keyword:
        """
        response = model.generate_content(prompt)
        keyword = response.text.strip().strip('"').strip("'")
        
        # Regex fallback
        if not keyword or len(keyword) > 50:
            matches = re.findall(r'[A-Z][a-zA-Z0-9]+', user_text)
            keyword = matches[0] if matches else user_text.split()[0]
        return [keyword]
    except:
        matches = re.findall(r'[A-Za-z][A-Za-z0-9]+', user_text)
        return [matches[0]] if matches else [user_text]

def search_polymarket_native(keywords):
    """🔥 V1.9 DeepSeek Logic: Multi-Endpoint + Local Filtering"""
    results = []
    seen = set()
    
    st.info(f"🔍 Searching for Keywords: {keywords}")
    
    # 1. Multi-Endpoint Search
    endpoints = [
        ("https://gamma-api.polymarket.com/markets", "markets"),
        ("https://gamma-api.polymarket.com/events", "events")
    ]
    
    for url, endpoint_type in endpoints:
        for kw in keywords:
            if len(kw) < 2: continue
            
            # Smart Params
            params = {"q": kw, "limit": 50, "closed": "false", "sort": "volume"}
            if "events" in endpoint_type: params = {"q": kw, "limit": 20}
            
            try:
                resp = requests.get(url, params=params, headers={"User-Agent": "BeHolmes/1.0"}, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    # Handle Events structure vs Markets structure
                    items = []
                    if endpoint_type == "events":
                        for ev in data: items.extend(ev.get('markets', []))
                    else:
                        items = data

                    for item in items:
                        p = normalize_market_data(item)
                        if p and p['slug'] not in seen:
                            # Fuzzy Match Title
                            if kw.lower() in p['title'].lower():
                                p['title'] = f"🌐 [{endpoint_type.upper()}] " + p['title']
                                results.append(p)
                                seen.add(p['slug'])
            except: pass

    # 2. BRUTE FORCE FALLBACK (The "DeepSeek Fix")
    # If API search failed, fetch TOP 200 markets and filter locally via Python
    if not results:
        st.warning("⚠️ Direct API match failed. Initiating Deep Scan (Local Filter)...")
        try:
            url = "https://gamma-api.polymarket.com/markets"
            params = {"limit": 200, "closed": "false", "sort": "volume"} # Fetch top 200
            resp = requests.get(url, params=params, timeout=10)
            
            if resp.status_code == 200:
                all_markets = resp.json()
                for m in all_markets:
                    p = normalize_market_data(m)
                    if p and p['slug'] not in seen:
                        # Check if keyword exists ANYWHERE in title or slug
                        full_text = f"{p['title']} {p['slug']}".lower()
                        for kw in keywords:
                            if kw.lower() in full_text:
                                p['title'] = "🔥 [DEEP SCAN] " + p['title']
                                results.append(p)
                                seen.add(p['slug'])
                                break
        except Exception as e: st.write(f"Deep scan error: {e}")

    # 3. Dome Backup (Last Resort)
    if not results and DOME_API_KEY:
        try:
            url = "https://api.domeapi.io/v1/polymarket/markets"
            r = requests.get(url, headers={"Authorization": f"Bearer {DOME_API_KEY}"}, params={"limit": 100}, timeout=4)
            if r.status_code == 200:
                for m in r.json():
                    p = normalize_market_data(m)
                    if p and p['slug'] not in seen:
                        for kw in keywords:
                            if kw.lower() in p['title'].lower():
                                results.append(p)
                                seen.add(p['slug'])
        except: pass

    results.sort(key=lambda x: x['volume'], reverse=True)
    return results

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
        st.caption("✅ Engine: DeepSeek Enhanced")

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
    st.caption("🌊 Live Feed (Top 5)")
    try:
        r = requests.get("https://gamma-api.polymarket.com/markets?limit=5&closed=false&sort=volume").json()
        for m in r:
            p = normalize_market_data(m)
            if p:
                st.caption(f"📅 {p['title']}")
                st.code(f"{p['odds']}")
    except: st.error("⚠️ Stream Offline")

# --- Main Stage ---
st.title("Be Holmes")
st.caption("EVENT-DRIVEN INTELLIGENCE | V1.9 DEEPSEEK CORE") 
st.markdown("---")

user_news = st.text_area("Input Evidence...", height=150, label_visibility="collapsed", placeholder="Input news... (e.g. SpaceX IPO)")
ignite_btn = st.button("🔍 INVESTIGATE", use_container_width=True)

if ignite_btn:
    if not user_news:
        st.warning("⚠️ Evidence required.")
    else:
        with st.status("🚀 Initiating Deep Scan...", expanded=True) as status:
            st.write("🧠 Optimizing keywords...")
            keywords = extract_search_terms_ai(user_news, active_key)
            
            st.write(f"🌊 Searching global database for: {keywords}...")
            sonar_markets = search_polymarket_native(keywords)
            
            if sonar_markets: 
                st.success(f"✅ FOUND: {len(sonar_markets)} markets.")
                for m in sonar_markets[:3]:
                    st.write(f"-> {m['title']}")
            else:
                st.error("⚠️ No relevant markets found.")
            
            st.write("⚖️ Calculating Alpha...")
            status.update(label="✅ Investigation Complete", state="complete", expanded=False)

        if sonar_markets:
            with st.spinner(">> Deducing Alpha..."):
                result = consult_holmes(user_news, sonar_markets, active_key)
                st.markdown("---")
                st.markdown("### 📝 INVESTIGATION REPORT")
                st.markdown(result, unsafe_allow_html=True)

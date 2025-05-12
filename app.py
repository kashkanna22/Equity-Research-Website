import streamlit as st
import yfinance as yf
import requests
import os
import re
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- Load API Keys ---
groq_api_key = os.getenv("GROQ_API_KEY")
alpha_vantage_key = "EYK7GNAZP045LRQT"
finnhub_key = "d0fte1pr01qr6dbu77mgd0fte1pr01qr6dbu77n0"

# --- App Layout ---
st.set_page_config(page_title="Equity Research AI", layout="centered")
st.title("📈 AI-Powered Equity Ressearch Assistant")
st.markdown("""
Welcome to your personalized equity research tool.  
Enter a **sector**, **company name**, or **ticker** to get started.
""")

# --- Custom CSS for Styling ---
st.markdown("""
<style>
    .main {
        max-width: 1000px;
    }
    .stExpander {
        border: 1px solid rgba(49, 51, 63, 0.2);
        border-radius: 8px;
        padding: 0.5rem;
        margin-bottom: 1rem;
    }
    .stExpander > summary {
        font-weight: 600;
        font-size: 1.1rem;
    }
    .metric-card {
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .strong-buy {
        background-color: #d4edda;
        color: #155724;
        padding: 0.5rem;
        border-radius: 4px;
        font-weight: bold;
    }
    .buy {
        background-color: #cce5ff;
        color: #004085;
        padding: 0.5rem;
        border-radius: 4px;
        font-weight: bold;
    }
    .hold {
        background-color: #fff3cd;
        color: #856404;
        padding: 0.5rem;
        border-radius: 4px;
        font-weight: bold;
    }
    .sell {
        background-color: #f8d7da;
        color: #721c24;
        padding: 0.5rem;
        border-radius: 4px;
        font-weight: bold;
    }
    .warning-box {
        border-left: 4px solid #ffc107;
        padding: 0.5rem 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# --- Format Numbers with No Rounding ---
def format_number(n):
    try:
        if abs(n) >= 1_000_000_000:
            return f"${n/1_000_000_000:.2f}B"
        elif abs(n) >= 1_000_000:
            return f"${n/1_000_000:.2f}M"
        elif abs(n) >= 1_000:
            return f"${n/1_000:.1f}K"
        return f"${n:,.2f}"
    except:
        return "N/A"

# --- Financial Term Definitions ---
definitions = {
    "Company Name": "The full legal name of the company being analyzed.",
    "Market Cap": "Market capitalization is the total value of a company's outstanding shares. It indicates company size.",
    "P/E Ratio": "The price-to-earnings ratio compares a company's stock price to its earnings per share (EPS).",
    "Revenue (TTM)": "Total revenue generated over the past 12 months from business operations.",
    "Net Income (TTM)": "The total profit after all expenses, taxes, and costs over the trailing twelve months.",
    "Sector": "The broad category of the economy in which the company operates.",
    "Industry": "A more specific classification than sector, representing the particular line of business.",
    "Competitive Advantage": "The unique strengths that allow a company to outperform its rivals.",
    "Management Quality": "Assessment of the executive team's competence and track record.",
    "Growth Prospects": "Potential for future expansion and revenue increase.",
    "Industry Trends": "The prevailing developments affecting this industry.",
    "Risks": "Factors that could negatively impact the company's performance."
}

# --- Get Price History ---
def get_price_history(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        return hist
    except:
        return None

# --- Create Dual-Panel Chart ---
def create_price_volume_chart(ticker):
    hist = get_price_history(ticker)
    if hist is None or hist.empty:
        return None
    
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                       vertical_spacing=0.05, row_heights=[0.7, 0.3])
    
    # Price chart
    fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], 
                         name='Price', line=dict(color='#1f77b4'))),
    # Volume chart
    fig.add_trace(go.Bar(x=hist.index, y=hist['Volume'], 
                      name='Volume', marker_color='#7f7f7f'),
               row=2, col=1)
    
    fig.update_layout(
        height=500,
        showlegend=False,
        margin=dict(l=20, r=20, t=30, b=20),
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(gridcolor='rgba(0,0,0,0.05)'),
        yaxis=dict(gridcolor='rgba(0,0,0,0.05)'),
        xaxis2=dict(gridcolor='rgba(0,0,0,0.05)'),
        yaxis2=dict(gridcolor='rgba(0,0,0,0.05)')
    )
    
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    
    return fig

# --- Ticker Resolution ---
def resolve_ticker(user_input):
    # First try direct match
    try:
        stock = yf.Ticker(user_input.upper())
        info = stock.info
        if 'longName' in info:
            return [{"symbol": user_input.upper(), "name": info['longName']}]
    except:
        pass
    
    # Fallback to search
    try:
        url = f"https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords={user_input}&apikey={alpha_vantage_key}"
        r = requests.get(url)
        data = r.json()
        if "bestMatches" in data:
            return [{"symbol": match["1. symbol"], "name": match["2. name"]} for match in data["bestMatches"]]
    except:
        pass
    
    # Final fallback to Groq AI
    try:
        prompt = f"""
        Identify the stock ticker symbol(s) for: '{user_input}'. 
        Return as JSON array with objects containing 'symbol' and 'name'.
        Example: [{{"symbol": "AAPL", "name": "Apple Inc."}}]
        """
        headers = {"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "llama3-70b-8192",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0
        }
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        matches = json.loads(re.search(r'\[.*\]', content, re.DOTALL)[0])
        return matches
    except:
        return []

# --- Dual-Source Financial Summary ---
def get_summary(ticker):
    # Primary: yfinance
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        if 'longName' in info and info.get("marketCap"):
            current_price = info.get('currentPrice', info.get('regularMarketPrice', 'N/A'))
            return {
                "Company Name": info.get("longName", "N/A"),
                "Current Price": current_price,
                "Market Cap": info.get("marketCap", "N/A"),
                "P/E Ratio": info.get("trailingPE", "N/A"),
                "Revenue (TTM)": info.get("totalRevenue", "N/A"),
                "Net Income (TTM)": info.get("netIncomeToCommon", "N/A"),
                "Industry": info.get("industry", "N/A"),
                "Sector": info.get("sector", "N/A")
            }
    except:
        pass

    # Fallback: Alpha Vantage
    try:
        url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={alpha_vantage_key}"
        r = requests.get(url)
        data = r.json()

        if "Name" in data:
            return {
                "Company Name": data.get("Name", "N/A"),
                "Current Price": data.get("50DayMovingAverage", "N/A"),  # Fallback if no current price
                "Market Cap": int(data.get("MarketCapitalization", 0)) if data.get("MarketCapitalization") else "N/A",
                "P/E Ratio": float(data.get("PERatio", 0)) if data.get("PERatio") else "N/A",
                "Revenue (TTM)": int(data.get("RevenueTTM", 0)) if data.get("RevenueTTM") else "N/A",
                "Net Income (TTM)": int(data.get("NetIncomeTTM", 0)) if data.get("NetIncomeTTM") else "N/A",
                "Industry": data.get("Industry", "N/A"),
                "Sector": data.get("Sector", "N/A")
            }
    except:
        pass

    # Fallback: Finnhub
    try:
        profile_url = f"https://finnhub.io/api/v1/stock/profile2?symbol={ticker}&token={finnhub_key}"
        metric_url = f"https://finnhub.io/api/v1/stock/metric?symbol={ticker}&metric=all&token={finnhub_key}"
        profile = requests.get(profile_url).json()
        metric = requests.get(metric_url).json().get("metric", {})
        if profile.get("name"):
            return {
                "Company Name": profile.get("name", "N/A"),
                "Current Price": metric.get("52WeekHigh", "N/A"),  # Fallback
                "Market Cap": int(metric.get("marketCapitalization", 0) * 1e6),
                "P/E Ratio": float(metric.get("peNormalizedAnnual", 0)),
                "Revenue (TTM)": int(metric.get("revenuePerShareAnnual", 0) * profile.get("shareOutstanding", 0)),
                "Net Income (TTM)": int(metric.get("netIncomePerShareAnnual", 0) * profile.get("shareOutstanding", 0)),
                "Industry": profile.get("finnhubIndustry", "N/A"),
                "Sector": "N/A"
            }
    except:
        pass

    # Fallback: Groq AI
    try:
        prompt = f"""
        Provide the following financial data for the company '{ticker}' as JSON:
        - Company Name
        - Current Price
        - Market Cap
        - P/E Ratio
        - Revenue (TTM)
        - Net Income (TTM)
        - Industry
        - Sector

        Use real-world information up to your latest knowledge.
        Output in strict JSON format with keys matching exactly:
        'Company Name', 'Current Price', 'Market Cap', 'P/E Ratio', 'Revenue (TTM)', 'Net Income (TTM)', 'Industry', 'Sector'
        """
        headers = {"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "llama3-70b-8192",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0
        }
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        json_data = json.loads(re.search(r'{.*}', content, re.DOTALL)[0])
        return json_data
    except:
        return {"error": "All data sources failed to retrieve information."}

# --- Get Qualitative Information ---
def get_qualitative_info(summary_data):
    try:
        prompt = f"""
        Provide qualitative analysis for {summary_data.get("Company Name", "the company")} ({summary_data.get("Industry", "unknown industry")}) in JSON format with these exact keys:
        - Competitive Advantage: Identify 2-3 key advantages
        - Management Quality: Assess leadership experience and track record
        - Growth Prospects: Highlight 1-2 major growth opportunities
        - Industry Trends: Describe 2-3 key trends affecting this industry
        - Risks: List 2-3 major risks facing the company
        
        Each value should be a concise paragraph (2-3 sentences). Focus on factual, actionable insights.
        Example format:
        {{
            "Competitive Advantage": "The company benefits from...",
            "Management Quality": "The leadership team has...",
            "Growth Prospects": "Key growth opportunities include...",
            "Industry Trends": "The industry is experiencing...",
            "Risks": "Major risks include..."
        }}
        """
        headers = {"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "llama3-70b-8192",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0
        }
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        return json.loads(re.search(r'{.*}', content, re.DOTALL)[0])
    except:
        return {
            "Competitive Advantage": "Information not available",
            "Management Quality": "Information not available",
            "Growth Prospects": "Information not available",
            "Industry Trends": "Information not available",
            "Risks": "Information not available"
        }

# --- AI Insight for Each Metric ---
def generate_explanation(label, value, summary_data):
    if label == "Company Name":
        prompt = f"Give a short history and origin of the company '{value}', including how it got its name and what it's known for."
    else:
        prompt = f"""
        You are an AI financial analyst. Explain what the metric '{label}' with value '{value}' tells us about {summary_data.get("Company Name")}.
        Do not define the term. Instead, evaluate the meaning in context of the company's financial state.
        Be concise (2-3 sentences max).
        """

    headers = {"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "llama3-70b-8192",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0
    }

    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except:
        return "AI explanation not available."

# --- Enhanced Score Calculation ---
def calculate_score(data, qualitative_data):
    try:
        score = 0
        max_score = 100
        
        # Quantitative Factors (60%)
        pe = data.get("P/E Ratio")
        cap = data.get("Market Cap")
        ni = data.get("Net Income (TTM)")
        rev = data.get("Revenue (TTM)")
        
        # P/E Ratio (15%)
        if isinstance(pe, (int, float)):
            if pe < 15: score += 15  # Very attractive
            elif pe < 20: score += 12  # Attractive
            elif pe < 25: score += 9  # Fair
            elif pe < 30: score += 6  # Expensive
            else: score += 3  # Very expensive
        
        # Profitability (20%)
        if isinstance(ni, (int, float)) and ni > 0 and isinstance(rev, (int, float)) and rev > 0:
            margin = ni / rev
            if margin > 0.20: score += 20
            elif margin > 0.15: score += 16
            elif margin > 0.10: score += 12
            elif margin > 0.05: score += 8
            else: score += 4
        
        # Revenue Growth Potential (15%)
        if isinstance(rev, (int, float)):
            if rev > 50e9: 
                score += 9  # Mega-cap (stable but lower growth)
            elif rev > 10e9: 
                score += 12  # Large-cap (balanced growth)
            elif rev > 1e9: 
                score += 15  # Mid-cap (high growth potential)
            elif rev > 100e6: 
                score += 10  # Small-cap
            else: 
                score += 6  # Micro-cap
        
        # Market Cap (10%)
        if isinstance(cap, (int, float)):
            if cap > 200e9: score += 6  # Mega-cap
            elif cap > 10e9: score += 8  # Large-cap
            elif cap > 2e9: score += 10  # Mid-cap (sweet spot)
            elif cap > 300e6: score += 7  # Small-cap
            else: score += 5  # Micro-cap
        
        # Qualitative Factors (40%)
        qual_map = {
            "Competitive Advantage": 15,
            "Management Quality": 10,
            "Growth Prospects": 10,
            "Industry Trends": 5
        }
        
        for factor, weight in qual_map.items():
            text = qualitative_data.get(factor, "").lower()
            positive_words = ["strong", "experienced", "growing", "innovative", "leading", "skilled", "expanding", "advantage", "proven", "dominant"]
            negative_words = ["weak", "poor", "declining", "risky", "unproven", "limited", "challenging", "uncertain", "volatile", "fierce"]
            
            pos_count = sum(1 for word in positive_words if word in text)
            neg_count = sum(1 for word in negative_words if word in text)
            
            if pos_count > neg_count + 1: score += weight  # Strong positive
            elif pos_count > neg_count: score += weight * 0.75  # Mild positive
            elif pos_count == neg_count: score += weight * 0.5  # Neutral
            else: score += weight * 0.25  # Negative
        
        return min(round(score), 100)
    except Exception as e:
        return f"N/A ({str(e)})"

# --- AI Investment Decision ---
def generate_investment_call(summary_data, qualitative_data, score):
    if isinstance(score, int):
        if score >= 80:
            recommendation = "Strong Buy"
            reasoning = "exceptional fundamentals and strong qualitative factors"
            css_class = "strong-buy"
        elif score >= 70:
            recommendation = "Buy"
            reasoning = "strong fundamentals and positive qualitative factors"
            css_class = "buy"
        elif score >= 60:
            recommendation = "Moderate Buy"
            reasoning = "good fundamentals with some positive qualitative factors"
            css_class = "buy"
        elif score >= 50:
            recommendation = "Hold"
            reasoning = "balanced mix of strengths and weaknesses"
            css_class = "hold"
        elif score >= 40:
            recommendation = "Weak Hold"
            reasoning = "some concerning factors but not severe enough to sell"
            css_class = "hold"
        else:
            recommendation = "Sell"
            reasoning = "multiple concerning factors and weak fundamentals"
            css_class = "sell"
    else:
        return "AI investment guidance not available."

    pe = summary_data.get("P/E Ratio", "N/A")
    margin = "N/A"
    if isinstance(summary_data.get("Net Income (TTM)"), (int, float)) and isinstance(summary_data.get("Revenue (TTM)"), (int, float)):
        margin = f"{summary_data['Net Income (TTM)'] / summary_data['Revenue (TTM)'] * 100:.1f}%"
    
    return f"""
    <div class="{css_class}">
        <strong>Recommendation: {recommendation}</strong><br>
        <strong>Score: {score}/100</strong> - {reasoning}
    </div>
    
    <div class="metric-card">
        <strong>Key Quantitative Factors:</strong>
        <ul>
            <li>Valuation (P/E): {pe}</li>
            <li>Profit Margin: {margin}</li>
            <li>Market Cap: {format_number(summary_data.get('Market Cap', 'N/A'))}</li>
        </ul>
    </div>
    
    <div class="metric-card">
        <strong>Qualitative Highlights:</strong>
        <ul>
            <li>{qualitative_data.get('Competitive Advantage', 'N/A')}</li>
            <li>{qualitative_data.get('Growth Prospects', 'N/A')}</li>
        </ul>
    </div>
    
    <div class="warning-box">
        <strong>Risks Considered:</strong><br>
        {qualitative_data.get('Risks', 'N/A')}
    </div>
    """

# --- UI ---
user_input = st.text_input("🔍 Search for a company or sector")

if user_input.strip():
    # Resolve ticker/company name (only when input changes)
    if 'matches' not in st.session_state or st.session_state.last_input != user_input:
        st.session_state.matches = resolve_ticker(user_input)
        st.session_state.last_input = user_input
        st.session_state.show_options = True  # Reset toggle when new search
    
    matches = st.session_state.matches
    
    if not matches:
        st.error("No matching companies found. Please try a different search term.")
    else:
        # For multiple matches, show selection interface
        if len(matches) > 1:
            # Toggle button to show/hide options (without rerun)
            st.session_state.show_options = st.toggle(
                "Show company selection options", 
                value=st.session_state.show_options,
                key="options_toggle"
            )
            
            if st.session_state.show_options:
                st.warning("Multiple matches found. Please select one:")
                selected = st.radio(
                    "Select company:", 
                    [f"{m['symbol']} - {m['name']}" for m in matches],
                    index=0,
                    key="company_selector"
                )
                st.session_state.selected_symbol = selected.split(" - ")[0]
            else:
                st.info(f"Selected: {st.session_state.selected_symbol}")
        else:
            st.session_state.selected_symbol = matches[0]["symbol"]
        
        # Generate Report button - only this triggers report generation
        if st.button("Generate Report"):
            # Clear previous report if it exists
            if 'current_report' in st.session_state:
                del st.session_state.current_report
            
        # Report generation (only when button clicked or symbol changes)
        if 'current_report' not in st.session_state and 'selected_symbol' in st.session_state:
            with st.spinner("Generating comprehensive report..."):
                symbol_to_use = st.session_state.selected_symbol
                summary = get_summary(symbol_to_use)
                
                if "error" not in summary:
                    qualitative_data = get_qualitative_info(summary)
                    st.session_state.current_report = {
                        'symbol': symbol_to_use,
                        'summary': summary,
                        'qualitative': qualitative_data,
                        'score': calculate_score(summary, qualitative_data),
                        'price_chart': create_price_volume_chart(symbol_to_use)
                    }
        
# Display report if available
if 'current_report' in st.session_state:
    report = st.session_state.current_report

    # Main Report Container using top-level expander
    with st.expander(f"📑 Full Research Report: {report['summary']['Company Name']} ({report['symbol']})", expanded=True):
        tab1, tab2, tab3 = st.tabs(["📊 Stock Overview", "🔍 Detailed Analysis", "📈 Investment Recommendation"])

        # === Stock Overview Tab ===
        with tab1:
            col1, col2 = st.columns([1, 2])
            with col1:
                st.metric(label="Current Price", 
                          value=f"${report['summary'].get('Current Price', 'N/A')}", 
                          delta=f"P/E: {report['summary'].get('P/E Ratio', 'N/A')}")
                st.markdown("### Key Metrics")
                st.table({
                    "Metric": ["Market Cap", "Revenue (TTM)", "Net Income (TTM)", "Sector", "Industry"],
                    "Value": [
                        format_number(report['summary'].get("Market Cap", "N/A")),
                        format_number(report['summary'].get("Revenue (TTM)", "N/A")),
                        format_number(report['summary'].get("Net Income (TTM)", "N/A")),
                        report['summary'].get("Sector", "N/A"),
                        report['summary'].get("Industry", "N/A")
                    ]
                })
            with col2:
                if report['price_chart']:
                    st.plotly_chart(report['price_chart'], use_container_width=True)
                else:
                    st.warning("Price history data not available")

        # === Detailed Analysis Tab ===
        with tab2:
            st.markdown("### Financial Metrics Analysis")
            cols = st.columns(2)
            for i, (label, value) in enumerate(report['summary'].items()):
                if label in ["Market Cap", "P/E Ratio", "Revenue (TTM)", "Net Income (TTM)"]:
                    with cols[i % 2]:
                        st.markdown(f"**{label}:** {format_number(value) if isinstance(value, (int, float)) else value}")
                        st.markdown(f"**Definition:** {definitions.get(label, 'Not available')}")
                        st.markdown(f"**Analysis:** {generate_explanation(label, value, report['summary'])}")
            
            st.markdown("### Qualitative Factors")
            for label, value in report['qualitative'].items():
                if label != "Risks":
                    st.markdown(f"**{label}**")
                    st.markdown(value)
                    st.markdown(f"*About this factor:* {definitions.get(label, 'Not available')}")

            st.markdown("### Risk Assessment")
            st.warning(f"**Key Risks:** {report['qualitative'].get('Risks', 'Not available')}")

        # === Investment Recommendation Tab ===
        with tab3:
            score = report['score']
            if isinstance(score, int):
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.markdown("### Overall Score")
                    if score >= 80:
                        st.markdown(f'<div style="text-align: center; font-size: 1.5rem;">{score}/100</div>', unsafe_allow_html=True)
                        st.success("Strong Buy")
                    elif score >= 70:
                        st.markdown(f'<div style="text-align: center; font-size: 1.5rem;">{score}/100</div>', unsafe_allow_html=True)
                        st.info("Buy")
                    elif score >= 50:
                        st.markdown(f'<div style="text-align: center; font-size: 1.5rem;">{score}/100</div>', unsafe_allow_html=True)
                        st.warning("Hold")
                    else:
                        st.markdown(f'<div style="text-align: center; font-size: 1.5rem;">{score}/100</div>', unsafe_allow_html=True)
                        st.error("Sell")

                    st.progress(score / 100)

                    if st.toggle("Scoring Methodology"):
                        st.markdown("""
                        **Scoring Formula (100 points total):**

                        **Quantitative Factors (60%):**
                        - P/E Ratio (15%): Lower is better
                        - Profitability (20%): Net income margin
                        - Revenue Size (15%): Growth potential
                        - Market Cap (10%): Company size

                        **Qualitative Factors (40%):**
                        - Competitive Advantage (15%)
                        - Management Quality (10%)
                        - Growth Prospects (10%)
                        - Industry Trends (5%)
                        """)
                with col2:
                    st.markdown("### AI Recommendation")
                    st.markdown(generate_investment_call(
                        report['summary'],
                        report['qualitative'],
                        report['score']
                    ), unsafe_allow_html=True)
            else:
                st.write(f"Score: {score}")

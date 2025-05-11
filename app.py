import streamlit as st
import yfinance as yf
import requests
import os
import re
import json

# --- Load API Keys ---
groq_api_key = os.getenv("GROQ_API_KEY")
alpha_vantage_key = "EYK7GNAZP045LRQT"
finnhub_key = "d0fte1pr01qr6dbu77mgd0fte1pr01qr6dbu77n0"

# --- App Layout ---
st.set_page_config(page_title="Equity Research AI", layout="centered")
st.title("📈 AI-Powered Equity Research Assistant")
st.markdown("""
Welcome to your personalized equity research tool.  
Enter a **sector**, **company name**, or **ticker** to get started.
""")

# --- Format Numbers with No Rounding ---
def format_number(n):
    try:
        return f"{float(n):,}"
    except:
        return "N/A"

# --- Financial Term Definitions ---
definitions = {
    "Company Name": "The full legal name of the company being analyzed.",
    "Market Cap": "Market capitalization is the total value of a company's outstanding shares. It indicates company size.",
    "P/E Ratio": "The price-to-earnings ratio compares a company's stock price to its earnings per share (EPS).",
    "Revenue (TTM)": "Total revenue generated over the past 12 months from business operations.",
    "Net Income (TTM)": "The total profit after all expenses, taxes, and costs over the trailing twelve months.",
    "Industry": "The primary business sector in which the company operates.",
    "Competitive Advantage": "Unique strengths that give the company an edge over competitors.",
    "Management Quality": "Assessment of the executive team's competence and track record.",
    "Growth Prospects": "Potential for future expansion and revenue increase."
}

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
            "temperature": 0.3
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
            return {
                "Company Name": info.get("longName", "N/A"),
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
                "Market Cap": int(metric.get("marketCapitalization", 0) * 1e6),
                "P/E Ratio": float(metric.get("peNormalizedAnnual", 0)),
                "Revenue (TTM)": int(metric.get("revenuePerShareAnnual", 0) * profile.get("shareOutstanding", 0)),
                "Net Income (TTM)": int(metric.get("netIncomePerShareAnnual", 0) * profile.get("shareOutstanding", 0)),
                "Industry": profile.get("finnhubIndustry", "N/A"),
                "Sector": "N/A"
            }
    except:
        pass

    # Final Fallback: Groq AI
    try:
        prompt = f"""
        Provide the following financial data for the company '{ticker}' as JSON:
        - Company Name
        - Market Cap
        - P/E Ratio
        - Revenue (TTM)
        - Net Income (TTM)
        - Industry
        - Sector

        Use real-world information up to your latest knowledge.
        Output in strict JSON format with keys matching exactly:
        'Company Name', 'Market Cap', 'P/E Ratio', 'Revenue (TTM)', 'Net Income (TTM)', 'Industry', 'Sector'
        """
        headers = {"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "llama3-70b-8192",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3
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
        Provide qualitative analysis for {summary_data.get("Company Name", "the company")} in JSON format with these exact keys:
        - Competitive Advantage
        - Management Quality
        - Growth Prospects
        - Industry Trends
        - Risks
        
        Be concise but insightful (1-2 sentences per metric). Focus on factual information.
        """
        headers = {"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "llama3-70b-8192",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.5
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
        "temperature": 0.5
    }

    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except:
        return "AI explanation not available."

# --- AI Investment Decision ---
def generate_investment_call(summary_data, qualitative_data, score):
    prompt = f"""
    You're an AI investment advisor. Based on the following data for {summary_data.get("Company Name")}, decide whether it's a good time to invest.

    Quantitative Metrics:
    - Valuation (P/E ratio): {summary_data.get("P/E Ratio", "N/A")}
    - Company size (market cap): {format_number(summary_data.get("Market Cap", "N/A"))}
    - Profitability (revenue + net income): {format_number(summary_data.get("Revenue (TTM)", "N/A"))} revenue, {format_number(summary_data.get("Net Income (TTM)", "N/A"))} net income
    
    Qualitative Factors:
    - Competitive Advantage: {qualitative_data.get("Competitive Advantage", "N/A")}
    - Management Quality: {qualitative_data.get("Management Quality", "N/A")}
    - Growth Prospects: {qualitative_data.get("Growth Prospects", "N/A")}
    - Industry Trends: {qualitative_data.get("Industry Trends", "N/A")}
    - Risks: {qualitative_data.get("Risks", "N/A")}

    Our scoring system rated this company: {score}/100

    Provide a specific recommendation (Buy/Hold/Sell) and explain why in 3-4 sentences.
    Consider both quantitative and qualitative factors in your analysis.
    """

    headers = {"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "llama3-70b-8192",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.5
    }

    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except:
        return "AI investment guidance not available."

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
            if pe < 10: score += 15
            elif pe < 15: score += 12
            elif pe < 20: score += 9
            elif pe < 25: score += 6
            elif pe < 30: score += 3
        else: score += 5
        
        # Profitability (20%)
        if isinstance(ni, (int, float)) and ni > 0 and isinstance(rev, (int, float)) and rev > 0:
            margin = ni / rev
            if margin > 0.15: score += 20
            elif margin > 0.10: score += 16
            elif margin > 0.05: score += 12
            elif margin > 0: score += 8
        else: score += 4
        
        # Revenue Growth Potential (15%)
        if isinstance(rev, (int, float)):
            if rev > 50e9: score += 15  # Mega-cap stability
            elif rev > 10e9: score += 12  # Large-cap growth
            elif rev > 1e9: score += 9   # Mid-cap potential
            elif rev > 100e6: score += 6 # Small-cap
            else: score += 3             # Micro-cap
        else: score += 5
        
        # Market Cap (10%)
        if isinstance(cap, (int, float)):
            if cap > 200e9: score += 10  # Mega-cap
            elif cap > 10e9: score += 8  # Large-cap
            elif cap > 2e9: score += 6   # Mid-cap
            elif cap > 300e6: score += 4 # Small-cap
            else: score += 2             # Micro-cap
        else: score += 3
        
        # Qualitative Factors (40%)
        qual_map = {
            "Competitive Advantage": 15,
            "Management Quality": 10,
            "Growth Prospects": 10,
            "Industry Trends": 5
        }
        
        for factor, weight in qual_map.items():
            text = qualitative_data.get(factor, "").lower()
            positive_words = ["strong", "experienced", "growing", "innovative", "leading", "skilled", "expanding"]
            negative_words = ["weak", "poor", "declining", "risky", "unproven", "limited"]
            
            pos_count = sum(1 for word in positive_words if word in text)
            neg_count = sum(1 for word in negative_words if word in text)
            
            if pos_count > neg_count: score += weight * 0.75
            elif pos_count == neg_count: score += weight * 0.5
            else: score += weight * 0.25
        
        return min(round(score), 100)
    except Exception as e:
        return f"N/A ({str(e)})"

# --- UI ---
user_input = st.text_input("🔍 Search for a company or sector")

if st.button("Generate Report"):
    if not user_input.strip():
        st.warning("Please enter a valid input.")
    else:
        # Resolve ticker/company name
        matches = resolve_ticker(user_input)
        
        if not matches:
            st.error("No matching companies found. Please try a different search term.")
        elif len(matches) > 1:
            st.warning("Multiple matches found. Please select one:")
            selected = st.radio("Select company:", 
                               [f"{m['symbol']} - {m['name']}" for m in matches],
                               index=0)
            selected_symbol = selected.split(" - ")[0]
        else:
            selected_symbol = matches[0]["symbol"]
        
        if len(matches) == 1 or ('selected_symbol' in locals() and selected_symbol):
            symbol_to_use = selected_symbol if 'selected_symbol' in locals() else matches[0]["symbol"]
            
            st.success(f"Generating report for: **{symbol_to_use}**")
            summary = get_summary(symbol_to_use)

            if "error" in summary:
                st.error(f"Error fetching data: {summary['error']}")
            else:
                # Get qualitative data
                qualitative_data = get_qualitative_info(summary)
                
                # Display Financial Overview
                st.subheader("📊 Financial Overview")
                for label, value in summary.items():
                    if label in ["Company Name", "Market Cap", "P/E Ratio", "Revenue (TTM)", "Net Income (TTM)", "Industry", "Sector"]:
                        formatted = format_number(value) if isinstance(value, (int, float)) else value
                        st.write(f"**{label}:** {formatted}")

                        with st.expander(f"ℹ️ What does '{label}' mean?"):
                            st.markdown(definitions.get(label, "Definition not available."))

                        with st.expander("🧠 What does this signify?"):
                            insight = generate_explanation(label, value, summary)
                            st.markdown(insight)
                
                # Display Qualitative Analysis
                st.subheader("🔍 Qualitative Analysis")
                for label, value in qualitative_data.items():
                    if label != "Risks":  # We'll show risks separately
                        st.write(f"**{label}:** {value}")
                        
                        with st.expander(f"ℹ️ About {label}"):
                            st.markdown(definitions.get(label, "Analysis not available."))
                
                # Show Risks in a warning box
                st.warning(f"⚠️ **Key Risks:** {qualitative_data.get('Risks', 'Not available')}")
                
                # Calculate and display score
                st.subheader("📈 Investment Score")
                score = calculate_score(summary, qualitative_data)
                
                if isinstance(score, int):
                    if score >= 80:
                        st.success(f"✅ **{score}/100** — Strong Buy")
                        st.progress(score/100)
                    elif score >= 65:
                        st.info(f"🔼 **{score}/100** — Buy")
                        st.progress(score/100)
                    elif score >= 50:
                        st.warning(f"🔄 **{score}/100** — Hold")
                        st.progress(score/100)
                    else:
                        st.error(f"🔻 **{score}/100** — Sell")
                        st.progress(score/100)
                else:
                    st.write(f"Score: {score}")
                
                with st.expander("📊 How is this score calculated?"):
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
                    
                    Each qualitative factor is scored based on positive/negative language analysis.
                    """)
                
                with st.expander("💬 AI Investment Recommendation"):
                    decision = generate_investment_call(summary, qualitative_data, score)
                    st.markdown(decision)
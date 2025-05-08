# --- Import Files ---
import streamlit as st
import yfinance as yf
import requests
import os

# --- Load API Key from .env ---
api_key = os.getenv("GROQ_API_KEY")

# --- Home Screen Visuals ---
st.set_page_config(page_title="Equity Research AI", layout="centered")
st.title("📈 AI-Powered Equity Research Assistant")

st.markdown("""
Welcome to your personalized equity research tool.  
Enter a **sector**, **company name**, or **ticker** to get started.
""")

# --- Function to Get Financial Summary ---
def get_summary(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        summary_data = {
            "Company Name": info.get("longName", "N/A"),
            "Market Cap": info.get("marketCap", "N/A"),
            "P/E Ratio": info.get("trailingPE", "N/A"),
            "Revenue (TTM)": info.get("totalRevenue", "N/A"),
            "Net Income (TTM)": info.get("netIncomeToCommon", "N/A")
        }
        return summary_data
    except Exception as e:
        return {"error": str(e)}

# --- Groq API Call Using LLaMA 3 ---
def generate_ai_summary(summary_data):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    prompt = f"""
    You're a financial analyst. Provide a short, professional investment summary for the following company based on its fundamentals:

    - Company Name: {summary_data.get("Company Name")}
    - Market Cap: {summary_data.get("Market Cap")}
    - P/E Ratio: {summary_data.get("P/E Ratio")}
    - Revenue (TTM): {summary_data.get("Revenue (TTM)")}
    - Net Income (TTM): {summary_data.get("Net Income (TTM)")}

    Explain if the stock appears undervalued, risky, or stable based on this data.
    """

    payload = {
        "model": "llama3-70b-8192",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        raw_text = result["choices"][0]["message"]["content"]
        clean_text = raw_text.replace("*", "").replace("_", "").replace("`", "").strip()
        return clean_text
    except Exception as e:
        try:
            return f"Error generating AI summary: {response.status_code} - {response.json()}"
        except:
            return f"Error generating AI summary: {e}"

# --- UI ---
user_input = st.text_input("🔍 Search for a company or sector")

if st.button("Generate Report"):
    if user_input.strip() == "":
        st.warning("Please enter a valid input.")
    else:
        st.success(f"Generating report for: **{user_input.upper()}**")

        summary = get_summary(user_input.upper())

        if "error" in summary:
            st.error(f"Error fetching data: {summary['error']}")
        else:
            st.subheader("📊 Company Financial Summary")
            for k, v in summary.items():
                st.write(f"**{k}:** {v}")

            st.subheader("🧠 AI-Generated Investment Summary")
            ai_summary = generate_ai_summary(summary)
            st.write(ai_summary)

import os
import feedparser
import yfinance as yf
import google.generativeai as genai
import requests
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in .env")

genai.configure(api_key=GOOGLE_API_KEY)

def fetch_rss_news():
    """Fetches top 5 headlines from Yahoo Finance RSS."""
    print("Fetching news...")
    url = "https://finance.yahoo.com/news/rssindex"
    feed = feedparser.parse(url)
    headlines = []
    for entry in feed.entries[:5]:
        headlines.append(entry.title)
    return headlines

def fetch_market_prices():
    """Fetches current prices for SPY, QQQ, GLD."""
    print("Fetching market prices...")
    tickers = ["SPY", "QQQ", "GLD"]
    data = yf.Tickers(" ".join(tickers))
    prices = {}
    for ticker in tickers:
        try:
            # Try to get regular market price, fallback to pre/post market if available
            info = data.tickers[ticker].info
            price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
            prices[ticker] = price
        except Exception as e:
            print(f"Error fetching {ticker}: {e}")
            prices[ticker] = "N/A"
    return prices

def analyze_market(news, prices):
    """Generates market analysis using Gemini."""
    print("Analyzing market with Gemini...")
    
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    prompt = f"""
    You are a Derivatives Trader. Analyze the following market data and news.
    
    **Market Prices:**
    {prices}
    
    **Top News Headlines:**
    {news}
    
    **Crucial Instruction:**
    Analyze this like a Derivatives Trader. Do not just summarize. Tell me:
    
    1. **The Narrative**: What is the one dominant story driving the market right now? (e.g., "Inflation fear," "AI capex boom").
    2. **The Volatility Trigger**: Is there a specific event today (like a Fed speech or Nvidia earnings) that could cause a >1% move?
    3. **Sentiment Score**: Rate the market sentiment from 0 (Extreme Fear) to 100 (Extreme Greed) based on this news.
    
    Format the output clearly for a Telegram message. Keep it concise but impactful.
    """
    
    response = model.generate_content(prompt)
    return response.text

def send_telegram_report(report):
    """Sends the report to Telegram."""
    print("Sending report to Telegram...")
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": report
    }
    response = requests.post(url, json=payload)
    if response.status_code != 200:
        print(f"Failed to send message: {response.text}")
    else:
        print("Report sent successfully!")

if __name__ == "__main__":
    try:
        news = fetch_rss_news()
        prices = fetch_market_prices()
        analysis = analyze_market(news, prices)
        send_telegram_report(analysis)
    except Exception as e:
        print(f"An error occurred: {e}")

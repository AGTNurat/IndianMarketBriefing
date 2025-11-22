import os
import pandas as pd
import yfinance as yf
import feedparser
import google.generativeai as genai
import requests
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in .env")

genai.configure(api_key=GOOGLE_API_KEY)

def load_portfolio(file_path="india_portfolio.csv"):
    """Reads portfolio CSV and formats symbols for yfinance."""
    try:
        df = pd.read_csv(file_path)
        # Append .NS to symbols if not already present
        df['Symbol'] = df['Symbol'].apply(lambda x: f"{x}.NS" if not str(x).endswith('.NS') else x)
        return df
    except Exception as e:
        print(f"Error loading portfolio: {e}")
        return None

def fetch_market_data(df):
    """Fetches current prices for portfolio and indices."""
    print("Fetching market data...")
    
    # Portfolio symbols
    symbols = df['Symbol'].tolist()
    
    # Indices
    indices = ["^NSEI", "^BSESN"]
    all_tickers = symbols + indices
    
    # Fetch data
    # Using period="5d" to ensure we get previous close even if today is a holiday/weekend
    data = yf.download(all_tickers, period="5d", progress=False)
    
    # Extract latest close/current price
    # yfinance download returns a MultiIndex DataFrame if multiple tickers
    # We need 'Close' column. 
    # Note: 'Close' might contain NaNs for today if market is open but data not yet available? 
    # Actually yfinance usually provides 'Close' as latest price during market hours.
    
    prices = {}
    changes = {}
    
    # Get the last two rows to calculate change
    # If market is open, the last row is current price, second last is previous close.
    # If market is closed, last row is close.
    
    # We'll try to get the latest valid price for each ticker
    close_data = data['Close']
    
    current_prices = {}
    percent_changes = {}
    
    for ticker in all_tickers:
        try:
            ticker_series = close_data[ticker].dropna()
            if len(ticker_series) >= 2:
                current_price = ticker_series.iloc[-1]
                prev_close = ticker_series.iloc[-2]
                change = ((current_price - prev_close) / prev_close) * 100
                
                current_prices[ticker] = current_price
                percent_changes[ticker] = change
            elif len(ticker_series) == 1:
                current_prices[ticker] = ticker_series.iloc[-1]
                percent_changes[ticker] = 0.0 # Can't calc change
            else:
                current_prices[ticker] = 0.0
                percent_changes[ticker] = 0.0
        except Exception as e:
            print(f"Error processing {ticker}: {e}")
            current_prices[ticker] = 0.0
            percent_changes[ticker] = 0.0
            
    return current_prices, percent_changes

def calculate_performance(df, current_prices, percent_changes):
    """Calculates P&L and identifies top movers."""
    
    df['CurrentPrice'] = df['Symbol'].map(current_prices)
    df['ChangePct'] = df['Symbol'].map(percent_changes)
    
    # Calculate Daily P&L
    # Daily P&L = (Current Price - Previous Close) * Quantity
    # We can approximate Daily P&L using ChangePct: CurrentValue * (ChangePct / (100 + ChangePct)) ??
    # Simpler: Daily P&L = Current Value - (Current Value / (1 + ChangePct/100))
    
    df['CurrentValue'] = df['Quantity'] * df['CurrentPrice']
    df['DailyPnL'] = df['CurrentValue'] - (df['CurrentValue'] / (1 + df['ChangePct']/100))
    
    total_value = df['CurrentValue'].sum()
    total_daily_pnl = df['DailyPnL'].sum()
    
    # Top Movers
    top_gainers = df.nlargest(3, 'ChangePct')[['Symbol', 'ChangePct', 'CurrentPrice']]
    top_losers = df.nsmallest(3, 'ChangePct')[['Symbol', 'ChangePct', 'CurrentPrice']]
    
    return {
        'total_value': total_value,
        'total_daily_pnl': total_daily_pnl,
        'top_gainers': top_gainers,
        'top_losers': top_losers,
        'full_df': df
    }

def fetch_news(queries):
    """Fetches news for specific queries using Google News RSS."""
    print(f"Fetching news for: {queries}")
    news_items = {}
    
    for query in queries:
        # Clean symbol for search (remove .NS)
        search_term = query.replace('.NS', '')
        import urllib.parse
        encoded_term = urllib.parse.quote(f"{search_term} India Business")
        url = f"https://news.google.com/rss/search?q={encoded_term}&hl=en-IN&gl=IN&ceid=IN:en"
        feed = feedparser.parse(url)
        
        items = []
        for entry in feed.entries[:2]: # Top 2 news per topic
            items.append(f"- [{entry.title}]({entry.link})")
        
        if items:
            news_items[query] = "\n".join(items)
            
    return news_items

def generate_analysis(perf_data, index_data, news_data):
    """Generates India Market Pulse using Gemini."""
    print("Generating analysis with Gemini...")
    
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    # Format data for prompt
    portfolio_summary = f"""
    Total Portfolio Value: ₹{perf_data['total_value']:,.2f}
    Today's P&L: ₹{perf_data['total_daily_pnl']:,.2f}
    """
    
    movers_summary = "Top Gainers:\n" + perf_data['top_gainers'].to_string(index=False) + "\n\nTop Losers:\n" + perf_data['top_losers'].to_string(index=False)
    
    indices_summary = f"""
    NIFTY 50: {index_data['^NSEI']['price']:.2f} ({index_data['^NSEI']['change']:.2f}%)
    SENSEX: {index_data['^BSESN']['price']:.2f} ({index_data['^BSESN']['change']:.2f}%)
    """
    
    news_summary = ""
    for key, value in news_data.items():
        news_summary += f"\nNews for {key}:\n{value}\n"
        
    prompt = f"""
    You are a Quantitative Analyst specializing in the Indian Stock Market. 
    Generate a "🇮🇳 India Market Pulse" report based on the following data.
    
    **Market Overview:**
    {indices_summary}
    
    **My Portfolio Performance:**
    {portfolio_summary}
    
    **Top Movers:**
    {movers_summary}
    
    **Relevant News:**
    {news_summary}
    
    **Instructions:**
    1. **Market Sentiment**: Briefly summarize the general market mood based on NIFTY/SENSEX.
    2. **Portfolio Pulse**: Comment on the daily performance.
    3. **Why They Moved**: For the Top Movers (Gainers/Losers), use the provided news (and your own knowledge if news is sparse) to explain WHY they moved. Be specific (e.g., "Earnings beat," "Sector rotation," "Global cues").
    4. **Outlook**: A one-sentence outlook for tomorrow.
    
    Format for Telegram. Keep it concise.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating analysis: {e}"

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

import schedule
import datetime
import pytz

# ... (existing imports and setup)

def send_error_alert(error_message):
    """Sends an error alert to Telegram."""
    print(f"Sending error alert: {error_message}")
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": f"⚠️ Error fetching India Data: {error_message}"
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Failed to send error alert: {e}")

def run_briefing():
    """Main execution logic with guardrails."""
    print(f"Starting briefing job at {datetime.datetime.now()}")
    
    # 1. Market Open Guardrails
    # Check if today is Saturday (5) or Sunday (6)
    today = datetime.datetime.now().weekday()
    if today >= 5:
        print("Today is a weekend. Skipping briefing.")
        return

    try:
        # 2. Load Portfolio
        df = load_portfolio()
        if df is None:
            raise Exception("Failed to load portfolio CSV")
            
        # 3. Fetch Data
        current_prices, percent_changes = fetch_market_data(df)
        
        # 4. Calculate Performance
        perf = calculate_performance(df, current_prices, percent_changes)
        
        # 5. Prepare Index Data
        index_data = {
            "^NSEI": {"price": current_prices.get("^NSEI", 0), "change": percent_changes.get("^NSEI", 0)},
            "^BSESN": {"price": current_prices.get("^BSESN", 0), "change": percent_changes.get("^BSESN", 0)}
        }
        
        # 6. Fetch News for Indices + Top Movers
        movers = perf['top_gainers']['Symbol'].tolist() + perf['top_losers']['Symbol'].tolist()
        search_queries = ["NIFTY 50"] + movers
        search_queries = list(set(search_queries))
        
        news = fetch_news(search_queries)
        
        # 7. Generate Analysis
        report = generate_analysis(perf, index_data, news)
        
        # 8. Send Report
        send_telegram_report(report)
        
    except Exception as e:
        print(f"Error in run_briefing: {e}")
        send_error_alert(str(e))

def job():
    """Scheduler job wrapper."""
    run_briefing()

if __name__ == "__main__":
    # Check if running in GitHub Actions
    if os.getenv("GITHUB_ACTIONS") == "true":
        print("Running in GitHub Actions mode (Single Run)...")
        run_briefing()
        exit()

    print("India Market Briefing Scheduler Started...")
    
    # Define EST timezone
    est = pytz.timezone('US/Eastern')
    
    # Get current date in EST and set time to 06:00:00
    now_est = datetime.datetime.now(est)
    
    # We want to schedule for 06:00 EST. 
    # Let's calculate what 06:00 EST is in local system time.
    # Note: This calculation is valid for the current day. 
    # If DST changes tomorrow, this static time might be off by an hour until restarted.
    # But for a daily script, it's a reasonable approximation if restarted occasionally.
    
    # Create a naive datetime for 6 AM today
    target_est = now_est.replace(hour=6, minute=0, second=0, microsecond=0)
    
    # Convert to UTC then to local system time
    # Actually, we can just convert the aware EST datetime to local system timezone
    local_tz = datetime.datetime.now().astimezone().tzinfo
    target_local = target_est.astimezone(local_tz)
    
    # Format as HH:MM for schedule
    schedule_time = target_local.strftime("%H:%M")
    
    print(f"Scheduled for 06:00 AM EST (which is {schedule_time} Local Time).")
    
    # Schedule the job
    schedule.every().day.at(schedule_time).do(job)
    
    # Also run immediately if testing? No, let's stick to schedule.
    # But to verify it works NOW, I'll print a message.
    
    while True:
        schedule.run_pending()
        time.sleep(60)


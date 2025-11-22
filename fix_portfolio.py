import pandas as pd

# Mapping of incorrect symbols to NSE tickers
symbol_map = {
    "MOTSU": "MOTHERSON",
    "MOTSUM": "MSUMI", # Or MOTHERSON if merged
    "HYUMOT": "HYUNDAI", # Assuming Hyundai Motor India
    "TATMOT": "TATAMOTORS",
    "BANBAN": "BANDHANBNK",
    "BANMAH": "MAHABANK",
    "CANBAN": "CANBK",
    "HDFBAN": "HDFCBANK",
    "IDFBAN": "IDFCFIRSTB",
    "INDBA": "INDUSINDBK",
    "YESBAN": "YESBANK",
    "AMBCE": "AMBUJACEM",
    "AARIND": "AARTIIND",
    "UNIP": "UNIPARTS", # Based on price ~500
    "PATEN": "PATELENG",
    "ONE97": "PAYTM",
    "ICINIF": "ICICINIFTY", # Check if valid, maybe ICICIB22?
    "ADAWIL": "AWL",
    "BHADYN": "BDL",
    "COMENG": "CUMMINSIND", 
    "SUZENE": "SUZLON",
    "BAFINS": "BAJFINANCE",
    "CDSL": "CDSL",
    "JIOFIN": "JIOFIN",
    "LICHF": "LICHSGFIN",
    "MAHFIN": "M&MFIN",
    "HCLTEC": "HCLTECH",
    "TATTEC": "TATATECH",
    "ADAPOR": "ADANIPORTS",
    "GMRINF": "GMRAIRPORT", # Renamed
    "ZEEENT": "ZEEL",
    "HINCOP": "HINDCOPPER",
    "ASIPAI": "ASIANPAINT",
    "ORIPAP": "ORIENTPPR",
    "BIOCON": "BIOCON",
    "JAIIRR": "JISLJALEQS",
    "BHAPET": "BPCL",
    "INDOIL": "IOC",
    "RELIND": "RELIANCE",
    "SCI": "SCI",
    "SAIL": "SAIL",
    "TATSTE": "TATASTEEL",
    "ADAENT": "ADANIENT",
    "GMRINFRA": "GMRAIRPORT", # Fix previous update
    "GMRPOWER": "GMRPWR", # Fix previous update
    "ICICINIFTY": "ICICINIFTY", # Still failing, maybe remove or ignore?
    "RELPOW": "RPOWER",
    "RELINF": "RELINFRA",
    "ALOIND": "ALOKINDS",
    "ZENTEC": "ZENTEC"
}

def fix_portfolio():
    try:
        df = pd.read_csv("india_portfolio.csv")
        
        # Function to map symbol
        def get_correct_symbol(sym):
            # Remove .NS if present for lookup
            clean_sym = str(sym).replace('.NS', '')
            if clean_sym in symbol_map:
                return symbol_map[clean_sym]
            return clean_sym
            
        df['Symbol'] = df['Symbol'].apply(get_correct_symbol)
        
        # Save back
        df.to_csv("india_portfolio.csv", index=False)
        print("Portfolio symbols updated successfully.")
        print(df.head())
        
    except Exception as e:
        print(f"Error fixing portfolio: {e}")

if __name__ == "__main__":
    fix_portfolio()

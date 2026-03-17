import os
import json
import pandas as pd
import requests
import yfinance as yf
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Global cache for GPR dataset to avoid repeated downloads and processing
_GPR_CACHE = None

AV_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')
AV_BASE_URL = os.getenv('ALPHA_VANTAGE_BASE_URL')
FRED_API_KEY = os.getenv('FRED_API_KEY')
FRED_BASE_URL = os.getenv('FRED_BASE_URL')

def safe_float(value):
    try:
        if value is None or value == "N/A":
            return 0.0
        return float(value)
    except (ValueError, TypeError):
        return 0.0

def get_cb_demand(target_date):
    year = target_date.year
    quarter = (target_date.month - 1) // 3 + 1
    key = f"{year}-Q{quarter}"
    
    filename = 'knowledge_base/banks_demand_2021_2025.json'
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
            val = data.get(key, {}).get("tons_value", 0)
            return safe_float(val)
    except FileNotFoundError:
        print(f"Error: {filename} not found.")
        return 0.0

def fetch_fred_data(series_id, target_date):
    endpoint = f"{FRED_BASE_URL}series/observations"
    # FRED has a lag in reporting, so we look back 10 days to ensure we get the latest available data
    start_date = (target_date - timedelta(days=10)).strftime("%Y-%m-%d")
    end_date = target_date.strftime("%Y-%m-%d")
    
    params = {
        'series_id': series_id,
        'api_key': FRED_API_KEY,
        'file_type': 'json',
        'observation_start': start_date,
        'observation_end': end_date,
        'sort_order': 'desc',
        'limit': 1
    }
    try:
        res = requests.get(endpoint, params=params).json()
        observations = res.get('observations', [])
        if observations:
            return observations[0]['value']
    except Exception as e:
        print(f"FRED Error ({series_id}): {e}")
    return "N/A"

def fetch_gpr_data(target_date):
    global _GPR_CACHE
    url = "https://www.matteoiacoviello.com/gpr_files/data_gpr_daily_recent.dta"
    local_filename = "data_gpr_daily_recent.dta"
    
    try:
        # 1. Download and cache the dataset if not already loaded
        if _GPR_CACHE is None:
            if not os.path.exists(local_filename):
                response = requests.get(url, timeout=20)
                with open(local_filename, 'wb') as f:
                    f.write(response.content)
            
            # Read the Stata file into a DataFrame
            _GPR_CACHE = pd.read_stata(local_filename)
            # Normalize column names to lowercase for easier access
            _GPR_CACHE.columns = [c.lower() for c in _GPR_CACHE.columns]
            _GPR_CACHE['date'] = pd.to_datetime(_GPR_CACHE['date'])

        # 2. Index column identification
        # Verify possible column names for the GPR index and select the first one that exists
        col_name = None
        for candidate in ['gprd', 'gpr_daily', 'gpr']:
            if candidate in _GPR_CACHE.columns:
                col_name = candidate
                break
        
        if not col_name:
            print("Error GPR: GPR index column not found in dataset.")
            return 0.0

        # 3. Data matching
        target_dt = pd.to_datetime(target_date.strftime("%Y-%m-%d"))
        row = _GPR_CACHE[_GPR_CACHE['date'] == target_dt]
        
        if not row.empty:
            gpr_val = float(row[col_name].iloc[0])
            
            return round(gpr_val, 2)
        else:
            print(f"   [!] Data {target_date.strftime('%Y-%m-%d')} doesn't exist in the dataset.")
            return 0.0

    except Exception as e:
        print(f"   [Error GPR] {e}")
        return 0.0

def fetch_gold_knowledge_base(target_date):
    date_str = target_date.strftime("%Y-%m-%d")

    kb = {
        "analyzed_date": date_str,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "variables_fuzzy": {}
    }

    print(f"--- Collecting data for: {date_str} ---")

    # 1. Inflation CPI - Alpha Vantage
    try:
        res_cpi = requests.get(f"{AV_BASE_URL}?function=CPI&interval=monthly&apikey=demo").json()
        cpi_data = res_cpi.get('data', [])
        val_cpi = "."
        if cpi_data:
            # Search for the most recent CPI value that is on or before the target date
            for entry in cpi_data:
                if entry['date'] <= date_str:
                    val_cpi = entry['value']
                    if val_cpi != ".":
                        break
        kb["variables_fuzzy"]["inflation_cpi"] = safe_float(val_cpi)
    except Exception as e:
        print(f"CPI Error: {e}")
        kb["variables_fuzzy"]["inflation_cpi"] = 0.0

    # 2. FED FUNDS RATE - FRED API
    val_fed = fetch_fred_data('DFF', target_date)
    kb["variables_fuzzy"]["fed_funds_rate"] = safe_float(val_fed)

    # 3. DOLAR INDEX - Yahoo Finance
    try:
        dxy = yf.Ticker("DX-Y.NYB")
        h_start = (target_date - timedelta(days=7)).strftime("%Y-%m-%d")
        h_end = (target_date + timedelta(days=1)).strftime("%Y-%m-%d")
        hist = dxy.history(start=h_start, end=h_end)
        if not hist.empty:
            kb["variables_fuzzy"]["dolar_index"] = round(float(hist['Close'].iloc[-1]), 2)
        else:
            kb["variables_fuzzy"]["dolar_index"] = 0.0 # Or a default value indicating no data
    except Exception as e:
        print(f"Yahoo DXY Error: {e}")
        kb["variables_fuzzy"]["dolar_index"] = 0.0

    # 4. Macro-Geopolitical Sentiment - Alpha Vantage News Sentiment
    val_gpr = fetch_gpr_data(target_date)
    kb["variables_fuzzy"]["geopolitical_sentiment"] = safe_float(val_gpr)

    # 5. VIX INDEX - Yahoo Finance
    try:
        vix = yf.Ticker("^VIX")
        h_start = (target_date - timedelta(days=7)).strftime("%Y-%m-%d")
        h_end = (target_date + timedelta(days=1)).strftime("%Y-%m-%d")
        v_hist = vix.history(start=h_start, end=h_end)
        if not v_hist.empty:
            kb["variables_fuzzy"]["vix_index"] = round(float(v_hist['Close'].iloc[-1]), 2)
        else:
            kb["variables_fuzzy"]["vix_index"] = 15.0 # Or a default value indicating no data, 15 is a common average for VIX
    except Exception as e:
        kb["variables_fuzzy"]["vix_index"] = 15.0

    # 6. Banks Demand for Gold - Local JSON
    kb["variables_fuzzy"]["banks_demand"] = get_cb_demand(target_date)

    # Save the knowledge base to a JSON file
    filename = f"knowledge_base/kb_gold_{date_str.replace('-', '_')}.json"
    with open(filename, "w") as f:
        json.dump(kb, f, indent=4)
    print(f"Succes: File {filename} created.")

if __name__ == "__main__":
    today = datetime(2025, 10, 31)
    start_date = today - timedelta(days=30)

    for i in range(31): # 31 to include today
        current_day = start_date + timedelta(days=i)
        
        try:
            fetch_gold_knowledge_base(current_day)
        except Exception as e:
            print(f"   [Error] Could not generate data for {current_day.strftime('%Y-%m-%d')}: {e}")

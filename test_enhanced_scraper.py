
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))
from nse_scraper import init_nse_session, custom_fetch_option_chain, process_to_df
import json

def test_custom_fetch():
    print("Initializing NSE Session...")
    if init_nse_session():
        print("Session Initialized.")
        print("Fetching NIFTY Option Chain via custom fetch...")
        data = custom_fetch_option_chain("NIFTY")
        if data and "records" in data:
            print("Success: Data fetched.")
            df = process_to_df(data)
            if df is not None:
                print(f"Processed DataFrame size: {df.shape}")
                print(df.head())
            else:
                print("Failure: Process to DF failed.")
        else:
            print(f"Failure: Custom fetch returned invalid data: {type(data)}")
    else:
        print("Failure: Session initialization failed.")

if __name__ == "__main__":
    test_custom_fetch()

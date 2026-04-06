from spot_utils import get_nifty_spot_fresh
import json

def get_nifty_spot():
    try:
        print("Fetching NIFTY 50 Index Quote (Fresh)...")
        spot = get_nifty_spot_fresh()
        
        if spot:
            print(f"SPOT_RESULT: {spot}")
            print("Note: Success. This uses the robust spot_utils logic.")
        else:
            print("FAILED: Could not retrieve fresh spot price.")
            
    except Exception as e:
        print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    get_nifty_spot()

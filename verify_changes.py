import sys
import os

# Add project root to sys.path
sys.path.append(r"e:\Meero Python 2.0")

try:
    print("Testing imports...")
    import config
    print("Config imported.")
    from core.actions import Actions
    print("Actions imported.")
    from backend.app import analyze_sentiment
    print("Server functions imported.")
    
    print("\nTesting Config Values:")
    print(f"Schedule Keys: {list(config.SCHEDULE.keys())}")
    print(f"Social Media: {list(config.SOCIAL_MEDIA_URLS.keys())}")
    
    print("\nImports and Config verified successfully.")
    
except Exception as e:
    print(f"VERIFICATION FAILED: {e}")
    exit(1)

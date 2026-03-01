import sys
import traceback
sys.path.insert(0, 'backend')
try:
    from app.core.auth import APIKey, get_optional_api_key
    from app.core.rate_limit import rate_limit
    from app.core.security import FileValidator, InputSanitizer
    print("SUCCESS")
except Exception as e:
    traceback.print_exc()

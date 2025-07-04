#!/usr/bin/env python3
"""
Debug script to see exactly what get_credential_names returns
"""

import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def debug_credential_output():
    """Debug the exact output of get_credential_names"""
    
    print("🔍 Debugging get_credential_names output")
    print("=" * 60)
    
    # Get user_id from environment
    test_user_id = os.getenv("TEST_USER_ID")
    if not test_user_id:
        print("❌ TEST_USER_ID environment variable not set")
        return
    
    print(f"📋 Testing with user_id: {test_user_id}")
    
    # Import the function
    from mongodb_tool import get_credential_names
    
    # Test the function
    input_data = {
        "user_id": test_user_id
    }
    
    try:
        result = get_credential_names(input_data)
        
        print(f"🔍 RAW RESULT TYPE: {type(result)}")
        print(f"🔍 RAW RESULT KEYS: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
        
        # Print the raw result as JSON
        print(f"\n📄 RAW JSON OUTPUT:")
        print(json.dumps(result, indent=2, default=str))
        
        # Check specific fields
        if isinstance(result, dict):
            print(f"\n📊 FIELD ANALYSIS:")
            print(f"   - message: {result.get('message', 'MISSING')}")
            print(f"   - count: {result.get('count', 'MISSING')}")
            print(f"   - data_type: {result.get('data_type', 'MISSING')}")
            print(f"   - credentials field exists: {'credentials' in result}")
            print(f"   - credential_names field exists: {'credential_names' in result}")
            
            if 'credentials' in result:
                creds = result['credentials']
                print(f"   - credentials type: {type(creds)}")
                print(f"   - credentials length: {len(creds) if isinstance(creds, (list, dict)) else 'Not countable'}")
                
                if isinstance(creds, list) and len(creds) > 0:
                    print(f"   - first credential: {creds[0]}")
                    print(f"   - first credential keys: {list(creds[0].keys()) if isinstance(creds[0], dict) else 'Not a dict'}")
            
            if 'credential_names' in result:
                names = result['credential_names']
                print(f"   - credential_names type: {type(names)}")
                print(f"   - credential_names length: {len(names) if isinstance(names, (list, dict)) else 'Not countable'}")
                if isinstance(names, list):
                    print(f"   - first few names: {names[:3]}")
        
        # Test JSON serialization
        print(f"\n🧪 JSON SERIALIZATION TEST:")
        try:
            json_str = json.dumps(result, default=str)
            print(f"   ✅ JSON serialization successful ({len(json_str)} chars)")
        except Exception as e:
            print(f"   ❌ JSON serialization failed: {e}")
            
    except Exception as e:
        print(f"❌ Error testing function: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_credential_output()
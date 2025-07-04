#!/usr/bin/env python3
"""
Test script to verify get_credential_names function works
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_get_credential_names():
    """Test the get_credential_names function"""
    
    print("🧪 Testing get_credential_names function")
    print("=" * 50)
    
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
        
        print(f"📊 Result:")
        print(f"   Message: {result.get('message', 'No message')}")
        print(f"   Count: {result.get('count', 0)}")
        
        if result.get('error'):
            print(f"   ❌ Error: {result['error']}")
        else:
            credentials = result.get('credentials', [])
            print(f"   ✅ Found {len(credentials)} credentials:")
            
            for i, cred in enumerate(credentials):
                name = cred.get('name', 'Unknown')
                desc = cred.get('description', 'No description')
                cred_type = cred.get('type', 'unknown')
                created_at = cred.get('created_at', 'Unknown')
                
                print(f"     {i+1}. {name} ({cred_type})")
                print(f"        Description: {desc}")
                print(f"        Created: {created_at}")
        
        if result.get('count', 0) > 0:
            print(f"\n🎉 SUCCESS! get_credential_names is working correctly!")
        else:
            print(f"\n⚠️ Function works but no credentials found for this user")
            
    except Exception as e:
        print(f"❌ Error testing function: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_get_credential_names()
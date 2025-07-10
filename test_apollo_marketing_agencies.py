#!/usr/bin/env python3
"""
Test Apollo API for marketing agencies lead generation
"""

import json
import os
from datetime import datetime
from dotenv import load_dotenv
from apollo_api import get_apollo_leads

# Load environment variables
load_dotenv()

def test_marketing_agencies():
    """Test Apollo API with marketing agency criteria."""
    
    # Campaign criteria for marketing agencies
    campaign_data = {
        "campaign": {
            # Marketing companies with revenue filter
            "q_keywords": "marketing agency",
            # Company size: 50-200 employees  
            "organization_num_employees_ranges": ["51,200"],
            # Revenue range: $1M-$5M in numeric format
            "revenue_range": {"min": 1000000, "max": 5000000},
            # Location: United States
            "organization_locations": ["United States"],
            # Get only 1 page
            "page": 1,
            "per_page": 25
        },
        # Features to extract
        "features": [
            "id",
            "first_name", 
            "last_name",
            "name",
            "email",
            "title",
            "linkedin_url",
            "phone_numbers",
            "organization_name",
            "organization_website_url",
            "organization_industry",
            "organization_size",
            "organization_revenue",
            "organization_city",
            "organization_state",
            "organization_country",
            "organization_linkedin_url"
        ]
    }
    
    # Use TEST_USER_ID from environment to get Apollo API key from credentials
    campaign_data['user_id'] = os.getenv('TEST_USER_ID')
    
    print("🚀 Testing Apollo API for Marketing Agencies")
    print("=" * 60)
    print("📋 Criteria:")
    print("  - Search: Marketing Agency")
    print("  - Employees: 50-200")
    print("  - Revenue: $1M-$5M (testing format)")
    print("  - Location: United States")
    print("  - Page: 1 (25 results)")
    print("=" * 60)
    
    # Call Apollo API
    result = get_apollo_leads(campaign_data)
    
    if result['success']:
        # Generate filename with datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"leads/leads_{timestamp}.json"
        
        # Save results
        with open(filename, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"\n✅ Success! Found {len(result['leads'])} leads")
        print(f"💾 Results saved to: {filename}")
        
        # Show sample lead
        if result['leads']:
            print("\n📋 Sample lead:")
            lead = result['leads'][0]
            print(f"  Name: {lead.get('name', 'N/A')}")
            print(f"  Title: {lead.get('title', 'N/A')}")
            print(f"  Company: {lead.get('organization_name', 'N/A')}")
            print(f"  Email: {lead.get('email', 'N/A')}")
            print(f"  Industry: {lead.get('organization_industry', 'N/A')}")
            print(f"  Revenue: {lead.get('organization_revenue', 'N/A')}")
            print(f"  Size: {lead.get('organization_size', 'N/A')}")
        
        print(f"\n📊 Total available: {result['metadata']['total_available']}")
        print(f"⏱️  Execution time: {result['metadata']['execution_time']:.2f}s")
        
    else:
        print(f"\n❌ Failed: {result['error']['message']}")
        if 'troubleshooting_steps' in result['error']:
            print("\n🔧 Troubleshooting:")
            for step in result['error']['troubleshooting_steps']:
                print(f"  - {step}")

if __name__ == "__main__":
    test_marketing_agencies()
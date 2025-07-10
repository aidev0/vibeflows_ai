#!/usr/bin/env python3
"""Test Apollo API for marketing agencies and save results"""

from apollo_api import get_apollo_leads
from datetime import datetime
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create leads directory
os.makedirs('leads', exist_ok=True)

# Test parameters
user_id = os.getenv('TEST_USER_ID', 'test_user')

print('🎯 Testing Apollo API for Marketing Agencies...')
print('Criteria:')
print('  - Industry: Marketing agencies')
print('  - Location: United States')
print('  - Employees: 50-200')
print('  - Revenue: $1M+')

# Apollo API request
input_data = {
    'user_id': user_id,
    'campaign': {
        'organization_industries': ['Marketing and Advertising', 'Marketing Services', 'Digital Marketing'],
        'organization_locations': ['United States'],
        'organization_num_employees_ranges': ['51,200'],
        'organization_revenue_ranges': ['$1M,$10M', '$10M,$50M', '$50M,$100M', '$100M,$500M'],
        'per_page': 25  # One page of results
    },
    'features': [
        'first_name', 'last_name', 'name', 'email', 'title', 'linkedin_url',
        'city', 'state', 'phone_numbers',
        'organization_name', 'organization_website_url', 'organization_industry',
        'organization_size', 'organization_revenue', 'organization_city',
        'organization_state', 'organization_linkedin_url'
    ]
}

try:
    print('\n📡 Calling Apollo API...')
    result = get_apollo_leads(input_data)
    
    if result['success']:
        print(f'\n✅ SUCCESS!')
        print(f'📊 Found {result["metadata"]["total_leads_found"]} leads on this page')
        print(f'📈 Total available: {result["metadata"]["total_available"]} leads')
        print(f'⏱️  Execution time: {result["metadata"]["execution_time"]:.2f}s')
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'leads/leads_{timestamp}.json'
        
        # Prepare data to save
        save_data = {
            'query': {
                'criteria': 'Marketing agencies in US, 50-200 employees, $1M+ ARR',
                'filters': input_data['campaign'],
                'timestamp': datetime.now().isoformat()
            },
            'metadata': result['metadata'],
            'leads': result['leads']
        }
        
        with open(filename, 'w') as f:
            json.dump(save_data, f, indent=2)
            
        print(f'\n💾 Saved to: {filename}')
        
        # Show sample leads
        if result['leads']:
            print('\n📋 Sample leads (first 3):')
            for i, lead in enumerate(result['leads'][:3], 1):
                print(f'\n--- Lead {i} ---')
                print(f'  Name: {lead.get("name", "N/A")}')
                print(f'  Title: {lead.get("title", "N/A")}')
                print(f'  Email: {lead.get("email", "N/A")}')
                print(f'  Company: {lead.get("organization_name", "N/A")}')
                print(f'  Industry: {lead.get("organization_industry", "N/A")}')
                print(f'  Company Size: {lead.get("organization_size", "N/A")}')
                print(f'  Revenue: {lead.get("organization_revenue", "N/A")}')
                print(f'  Location: {lead.get("organization_city", "")}, {lead.get("organization_state", "")}')
            
    else:
        print(f'\n❌ FAILED: {result["error"]["message"]}')
        print(f'Error type: {result["error"]["type"]}')
        if 'troubleshooting_steps' in result['error']:
            print('\n🔧 Troubleshooting:')
            for step in result['error']['troubleshooting_steps']:
                print(f'  - {step}')
        
except Exception as e:
    print(f'\n💥 Error: {str(e)}')
    import traceback
    traceback.print_exc()
#!/usr/bin/env python3
"""
Apollo API Lead Generation Module
=================================
Retrieves leads data from Apollo.io API based on campaign queries.
Supports customizable features and provides preset defaults.
"""

import os
import sys
import json
import requests
import time
from typing import Dict, Any, List, Optional
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
from datetime import datetime, timezone

class ApolloAPI:
    """Handle Apollo.io API interactions for lead generation."""
    
    def __init__(self, user_id: str = None, api_key: str = None):
        """
        Initialize Apollo API client with credentials from database.
        
        Args:
            user_id: User identifier to retrieve credentials
            api_key: Apollo API key (optional, will get from credentials if not provided)
        """
        load_dotenv()
        self.base_url = "https://api.apollo.io/v1"
        
        # Get API key from credentials if not provided
        if not api_key and user_id:
            self.api_key = self.get_apollo_api_key(user_id)
        else:
            self.api_key = api_key
        
        if not self.api_key:
            raise Exception("Apollo API key not found. Provide user_id or api_key.")
        
        self.headers = {
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache',
            'X-Api-Key': self.api_key
        }
    
    def get_apollo_api_key(self, user_id: str) -> str:
        """
        Retrieve Apollo API key from credentials collection.
        
        Args:
            user_id: User identifier
            
        Returns:
            Apollo API key
            
        Raises:
            Exception: If credentials not found
        """
        try:
            # Apply URL decoding fix for user_id (handle %7C -> | encoding)
            clean_user_id = str(user_id).replace('%7C', '|').replace('%7c', '|')
            
            # Connect to MongoDB
            mongo_client = MongoClient(os.getenv('MONGODB_URI'))
            db = mongo_client.vibeflows
            
            # Query Apollo API key credential
            apollo_cred = db.credentials.find_one({
                'user_id': clean_user_id,
                'name': 'APOLLO_API_KEY'
            })
            
            if not apollo_cred:
                raise Exception(f"APOLLO_API_KEY credential not found for user_id: {user_id}")
            
            api_key = apollo_cred.get('value')
            if not api_key:
                raise Exception(f"APOLLO_API_KEY value is empty for user_id: {user_id}")
            
            mongo_client.close()
            return api_key
            
        except Exception as e:
            raise Exception(f"Error retrieving Apollo API key: {str(e)}")
    
    def get_default_features(self) -> List[str]:
        """
        Get default lead features to retrieve.
        
        Returns:
            List of default feature fields
        """
        return [
            'id',
            'first_name',
            'last_name',
            'name',
            'email',
            'title',
            'organization',
            'linkedin_url',
            'twitter_url',
            'city',
            'state',
            'country',
            'industry',
            'keywords',
            'phone_numbers',
            'organization_name',
            'organization_linkedin_url',
            'organization_website_url',
            'organization_industry',
            'organization_size',
            'organization_founded_year',
            'organization_revenue',
            'organization_city',
            'organization_state',
            'organization_country'
        ]
    
    def build_search_query(self, campaign_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build Apollo API search query from campaign information.
        
        Args:
            campaign_info: Dictionary containing campaign parameters
            
        Returns:
            Apollo API search query payload
        """
        query = {
            "api_key": self.api_key,
            "page": campaign_info.get('page', 1),
            "per_page": campaign_info.get('per_page', 25)  # Max 100
        }
        
        # Person filters
        if campaign_info.get('person_titles'):
            query['person_titles'] = campaign_info['person_titles']
        
        if campaign_info.get('person_locations'):
            query['person_locations'] = campaign_info['person_locations']
        
        if campaign_info.get('person_seniorities'):
            query['person_seniorities'] = campaign_info['person_seniorities']
        
        if campaign_info.get('person_departments'):
            query['person_departments'] = campaign_info['person_departments']
        
        # Organization filters
        if campaign_info.get('organization_names'):
            query['organization_names'] = campaign_info['organization_names']
        
        if campaign_info.get('organization_locations'):
            query['organization_locations'] = campaign_info['organization_locations']
        
        if campaign_info.get('organization_industries'):
            query['organization_industries'] = campaign_info['organization_industries']
        
        if campaign_info.get('organization_keywords'):
            query['organization_keywords'] = campaign_info['organization_keywords']
        
        if campaign_info.get('organization_num_employees_ranges'):
            query['organization_num_employees_ranges'] = campaign_info['organization_num_employees_ranges']
        
        if campaign_info.get('organization_revenue_ranges'):
            query['organization_revenue_ranges'] = campaign_info['organization_revenue_ranges']
        
        # Revenue range in numeric format
        if campaign_info.get('revenue_range'):
            query['revenue_range'] = campaign_info['revenue_range']
        
        # Technology filters
        if campaign_info.get('technologies'):
            query['technologies'] = campaign_info['technologies']
        
        # Intent signals
        if campaign_info.get('intent_strength'):
            query['intent_strength'] = campaign_info['intent_strength']
        
        # Keywords
        if campaign_info.get('q_keywords'):
            query['q_keywords'] = campaign_info['q_keywords']
        
        return query
    
    def search_people(self, search_query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search for people using Apollo API.
        
        Args:
            search_query: Apollo API search parameters
            
        Returns:
            Search results from Apollo API
        """
        endpoint = f"{self.base_url}/mixed_people/search"
        
        try:
            print(f"🔍 Searching Apollo for leads...")
            print(f"📊 Query parameters: {len(search_query)} filters")
            
            start_time = time.time()
            
            response = requests.post(
                endpoint,
                headers=self.headers,
                json=search_query,
                timeout=60
            )
            
            execution_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Apollo search successful in {execution_time:.2f}s")
                print(f"📈 Found {data.get('pagination', {}).get('total_entries', 0)} total leads")
                print(f"📄 Retrieved {len(data.get('people', []))} leads in this page")
                
                return {
                    'success': True,
                    'data': data,
                    'execution_time': execution_time,
                    'pagination': data.get('pagination', {}),
                    'people': data.get('people', [])
                }
            else:
                error_data = response.text
                try:
                    error_json = response.json()
                    error_message = error_json.get('message', 'Unknown error')
                except:
                    error_message = error_data
                
                print(f"❌ Apollo search failed: HTTP {response.status_code}")
                print(f"🚨 Error: {error_message}")
                
                return {
                    'success': False,
                    'error': {
                        'status_code': response.status_code,
                        'message': error_message,
                        'type': 'apollo_api_error'
                    }
                }
                
        except requests.exceptions.Timeout:
            print("❌ Apollo API request timed out")
            return {
                'success': False,
                'error': {
                    'type': 'timeout',
                    'message': 'Apollo API request timed out after 60 seconds'
                }
            }
        
        except requests.exceptions.RequestException as e:
            print(f"❌ Apollo API request failed: {str(e)}")
            return {
                'success': False,
                'error': {
                    'type': 'request_error',
                    'message': f'Request failed: {str(e)}'
                }
            }
        
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
            return {
                'success': False,
                'error': {
                    'type': 'unexpected_error',
                    'message': f'Unexpected error: {str(e)}'
                }
            }
    
    def extract_lead_features(self, people: List[Dict], requested_features: List[str]) -> List[Dict]:
        """
        Extract requested features from lead data.
        
        Args:
            people: List of people from Apollo API
            requested_features: List of features to extract
            
        Returns:
            List of leads with only requested features
        """
        extracted_leads = []
        
        for person in people:
            lead = {}
            
            for feature in requested_features:
                # Handle nested organization data
                if feature.startswith('organization_') and 'organization' in person:
                    org_field = feature.replace('organization_', '')
                    lead[feature] = person.get('organization', {}).get(org_field)
                else:
                    lead[feature] = person.get(feature)
            
            extracted_leads.append(lead)
        
        return extracted_leads
    
    def get_campaign_leads(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point to get leads data for a campaign.
        
        Args:
            input_data: Dictionary containing:
                - campaign: Campaign parameters for Apollo search
                - features: List of features to extract (optional)
                - Additional parameters
        
        Returns:
            Dictionary with leads data and metadata
        """
        try:
            print("🚀 Starting Apollo lead generation")
            
            # Extract campaign information
            campaign_info = input_data.get('campaign', {})
            if not campaign_info:
                return {
                    'success': False,
                    'error': {
                        'type': 'validation_error',
                        'message': 'Campaign information is required',
                        'troubleshooting_steps': [
                            'Provide campaign parameters in input_data["campaign"]',
                            'Include search criteria like person_titles, organization_industries, etc.',
                            'Check Apollo API documentation for available filters'
                        ]
                    }
                }
            
            # Get requested features or use defaults
            requested_features = input_data.get('features')
            if not requested_features:
                requested_features = self.get_default_features()
                print(f"📋 Using default features: {len(requested_features)} fields")
            else:
                print(f"📋 Using custom features: {len(requested_features)} fields")
            
            # Build search query
            search_query = self.build_search_query(campaign_info)
            
            # Search for leads
            search_result = self.search_people(search_query)
            
            if not search_result['success']:
                return {
                    'success': False,
                    'error': search_result['error'],
                    'query_used': search_query
                }
            
            # Extract requested features
            people = search_result['people']
            leads = self.extract_lead_features(people, requested_features)
            
            # Prepare final result
            result = {
                'success': True,
                'leads': leads,
                'metadata': {
                    'total_leads_found': len(leads),
                    'total_available': search_result['pagination'].get('total_entries', 0),
                    'page': search_result['pagination'].get('page', 1),
                    'per_page': search_result['pagination'].get('per_page', 25),
                    'features_extracted': requested_features,
                    'execution_time': search_result['execution_time'],
                    'timestamp': datetime.now(timezone.utc).isoformat()
                },
                'pagination': search_result['pagination'],
                'query_used': search_query
            }
            
            print(f"✅ Campaign leads generation completed")
            print(f"📊 Total leads: {len(leads)}")
            print(f"🎯 Features per lead: {len(requested_features)}")
            
            return result
            
        except Exception as e:
            print(f"❌ Error in campaign leads generation: {str(e)}")
            return {
                'success': False,
                'error': {
                    'type': 'unexpected_error',
                    'message': f'Campaign leads generation failed: {str(e)}',
                    'troubleshooting_steps': [
                        'Check Apollo API key is valid',
                        'Verify campaign parameters format',
                        'Check network connectivity',
                        'Review Apollo API rate limits'
                    ]
                }
            }

def get_apollo_leads(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Entry function to get Apollo leads data for a campaign.
    
    Args:
        input_data: Dictionary containing:
            - user_id: User identifier for credential lookup (required unless api_key provided)
            - campaign: Campaign search parameters
            - features: List of features to extract (optional)
            - api_key: Apollo API key (optional, will get from credentials if not provided)
    
    Returns:
        Dictionary with leads data and metadata
    
    Examples:
        # Basic usage with default features
        result = get_apollo_leads({
            "user_id": "google-oauth2|123456789",
            "campaign": {
                "person_titles": ["CEO", "CTO", "VP Engineering"],
                "organization_industries": ["Software", "Technology"],
                "organization_locations": ["San Francisco", "New York"],
                "per_page": 25
            }
        })
        
        # With custom features
        result = get_apollo_leads({
            "user_id": "google-oauth2|123456789",
            "campaign": {
                "person_titles": ["Marketing Manager"],
                "organization_num_employees_ranges": ["1,10", "11,50"]
            },
            "features": [
                "first_name", "last_name", "email", "title",
                "organization_name", "organization_website_url"
            ]
        })
        
        # Advanced search with multiple filters
        result = get_apollo_leads({
            "user_id": "google-oauth2|123456789",
            "campaign": {
                "q_keywords": "artificial intelligence OR machine learning",
                "person_seniorities": ["director", "vp", "c_level"],
                "organization_industries": ["Computer Software", "Information Technology"],
                "technologies": ["Salesforce", "HubSpot"],
                "intent_strength": "high",
                "page": 1,
                "per_page": 50
            },
            "features": [
                "name", "email", "title", "linkedin_url",
                "organization_name", "organization_industry",
                "organization_size", "organization_revenue"
            ]
        })
    
    Available Campaign Filters:
        Person Filters:
        - person_titles: List of job titles
        - person_locations: List of locations
        - person_seniorities: ["individual_contributor", "manager", "director", "vp", "c_level"]
        - person_departments: ["engineering", "marketing", "sales", "finance", etc.]
        
        Organization Filters:
        - organization_names: List of company names
        - organization_locations: List of company locations
        - organization_industries: List of industries
        - organization_keywords: List of keywords
        - organization_num_employees_ranges: ["1,10", "11,50", "51,200", etc.]
        - organization_revenue_ranges: ["$1M,$10M", "$10M,$50M", etc.]
        
        Technology & Intent:
        - technologies: List of technologies used
        - intent_strength: ["high", "medium", "low"]
        - q_keywords: Search keywords
        
        Pagination:
        - page: Page number (default: 1)
        - per_page: Results per page (max: 100, default: 25)
    
    Default Features Extracted:
        Personal: id, first_name, last_name, name, email, title, linkedin_url,
                 twitter_url, city, state, country, industry, keywords, phone_numbers
        Organization: organization_name, organization_linkedin_url, organization_website_url,
                     organization_industry, organization_size, organization_founded_year,
                     organization_revenue, organization_city, organization_state, organization_country
    """
    try:
        # Get user_id and api_key from input
        user_id = input_data.get('user_id')
        api_key = input_data.get('api_key')
        
        # Validate that we have either user_id or api_key
        if not user_id and not api_key:
            return {
                'success': False,
                'error': {
                    'type': 'validation_error',
                    'message': 'Either user_id or api_key is required',
                    'troubleshooting_steps': [
                        'Provide user_id to retrieve Apollo API key from credentials',
                        'Or provide api_key directly in input_data',
                        'Ensure user has APOLLO_API_KEY in credentials collection'
                    ]
                }
            }
        
        # Initialize Apollo API client
        apollo = ApolloAPI(user_id=user_id, api_key=api_key)
        
        # Get campaign leads
        return apollo.get_campaign_leads(input_data)
        
    except Exception as e:
        return {
            'success': False,
            'error': {
                'type': 'initialization_error',
                'message': f'Failed to initialize Apollo API: {str(e)}',
                'troubleshooting_steps': [
                    'Check Apollo API key is provided or set in environment',
                    'Verify Apollo API key is valid and active',
                    'Check network connectivity',
                    'Ensure apollo_api.py dependencies are installed'
                ]
            }
        }

if __name__ == "__main__":
    """Command line interface for Apollo lead generation."""
    
    if len(sys.argv) < 2:
        print("Usage: python apollo_api.py <campaign_json>")
        print("\nExample:")
        print('python apollo_api.py \'{"campaign": {"person_titles": ["CEO"], "organization_industries": ["Software"]}}\'')
        sys.exit(1)
    
    try:
        # Parse command line input
        input_data = json.loads(sys.argv[1])
        
        # Get leads
        result = get_apollo_leads(input_data)
        
        print("\n" + "="*60)
        print("📊 APOLLO LEADS RESULTS")
        print("="*60)
        
        if result['success']:
            print("✅ Status: SUCCESS")
            print(f"📈 Total leads found: {result['metadata']['total_leads_found']}")
            print(f"📄 Total available: {result['metadata']['total_available']}")
            print(f"⏱️  Execution time: {result['metadata']['execution_time']:.2f}s")
            print(f"🎯 Features per lead: {len(result['metadata']['features_extracted'])}")
            
            print("\n📋 Sample lead (first result):")
            if result['leads']:
                first_lead = result['leads'][0]
                for key, value in first_lead.items():
                    if value:  # Only show non-empty values
                        print(f"  {key}: {value}")
            
            print(f"\n💾 Full results: {len(result['leads'])} leads with {len(result['metadata']['features_extracted'])} features each")
            
        else:
            print("❌ Status: FAILED")
            print(f"🚨 Error: {result['error']['message']}")
            if 'troubleshooting_steps' in result['error']:
                print("\n🔧 Troubleshooting Steps:")
                for i, step in enumerate(result['error']['troubleshooting_steps'], 1):
                    print(f"   {i}. {step}")
        
    except json.JSONDecodeError:
        print("❌ Invalid JSON input")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️  Execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Fatal error: {str(e)}")
        sys.exit(1)
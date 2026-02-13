#!/usr/bin/env python
"""
Test script to call the /api/employee/ endpoint and display the response.
"""

import requests
import json
import sys

# API endpoint
API_URL = "http://localhost:8000/api/employee/"

def test_employee_endpoint():
    """Call the /api/employee/ endpoint and display the response."""
    try:
        print(f"Calling endpoint: {API_URL}")
        print("-" * 80)
        
        response = requests.get(API_URL)
        
        # Check if request was successful
        if response.status_code == 200:
            data = response.json()
            print("Response Status: 200 OK")
            print("-" * 80)
            print("Complete JSON Response:")
            print(json.dumps(data, indent=2))
            print("-" * 80)
            
            # Highlight menu_items_by_section if it exists
            if "menu_items_by_section" in data:
                print("\nmenu_items_by_section:")
                print(json.dumps(data["menu_items_by_section"], indent=2))
            else:
                print("\nNote: 'menu_items_by_section' not found in response")
                print("Available keys:", list(data.keys()))
        else:
            print(f"Response Status: {response.status_code}")
            print("Response Text:")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to {API_URL}")
        print("Make sure the Django development server is running on port 8000")
        print("Run: python manage.py runserver")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        sys.exit(1)
    except json.JSONDecodeError:
        print("Error: Response is not valid JSON")
        print("Response Text:")
        print(response.text)
        sys.exit(1)

if __name__ == "__main__":
    test_employee_endpoint()

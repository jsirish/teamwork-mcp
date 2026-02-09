#!/usr/bin/env python3
"""Test the get_project_budget method."""

import os
from teamwork_mcp.client import TeamworkClient

def test_budget():
    token = os.getenv("TEAMWORK_TOKEN")
    domain = os.getenv("TEAMWORK_DOMAIN")
    
    if not token or not domain:
        print("❌ Error: TEAMWORK_TOKEN and TEAMWORK_DOMAIN required.")
        return

    print(f"🔄 Connecting to {domain}...")
    client = TeamworkClient(access_token=token, installation_domain=domain)
    
    # Test with a known budget ID
    budget_id = "127645"
    print(f"\n📋 Fetching budget {budget_id}...")
    
    try:
        result = client.get_project_budget(budget_id)
        print(f"✅ Success!")
        print(f"Result: {result}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_budget()

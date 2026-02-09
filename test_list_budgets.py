#!/usr/bin/env python3
"""Test the list_project_budgets method."""

import os
from teamwork_mcp.client import TeamworkClient

def test_list_budgets():
    token = os.getenv("TEAMWORK_TOKEN")
    domain = os.getenv("TEAMWORK_DOMAIN")
    
    if not token or not domain:
        print("❌ Error: TEAMWORK_TOKEN and TEAMWORK_DOMAIN required.")
        return

    print(f"🔄 Connecting to {domain}...")
    client = TeamworkClient(access_token=token, installation_domain=domain)
    
    # Test with a project that has a budget (ID 1174174)
    project_id = "1174174"
    print(f"\n📋 Listing budgets for project {project_id}...")
    
    try:
        result = client.list_project_budgets(project_id)
        print(f"✅ Success!")
        print(f"Project: {result['project_name']}")
        print(f"Has time budget: {result['has_time_budget']}")
        print(f"Has financial budget: {result['has_financial_budget']}")
        print(f"\nBudgets ({len(result['budgets'])}):")
        for b in result['budgets']:
            print(f"  - Type: {b.get('type')}")
            print(f"    Status: {b.get('status')}")
            print(f"    Capacity: {b.get('capacity')}")
            print(f"    Used: {b.get('capacityUsed')}")
            print(f"    Remaining: {b.get('capacity', 0) - b.get('capacityUsed', 0)}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_list_budgets()

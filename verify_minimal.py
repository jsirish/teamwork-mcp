#!/usr/bin/env python3
"""Verify budget appears in MINIMAL mode for a specific project."""

import os
from teamwork_mcp.client import TeamworkClient

def verify_minimal_budget():
    token = os.getenv("TEAMWORK_TOKEN")
    domain = os.getenv("TEAMWORK_DOMAIN")
    
    if not token or not domain:
        print("❌ Error: TEAMWORK_TOKEN and TEAMWORK_DOMAIN required.")
        return

    print(f"🔄 Connecting to {domain}...")
    client = TeamworkClient(access_token=token, installation_domain=domain)
    
    # Fetch in MINIMAL mode
    print("\n📋 Fetching projects in MINIMAL mode...")
    response = client.list_projects(page=2, page_size=100, include_details=False)
    
    projects = response.get("projects", [])
    
    # Find project with budget
    for p in projects:
        if p.get("financialBudget") is not None:
            print(f"\n✅ FOUND PROJECT WITH BUDGET IN MINIMAL MODE:")
            print(f"   Name: {p['name']}")
            print(f"   ID: {p['id']}")
            print(f"   Keys: {list(p.keys())}")
            print(f"   financialBudget: {p['financialBudget']}")
            print(f"   timeBudget: {p['timeBudget']}")
            return True
    
    print("❌ No budgeted project found on this page")
    return False

if __name__ == "__main__":
    if verify_minimal_budget():
        print("\n🎉 SUCCESS: Budget fields work in minimal mode!")

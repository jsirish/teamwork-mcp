#!/usr/bin/env python3
"""Search for projects by name and check budget values."""

import os
from teamwork_mcp.client import TeamworkClient

def search_projects(search_terms):
    token = os.getenv("TEAMWORK_TOKEN")
    domain = os.getenv("TEAMWORK_DOMAIN")
    
    if not token or not domain:
        print("❌ Error: TEAMWORK_TOKEN and TEAMWORK_DOMAIN required.")
        return

    print(f"🔄 Connecting to {domain}...")
    client = TeamworkClient(access_token=token, installation_domain=domain)
    
    # Fetch more projects
    print(f"\n📋 Fetching projects (searching for: {search_terms})...")
    response = client.list_projects(page_size=100, include_details=True)
    
    projects = response.get("projects", [])
    print(f"Total projects returned: {len(projects)}")
    
    # Search for matching projects
    for term in search_terms:
        print(f"\n🔍 Searching for '{term}'...")
        matches = [p for p in projects if term.lower() in p.get("name", "").lower()]
        
        if not matches:
            print(f"   No matches found for '{term}'")
            continue
            
        for p in matches[:3]:  # Show up to 3 matches per term
            name = p.get("name", "Unknown")
            p_id = p.get("id")
            tb = p.get("timeBudget")
            fb = p.get("financialBudget")
            tb_id = p.get("timeBudgetId")
            fb_id = p.get("financialBudgetId")
            
            print(f"\n   📁 {name} (ID: {p_id})")
            print(f"      timeBudget: {tb}")
            print(f"      financialBudget: {fb}")
            print(f"      timeBudgetId: {tb_id}")
            print(f"      financialBudgetId: {fb_id}")
            
            if tb or fb:
                print("      ✅ HAS BUDGET DATA!")

if __name__ == "__main__":
    search_projects(["ao website", "rockline", "redesign"])

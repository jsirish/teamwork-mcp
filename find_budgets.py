#!/usr/bin/env python3
"""Search all projects for any with non-None budget values."""

import os
from teamwork_mcp.client import TeamworkClient

def find_budgeted_projects():
    token = os.getenv("TEAMWORK_TOKEN")
    domain = os.getenv("TEAMWORK_DOMAIN")
    
    if not token or not domain:
        print("❌ Error: TEAMWORK_TOKEN and TEAMWORK_DOMAIN required.")
        return

    print(f"🔄 Connecting to {domain}...")
    client = TeamworkClient(access_token=token, installation_domain=domain)
    
    # Fetch multiple pages
    all_projects = []
    for page in range(1, 6):  # Check first 5 pages (500 projects)
        print(f"📋 Fetching page {page}...")
        response = client.list_projects(page=page, page_size=100, include_details=True)
        projects = response.get("projects", [])
        if not projects:
            break
        all_projects.extend(projects)
    
    print(f"\nTotal projects fetched: {len(all_projects)}")
    
    # Find any with non-None budget values
    budgeted = []
    for p in all_projects:
        tb = p.get("timeBudget")
        fb = p.get("financialBudget")
        tb_id = p.get("timeBudgetId")
        fb_id = p.get("financialBudgetId")
        
        if tb is not None or fb is not None or tb_id is not None or fb_id is not None:
            budgeted.append({
                "name": p.get("name"),
                "id": p.get("id"),
                "timeBudget": tb,
                "financialBudget": fb,
                "timeBudgetId": tb_id,
                "financialBudgetId": fb_id,
            })
    
    if budgeted:
        print(f"\n✅ Found {len(budgeted)} projects with budget data:")
        for p in budgeted[:10]:
            print(f"\n   📁 {p['name']} (ID: {p['id']})")
            print(f"      timeBudget: {p['timeBudget']}")
            print(f"      financialBudget: {p['financialBudget']}")
    else:
        print("\n❌ No projects found with budget data.")
        print("   This could mean:")
        print("   1. No projects have budgets configured in Teamwork")
        print("   2. The token lacks permissions to view budget data")

if __name__ == "__main__":
    find_budgeted_projects()

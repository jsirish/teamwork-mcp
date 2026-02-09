import os
import json
import logging
from teamwork_mcp.client import TeamworkClient

# Configure logging
logging.basicConfig(level=logging.INFO)

def check_budgets():
    token = os.getenv("TEAMWORK_TOKEN")
    domain = os.getenv("TEAMWORK_DOMAIN")
    
    if not token or not domain:
        print("❌ Error: TEAMWORK_TOKEN and TEAMWORK_DOMAIN environment variables are required.")
        print("Please export them and try again.")
        return

    print(f"🔄 Connecting to {domain}...")
    client = TeamworkClient(access_token=token, installation_domain=domain)
    
    try:
        # 1. Check list_projects response
        print("\n📋 Fetching project list...")
        response = client.list_projects(page_size=3, include_details=True) # Use True to check full response
        projects = response.get("projects", [])
        
        if not projects:
            print("⚠️ No projects found.")
            return

        print(f"Found {len(projects)} projects in sample.")
        
        found_budget = False
        for p in projects:
            p_id = p.get("id")
            name = p.get("name")
            print(f"\n🔍 Inspecting Project: {name} ({p_id})")
            
            # Print all keys to see what's there
            print(f"Keys: {list(p.keys())}")
            
            # Check for budget related fields
            budget_keys = [k for k in p.keys() if "budget" in k.lower() or "financial" in k.lower() or "cost" in k.lower()]
            if budget_keys:
                print(f"✅ Found budget-related keys: {budget_keys}")
                for k in budget_keys:
                    print(f"   - {k}: {p[k]}")
                found_budget = True
            else:
                print("❌ No direct budget keys found.")
                
            # Check nested defaults
            if "defaults" in p:
                print("   Checking defaults...")
                defaults = p["defaults"]
                print(f"   Defaults keys: {list(defaults.keys())}")
        
        if not found_budget:
            print("\n⚠️ No budget info found in standard list response.")
            print("💡 Hypothesis: Need to fetch individual project details?")
            
            # Try fetching single project
            p_id = projects[0]["id"]
            print(f"\n📋 Fetching single project details for ID {p_id}...")
            p_detail = client.get_project(p_id)
            project_obj = p_detail.get("project", {})
            
            budget_keys = [k for k in project_obj.keys() if "budget" in k.lower()]
            if budget_keys:
                print(f"✅ Found budget keys in Detail view: {budget_keys}")
            else:
                print("❌ Still no budget keys in Detail view.")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_budgets()

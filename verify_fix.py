#!/usr/bin/env python3
"""Verify budget fields are now included in minimal response."""

import os
import json
from teamwork_mcp.client import TeamworkClient

def verify_fix():
    token = os.getenv("TEAMWORK_TOKEN")
    domain = os.getenv("TEAMWORK_DOMAIN")
    
    if not token or not domain:
        print("❌ Error: TEAMWORK_TOKEN and TEAMWORK_DOMAIN required.")
        return False

    print(f"🔄 Connecting to {domain}...")
    client = TeamworkClient(access_token=token, installation_domain=domain)
    
    print("\n📋 Testing minimal mode (include_details=False)")
    response = client.list_projects(page_size=3, include_details=False)
    
    projects = response.get("projects", [])
    if not projects:
        print("⚠️ No projects found.")
        return False
    
    print(f"Found {len(projects)} projects.\n")
    
    success = True
    for p in projects:
        name = p.get("name", "Unknown")[:40]
        print(f"Project: {name}")
        print(f"   Keys: {list(p.keys())}")
        
        # Check budget keys exist
        if "timeBudget" not in p or "financialBudget" not in p:
            print("   ❌ FAIL: Budget keys missing!")
            success = False
        else:
            print(f"   ✅ timeBudget: {p['timeBudget']}")
            print(f"   ✅ financialBudget: {p['financialBudget']}")
    
    return success

if __name__ == "__main__":
    if verify_fix():
        print("\n✅ VERIFICATION PASSED: Budget fields are now included!")
    else:
        print("\n❌ VERIFICATION FAILED")

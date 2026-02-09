#!/usr/bin/env python3
"""Script to test including budget data via includeProjectProfitability."""

import os
import json
import logging
from teamwork_mcp.client import TeamworkClient

logging.basicConfig(level=logging.INFO)

def test_budget_include():
    token = os.getenv("TEAMWORK_TOKEN")
    domain = os.getenv("TEAMWORK_DOMAIN")
    
    if not token or not domain:
        print("❌ Error: TEAMWORK_TOKEN and TEAMWORK_DOMAIN required.")
        return

    print(f"🔄 Connecting to {domain}...")
    client = TeamworkClient(access_token=token, installation_domain=domain)
    
    print("\n📋 Test 1: WITHOUT includeProjectProfitability")
    response1 = client._request(
        "GET",
        "/projects.json",
        params={"pageSize": 2}
    )
    
    for p in response1.get("projects", [])[:1]:
        p_id = p.get("id")
        name = p.get("name")
        tb = p.get("timeBudget")
        fb = p.get("financialBudget")
        print(f"   Project: {name[:40]}...")
        print(f"   timeBudget: {tb}")
        print(f"   financialBudget: {fb}")
    
    print("\n📋 Test 2: WITH includeProjectProfitability=true")
    response2 = client._request(
        "GET",
        "/projects.json",
        params={"pageSize": 2, "includeProjectProfitability": "true"}
    )
    
    for p in response2.get("projects", [])[:1]:
        p_id = p.get("id")
        name = p.get("name")
        tb = p.get("timeBudget")
        fb = p.get("financialBudget")
        print(f"   Project: {name[:40]}...")
        print(f"   timeBudget: {tb}")
        print(f"   financialBudget: {fb}")
        
        # Also look for any keys containing 'profit' or 'budget'
        budget_keys = [k for k in p.keys() if 'budget' in k.lower() or 'profit' in k.lower()]
        print(f"   Budget-related keys: {budget_keys}")
        for k in budget_keys:
            if p.get(k) is not None:
                print(f"      {k}: {p[k]}")

if __name__ == "__main__":
    test_budget_include()

#!/usr/bin/env python3

import os
from github import Github
from dotenv import load_dotenv

load_dotenv()

def check_webhook_config():
    github_token = os.getenv('GITHUB_TOKEN')
    org_name = os.getenv('GITHUB_ORG_NAME', 'tickarus-demo-org')
    
    if not github_token:
        print("Error: GITHUB_TOKEN not found")
        return
    
    g = Github(github_token)
    org = g.get_organization(org_name)
    
    print(f"Checking webhooks for organization: {org_name}")
    
    # Check the frontend-webapp repository specifically
    repo_name = "frontend-webapp"
    try:
        repo = org.get_repo(repo_name)
        print(f"\n=== Repository: {repo.full_name} ===")
        
        hooks = repo.get_hooks()
        for hook in hooks:
            print(f"Hook ID: {hook.id}")
            print(f"Name: {hook.name}")
            print(f"Active: {hook.active}")
            print(f"Events: {hook.events}")
            print(f"Config URL: {hook.config.get('url', 'N/A')}")
            print(f"Config Content Type: {hook.config.get('content_type', 'N/A')}")
            print(f"Config Insecure SSL: {hook.config.get('insecure_ssl', 'N/A')}")
            print(f"Has Secret: {'secret' in hook.config and hook.config['secret'] is not None}")
            if 'secret' in hook.config:
                # Don't print the actual secret, just indicate if it exists
                secret = hook.config['secret']
                if secret:
                    print(f"Secret Length: {len(secret)} characters")
                    print(f"Secret Preview: {secret[:8]}..." if len(secret) > 8 else secret)
                else:
                    print("Secret: Empty")
            else:
                print("Secret: Not configured")
            print("-" * 40)
            
    except Exception as e:
        print(f"Error checking repository {repo_name}: {e}")

if __name__ == "__main__":
    check_webhook_config()
#!/usr/bin/env python3

import os
from github import Github
from dotenv import load_dotenv

load_dotenv()

def trigger_workflow():
    github_token = os.getenv('GITHUB_TOKEN')
    org_name = os.getenv('GITHUB_ORG_NAME', 'tickarus-demo-org')
    
    if not github_token:
        print("Error: GITHUB_TOKEN not found")
        return
    
    g = Github(github_token)
    org = g.get_organization(org_name)
    
    # Use frontend-webapp as our test repository
    repo_name = "frontend-webapp"
    
    try:
        repo = org.get_repo(repo_name)
        print(f"Triggering workflow in {repo.full_name}")
        
        # Get the workflows
        workflows = list(repo.get_workflows())
        if not workflows:
            print("No workflows found in repository")
            return
        
        workflow = workflows[0]  # Use the first workflow
        print(f"Found workflow: {workflow.name}")
        
        # Trigger the workflow on main branch
        result = workflow.create_dispatch(ref="main")
        print(f"Workflow dispatch triggered successfully")
        print("Check GitHub Actions tab to see the failing workflow run")
        print("This should trigger a webhook to your backend and create a ticket")
        
    except Exception as e:
        print(f"Error triggering workflow: {e}")

if __name__ == "__main__":
    trigger_workflow()
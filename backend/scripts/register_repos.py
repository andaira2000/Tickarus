#!/usr/bin/env python3

import os
import asyncio
from uuid import uuid4
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

async def register_repositories():
    """Register all demo repositories in the database"""
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    
    if not supabase_url or not supabase_key:
        print("Error: Supabase credentials not found")
        return
    
    supabase = create_client(supabase_url, supabase_key)
    
    repositories = [
        {
            "org_name": "tickarus-demo-org",
            "repo_name": "frontend-webapp",
            "full_name": "tickarus-demo-org/frontend-webapp",
            "description": "React TypeScript web application with CI/CD pipeline",
            "primary_language": "TypeScript",
        },
        {
            "org_name": "tickarus-demo-org", 
            "repo_name": "backend-api",
            "full_name": "tickarus-demo-org/backend-api",
            "description": "FastAPI backend service with database integration",
            "primary_language": "Python",
        },
        {
            "org_name": "tickarus-demo-org",
            "repo_name": "mobile-app", 
            "full_name": "tickarus-demo-org/mobile-app",
            "description": "React Native mobile application",
            "primary_language": "JavaScript",
        },
        {
            "org_name": "tickarus-demo-org",
            "repo_name": "data-pipeline",
            "full_name": "tickarus-demo-org/data-pipeline",
            "description": "ETL data processing pipeline with Apache Airflow",
            "primary_language": "Python",
        },
        {
            "org_name": "tickarus-demo-org",
            "repo_name": "ml-models",
            "full_name": "tickarus-demo-org/ml-models",
            "description": "Machine learning models for predictive analytics",
            "primary_language": "Python",
        },
        {
            "org_name": "tickarus-demo-org",
            "repo_name": "legacy-system",
            "full_name": "tickarus-demo-org/legacy-system",
            "description": "Legacy Java Spring Boot application",
            "primary_language": "Java",
        }
    ]
    
    for repo_data in repositories:
        try:
            # Check if repository already exists
            existing = supabase.table("github_repositories").select("*").eq("full_name", repo_data["full_name"]).execute()
            
            if existing.data:
                print(f"Repository {repo_data['full_name']} already exists")
                continue
                
            # Add timestamps
            repo_data["created_at"] = datetime.utcnow().isoformat()
            repo_data["is_active"] = True
            
            # Insert repository
            result = supabase.table("github_repositories").insert(repo_data).execute()
            print(f"Registered repository: {repo_data['full_name']}")
            
        except Exception as e:
            print(f"Error registering {repo_data['full_name']}: {e}")

if __name__ == "__main__":
    asyncio.run(register_repositories())
#!/usr/bin/env python3

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def check_recent_tickets():
    """Check for tickets created in the last hour that might be from CI failures"""
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    
    if not supabase_url or not supabase_key:
        print("Error: Supabase credentials not found")
        return
    
    supabase = create_client(supabase_url, supabase_key)
    
    # Get tickets created in the last hour
    one_hour_ago = (datetime.utcnow() - timedelta(hours=1)).isoformat()
    
    try:
        # Query tickets
        tickets_result = (supabase.table("tickets")
                         .select("*")
                         .gte("created_at", one_hour_ago)
                         .order("created_at", desc=True)
                         .execute())
        
        print(f"Found {len(tickets_result.data)} tickets created in the last hour:")
        
        for ticket in tickets_result.data:
            print(f"\n--- Ticket {ticket['id']} ---")
            print(f"Title: {ticket['title']}")
            print(f"Description: {ticket['description'][:200]}...")
            print(f"Status: {ticket['status']}")
            print(f"Priority: {ticket['priority']}")
            print(f"Created: {ticket['created_at']}")
            print(f"Created by: {ticket.get('created_by', 'System')}")
        
        # Also check CI failures
        ci_failures_result = (supabase.table("ci_failures")
                             .select("*")
                             .gte("created_at", one_hour_ago)
                             .order("created_at", desc=True)
                             .execute())
        
        print(f"\nFound {len(ci_failures_result.data)} CI failures in the last hour:")
        
        for failure in ci_failures_result.data:
            print(f"\n--- CI Failure {failure['id']} ---")
            print(f"Workflow: {failure['workflow_name']}")
            print(f"Branch: {failure['branch_name']}")
            print(f"Commit: {failure['commit_sha'][:8]}")
            print(f"Reason: {failure['failure_reason']}")
            print(f"Ticket ID: {failure.get('ticket_id', 'None')}")
            print(f"Created: {failure['created_at']}")
            
    except Exception as e:
        print(f"Error checking tickets: {e}")

if __name__ == "__main__":
    check_recent_tickets()
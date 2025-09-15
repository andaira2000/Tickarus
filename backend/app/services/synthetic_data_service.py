import random
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from app.db.database import get_service_client, exec_query
from app.models.ticket import TicketCreate, TicketStatus, TicketPriority
import logging

logger = logging.getLogger(__name__)


class SyntheticDataService:
    """
    Generate synthetic ticket data with known ground truth for AI evaluation
    """
    
    def __init__(self):
        self.ticket_templates = [
            # Database issues
            {
                "title_patterns": [
                    "Database connection timeout in {service}",
                    "{service} cannot connect to database",
                    "DB connection pool exhausted for {service}",
                    "Database deadlock detected in {service}"
                ],
                "description_patterns": [
                    "The {service} service is experiencing database connection timeouts. Users report slow response times and some requests are failing with connection timeout errors after 30 seconds.",
                    "Multiple users reporting that {service} is unable to establish connections to the main database. Error logs show connection refused messages.",
                    "The connection pool for {service} database is reaching maximum capacity during peak hours, causing new connections to fail.",
                    "Database deadlock detected between {service} operations. Transactions are being rolled back automatically."
                ],
                "ground_truth": {
                    "category": "database",
                    "root_cause": "Database connectivity issues",
                    "expected_keywords": ["database", "connection", "timeout", "db"],
                    "priority": "high",
                    "similar_group": "db_connectivity"
                }
            },
            # Memory issues
            {
                "title_patterns": [
                    "OutOfMemoryError in {service}",
                    "{service} experiencing memory leaks",
                    "Heap space exhausted for {service}",
                    "Memory usage spiking in {service}"
                ],
                "description_patterns": [
                    "The {service} application is throwing OutOfMemoryError exceptions. Heap dumps show memory usage has grown steadily over the past 24 hours.",
                    "Memory consumption in {service} continues to increase without garbage collection. This appears to be a memory leak in recent code changes.",
                    "Java heap space is being exhausted in {service}. The application becomes unresponsive when memory usage reaches 95%.",
                    "Monitoring shows {service} memory usage has increased by 300% since the last deployment. Response times are degrading."
                ],
                "ground_truth": {
                    "category": "memory",
                    "root_cause": "Memory exhaustion",
                    "expected_keywords": ["memory", "heap", "oom", "leak"],
                    "priority": "high",
                    "similar_group": "memory_issues"
                }
            },
            # Performance issues
            {
                "title_patterns": [
                    "Slow response times in {service}",
                    "{service} API performance degradation",
                    "High latency detected for {service}",
                    "Performance bottleneck in {service}"
                ],
                "description_patterns": [
                    "API response times for {service} have increased from 200ms to 3+ seconds. Users are experiencing delays in page loading.",
                    "Performance monitoring shows {service} is taking much longer to process requests. Database queries appear to be the bottleneck.",
                    "The {service} endpoint is responding slowly during peak traffic hours. Load testing shows performance degrades significantly under load.",
                    "Users report that {service} features are loading very slowly. Profiling shows inefficient algorithms in recent code changes."
                ],
                "ground_truth": {
                    "category": "performance",
                    "root_cause": "Performance degradation",
                    "expected_keywords": ["slow", "performance", "latency", "response"],
                    "priority": "medium",
                    "similar_group": "performance_issues"
                }
            },
            # Authentication issues
            {
                "title_patterns": [
                    "Login failures in {service}",
                    "Authentication errors for {service}",
                    "Users cannot access {service}",
                    "Permission denied errors in {service}"
                ],
                "description_patterns": [
                    "Multiple users report they cannot log into {service}. Authentication service returns 401 unauthorized errors consistently.",
                    "Users with valid credentials are getting permission denied when accessing {service} features. Role-based access seems to be malfunctioning.",
                    "The {service} login page is not accepting valid username/password combinations. OAuth flow appears to be broken.",
                    "Session timeouts are occurring much faster than expected in {service}. Users are being logged out every few minutes."
                ],
                "ground_truth": {
                    "category": "authentication",
                    "root_cause": "Authentication or authorization issues",
                    "expected_keywords": ["auth", "login", "unauthorized", "permission"],
                    "priority": "high",
                    "similar_group": "auth_issues"
                }
            },
            # 404/Missing resource issues
            {
                "title_patterns": [
                    "404 errors on {service} endpoints",
                    "Missing resources in {service}",
                    "Broken links in {service}",
                    "API endpoints not found in {service}"
                ],
                "description_patterns": [
                    "Users are getting 404 Not Found errors when trying to access certain {service} pages. The URLs appear to be correct.",
                    "Several API endpoints in {service} are returning 404 errors. These endpoints were working before the latest deployment.",
                    "The {service} application has broken internal links. Navigation to certain sections results in page not found errors.",
                    "Frontend requests to {service} backend are failing with 404 errors. The routing configuration may have changed."
                ],
                "ground_truth": {
                    "category": "missing_resources",
                    "root_cause": "Missing resources or configuration",
                    "expected_keywords": ["404", "not found", "missing", "endpoint"],
                    "priority": "medium",
                    "similar_group": "missing_resources"
                }
            },
            # General server errors
            {
                "title_patterns": [
                    "500 Internal Server Error in {service}",
                    "{service} application crashes",
                    "Unhandled exceptions in {service}",
                    "Server errors affecting {service}"
                ],
                "description_patterns": [
                    "The {service} application is throwing 500 Internal Server Error responses. Stack traces show unhandled null pointer exceptions.",
                    "Frequent application crashes in {service} are causing service interruptions. Error logs show various runtime exceptions.",
                    "Users encounter server errors when performing specific actions in {service}. The application seems unstable after recent changes.",
                    "Multiple 500 errors are being logged for {service}. The application fails to handle edge cases properly."
                ],
                "ground_truth": {
                    "category": "server_errors",
                    "root_cause": "Application runtime error",
                    "expected_keywords": ["500", "internal server", "crash", "exception"],
                    "priority": "high",
                    "similar_group": "server_errors"
                }
            }
        ]
        
        self.services = [
            "user-service", "payment-service", "inventory-service", "notification-service",
            "auth-service", "analytics-service", "reporting-service", "api-gateway",
            "order-service", "product-service", "search-service", "recommendation-service"
        ]
    
    @staticmethod
    def _c():
        return get_service_client()
    
    async def _get_teams_and_actors(self) -> Dict[str, Any]:
        """Get available teams and system actors for ticket creation"""
        c = self._c()
        
        # Get teams
        teams_resp = exec_query(c.table("teams").select("id, name"))
        teams = teams_resp.data or []
        
        # Get system actors (for creating tickets)
        actors_resp = exec_query(
            c.table("actors")
            .select("id, actor_type")
            .eq("actor_type", "system")
        )
        system_actors = actors_resp.data or []
        
        return {
            "teams": teams,
            "system_actors": system_actors
        }
    
    async def generate_ticket_set(
        self, 
        count: int = 50,
        include_similar_pairs: bool = True
    ) -> Dict[str, Any]:
        """
        Generate a set of synthetic tickets with ground truth
        
        Args:
            count: Number of tickets to generate
            include_similar_pairs: Whether to include intentionally similar tickets
            
        Returns:
            Generated tickets with ground truth metadata
        """
        logger.info(f"Generating {count} synthetic tickets")
        
        # Get required data
        data = await self._get_teams_and_actors()
        teams = data["teams"]
        system_actors = data["system_actors"]
        
        if not teams or not system_actors:
            raise Exception("Missing required teams or system actors for ticket generation")
        
        generated_tickets = []
        ground_truth = []
        
        # Generate tickets
        for i in range(count):
            template = random.choice(self.ticket_templates)
            service = random.choice(self.services)
            team = random.choice(teams)
            actor = random.choice(system_actors)
            
            # Create ticket content
            title = random.choice(template["title_patterns"]).format(service=service)
            description = random.choice(template["description_patterns"]).format(service=service)
            
            # Random status and priority
            status = random.choice([TicketStatus.OPEN, TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED])
            priority = TicketPriority(template["ground_truth"]["priority"]) if random.random() < 0.7 else random.choice(list(TicketPriority))
            
            # Create ticket
            ticket_data = {
                "title": title,
                "description": description,
                "team_id": team["id"],
                "status": status,
                "priority": priority,
                "created_at": (datetime.utcnow() - timedelta(days=random.randint(1, 30))).isoformat()
            }
            
            # Insert ticket
            c = self._c()
            ticket_resp = exec_query(
                c.table("tickets")
                .insert({
                    **ticket_data,
                    "actor_id": actor["id"],
                    "status": ticket_data["status"].value,
                    "priority": ticket_data["priority"].value
                }, returning="representation")
            )
            
            if ticket_resp.data:
                ticket = ticket_resp.data[0]
                generated_tickets.append(ticket)
                
                # Store ground truth
                ground_truth.append({
                    "ticket_id": ticket["id"],
                    "category": template["ground_truth"]["category"],
                    "root_cause": template["ground_truth"]["root_cause"],
                    "expected_keywords": template["ground_truth"]["expected_keywords"],
                    "similar_group": template["ground_truth"]["similar_group"],
                    "service": service,
                    "template_used": template["ground_truth"]["category"]
                })
        
        # Generate similar pairs if requested
        similar_pairs = []
        if include_similar_pairs and len(generated_tickets) >= 10:
            # Create 5 pairs of intentionally similar tickets
            for _ in range(5):
                template = random.choice(self.ticket_templates)
                service = random.choice(self.services)
                team = random.choice(teams)
                actor = random.choice(system_actors)
                
                # Create two similar tickets
                for j in range(2):
                    title = random.choice(template["title_patterns"]).format(service=service)
                    description = random.choice(template["description_patterns"]).format(service=service)
                    
                    ticket_data = {
                        "title": title,
                        "description": description,
                        "team_id": team["id"],
                        "status": TicketStatus.OPEN.value,
                        "priority": TicketPriority.MEDIUM.value,
                        "actor_id": actor["id"]
                    }
                    
                    ticket_resp = exec_query(
                        c.table("tickets").insert(ticket_data, returning="representation")
                    )
                    
                    if ticket_resp.data:
                        ticket = ticket_resp.data[0]
                        similar_pairs.append(ticket["id"])
        
        logger.info(f"Generated {len(generated_tickets)} tickets with ground truth")
        
        return {
            "tickets_generated": len(generated_tickets),
            "ticket_ids": [t["id"] for t in generated_tickets],
            "ground_truth": ground_truth,
            "similar_pairs": [similar_pairs[i:i+2] for i in range(0, len(similar_pairs), 2)],
            "categories": list(set(gt["category"] for gt in ground_truth))
        }
    
    async def evaluate_similarity_accuracy(self, ticket_ids: List[str], ground_truth: List[Dict]) -> Dict[str, Any]:
        """
        Evaluate similarity detection accuracy using generated data
        
        Args:
            ticket_ids: List of ticket IDs to test
            ground_truth: Ground truth data for evaluation
            
        Returns:
            Evaluation metrics
        """
        from app.services.similarity_service import similarity_service
        
        correct_predictions = 0
        total_predictions = 0
        
        # Group tickets by similar_group for evaluation
        groups = {}
        for gt in ground_truth:
            group = gt["similar_group"]
            if group not in groups:
                groups[group] = []
            groups[group].append(gt["ticket_id"])
        
        # Test similarity detection
        for ticket_id in ticket_ids[:10]:  # Test first 10 tickets
            # Get ground truth for this ticket
            ticket_gt = next((gt for gt in ground_truth if gt["ticket_id"] == ticket_id), None)
            if not ticket_gt:
                continue
            
            # Get ticket content
            c = self._c()
            ticket_resp = exec_query(
                c.table("tickets")
                .select("title, description")
                .eq("id", ticket_id)
                .single()
            )
            
            if not ticket_resp.data:
                continue
            
            ticket = ticket_resp.data
            ticket_text = f"{ticket['title']}. {ticket['description']}"
            
            # Get similar tickets
            similar_tickets = await similarity_service.find_similar_tickets(
                ticket_text=ticket_text,
                current_ticket_id=ticket_id,
                limit=5
            )
            
            # Check if any similar tickets are in the same ground truth group
            expected_group = ticket_gt["similar_group"]
            expected_tickets = groups.get(expected_group, [])
            
            found_similar = any(
                sim["id"] in expected_tickets 
                for sim in similar_tickets
            )
            
            total_predictions += 1
            if found_similar:
                correct_predictions += 1
        
        accuracy = (correct_predictions / total_predictions * 100) if total_predictions > 0 else 0
        
        return {
            "similarity_accuracy": round(accuracy, 2),
            "correct_predictions": correct_predictions,
            "total_predictions": total_predictions,
            "test_groups": len(groups)
        }


# Global instance
synthetic_data_service = SyntheticDataService()
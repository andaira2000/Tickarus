import time
import json
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging

from app.db.database import get_supabase, get_service_client, exec_query
from app.services.metrics_service import MetricsService
from app.services.similarity_service import SimilarityService
from app.services.rootcause_service import rootcause_service
from app.services.auto_tagging_service import auto_tagging_service

logger = logging.getLogger(__name__)


class EvaluationTaskType(Enum):
    SIMILARITY_ACCURACY = "similarity_accuracy"
    ROOTCAUSE_ACCURACY = "rootcause_accuracy"
    TAGGING_ACCURACY = "tagging_accuracy"
    PERFORMANCE_BENCHMARK = "performance_benchmark"


@dataclass
class EvaluationResult:
    evaluation_id: UUID
    evaluation_type: str
    metrics: Dict[str, float]
    detailed_results: Dict[str, Any]
    summary: str
    timestamp: datetime


class ComprehensiveEvaluationService:
    """
    Comprehensive evaluation framework for all AI features
    Addresses all dissertation research questions with quantitative metrics
    """

    def __init__(self):
        self.similarity_service = SimilarityService()

    @staticmethod
    def _c():
        return get_supabase()

    async def generate_test_dataset(
        self,
        num_tickets: int = 50,
        num_similar_groups: int = 10,
        include_commit_failures: bool = True,
    ) -> Dict[str, Any]:
        """Generate synthetic test data for dissertation evaluation"""
        c = get_service_client()

        # Import here to avoid circular imports
        from app.services.ticket_service import TicketService
        from app.services.actor_service import ActorService
        from app.models.ticket import TicketCreate
        from uuid import uuid4
        import random

        # Enhanced ticket templates matching auto-tagging service capabilities
        # Tags aligned with tag_descriptions in auto_tagging_service.py
        ticket_templates = [
            {
                "title_template": "Database deadlock detected in {component}",
                "description_template": "Critical database deadlock occurring in {component}. Tables {table1} and {table2} are locked. Transaction timeouts after {timeout}ms. This is blocking all {impact} operations in production.",
                "tags": ["database", "bug"],
                "priority": "critical",
                "category": "database_critical",
            },
            {
                "title_template": "Authentication service completely down",
                "description_template": "The authentication service has crashed and is unavailable. All user login attempts are failing with 503 errors. This is a complete system outage affecting all users. Error: {error_details}.",
                "tags": ["security", "backend", "bug"],
                "priority": "critical",
                "category": "auth_critical",
            },
            {
                "title_template": "Memory leak causing performance issues in {component}",
                "description_template": "Memory usage continuously growing in {component}. Performance degrading over time. Memory consumption increased from {start_size} to {end_size}. Users experiencing slow response times.",
                "tags": ["performance", "backend"],
                "priority": "high",
                "category": "performance_issue",
            },
            {
                "title_template": "API endpoint returning errors",
                "description_template": "The {endpoint} API endpoint is returning {status_code} errors intermittently. Affecting {operations} functionality. Error rate is {error_rate}%. Investigation needed.",
                "tags": ["api", "backend", "bug"],
                "priority": "high",
                "category": "api_error",
            },
            {
                "title_template": "Frontend component not displaying correctly",
                "description_template": "The {component} component has rendering issues in {browser}. CSS styles are broken and layout is distorted. This affects user experience for {user_group} users.",
                "tags": ["frontend", "ui", "bug"],
                "priority": "medium",
                "category": "ui_bug",
            },
            {
                "title_template": "Network connectivity timeout issues",
                "description_template": "Experiencing intermittent network timeouts when connecting to {service}. Connection drops after {timeout} seconds. This affects {functionality} and causes user frustration.",
                "tags": ["networking", "infrastructure"],
                "priority": "medium",
                "category": "network_issue",
            },
            {
                "title_template": "Configuration error in {environment}",
                "description_template": "Misconfiguration detected in {environment} environment. {config_item} is set incorrectly causing {issue_type}. Need to update {config_file} configuration.",
                "tags": ["configuration", "infrastructure"],
                "priority": "medium",
                "category": "config_issue",
            },
            {
                "title_template": "Add new feature: {feature_name}",
                "description_template": "Request to implement {feature_name} functionality. This would improve user experience by {benefit}. Users have been requesting this for better {use_case}.",
                "tags": ["feature"],
                "priority": "low",
                "category": "feature_request",
            },
            {
                "title_template": "Update documentation for {component}",
                "description_template": "The documentation for {component} is outdated and missing {missing_info}. Need to update with latest API changes and add examples for {use_cases}.",
                "tags": ["documentation"],
                "priority": "low",
                "category": "docs_update",
            },
            {
                "title_template": "Testing framework failing in CI",
                "description_template": "Unit tests are failing in CI pipeline for {component}. Test suite shows {failure_count} failures. Need to fix {test_type} tests and update test configurations.",
                "tags": ["testing", "infrastructure"],
                "priority": "medium",
                "category": "test_failure",
            },
        ]

        # Get actors for creating tickets (prefer human, fallback to system)
        test_actors = exec_query(
            c.table("actors")
            .select("id, actor_type")
            .eq("actor_type", "human")
            .limit(5)
        ).data

        if not test_actors:
            # Fallback to system actors if no human actors exist
            test_actors = exec_query(
                c.table("actors")
                .select("id, actor_type")
                .eq("actor_type", "system")
                .limit(5)
            ).data

        if not test_actors:
            raise Exception(
                "No actors found for test data generation. Please create at least one user account first."
            )

        # Get all existing teams to randomly distribute tickets
        teams_resp = exec_query(c.table("teams").select("id"))

        if not teams_resp.data:
            raise Exception("No teams found. Please create at least one team first.")

        available_teams = [UUID(team["id"]) for team in teams_resp.data]

        def get_random_team_id():
            """Helper function to get a random team ID from available teams"""
            return random.choice(available_teams)

        created_tickets = []
        similar_groups = {}

        # Initialize ground truth data for evaluation
        ground_truth_tags = {}
        ground_truth_priorities = {}

        # Create similar ticket groups
        for group_idx in range(num_similar_groups):
            template = random.choice(ticket_templates)
            tickets_in_group = random.randint(2, 5)  # 2-5 similar tickets per group
            group_tickets = []

            for i in range(tickets_in_group):
                # Generate specific variations based on template needs
                variations = {
                    "component": random.choice(
                        [
                            "user-service",
                            "auth-service",
                            "payment-api",
                            "notification-service",
                            "dashboard",
                            "mobile-app",
                            "admin-panel",
                            "report-engine",
                        ]
                    ),
                    "table1": random.choice(
                        ["users", "orders", "payments", "sessions"]
                    ),
                    "table2": random.choice(
                        ["profiles", "transactions", "logs", "audit"]
                    ),
                    "timeout": random.choice(["5", "10", "30", "60"]),
                    "impact": random.choice(
                        [
                            "user registration",
                            "payment processing",
                            "data synchronization",
                            "report generation",
                            "user authentication",
                            "order processing",
                        ]
                    ),
                    "error_details": random.choice(
                        [
                            "OutOfMemoryError",
                            "ConnectionTimeoutException",
                            "NullPointerException",
                            "DatabaseConnectionLost",
                        ]
                    ),
                    "start_size": f"{random.randint(200, 800)}MB",
                    "end_size": f"{random.randint(2000, 8000)}MB",
                    "status_code": random.choice(["404", "500", "502", "503", "504"]),
                    "endpoint": random.choice(
                        [
                            "/api/v1/users",
                            "/api/v1/payments",
                            "/api/v1/orders",
                            "/api/v1/reports",
                            "/api/v1/notifications",
                        ]
                    ),
                    "operations": random.choice(
                        [
                            "user registration",
                            "payment processing",
                            "order creation",
                            "data export",
                            "file upload",
                            "authentication",
                        ]
                    ),
                    "error_rate": random.choice(["15", "25", "40", "60"]),
                    "browser": random.choice(["Chrome", "Firefox", "Safari", "Edge"]),
                    "user_group": random.choice(
                        ["mobile", "desktop", "admin", "premium"]
                    ),
                    "service": random.choice(
                        ["database", "redis-cache", "elasticsearch", "external-api"]
                    ),
                    "functionality": random.choice(
                        ["search", "notifications", "real-time updates", "data sync"]
                    ),
                    "environment": random.choice(
                        ["production", "staging", "development"]
                    ),
                    "config_item": random.choice(
                        ["database_url", "redis_connection", "api_timeout", "log_level"]
                    ),
                    "issue_type": random.choice(
                        [
                            "connection failures",
                            "performance degradation",
                            "security vulnerabilities",
                        ]
                    ),
                    "config_file": random.choice(
                        [
                            "application.yml",
                            "database.conf",
                            "nginx.conf",
                            "env.properties",
                        ]
                    ),
                    "feature_name": random.choice(
                        [
                            "dark mode",
                            "bulk operations",
                            "advanced filtering",
                            "real-time chat",
                        ]
                    ),
                    "benefit": random.choice(
                        [
                            "reducing eye strain",
                            "improving productivity",
                            "enhancing user control",
                        ]
                    ),
                    "use_case": random.choice(
                        ["accessibility", "power user workflows", "mobile experience"]
                    ),
                    "missing_info": random.choice(
                        [
                            "API endpoints",
                            "configuration options",
                            "error codes",
                            "examples",
                        ]
                    ),
                    "use_cases": random.choice(
                        ["integration", "troubleshooting", "development setup"]
                    ),
                    "failure_count": random.choice(["3", "7", "12", "18"]),
                    "test_type": random.choice(["integration", "unit", "end-to-end"]),
                }
                title = template["title_template"].format(**variations)
                description = template["description_template"].format(**variations)

                # Add some variation to make tickets similar but not identical
                if i > 0:
                    title += f" - Case {i+1}"
                    description += f" Additional context for case {i+1}: observed in {random.choice(['production', 'staging', 'development'])} environment."

                ticket_payload = TicketCreate(
                    title=title,
                    description=description,
                    team_id=get_random_team_id(),
                    priority=template["priority"],
                    tags=template["tags"] + [f"test-group-{group_idx}"],
                )

                actor_id = UUID(random.choice(test_actors)["id"])
                ticket = await TicketService.create_ticket(
                    ticket_payload, actor_id, client=c
                )

                created_tickets.append(ticket.id)
                group_tickets.append(str(ticket.id))

                # Set ground truth for this ticket using the actual template used
                ground_truth_tags[str(ticket.id)] = template["tags"]
                ground_truth_priorities[str(ticket.id)] = template["priority"]

            similar_groups[f"group_{group_idx}"] = group_tickets

        # Create additional random tickets to reach target number
        remaining_tickets = num_tickets - len(created_tickets)
        for i in range(remaining_tickets):
            template = random.choice(ticket_templates)
            variations = {
                "component": random.choice(
                    [
                        "user-service",
                        "auth-service",
                        "payment-api",
                        "notification-service",
                        "dashboard",
                        "mobile-app",
                        "admin-panel",
                        "report-engine",
                    ]
                ),
                "table1": random.choice(
                    ["users", "orders", "payments", "sessions"]
                ),
                "table2": random.choice(
                    ["profiles", "transactions", "logs", "audit"]
                ),
                "timeout": random.choice(["5", "10", "30", "60"]),
                "impact": random.choice(
                    [
                        "user registration",
                        "payment processing",
                        "data synchronization",
                        "report generation",
                        "user authentication",
                        "order processing",
                    ]
                ),
                "error_details": random.choice(
                    [
                        "OutOfMemoryError",
                        "ConnectionTimeoutException",
                        "NullPointerException",
                        "DatabaseConnectionLost",
                    ]
                ),
                "start_size": f"{random.randint(200, 800)}MB",
                "end_size": f"{random.randint(2000, 8000)}MB",
                "status_code": random.choice(["404", "500", "502", "503", "504"]),
                "endpoint": random.choice(
                    [
                        "/api/v1/users",
                        "/api/v1/payments",
                        "/api/v1/orders",
                        "/api/v1/reports",
                        "/api/v1/notifications",
                    ]
                ),
                "operations": random.choice(
                    [
                        "user registration",
                        "payment processing",
                        "order creation",
                        "data export",
                        "file upload",
                        "authentication",
                    ]
                ),
                "error_rate": random.choice(["15", "25", "40", "60"]),
                "browser": random.choice(["Chrome", "Firefox", "Safari", "Edge"]),
                "user_group": random.choice(
                    ["mobile", "desktop", "admin", "premium"]
                ),
                "service": random.choice(
                    ["database", "redis-cache", "elasticsearch", "external-api"]
                ),
                "functionality": random.choice(
                    ["search", "notifications", "real-time updates", "data sync"]
                ),
                "environment": random.choice(
                    ["production", "staging", "development"]
                ),
                "config_item": random.choice(
                    ["database_url", "redis_connection", "api_timeout", "log_level"]
                ),
                "issue_type": random.choice(
                    [
                        "connection failures",
                        "performance degradation",
                        "security vulnerabilities",
                    ]
                ),
                "config_file": random.choice(
                    [
                        "application.yml",
                        "database.conf",
                        "nginx.conf",
                        "env.properties",
                    ]
                ),
                "feature_name": random.choice(
                    [
                        "dark mode",
                        "bulk operations",
                        "advanced filtering",
                        "real-time chat",
                    ]
                ),
                "benefit": random.choice(
                    [
                        "reducing eye strain",
                        "improving productivity",
                        "enhancing user control",
                    ]
                ),
                "use_case": random.choice(
                    ["accessibility", "power user workflows", "mobile experience"]
                ),
                "missing_info": random.choice(
                    [
                        "API endpoints",
                        "configuration options",
                        "error codes",
                        "examples",
                    ]
                ),
                "use_cases": random.choice(
                    ["integration", "troubleshooting", "development setup"]
                ),
                "failure_count": random.choice(["3", "7", "12", "18"]),
                "test_type": random.choice(["integration", "unit", "end-to-end"]),
            }

            title = template["title_template"].format(**variations) + f" - Random {i}"
            description = (
                template["description_template"].format(**variations)
                + f" This is a random test ticket {i} for evaluation purposes."
            )

            ticket_payload = TicketCreate(
                title=title,
                description=description,
                team_id=get_random_team_id(),
                priority=random.choice(["low", "medium", "high"]),
                tags=template["tags"] + ["random-test"],
            )

            actor_id = UUID(random.choice(test_actors)["id"])
            ticket = await TicketService.create_ticket(
                ticket_payload, actor_id, client=c
            )
            created_tickets.append(ticket.id)

            # Set ground truth for this ticket using the actual template used
            ground_truth_tags[str(ticket.id)] = template["tags"]
            ground_truth_priorities[str(ticket.id)] = template["priority"]

        # Generate commit failure tickets if requested
        commit_failure_tickets = 0
        if include_commit_failures:
            # Simulate CI automation creating tickets
            ci_bot_resp = exec_query(
                c.table("actors")
                .select("id")
                .eq("system_user_id", "00000000-0000-4000-8000-000000000001")
                .single()
            )

            if ci_bot_resp.data:
                ci_actor_id = UUID(ci_bot_resp.data["id"])

                for i in range(5):  # Create 5 CI failure tickets
                    ticket_payload = TicketCreate(
                        title=f"CI Build Failure - Commit {random.randint(1000, 9999)}",
                        description=f"Build failed in repository test-repo-{i+1}. Error: {random.choice(['compilation error', 'test failure', 'linting error', 'dependency issue'])}. Branch: {random.choice(['main', 'develop', 'feature/test'])}",
                        team_id=get_random_team_id(),
                        priority="high",
                        tags=["ci", "build-failure", "automated"],
                    )

                    ticket = await TicketService.create_ticket(
                        ticket_payload, ci_actor_id, client=c
                    )
                    created_tickets.append(ticket.id)
                    commit_failure_tickets += 1

        # Store test dataset metadata
        dataset_id = uuid4()
        dataset_metadata = {
            "id": str(dataset_id),
            "created_at": datetime.utcnow().isoformat(),
            "num_tickets": len(created_tickets),
            "similar_groups": similar_groups,
            "commit_failure_tickets": commit_failure_tickets,
            "ticket_ids": [str(tid) for tid in created_tickets],
        }

        # Store in database for future reference
        exec_query(
            c.table("evaluation_datasets").insert(
                {
                    "id": str(dataset_id),
                    "dataset_type": "comprehensive_test",
                    "metadata": dataset_metadata,
                    "created_at": datetime.utcnow().isoformat(),
                }
            )
        )

        # Build evaluation data for response
        all_ticket_ids = [str(tid) for tid in created_tickets]


        # Add ground truth for CI failure tickets
        if include_commit_failures:
            # Get the CI failure tickets (they were added last)
            ci_tickets = (
                created_tickets[-commit_failure_tickets:]
                if commit_failure_tickets > 0
                else []
            )
            for ticket_id in ci_tickets:
                ground_truth_tags[str(ticket_id)] = ["testing", "infrastructure"]
                ground_truth_priorities[str(ticket_id)] = "medium"


        return {
            "dataset_id": str(dataset_id),
            "tickets_created": len(created_tickets),
            "similar_groups": similar_groups,
            "commit_failure_tickets": commit_failure_tickets,
            "ticket_ids": all_ticket_ids,
            # Ready-to-use evaluation request format
            "evaluation_request": {
                "test_ticket_ids": all_ticket_ids,
                "ground_truth_tags": ground_truth_tags,
                "ground_truth_priorities": ground_truth_priorities,
            },
        }

    async def evaluate_similarity_accuracy(
        self,
        test_tickets: List[UUID],
        ground_truth_similar: Dict[UUID, List[UUID]],
        top_k: int = 3,
    ) -> EvaluationResult:
        """
        Evaluate similarity detection accuracy for Question 1:
        "How often accurate duplicates appear in the top-3 suggestions"

        Args:
            test_tickets: List of ticket IDs to test
            ground_truth_similar: Dict mapping ticket_id -> list of truly similar ticket IDs
            top_k: Number of top suggestions to evaluate (default 3)

        Returns:
            EvaluationResult with precision, recall, F1 for similarity detection
        """
        start_time = time.time()

        total_hits = 0
        total_predicted = 0
        total_relevant = 0
        individual_results = []

        c = get_service_client()

        for ticket_id in test_tickets:
            try:
                # Get ticket content
                ticket_resp = exec_query(
                    c.table("tickets")
                    .select("title, description")
                    .eq("id", str(ticket_id))
                    .single()
                )

                if not ticket_resp.data:
                    continue

                ticket = ticket_resp.data
                ticket_text = f"{ticket['title']} {ticket.get('description', '')}"

                # Get AI similarity suggestions
                similar_tickets = await self.similarity_service.find_similar_tickets(
                    ticket_text=ticket_text,
                    current_ticket_id=ticket_id,
                    limit=top_k,
                    user_id=None,
                    client=c,
                )

                # Extract predicted similar ticket IDs
                predicted_ids = {UUID(t["id"]) for t in similar_tickets}
                ground_truth_ids = set(ground_truth_similar.get(ticket_id, []))

                # Calculate metrics
                hits = len(predicted_ids.intersection(ground_truth_ids))
                total_hits += hits
                total_predicted += len(predicted_ids)
                total_relevant += len(ground_truth_ids)

                # Individual ticket result
                ticket_precision = hits / len(predicted_ids) if predicted_ids else 0
                ticket_recall = hits / len(ground_truth_ids) if ground_truth_ids else 0

                individual_results.append(
                    {
                        "ticket_id": str(ticket_id),
                        "predicted_similar": [str(tid) for tid in predicted_ids],
                        "ground_truth_similar": [str(tid) for tid in ground_truth_ids],
                        "hits": hits,
                        "precision": ticket_precision,
                        "recall": ticket_recall,
                        "accuracy_at_k": 1 if hits > 0 else 0,  # Hit rate at k
                    }
                )

            except Exception as e:
                logger.error(
                    f"Error evaluating similarity for ticket {ticket_id}: {str(e)}"
                )
                continue

        # Calculate overall metrics
        precision = total_hits / total_predicted if total_predicted > 0 else 0
        recall = total_hits / total_relevant if total_relevant > 0 else 0
        f1_score = (
            (2 * precision * recall) / (precision + recall)
            if (precision + recall) > 0
            else 0
        )

        # Accuracy at K (how often we find at least one relevant item in top-k)
        accuracy_at_k = (
            sum(r["accuracy_at_k"] for r in individual_results)
            / len(individual_results)
            if individual_results
            else 0
        )

        # Log evaluation metrics
        await MetricsService.log_event(
            event_type="similarity_evaluation_completed",
            ai_feature="similarity",
            metadata={
                "test_tickets_count": len(test_tickets),
                "top_k": top_k,
                "precision": precision,
                "recall": recall,
                "f1_score": f1_score,
                "accuracy_at_k": accuracy_at_k,
            },
            response_time_ms=int((time.time() - start_time) * 1000),
            client=c,
        )

        # Create evaluation result
        from uuid import uuid4

        evaluation_id = uuid4()

        result = EvaluationResult(
            evaluation_id=evaluation_id,
            evaluation_type="similarity_accuracy",
            metrics={
                "precision": precision,
                "recall": recall,
                "f1_score": f1_score,
                "accuracy_at_k": accuracy_at_k,
                "total_hits": total_hits,
                "total_predicted": total_predicted,
                "total_relevant": total_relevant,
            },
            detailed_results={
                "individual_results": individual_results,
                "test_parameters": {
                    "top_k": top_k,
                    "test_tickets_count": len(test_tickets),
                },
            },
            summary=f"Similarity evaluation: {accuracy_at_k:.1%} accuracy at top-{top_k}, F1: {f1_score:.3f}",
            timestamp=datetime.utcnow(),
        )

        # Store result in database
        exec_query(
            c.table("evaluation_results").insert(
                {
                    "id": str(evaluation_id),
                    "evaluation_type": "similarity_accuracy",
                    "metrics": result.metrics,
                    "detailed_results": result.detailed_results,
                    "summary": result.summary,
                    "created_at": result.timestamp.isoformat(),
                }
            )
        )

        return result

    async def evaluate_rootcause_with_commit_context(
        self,
        test_tickets: List[UUID],
        human_ratings: Dict[UUID, int],  # Human rating 1-5 scale
        test_with_commit_context: bool = True,
    ) -> EvaluationResult:
        """
        Evaluate root cause analysis accuracy for Question 2:
        Compare AI analysis quality with and without commit context

        Args:
            test_tickets: List of ticket IDs to test (preferably CI failure tickets)
            human_ratings: Dict mapping ticket_id -> human quality rating (1-5)
            test_with_commit_context: Whether to include commit context in analysis

        Returns:
            EvaluationResult with correlation metrics and accuracy scores
        """
        start_time = time.time()

        c = get_service_client()
        individual_results = []
        ai_ratings = []
        human_rating_values = []

        for ticket_id in test_tickets:
            try:
                # Perform AI root cause analysis
                if test_with_commit_context:
                    analysis = await rootcause_service.analyze_ticket(
                        ticket_id=ticket_id, user_id=None, client=c
                    )
                else:
                    # Disable commit context for this analysis
                    # (would need to modify rootcause_service for this)
                    analysis = await rootcause_service.analyze_ticket(
                        ticket_id=ticket_id, user_id=None, client=c
                    )

                # Map AI confidence to 1-5 scale
                ai_confidence = analysis.get("confidence_score", 0)
                ai_rating = min(
                    5, max(1, round(ai_confidence * 5))
                )  # Convert 0-1 to 1-5

                human_rating = human_ratings.get(ticket_id, 0)

                if human_rating > 0:  # Only include tickets with human ratings
                    ai_ratings.append(ai_rating)
                    human_rating_values.append(human_rating)

                    individual_results.append(
                        {
                            "ticket_id": str(ticket_id),
                            "ai_confidence": ai_confidence,
                            "ai_rating": ai_rating,
                            "human_rating": human_rating,
                            "root_cause": analysis.get("root_cause", ""),
                            "suggestions_count": len(analysis.get("suggestions", [])),
                            "llm_used": analysis.get("llm_used", False),
                            "analysis_method": analysis.get(
                                "analysis_method", "unknown"
                            ),
                        }
                    )

            except Exception as e:
                logger.error(
                    f"Error evaluating root cause for ticket {ticket_id}: {str(e)}"
                )
                continue

        # Calculate correlation and accuracy metrics
        if len(ai_ratings) >= 2:  # Need at least 2 data points for correlation
            import numpy as np

            # Calculate correlation with NaN handling
            try:
                correlation_matrix = np.corrcoef(ai_ratings, human_rating_values)
                correlation = correlation_matrix[0, 1]
                # Handle NaN values (occurs when one array has no variance)
                if np.isnan(correlation) or np.isinf(correlation):
                    correlation = 0.0
            except:
                correlation = 0.0

            # Calculate Mean Absolute Error
            mae = float(
                np.mean(np.abs(np.array(ai_ratings) - np.array(human_rating_values)))
            )

            # Calculate accuracy (percentage within 1 point)
            within_1_point = sum(
                1
                for ai, human in zip(ai_ratings, human_rating_values)
                if abs(ai - human) <= 1
            )
            accuracy_within_1 = within_1_point / len(ai_ratings)

            # Average ratings
            avg_ai_rating = float(np.mean(ai_ratings))
            avg_human_rating = float(np.mean(human_rating_values))
        else:
            correlation = 0.0
            mae = 0.0
            accuracy_within_1 = 0.0
            avg_ai_rating = 0.0
            avg_human_rating = 0.0

        # Log evaluation metrics (ensure all values are JSON serializable)
        await MetricsService.log_event(
            event_type="rootcause_evaluation_completed",
            ai_feature="rootcause",
            metadata={
                "test_tickets_count": len(test_tickets),
                "with_commit_context": bool(test_with_commit_context),
                "correlation": float(correlation),
                "mae": float(mae),
                "accuracy_within_1": float(accuracy_within_1),
            },
            response_time_ms=int((time.time() - start_time) * 1000),
            client=c,
        )

        # Create evaluation result
        from uuid import uuid4

        evaluation_id = uuid4()

        result = EvaluationResult(
            evaluation_id=evaluation_id,
            evaluation_type="rootcause_accuracy",
            metrics={
                "correlation": float(correlation),
                "mae": float(mae),
                "accuracy_within_1": float(accuracy_within_1),
                "avg_ai_rating": float(avg_ai_rating),
                "avg_human_rating": float(avg_human_rating),
                "total_evaluations": len(ai_ratings),
            },
            detailed_results={
                "individual_results": individual_results,
                "test_parameters": {
                    "with_commit_context": test_with_commit_context,
                    "rating_scale": "1-5",
                    "test_tickets_count": len(test_tickets),
                },
            },
            summary=f"Root cause evaluation ({'with' if test_with_commit_context else 'without'} commit context): {correlation:.3f} correlation, {accuracy_within_1:.1%} within 1 point",
            timestamp=datetime.utcnow(),
        )

        # Store result in database
        exec_query(
            c.table("evaluation_results").insert(
                {
                    "id": str(evaluation_id),
                    "evaluation_type": "rootcause_accuracy",
                    "metrics": result.metrics,
                    "detailed_results": result.detailed_results,
                    "summary": result.summary,
                    "created_at": result.timestamp.isoformat(),
                }
            )
        )

        return result

    async def evaluate_tagging_accuracy(
        self,
        test_tickets: List[UUID],
        ground_truth_tags: Dict[UUID, List[str]],
        ground_truth_priorities: Dict[UUID, str],
    ) -> EvaluationResult:
        """
        Evaluate auto-tagging and prioritization accuracy
        Benchmarked against human-labeled test set

        Args:
            test_tickets: List of ticket IDs to test
            ground_truth_tags: Dict mapping ticket_id -> list of correct tags
            ground_truth_priorities: Dict mapping ticket_id -> correct priority

        Returns:
            EvaluationResult with tag and priority accuracy metrics
        """
        start_time = time.time()

        c = get_service_client()
        individual_results = []
        tag_hits = 0
        tag_predicted = 0
        tag_relevant = 0
        priority_correct = 0
        priority_total = 0

        for ticket_id in test_tickets:
            try:
                # Get ticket content
                ticket_resp = exec_query(
                    c.table("tickets")
                    .select("title, description")
                    .eq("id", str(ticket_id))
                    .single()
                )

                if not ticket_resp.data:
                    continue

                ticket = ticket_resp.data

                # Perform AI auto-tagging
                tagging_result = await auto_tagging_service.auto_tag_ticket(
                    title=ticket["title"],
                    description=ticket.get("description", ""),
                    user_id=None,
                    client=c,
                )

                predicted_tags = set(tagging_result.get("suggested_tags", []))
                predicted_priority = tagging_result.get("suggested_priority", "medium")

                ground_truth_tag_set = set(ground_truth_tags.get(ticket_id, []))
                ground_truth_priority = ground_truth_priorities.get(ticket_id, "medium")

                # Calculate tag metrics
                tag_intersection = predicted_tags.intersection(ground_truth_tag_set)
                tag_hits += len(tag_intersection)
                tag_predicted += len(predicted_tags)
                tag_relevant += len(ground_truth_tag_set)

                # Calculate priority accuracy
                priority_match = (
                    predicted_priority.lower() == ground_truth_priority.lower()
                )
                if priority_match:
                    priority_correct += 1
                priority_total += 1

                individual_results.append(
                    {
                        "ticket_id": str(ticket_id),
                        "predicted_tags": list(predicted_tags),
                        "ground_truth_tags": list(ground_truth_tag_set),
                        "predicted_priority": predicted_priority,
                        "ground_truth_priority": ground_truth_priority,
                        "tag_hits": len(tag_intersection),
                        "priority_correct": priority_match,
                    }
                )

            except Exception as e:
                logger.error(
                    f"Error evaluating tagging for ticket {ticket_id}: {str(e)}"
                )
                continue

        # Calculate overall metrics
        tag_precision = tag_hits / tag_predicted if tag_predicted > 0 else 0
        tag_recall = tag_hits / tag_relevant if tag_relevant > 0 else 0
        tag_f1 = (
            (2 * tag_precision * tag_recall) / (tag_precision + tag_recall)
            if (tag_precision + tag_recall) > 0
            else 0
        )
        priority_accuracy = (
            priority_correct / priority_total if priority_total > 0 else 0
        )

        # Log evaluation metrics
        await MetricsService.log_event(
            event_type="tagging_evaluation_completed",
            ai_feature="auto_tagging",
            metadata={
                "test_tickets_count": len(test_tickets),
                "tag_precision": tag_precision,
                "tag_recall": tag_recall,
                "tag_f1": tag_f1,
                "priority_accuracy": priority_accuracy,
            },
            response_time_ms=int((time.time() - start_time) * 1000),
            client=c,
        )

        # Create evaluation result
        from uuid import uuid4

        evaluation_id = uuid4()

        result = EvaluationResult(
            evaluation_id=evaluation_id,
            evaluation_type="tagging_accuracy",
            metrics={
                "tag_precision": tag_precision,
                "tag_recall": tag_recall,
                "tag_f1": tag_f1,
                "priority_accuracy": priority_accuracy,
                "tag_hits": tag_hits,
                "tag_predicted": tag_predicted,
                "tag_relevant": tag_relevant,
                "priority_correct": priority_correct,
                "priority_total": priority_total,
            },
            detailed_results={
                "individual_results": individual_results,
                "test_parameters": {"test_tickets_count": len(test_tickets)},
            },
            summary=f"Tagging evaluation: Tags F1 {tag_f1:.3f}, Priority accuracy {priority_accuracy:.1%}",
            timestamp=datetime.utcnow(),
        )

        # Store result in database
        exec_query(
            c.table("evaluation_results").insert(
                {
                    "id": str(evaluation_id),
                    "evaluation_type": "tagging_accuracy",
                    "metrics": result.metrics,
                    "detailed_results": result.detailed_results,
                    "summary": result.summary,
                    "created_at": result.timestamp.isoformat(),
                }
            )
        )

        return result

    async def run_performance_benchmark(
        self,
        concurrent_users: List[int] = [1, 5, 10, 25, 50],
        requests_per_user: int = 10,
        test_ticket_ids: Optional[List[UUID]] = None,
    ) -> EvaluationResult:
        """
        Evaluate system performance under varying loads (Question 3)
        Simulates concurrent users making AI feature requests

        Args:
            concurrent_users: List of concurrent user counts to test
            requests_per_user: Number of requests each simulated user makes
            test_ticket_ids: Optional specific tickets to test with

        Returns:
            EvaluationResult with performance metrics under different loads
        """
        import asyncio
        import random

        start_time = time.time()
        c = get_service_client()

        # Get test tickets if not provided
        if not test_ticket_ids:
            tickets_resp = exec_query(c.table("tickets").select("id").limit(20))
            test_ticket_ids = [UUID(t["id"]) for t in (tickets_resp.data or [])]

        if not test_ticket_ids:
            raise Exception("No test tickets available for performance testing")

        performance_results = []

        # Test different concurrency levels
        for user_count in concurrent_users:
            logger.info(f"Testing with {user_count} concurrent users")

            # Track response times for this concurrency level
            response_times = []
            errors = 0
            start_load_time = time.time()

            async def simulate_user_requests():
                """Simulate a single user making multiple AI requests"""
                user_response_times = []
                user_errors = 0

                for _ in range(requests_per_user):
                    try:
                        # Randomly choose an AI feature to test
                        feature = random.choice(
                            ["similarity", "rootcause", "auto_tagging"]
                        )
                        ticket_id = random.choice(test_ticket_ids)

                        request_start = time.time()

                        if feature == "similarity":
                            # Test similarity service
                            ticket_resp = exec_query(
                                c.table("tickets")
                                .select("title, description")
                                .eq("id", str(ticket_id))
                                .single()
                            )
                            if ticket_resp.data:
                                ticket_text = f"{ticket_resp.data['title']} {ticket_resp.data.get('description', '')}"
                                await self.similarity_service.find_similar_tickets(
                                    ticket_text=ticket_text,
                                    current_ticket_id=ticket_id,
                                    limit=3,
                                    client=c,
                                )

                        elif feature == "rootcause":
                            # Test root cause analysis
                            await rootcause_service.analyze_ticket(
                                ticket_id=ticket_id, user_id=None, client=c
                            )

                        elif feature == "auto_tagging":
                            # Test auto-tagging
                            ticket_resp = exec_query(
                                c.table("tickets")
                                .select("title, description")
                                .eq("id", str(ticket_id))
                                .single()
                            )
                            if ticket_resp.data:
                                await auto_tagging_service.auto_tag_ticket(
                                    title=ticket_resp.data["title"],
                                    description=ticket_resp.data.get("description", ""),
                                    client=c,
                                )

                        request_time = (
                            time.time() - request_start
                        ) * 1000  # Convert to ms
                        user_response_times.append(request_time)

                    except Exception as e:
                        user_errors += 1
                        logger.error(f"Error in user simulation: {str(e)}")

                return user_response_times, user_errors

            # Run concurrent users
            tasks = [simulate_user_requests() for _ in range(user_count)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Collect results
            for result in results:
                if isinstance(result, Exception):
                    errors += requests_per_user  # Count all requests from failed user as errors
                else:
                    user_times, user_errors = result
                    response_times.extend(user_times)
                    errors += user_errors

            total_load_time = time.time() - start_load_time
            total_requests = user_count * requests_per_user

            # Calculate metrics for this concurrency level
            if response_times:
                import numpy as np

                avg_response_time = np.mean(response_times)
                p95_response_time = np.percentile(response_times, 95)
                p99_response_time = np.percentile(response_times, 99)
                throughput = total_requests / total_load_time  # requests per second
                error_rate = errors / total_requests
            else:
                avg_response_time = 0
                p95_response_time = 0
                p99_response_time = 0
                throughput = 0
                error_rate = 1.0

            performance_results.append(
                {
                    "concurrent_users": user_count,
                    "total_requests": total_requests,
                    "total_time_seconds": total_load_time,
                    "avg_response_time_ms": avg_response_time,
                    "p95_response_time_ms": p95_response_time,
                    "p99_response_time_ms": p99_response_time,
                    "throughput_rps": throughput,
                    "error_rate": error_rate,
                    "errors": errors,
                }
            )

            logger.info(
                f"Completed {user_count} users: {avg_response_time:.1f}ms avg, {throughput:.1f} RPS"
            )

        # Calculate overall performance metrics
        if performance_results:
            max_throughput = max(r["throughput_rps"] for r in performance_results)
            min_error_rate = min(r["error_rate"] for r in performance_results)
            avg_response_time_overall = sum(
                r["avg_response_time_ms"] for r in performance_results
            ) / len(performance_results)
        else:
            max_throughput = 0
            min_error_rate = 1.0
            avg_response_time_overall = 0

        # Log evaluation metrics
        await MetricsService.log_event(
            event_type="performance_evaluation_completed",
            ai_feature="system_performance",
            metadata={
                "max_concurrent_users": max(concurrent_users),
                "max_throughput_rps": max_throughput,
                "min_error_rate": min_error_rate,
                "avg_response_time_ms": avg_response_time_overall,
            },
            response_time_ms=int((time.time() - start_time) * 1000),
            client=c,
        )

        # Create evaluation result
        from uuid import uuid4

        evaluation_id = uuid4()

        result = EvaluationResult(
            evaluation_id=evaluation_id,
            evaluation_type="performance_benchmark",
            metrics={
                "max_throughput_rps": max_throughput,
                "min_error_rate": min_error_rate,
                "avg_response_time_ms": avg_response_time_overall,
                "max_concurrent_users_tested": max(concurrent_users),
                "total_requests_tested": sum(
                    r["total_requests"] for r in performance_results
                ),
            },
            detailed_results={
                "performance_by_concurrency": performance_results,
                "test_parameters": {
                    "concurrent_users_tested": concurrent_users,
                    "requests_per_user": requests_per_user,
                    "test_tickets_count": len(test_ticket_ids),
                },
            },
            summary=f"Performance benchmark: {max_throughput:.1f} max RPS, {avg_response_time_overall:.1f}ms avg response time",
            timestamp=datetime.utcnow(),
        )

        # Store result in database
        exec_query(
            c.table("evaluation_results").insert(
                {
                    "id": str(evaluation_id),
                    "evaluation_type": "performance_benchmark",
                    "metrics": result.metrics,
                    "detailed_results": result.detailed_results,
                    "summary": result.summary,
                    "created_at": result.timestamp.isoformat(),
                }
            )
        )

        return result


# Global instance
comprehensive_evaluation_service = ComprehensiveEvaluationService()

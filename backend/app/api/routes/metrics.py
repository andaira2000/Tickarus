from fastapi import APIRouter, Depends, Query
from typing import Dict, Any
from uuid import UUID
from app.api.dependencies import get_current_user_id
from app.services.metrics_service import MetricsService

router = APIRouter()


@router.get("/similarity", response_model=Dict[str, Any])
async def get_similarity_metrics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get similarity feature performance metrics"""
    return await MetricsService.get_similarity_metrics(days=days)


@router.get("/rootcause", response_model=Dict[str, Any])
async def get_rootcause_metrics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get root cause analysis performance metrics"""
    return await MetricsService.get_rootcause_metrics(days=days)


@router.get("/performance", response_model=Dict[str, Any])
async def get_performance_metrics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get overall AI feature performance metrics"""
    return await MetricsService.get_performance_metrics(days=days)


@router.post("/feedback")
async def submit_ai_feedback(
    event_type: str,
    ai_feature: str,
    user_rating: int,
    ticket_id: UUID = None,
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Submit user feedback for AI features"""
    await MetricsService.log_event(
        event_type=event_type,
        ticket_id=ticket_id,
        user_id=current_user_id,
        ai_feature=ai_feature,
        user_rating=user_rating,
    )
    return {"message": "Feedback submitted successfully"}


@router.post("/synthetic-data/generate")
async def generate_synthetic_tickets(
    count: int = Query(50, ge=10, le=200, description="Number of tickets to generate"),
    include_similar_pairs: bool = Query(
        True, description="Include intentionally similar tickets"
    ),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Generate synthetic ticket data for AI evaluation"""
    from app.services.synthetic_data_service import synthetic_data_service

    result = await synthetic_data_service.generate_ticket_set(
        count=count, include_similar_pairs=include_similar_pairs
    )

    return result


@router.post("/evaluate/similarity")
async def evaluate_similarity_accuracy(
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Evaluate similarity detection accuracy using synthetic data"""
    from app.services.synthetic_data_service import synthetic_data_service
    from app.db.database import get_service_client, exec_query

    # Get recent synthetic tickets (those created by system actors)
    c = get_service_client()
    tickets_resp = exec_query(
        c.table("tickets")
        .select("id, actor_id, actors!inner(actor_type)")
        .eq("actors.actor_type", "system")
        .order("created_at", desc=True)
        .limit(50)
    )

    if not tickets_resp.data:
        return {"error": "No synthetic tickets found. Generate some first."}

    ticket_ids = [t["id"] for t in tickets_resp.data]

    # For evaluation, we'll create a simple ground truth based on ticket content
    # In a real scenario, this would come from the generation metadata
    ground_truth = []
    for ticket_id in ticket_ids:
        # Simple categorization based on ticket content
        ticket_resp = exec_query(
            c.table("tickets").select("title, description").eq("id", ticket_id).single()
        )

        if ticket_resp.data:
            content = (
                f"{ticket_resp.data['title']} {ticket_resp.data['description']}".lower()
            )

            if "database" in content or "db" in content:
                category = "database"
                similar_group = "db_connectivity"
            elif "memory" in content or "oom" in content:
                category = "memory"
                similar_group = "memory_issues"
            elif "slow" in content or "performance" in content:
                category = "performance"
                similar_group = "performance_issues"
            elif "auth" in content or "login" in content:
                category = "authentication"
                similar_group = "auth_issues"
            elif "404" in content or "not found" in content:
                category = "missing_resources"
                similar_group = "missing_resources"
            else:
                category = "server_errors"
                similar_group = "server_errors"

            ground_truth.append(
                {
                    "ticket_id": ticket_id,
                    "category": category,
                    "similar_group": similar_group,
                }
            )

    result = await synthetic_data_service.evaluate_similarity_accuracy(
        ticket_ids=ticket_ids, ground_truth=ground_truth
    )

    return result


@router.get("/evaluation/tasks")
async def get_evaluation_tasks(
    task_type: str = Query(
        "similarity", description="Type of evaluation task (similarity, rootcause)"
    ),
    limit: int = Query(10, ge=1, le=50, description="Number of tasks to return"),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get AI predictions that need human evaluation"""
    from app.services.evaluation_service import evaluation_service

    tasks = await evaluation_service.get_evaluation_tasks(
        user_id=current_user_id, task_type=task_type, limit=limit
    )

    return {"task_type": task_type, "tasks": tasks, "count": len(tasks)}


@router.post("/evaluation/submit")
async def submit_evaluation(
    task_id: str,
    task_type: str,
    evaluation: Dict[str, Any],
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Submit human evaluation of AI prediction"""
    from app.services.evaluation_service import evaluation_service

    result = await evaluation_service.submit_evaluation(
        task_id=task_id,
        user_id=current_user_id,
        task_type=task_type,
        evaluation=evaluation,
    )

    return result


@router.get("/evaluation/stats")
async def get_evaluation_stats(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user_id: UUID = Depends(get_current_user_id),
):
    """Get evaluation statistics"""
    from app.services.evaluation_service import evaluation_service

    stats = await evaluation_service.get_evaluation_stats(days=days)
    return stats

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
from uuid import UUID
from pydantic import BaseModel

from app.auth.auth import get_current_user
from app.services.comprehensive_evaluation_service import comprehensive_evaluation_service, EvaluationResult
from app.db.database import get_service_client

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


class SimilarityEvaluationRequest(BaseModel):
    test_ticket_ids: List[UUID]
    ground_truth_similar: Dict[str, List[str]]  # UUID as string keys
    top_k: int = 3


class RootCauseEvaluationRequest(BaseModel):
    test_ticket_ids: List[UUID]
    human_ratings: Dict[str, int]  # UUID as string keys, rating 1-5
    test_with_commit_context: bool = True


class TaggingEvaluationRequest(BaseModel):
    test_ticket_ids: List[UUID]
    ground_truth_tags: Dict[str, List[str]]  # UUID as string keys
    ground_truth_priorities: Dict[str, str]  # UUID as string keys


class PerformanceEvaluationRequest(BaseModel):
    concurrent_users: List[int] = [1, 5, 10, 25, 50]
    requests_per_user: int = 10
    test_ticket_ids: Optional[List[UUID]] = None


class TestDataGenerationRequest(BaseModel):
    num_tickets: int = 50
    num_similar_groups: int = 10
    include_commit_failures: bool = True


@router.post("/similarity", response_model=Dict[str, Any])
async def evaluate_similarity_accuracy(
    request: SimilarityEvaluationRequest,
    current_user=Depends(get_current_user)
):
    """Evaluate similarity detection accuracy (Research Question 1)"""
    try:
        # Convert string keys back to UUIDs
        ground_truth_similar = {
            UUID(k): [UUID(tid) for tid in v]
            for k, v in request.ground_truth_similar.items()
        }

        result = await comprehensive_evaluation_service.evaluate_similarity_accuracy(
            test_tickets=request.test_ticket_ids,
            ground_truth_similar=ground_truth_similar,
            top_k=request.top_k
        )

        return {
            "evaluation_type": "similarity_accuracy",
            "metrics": result.metrics,
            "detailed_results": result.detailed_results,
            "summary": result.summary,
            "evaluation_id": str(result.evaluation_id)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


@router.post("/rootcause", response_model=Dict[str, Any])
async def evaluate_rootcause_accuracy(
    request: RootCauseEvaluationRequest,
    current_user=Depends(get_current_user)
):
    """Evaluate root cause analysis accuracy (Research Question 2)"""
    try:
        # Convert string keys back to UUIDs
        human_ratings = {
            UUID(k): v for k, v in request.human_ratings.items()
        }

        result = await comprehensive_evaluation_service.evaluate_rootcause_with_commit_context(
            test_tickets=request.test_ticket_ids,
            human_ratings=human_ratings,
            test_with_commit_context=request.test_with_commit_context
        )

        return {
            "evaluation_type": "rootcause_accuracy",
            "metrics": result.metrics,
            "detailed_results": result.detailed_results,
            "summary": result.summary,
            "evaluation_id": str(result.evaluation_id)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


@router.post("/tagging", response_model=Dict[str, Any])
async def evaluate_tagging_accuracy(
    request: TaggingEvaluationRequest,
    current_user=Depends(get_current_user)
):
    """Evaluate auto-tagging and prioritization accuracy (Research Question 3)"""
    try:
        # Convert string keys back to UUIDs
        ground_truth_tags = {
            UUID(k): v for k, v in request.ground_truth_tags.items()
        }
        ground_truth_priorities = {
            UUID(k): v for k, v in request.ground_truth_priorities.items()
        }

        result = await comprehensive_evaluation_service.evaluate_tagging_accuracy(
            test_tickets=request.test_ticket_ids,
            ground_truth_tags=ground_truth_tags,
            ground_truth_priorities=ground_truth_priorities
        )

        return {
            "evaluation_type": "tagging_accuracy",
            "metrics": result.metrics,
            "detailed_results": result.detailed_results,
            "summary": result.summary,
            "evaluation_id": str(result.evaluation_id)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


@router.post("/performance", response_model=Dict[str, Any])
async def evaluate_performance(
    request: PerformanceEvaluationRequest,
    current_user=Depends(get_current_user)
):
    """Evaluate system performance under load (Research Question 3)"""
    try:
        result = await comprehensive_evaluation_service.run_performance_benchmark(
            concurrent_users=request.concurrent_users,
            requests_per_user=request.requests_per_user,
            test_ticket_ids=request.test_ticket_ids
        )

        return {
            "evaluation_type": "performance_benchmark",
            "metrics": result.metrics,
            "detailed_results": result.detailed_results,
            "summary": result.summary,
            "evaluation_id": str(result.evaluation_id)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


@router.post("/generate-test-data", response_model=Dict[str, Any])
async def generate_test_data(
    request: TestDataGenerationRequest,
    current_user=Depends(get_current_user)
):
    """Generate synthetic test data for dissertation evaluation"""
    try:
        result = await comprehensive_evaluation_service.generate_test_dataset(
            num_tickets=request.num_tickets,
            num_similar_groups=request.num_similar_groups,
            include_commit_failures=request.include_commit_failures
        )

        return {
            "message": "Test data generated successfully",
            "tickets_created": result["tickets_created"],
            "similar_groups": result["similar_groups"],
            "commit_failure_tickets": result.get("commit_failure_tickets", 0),
            "test_dataset_id": result["dataset_id"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test data generation failed: {str(e)}")


@router.get("/results/{evaluation_id}")
async def get_evaluation_results(
    evaluation_id: UUID,
    current_user=Depends(get_current_user)
):
    """Retrieve stored evaluation results"""
    try:
        c = get_service_client()
        from app.db.database import exec_query

        resp = exec_query(
            c.table("evaluation_results")
            .select("*")
            .eq("id", str(evaluation_id))
            .single()
        )

        if not resp.data:
            raise HTTPException(status_code=404, detail="Evaluation results not found")

        return resp.data

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve results: {str(e)}")


@router.get("/summary")
async def get_evaluation_summary(
    current_user=Depends(get_current_user)
):
    """Get summary of all evaluation runs for dissertation report"""
    try:
        c = get_service_client()
        from app.db.database import exec_query

        resp = exec_query(
            c.table("evaluation_results")
            .select("id, evaluation_type, created_at, metrics, summary")
            .order("created_at", desc=True)
            .limit(50)
        )

        evaluations = resp.data or []

        # Aggregate summary statistics
        summary_stats = {
            "total_evaluations": len(evaluations),
            "by_type": {},
            "recent_results": evaluations[:10]
        }

        for eval_result in evaluations:
            eval_type = eval_result.get("evaluation_type", "unknown")
            if eval_type not in summary_stats["by_type"]:
                summary_stats["by_type"][eval_type] = 0
            summary_stats["by_type"][eval_type] += 1

        return summary_stats

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get summary: {str(e)}")
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
from uuid import UUID
from pydantic import BaseModel

from app.api.dependencies import get_current_user
from app.services.evaluation_service import (
    evaluation_service,
)

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


class SimilarityEvaluationRequest(BaseModel):
    test_ticket_ids: List[UUID]
    ground_truth_similar: Dict[str, List[str]]
    top_k: int = 3


class RootCauseEvaluationRequest(BaseModel):
    test_ticket_ids: List[UUID]
    human_ratings: Dict[str, int]
    test_with_commit_context: bool = True


class TaggingEvaluationRequest(BaseModel):
    test_ticket_ids: List[UUID]
    ground_truth_tags: Dict[str, List[str]]
    ground_truth_priorities: Dict[str, str]


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
    request: SimilarityEvaluationRequest, current_user=Depends(get_current_user)
):
    """Evaluate similarity detection accuracy"""
    try:
        ground_truth_similar = {
            UUID(k): [UUID(tid) for tid in v]
            for k, v in request.ground_truth_similar.items()
        }

        result = await evaluation_service.evaluate_similarity_accuracy(
            test_tickets=request.test_ticket_ids,
            ground_truth_similar=ground_truth_similar,
            top_k=request.top_k,
        )

        return {
            "evaluation_type": "similarity_accuracy",
            "metrics": result.metrics,
            "detailed_results": result.detailed_results,
            "summary": result.summary,
            "evaluation_id": str(result.evaluation_id),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


@router.post("/tagging", response_model=Dict[str, Any])
async def evaluate_tagging_accuracy(
    request: TaggingEvaluationRequest, current_user=Depends(get_current_user)
):
    """Evaluate auto-tagging and prioritization accuracy"""
    try:
        ground_truth_tags = {UUID(k): v for k, v in request.ground_truth_tags.items()}
        ground_truth_priorities = {
            UUID(k): v for k, v in request.ground_truth_priorities.items()
        }

        result = await evaluation_service.evaluate_tagging_accuracy(
            test_tickets=request.test_ticket_ids,
            ground_truth_tags=ground_truth_tags,
            ground_truth_priorities=ground_truth_priorities,
        )

        return {
            "evaluation_type": "tagging_accuracy",
            "metrics": result.metrics,
            "detailed_results": result.detailed_results,
            "summary": result.summary,
            "evaluation_id": str(result.evaluation_id),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


@router.post("/performance", response_model=Dict[str, Any])
async def evaluate_performance(
    request: PerformanceEvaluationRequest, current_user=Depends(get_current_user)
):
    """Evaluate system performance under load."""
    try:
        result = await evaluation_service.run_performance_benchmark(
            concurrent_users=request.concurrent_users,
            requests_per_user=request.requests_per_user,
            test_ticket_ids=request.test_ticket_ids,
        )

        return {
            "evaluation_type": "performance_benchmark",
            "metrics": result.metrics,
            "detailed_results": result.detailed_results,
            "summary": result.summary,
            "evaluation_id": str(result.evaluation_id),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")


@router.post("/generate-test-data", response_model=Dict[str, Any])
async def generate_test_data(
    request: TestDataGenerationRequest, current_user=Depends(get_current_user)
):
    """Generate synthetic test data"""
    try:
        return await evaluation_service.generate_test_dataset(
            num_tickets=request.num_tickets,
            num_similar_groups=request.num_similar_groups,
            include_commit_failures=request.include_commit_failures,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Test data generation failed: {str(e)}"
        )

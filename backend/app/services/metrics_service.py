from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta, timezone

from app.db.database import get_service_client
from app.models.ai_metrics import AIMetricsCreate, AIMetrics


class MetricsService:
    @staticmethod
    async def log_event(
        event_type: str,
        ticket_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        ai_feature: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        user_rating: Optional[int] = None,
        response_time_ms: Optional[int] = None,
    ) -> AIMetrics:
        """Log an AI metrics event"""
        supabase_client = get_service_client()

        metrics_data = AIMetricsCreate(
            event_type=event_type,
            ticket_id=str(ticket_id) if ticket_id else None,
            user_id=str(user_id) if user_id else None,
            ai_feature=ai_feature,
            metadata=metadata,
            user_rating=user_rating,
            response_time_ms=response_time_ms,
        )

        metrics = (
            await supabase_client.table("ai_metrics")
            .insert(metrics_data.model_dump(), returning="representation")
            .execute()
        ).data[0]

        return AIMetrics(**metrics)

    @staticmethod
    async def get_similarity_metrics(days: int = 30) -> Dict[str, Any]:
        """Get similarity feature metrics for the last N days."""
        supabase_client = get_service_client()

        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        shown_total = (
            await supabase_client.table("ai_metrics")
            .select("*", count="exact")
            .eq("event_type", "similarity_shown")
            .eq("ai_feature", "similarity")
            .gte("created_at", cutoff_date)
            .execute()
        ).count

        clicked_total = (
            await supabase_client.table("ai_metrics")
            .select("*", count="exact")
            .eq("event_type", "similarity_clicked")
            .eq("ai_feature", "similarity")
            .gte("created_at", cutoff_date)
            .execute()
        ).count

        total_shown = shown_total or 0
        total_clicked = clicked_total or 0

        click_rate = (total_clicked / total_shown * 100) if total_shown > 0 else 0

        return {
            "total_suggestions_shown": total_shown,
            "total_suggestions_clicked": total_clicked,
            "click_through_rate": round(click_rate, 2),
            "period_days": days,
        }

    @staticmethod
    async def get_rootcause_metrics(days: int = 30) -> Dict[str, Any]:
        """Get root cause analysis metrics for the last N days"""
        supabase_client = get_service_client()

        cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()

        ratings = (
            await supabase_client.table("ai_metrics")
            .select("user_rating")
            .eq("ai_feature", "rootcause")
            .not_.is_("user_rating", "null")
            .gte("created_at", cutoff_date)
            .execute()
        ).data

        total = (
            await supabase_client.table("ai_metrics")
            .select("*", count="exact")
            .eq("event_type", "rootcause_requested")
            .eq("ai_feature", "rootcause")
            .gte("created_at", cutoff_date)
            .execute()
        ).count

        ratings = [row["user_rating"] for row in ratings]
        total_requests = total.count or 0

        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        positive_ratings = len([r for r in ratings if r >= 3]) if ratings else 0
        positive_rate = (positive_ratings / len(ratings) * 100) if ratings else 0

        return {
            "total_analyses_requested": total_requests,
            "total_ratings_given": len(ratings),
            "average_rating": round(avg_rating, 2),
            "positive_rating_percentage": round(positive_rate, 2),
            "period_days": days,
        }

    @staticmethod
    async def get_performance_metrics(days: int = 30) -> Dict[str, Any]:
        """Get performance metrics for all AI features"""
        supabase_client = get_service_client()

        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        performance_metrics = (
            await supabase_client.table("ai_metrics")
            .select("response_time_ms, ai_feature")
            .not_.is_("response_time_ms", "null")
            .gte("created_at", cutoff_date)
            .execute()
        ).data

        response_times = [metric["response_time_ms"] for metric in performance_metrics]

        if not response_times:
            return {
                "average_response_time_ms": 0,
                "p95_response_time_ms": 0,
                "total_requests": 0,
                "period_days": days,
            }

        response_times.sort()
        avg_time = sum(response_times) / len(response_times)
        p95_index = int(len(response_times) * 0.95)
        p95_time = (
            response_times[p95_index]
            if p95_index < len(response_times)
            else response_times[-1]
        )

        return {
            "average_response_time_ms": round(avg_time, 2),
            "p95_response_time_ms": p95_time,
            "total_requests": len(response_times),
            "period_days": days,
        }

from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime, timedelta
from app.db.database import get_supabase, get_service_client, exec_query, exec_single
from app.models.ai_metrics import AIMetricsCreate, AIMetrics


class MetricsService:
    @staticmethod
    def _c():
        return get_supabase()
    
    @classmethod
    async def log_event(
        cls,
        event_type: str,
        ticket_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        ai_feature: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        user_rating: Optional[int] = None,
        response_time_ms: Optional[int] = None,
        client=None
    ) -> AIMetrics:
        """Log an AI metrics event"""
        c = client or cls._c()
        
        metrics_data = AIMetricsCreate(
            event_type=event_type,
            ticket_id=ticket_id,
            user_id=user_id,
            ai_feature=ai_feature,
            metadata=metadata,
            user_rating=user_rating,
            response_time_ms=response_time_ms
        )
        
        payload = {
            "event_type": metrics_data.event_type,
            "ticket_id": str(metrics_data.ticket_id) if metrics_data.ticket_id else None,
            "user_id": str(metrics_data.user_id) if metrics_data.user_id else None,
            "ai_feature": metrics_data.ai_feature,
            "metadata": metrics_data.metadata,
            "user_rating": metrics_data.user_rating,
            "response_time_ms": metrics_data.response_time_ms,
        }
        
        resp = exec_query(
            c.table("ai_metrics").insert(payload, returning="representation")
        )
        
        if not resp.data:
            raise Exception("Failed to log metrics event")
        
        return AIMetrics(**resp.data[0])
    
    @classmethod
    async def get_similarity_metrics(cls, days: int = 30) -> Dict[str, Any]:
        """Get similarity feature metrics for the last N days"""
        c = get_service_client()  # Use service client for analytics
        
        cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        # Get total suggestions shown
        shown_resp = exec_query(
            c.table("ai_metrics")
            .select("*", count="exact")
            .eq("event_type", "similarity_shown")
            .eq("ai_feature", "similarity")
            .gte("created_at", cutoff_date)
        )
        
        # Get total suggestions clicked
        clicked_resp = exec_query(
            c.table("ai_metrics")
            .select("*", count="exact")
            .eq("event_type", "similarity_clicked")
            .eq("ai_feature", "similarity")
            .gte("created_at", cutoff_date)
        )
        
        total_shown = getattr(shown_resp, "count", 0) or 0
        total_clicked = getattr(clicked_resp, "count", 0) or 0
        
        click_rate = (total_clicked / total_shown * 100) if total_shown > 0 else 0
        
        return {
            "total_suggestions_shown": total_shown,
            "total_suggestions_clicked": total_clicked,
            "click_through_rate": round(click_rate, 2),
            "period_days": days
        }
    
    @classmethod
    async def get_rootcause_metrics(cls, days: int = 30) -> Dict[str, Any]:
        """Get root cause analysis metrics for the last N days"""
        c = get_service_client()
        
        cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        # Get all root cause analysis events with ratings
        ratings_resp = exec_query(
            c.table("ai_metrics")
            .select("user_rating")
            .eq("ai_feature", "rootcause")
            .not_.is_("user_rating", "null")
            .gte("created_at", cutoff_date)
        )
        
        # Get total analyses requested
        total_resp = exec_query(
            c.table("ai_metrics")
            .select("*", count="exact")
            .eq("event_type", "rootcause_requested")
            .eq("ai_feature", "rootcause")
            .gte("created_at", cutoff_date)
        )
        
        ratings = [row["user_rating"] for row in (ratings_resp.data or [])]
        total_requests = getattr(total_resp, "count", 0) or 0
        
        avg_rating = sum(ratings) / len(ratings) if ratings else 0
        positive_ratings = len([r for r in ratings if r >= 3]) if ratings else 0
        positive_rate = (positive_ratings / len(ratings) * 100) if ratings else 0
        
        return {
            "total_analyses_requested": total_requests,
            "total_ratings_given": len(ratings),
            "average_rating": round(avg_rating, 2),
            "positive_rating_percentage": round(positive_rate, 2),
            "period_days": days
        }
    
    @classmethod
    async def get_performance_metrics(cls, days: int = 30) -> Dict[str, Any]:
        """Get performance metrics for all AI features"""
        c = get_service_client()
        
        cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        # Get all events with response times
        perf_resp = exec_query(
            c.table("ai_metrics")
            .select("response_time_ms, ai_feature")
            .not_.is_("response_time_ms", "null")
            .gte("created_at", cutoff_date)
        )
        
        response_times = [row["response_time_ms"] for row in (perf_resp.data or [])]
        
        if not response_times:
            return {
                "average_response_time_ms": 0,
                "p95_response_time_ms": 0,
                "total_requests": 0,
                "period_days": days
            }
        
        response_times.sort()
        avg_time = sum(response_times) / len(response_times)
        p95_index = int(len(response_times) * 0.95)
        p95_time = response_times[p95_index] if p95_index < len(response_times) else response_times[-1]
        
        return {
            "average_response_time_ms": round(avg_time, 2),
            "p95_response_time_ms": p95_time,
            "total_requests": len(response_times),
            "period_days": days
        }
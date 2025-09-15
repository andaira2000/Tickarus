import time
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timedelta
from app.db.database import get_supabase, get_service_client, exec_query
from app.services.metrics_service import MetricsService
import logging

logger = logging.getLogger(__name__)


class EvaluationService:
    """
    Human evaluation interface for AI feature accuracy assessment
    Supports dissertation evaluation with user feedback collection
    """
    
    @staticmethod
    def _c():
        return get_supabase()
    
    @staticmethod
    def _service_c():
        return get_service_client()
    
    async def get_evaluation_tasks(
        self, 
        user_id: UUID,
        task_type: str = "similarity",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get AI predictions that need human evaluation
        
        Args:
            user_id: User performing evaluation
            task_type: Type of AI feature to evaluate (similarity, rootcause)
            limit: Number of tasks to return
            
        Returns:
            List of evaluation tasks
        """
        c = self._service_c()
        
        if task_type == "similarity":
            return await self._get_similarity_evaluation_tasks(c, limit)
        elif task_type == "rootcause":
            return await self._get_rootcause_evaluation_tasks(c, limit)
        else:
            raise ValueError(f"Unsupported task type: {task_type}")
    
    async def _get_similarity_evaluation_tasks(self, c, limit: int) -> List[Dict[str, Any]]:
        """Get similarity predictions for human evaluation"""
        
        # Get recent similarity events that haven't been evaluated
        metrics_resp = exec_query(
            c.table("ai_metrics")
            .select("id, ticket_id, metadata, created_at")
            .eq("event_type", "similarity_shown")
            .eq("ai_feature", "similarity")
            .not_.is_("metadata", "null")
            .order("created_at", desc=True)
            .limit(limit * 2)  # Get more to filter
        )
        
        tasks = []
        seen_tickets = set()
        
        for metric in (metrics_resp.data or []):
            ticket_id = metric["ticket_id"]
            if ticket_id in seen_tickets:
                continue
            seen_tickets.add(ticket_id)
            
            # Get the original ticket
            ticket_resp = exec_query(
                c.table("tickets")
                .select("id, title, description, teams(name)")
                .eq("id", ticket_id)
                .single()
            )
            
            if not ticket_resp.data:
                continue
            
            ticket = ticket_resp.data
            suggestions = metric["metadata"].get("suggestions", [])
            
            if not suggestions:
                continue
            
            # Get the suggested similar tickets
            similar_tickets = []
            for suggestion_id in suggestions[:3]:  # Top 3 suggestions
                sim_resp = exec_query(
                    c.table("tickets")
                    .select("id, title, description, teams(name)")
                    .eq("id", suggestion_id)
                    .single()
                )
                
                if sim_resp.data:
                    similar_tickets.append(sim_resp.data)
            
            if similar_tickets:
                tasks.append({
                    "task_id": metric["id"],
                    "task_type": "similarity",
                    "original_ticket": {
                        "id": ticket["id"],
                        "title": ticket["title"],
                        "description": ticket["description"][:300] + "..." if len(ticket["description"]) > 300 else ticket["description"],
                        "team_name": ticket.get("teams", {}).get("name") if ticket.get("teams") else None
                    },
                    "suggestions": [
                        {
                            "id": st["id"],
                            "title": st["title"],
                            "description": st["description"][:200] + "..." if len(st["description"]) > 200 else st["description"],
                            "team_name": st.get("teams", {}).get("name") if st.get("teams") else None
                        } for st in similar_tickets
                    ],
                    "created_at": metric["created_at"]
                })
            
            if len(tasks) >= limit:
                break
        
        return tasks
    
    async def _get_rootcause_evaluation_tasks(self, c, limit: int) -> List[Dict[str, Any]]:
        """Get root cause analysis predictions for human evaluation"""
        
        # Get recent root cause analyses that haven't been rated
        metrics_resp = exec_query(
            c.table("ai_metrics")
            .select("id, ticket_id, metadata, created_at")
            .eq("event_type", "rootcause_requested")
            .eq("ai_feature", "rootcause")
            .is_("user_rating", "null")
            .order("created_at", desc=True)
            .limit(limit)
        )
        
        tasks = []
        
        for metric in (metrics_resp.data or []):
            ticket_id = metric["ticket_id"]
            
            # Get the ticket details
            ticket_resp = exec_query(
                c.table("tickets")
                .select("id, title, description, status, teams(name)")
                .eq("id", ticket_id)
                .single()
            )
            
            if not ticket_resp.data:
                continue
            
            ticket = ticket_resp.data
            
            # For this demo, we'll simulate the AI analysis result
            # In practice, this would be stored with the metrics
            confidence = metric["metadata"].get("confidence_score", 0.5)
            pattern_matched = metric["metadata"].get("pattern_matched", False)
            
            # Generate a mock analysis for evaluation
            analysis = {
                "root_cause": "Database connectivity issues" if "database" in ticket["title"].lower() else "Performance degradation",
                "confidence_score": confidence,
                "suggestions": [
                    "Check system logs for error patterns",
                    "Review recent deployments or changes",
                    "Verify service dependencies and network connectivity"
                ]
            }
            
            tasks.append({
                "task_id": metric["id"],
                "task_type": "rootcause",
                "ticket": {
                    "id": ticket["id"],
                    "title": ticket["title"],
                    "description": ticket["description"][:400] + "..." if len(ticket["description"]) > 400 else ticket["description"],
                    "status": ticket["status"],
                    "team_name": ticket.get("teams", {}).get("name") if ticket.get("teams") else None
                },
                "ai_analysis": analysis,
                "created_at": metric["created_at"]
            })
        
        return tasks
    
    async def submit_evaluation(
        self,
        task_id: str,
        user_id: UUID,
        task_type: str,
        evaluation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Submit human evaluation of AI prediction
        
        Args:
            task_id: ID of the evaluation task (metrics record ID)
            user_id: User performing evaluation
            task_type: Type of evaluation (similarity, rootcause)
            evaluation: Evaluation data
            
        Returns:
            Confirmation of submission
        """
        
        if task_type == "similarity":
            return await self._submit_similarity_evaluation(task_id, user_id, evaluation)
        elif task_type == "rootcause":
            return await self._submit_rootcause_evaluation(task_id, user_id, evaluation)
        else:
            raise ValueError(f"Unsupported task type: {task_type}")
    
    async def _submit_similarity_evaluation(
        self, 
        task_id: str, 
        user_id: UUID, 
        evaluation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Submit similarity evaluation"""
        
        # Expected evaluation format:
        # {
        #   "relevant_suggestions": ["ticket_id1", "ticket_id2"],
        #   "overall_rating": 4,
        #   "comments": "Good suggestions but missed one obvious match"
        # }
        
        relevant_count = len(evaluation.get("relevant_suggestions", []))
        overall_rating = evaluation.get("overall_rating", 3)
        
        # Log the evaluation
        await MetricsService.log_event(
            event_type="similarity_evaluated",
            user_id=user_id,
            ai_feature="similarity",
            user_rating=overall_rating,
            metadata={
                "task_id": task_id,
                "relevant_suggestions_count": relevant_count,
                "relevant_suggestions": evaluation.get("relevant_suggestions", []),
                "comments": evaluation.get("comments"),
                "evaluator_id": str(user_id)
            }
        )
        
        return {
            "message": "Similarity evaluation submitted successfully",
            "task_id": task_id,
            "rating": overall_rating,
            "relevant_count": relevant_count
        }
    
    async def _submit_rootcause_evaluation(
        self, 
        task_id: str, 
        user_id: UUID, 
        evaluation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Submit root cause evaluation"""
        
        # Expected evaluation format:
        # {
        #   "accuracy_rating": 4,
        #   "usefulness_rating": 3,
        #   "correct_root_cause": "Actually a network issue",
        #   "comments": "AI identified database but it was network connectivity"
        # }
        
        accuracy_rating = evaluation.get("accuracy_rating", 3)
        usefulness_rating = evaluation.get("usefulness_rating", 3)
        
        # Average the ratings
        overall_rating = round((accuracy_rating + usefulness_rating) / 2)
        
        # Update the original metrics record with the rating
        c = self._service_c()
        exec_query(
            c.table("ai_metrics")
            .update({"user_rating": overall_rating})
            .eq("id", task_id)
        )
        
        # Log the detailed evaluation
        await MetricsService.log_event(
            event_type="rootcause_evaluated",
            user_id=user_id,
            ai_feature="rootcause",
            user_rating=overall_rating,
            metadata={
                "task_id": task_id,
                "accuracy_rating": accuracy_rating,
                "usefulness_rating": usefulness_rating,
                "correct_root_cause": evaluation.get("correct_root_cause"),
                "comments": evaluation.get("comments"),
                "evaluator_id": str(user_id)
            }
        )
        
        return {
            "message": "Root cause evaluation submitted successfully",
            "task_id": task_id,
            "overall_rating": overall_rating,
            "accuracy_rating": accuracy_rating,
            "usefulness_rating": usefulness_rating
        }
    
    async def get_evaluation_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get evaluation statistics for dissertation analysis"""
        
        c = self._service_c()
        cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        # Get similarity evaluations
        sim_evals = exec_query(
            c.table("ai_metrics")
            .select("user_rating, metadata")
            .eq("event_type", "similarity_evaluated")
            .gte("created_at", cutoff_date)
        )
        
        # Get root cause evaluations
        rc_evals = exec_query(
            c.table("ai_metrics")
            .select("user_rating, metadata")
            .eq("event_type", "rootcause_evaluated")
            .gte("created_at", cutoff_date)
        )
        
        sim_ratings = [r["user_rating"] for r in (sim_evals.data or []) if r["user_rating"]]
        rc_ratings = [r["user_rating"] for r in (rc_evals.data or []) if r["user_rating"]]
        
        return {
            "period_days": days,
            "similarity_evaluation": {
                "total_evaluations": len(sim_ratings),
                "average_rating": round(sum(sim_ratings) / len(sim_ratings), 2) if sim_ratings else 0,
                "rating_distribution": {
                    str(i): sim_ratings.count(i) for i in range(1, 6)
                }
            },
            "rootcause_evaluation": {
                "total_evaluations": len(rc_ratings),
                "average_rating": round(sum(rc_ratings) / len(rc_ratings), 2) if rc_ratings else 0,
                "rating_distribution": {
                    str(i): rc_ratings.count(i) for i in range(1, 6)
                }
            },
            "overall_stats": {
                "total_evaluations": len(sim_ratings) + len(rc_ratings),
                "overall_average": round(sum(sim_ratings + rc_ratings) / len(sim_ratings + rc_ratings), 2) if (sim_ratings + rc_ratings) else 0
            }
        }


# Global instance
evaluation_service = EvaluationService()
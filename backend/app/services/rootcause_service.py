import time
import asyncio
from typing import List, Dict, Any, Optional
from uuid import UUID
import logging
from app.db.database import get_supabase, exec_query
from app.services.metrics_service import MetricsService

logger = logging.getLogger(__name__)


class RootCauseService:
    """
    Root cause analysis using pattern matching and heuristics
    For dissertation: measures accuracy of root cause suggestions
    """
    
    def __init__(self):
        self.analysis_patterns = [
            {
                "pattern": ["timeout", "connection", "database", "db"],
                "root_cause": "Database connectivity issues",
                "suggestions": [
                    "Check database server status and availability",
                    "Review connection pool configuration",
                    "Verify network connectivity between services",
                    "Check for database locks or long-running queries"
                ]
            },
            {
                "pattern": ["memory", "heap", "oom", "out of memory"],
                "root_cause": "Memory exhaustion",
                "suggestions": [
                    "Analyze memory usage patterns and heap dumps",
                    "Review application memory configuration",
                    "Check for memory leaks in recent code changes",
                    "Scale up instance memory or optimize memory usage"
                ]
            },
            {
                "pattern": ["404", "not found", "missing", "endpoint"],
                "root_cause": "Missing resources or configuration",
                "suggestions": [
                    "Verify API endpoint configuration",
                    "Check routing table and URL mappings",
                    "Ensure required resources are deployed",
                    "Review recent deployment changes"
                ]
            },
            {
                "pattern": ["500", "internal server", "crash", "exception"],
                "root_cause": "Application runtime error",
                "suggestions": [
                    "Review application logs for stack traces",
                    "Check for recent code changes or deployments",
                    "Verify environment configuration",
                    "Test error reproduction in staging environment"
                ]
            },
            {
                "pattern": ["slow", "performance", "latency", "response time"],
                "root_cause": "Performance degradation",
                "suggestions": [
                    "Analyze performance metrics and bottlenecks",
                    "Review database query performance",
                    "Check system resource utilization",
                    "Optimize slow queries or inefficient code paths"
                ]
            },
            {
                "pattern": ["auth", "login", "unauthorized", "permission"],
                "root_cause": "Authentication or authorization issues",
                "suggestions": [
                    "Verify user credentials and permissions",
                    "Check authentication service status",
                    "Review access control configuration",
                    "Validate token expiration and refresh logic"
                ]
            }
        ]
    
    @staticmethod
    def _c():
        return get_supabase()
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from ticket content"""
        if not text:
            return []
        
        # Simple keyword extraction - normalize and split
        words = text.lower().replace(',', ' ').replace('.', ' ').split()
        # Filter out common words and short words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'must'}
        return [word for word in words if len(word) > 2 and word not in stop_words]
    
    def _match_patterns(self, keywords: List[str]) -> Optional[Dict[str, Any]]:
        """Match keywords against known patterns"""
        best_match = None
        best_score = 0
        
        for pattern_def in self.analysis_patterns:
            pattern_keywords = pattern_def["pattern"]
            matches = sum(1 for keyword in keywords if any(pk in keyword for pk in pattern_keywords))
            
            if matches > best_score:
                best_score = matches
                best_match = pattern_def
        
        return best_match if best_score > 0 else None
    
    async def _get_similar_resolved_tickets(self, keywords: List[str], limit: int = 3) -> List[Dict[str, Any]]:
        """Find similar resolved tickets for reference"""
        try:
            c = self._c()
            
            # Simple keyword-based search in resolved tickets
            search_terms = ' | '.join(keywords[:5])  # Use top 5 keywords
            
            query = (c.table("tickets")
                    .select("id, title, description, status, created_at")
                    .in_("status", ["resolved", "closed"])
                    .text_search("search_tsv", search_terms))
            
            resp = exec_query(query)
            data = resp.data or []
            return data[:limit]  # Apply limit after query
            
        except Exception as e:
            logger.error(f"Error finding similar resolved tickets: {str(e)}")
            return []
    
    async def analyze_ticket(
        self, 
        ticket_id: UUID, 
        user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Perform root cause analysis on a ticket
        
        Args:
            ticket_id: ID of ticket to analyze
            user_id: User requesting analysis (for metrics)
            
        Returns:
            Analysis results with root cause and suggestions
        """
        start_time = time.time()
        
        try:
            # Get ticket details
            c = self._c()
            ticket_resp = exec_query(
                c.table("tickets")
                .select("id, title, description, status")
                .eq("id", str(ticket_id))
                .single()
            )
            
            if not ticket_resp.data:
                raise Exception("Ticket not found")
            
            ticket = ticket_resp.data
            
            # Extract keywords from title and description
            text_content = f"{ticket['title']} {ticket.get('description', '')}"
            keywords = self._extract_keywords(text_content)
            
            # Match against patterns
            pattern_match = self._match_patterns(keywords)
            
            # Get similar resolved tickets
            similar_tickets = await self._get_similar_resolved_tickets(keywords)
            
            # Simulate analysis delay (realistic for LLM call)
            await asyncio.sleep(0.5)
            
            # Build analysis result
            analysis = {
                "ticket_id": str(ticket_id),
                "analysis_timestamp": time.time(),
                "root_cause": pattern_match["root_cause"] if pattern_match else "Unknown - requires manual investigation",
                "confidence_score": 0.8 if pattern_match else 0.2,
                "suggestions": pattern_match["suggestions"] if pattern_match else [
                    "Review ticket details and error messages carefully",
                    "Check system logs around the time of the issue",
                    "Contact relevant team members for additional context"
                ],
                "similar_resolved_tickets": [
                    {
                        "id": t["id"],
                        "title": t["title"],
                        "status": t["status"]
                    } for t in similar_tickets
                ],
                "keywords_analyzed": keywords[:10],  # Top 10 keywords
                "pattern_matched": pattern_match["pattern"] if pattern_match else None
            }
            
            # Log metrics
            response_time = int((time.time() - start_time) * 1000)
            await MetricsService.log_event(
                event_type="rootcause_requested",
                ticket_id=ticket_id,
                user_id=user_id,
                ai_feature="rootcause",
                metadata={
                    "confidence_score": analysis["confidence_score"],
                    "pattern_matched": bool(pattern_match),
                    "keywords_count": len(keywords),
                    "similar_tickets_found": len(similar_tickets)
                },
                response_time_ms=response_time
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in root cause analysis: {str(e)}")
            # Still log the attempt for metrics
            response_time = int((time.time() - start_time) * 1000)
            await MetricsService.log_event(
                event_type="rootcause_error",
                ticket_id=ticket_id,
                user_id=user_id,
                ai_feature="rootcause",
                metadata={"error": str(e)},
                response_time_ms=response_time
            )
            raise
    
    async def submit_feedback(
        self,
        ticket_id: UUID,
        user_id: UUID,
        rating: int,
        feedback_text: Optional[str] = None
    ):
        """Submit user feedback on root cause analysis quality"""
        await MetricsService.log_event(
            event_type="rootcause_feedback",
            ticket_id=ticket_id,
            user_id=user_id,
            ai_feature="rootcause",
            user_rating=rating,
            metadata={
                "feedback_text": feedback_text
            } if feedback_text else None
        )


# Global instance
rootcause_service = RootCauseService()
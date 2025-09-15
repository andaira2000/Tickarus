import time
from typing import List, Dict, Any, Optional
from uuid import UUID
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from app.db.database import get_supabase, exec_query
from app.services.metrics_service import MetricsService
import logging

logger = logging.getLogger(__name__)


class SimilarityService:
    """
    Simple similarity detection using Sentence-BERT embeddings
    For dissertation evaluation: measures top-K suggestion accuracy
    """
    
    def __init__(self):
        # Load a lightweight sentence transformer model
        self.model = SentenceTransformer('all-MiniLM-L6-v2')  # Fast, good quality
        self._embeddings_cache = {}  # Simple in-memory cache
        
    @staticmethod
    def _c():
        return get_supabase()
    
    def _get_ticket_text(self, ticket: Dict[str, Any]) -> str:
        """Combine title and description for embedding"""
        title = ticket.get("title", "")
        description = ticket.get("description", "")
        return f"{title}. {description}"
    
    def _compute_embedding(self, text: str) -> np.ndarray:
        """Compute sentence embedding for given text"""
        # Simple caching to avoid recomputing
        text_hash = hash(text)
        if text_hash in self._embeddings_cache:
            return self._embeddings_cache[text_hash]
            
        embedding = self.model.encode([text])[0]
        self._embeddings_cache[text_hash] = embedding
        return embedding
    
    async def find_similar_tickets(
        self, 
        ticket_text: str, 
        current_ticket_id: Optional[UUID] = None,
        limit: int = 5,
        user_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """
        Find similar tickets using semantic similarity
        
        Args:
            ticket_text: Title + description to find similarities for
            current_ticket_id: Exclude this ticket from results 
            limit: Number of similar tickets to return
            user_id: For logging metrics
            
        Returns:
            List of similar tickets with similarity scores
        """
        start_time = time.time()
        
        try:
            # Get all existing tickets for comparison
            c = self._c()
            query = c.table("tickets").select("id, title, description, status, created_at, teams(name)")
            
            # Exclude current ticket if provided
            if current_ticket_id:
                query = query.neq("id", str(current_ticket_id))
                
            resp = exec_query(query)
            all_tickets = resp.data or []
            
            if not all_tickets:
                return []
            
            # Compute embedding for input text
            input_embedding = self._compute_embedding(ticket_text)
            
            # Compute embeddings for all tickets and calculate similarities
            similarities = []
            for ticket in all_tickets:
                ticket_text_full = self._get_ticket_text(ticket)
                ticket_embedding = self._compute_embedding(ticket_text_full)
                
                # Cosine similarity
                similarity_score = cosine_similarity(
                    [input_embedding], [ticket_embedding]
                )[0][0]
                
                similarities.append({
                    "ticket": ticket,
                    "similarity_score": float(similarity_score)
                })
            
            # Sort by similarity score (descending) and take top results
            similarities.sort(key=lambda x: x["similarity_score"], reverse=True)
            top_similar = similarities[:limit]
            
            # Format results
            results = []
            for item in top_similar:
                ticket = item["ticket"]
                team_name = None
                if ticket.get("teams") and isinstance(ticket["teams"], dict):
                    team_name = ticket["teams"].get("name")
                
                results.append({
                    "id": ticket["id"],
                    "title": ticket["title"], 
                    "description": ticket["description"][:200] + "..." if len(ticket["description"]) > 200 else ticket["description"],
                    "team_name": team_name,
                    "status": ticket["status"],
                    "similarity_score": round(item["similarity_score"], 3),
                    "created_at": ticket["created_at"]
                })
            
            # Log metrics for dissertation evaluation
            response_time = int((time.time() - start_time) * 1000)
            suggestion_ids = [r["id"] for r in results]
            
            await MetricsService.log_event(
                event_type="similarity_shown",
                ticket_id=current_ticket_id,
                user_id=user_id,
                ai_feature="similarity",
                metadata={
                    "suggestions": suggestion_ids,
                    "similarity_scores": [r["similarity_score"] for r in results],
                    "query_length": len(ticket_text)
                },
                response_time_ms=response_time
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error in similarity detection: {str(e)}")
            return []
    
    async def log_similarity_click(
        self, 
        clicked_ticket_id: UUID, 
        original_ticket_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None
    ):
        """Log when user clicks on a similarity suggestion (for evaluation)"""
        await MetricsService.log_event(
            event_type="similarity_clicked",
            ticket_id=original_ticket_id,
            user_id=user_id,
            ai_feature="similarity",
            metadata={
                "clicked_ticket": str(clicked_ticket_id)
            }
        )


# Global instance (simple singleton pattern)
similarity_service = SimilarityService()
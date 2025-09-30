import logging
import time
from typing import List, Dict, Any, Optional
from uuid import UUID

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from app.db.database import get_service_client
from app.services.metrics_service import MetricsService

logger = logging.getLogger(__name__)


class SimilarityService:
    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self._embeddings_cache = {}

    def _get_ticket_text(self, ticket: Dict[str, Any]) -> str:
        title = ticket.get("title", "")
        description = ticket.get("description", "")
        return f"{title}. {description}"

    def _compute_embedding(self, text: str) -> np.ndarray:
        text_hash = hash(text)
        if text_hash in self._embeddings_cache:
            return self._embeddings_cache[text_hash]

        embedding = self.model.encode([text])[0]
        self._embeddings_cache[text_hash] = embedding
        return embedding

    async def precompute_embeddings_for_existing_tickets(self):
        supabase_client = get_service_client()
        tickets = (
            await supabase_client.table("tickets")
            .select("id, title, description")
            .execute()
        ).data

        for ticket in tickets:
            ticket_text = self._get_ticket_text(ticket)
            self._compute_embedding(ticket_text)

    async def find_similar_tickets(
        self,
        ticket_text: str,
        current_ticket_id: Optional[UUID] = None,
        limit: int = 5,
        user_id: Optional[UUID] = None,
    ) -> List[Dict[str, Any]]:
        """Find similar tickets using semantic similarity."""
        try:
            start_time = time.time()
            supabase_client = get_service_client()

            query = supabase_client.table("tickets").select(
                "id, title, description, status, created_at, teams(name)"
            )

            # Exclude current ticket if provided
            if current_ticket_id:
                query = query.neq("id", str(current_ticket_id))

            tickets = (await query.execute()).data

            if not tickets:
                return []

            input_embedding = self._compute_embedding(ticket_text)

            similarities = []
            for ticket in tickets:
                ticket_text_full = self._get_ticket_text(ticket)
                ticket_embedding = self._compute_embedding(ticket_text_full)

                similarity_score = cosine_similarity(
                    [input_embedding], [ticket_embedding]
                )[0][0]

                similarities.append(
                    {"ticket": ticket, "similarity_score": float(similarity_score)}
                )

            similarities.sort(key=lambda x: x["similarity_score"], reverse=True)
            top_similar = similarities[:limit]

            suggestions = []
            for item in top_similar:
                ticket = item["ticket"]
                team_name = ticket.get("teams", {}).get("name")
                suggestions.append(
                    {
                        "id": ticket["id"],
                        "title": ticket["title"],
                        "description": (
                            ticket["description"][:200] + "..."
                            if len(ticket["description"]) > 200
                            else ticket["description"]
                        ),
                        "team_name": team_name,
                        "status": ticket["status"],
                        "similarity_score": round(item["similarity_score"], 3),
                        "created_at": ticket["created_at"],
                    }
                )

            response_time = int((time.time() - start_time) * 1000)
            suggestion_ids = [suggestion["id"] for suggestion in suggestions]

            await MetricsService.log_event(
                event_type="similarity_shown",
                ticket_id=current_ticket_id,
                user_id=user_id,
                ai_feature="similarity",
                metadata={
                    "suggestions": suggestion_ids,
                    "similarity_scores": [
                        suggestion["similarity_score"] for suggestion in suggestions
                    ],
                    "query_length": len(ticket_text),
                },
                response_time_ms=response_time,
            )

            return suggestions

        except Exception as e:
            logger.error(f"Error in similarity detection: {str(e)}")
            return []


similarity_service = SimilarityService()

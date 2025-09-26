import time
import re
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
import logging
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from app.db.database import get_supabase, get_service_client, exec_query
from app.models.ticket import TicketPriority
from app.services.metrics_service import MetricsService

logger = logging.getLogger(__name__)


class AutoTaggingService:
    """
    Semantic automatic tagging and prioritization service using BERT embeddings
    Analyzes ticket content to suggest tags and priority levels using similarity to semantic descriptions
    """

    def __init__(self):
        # Load the same sentence transformer model as similarity service for consistency
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self._embeddings_cache = {}  # Cache for tag description embeddings

        # Semantic tag descriptions for BERT-based classification
        self.tag_descriptions = {
            "database": "Database related issues including SQL queries, connections, timeouts, data integrity, migration problems, deadlocks, performance issues, and database server connectivity problems",
            "frontend": "User interface and client-side issues including React components, CSS styling, HTML markup, JavaScript errors, responsive design, browser compatibility, and visual rendering problems",
            "backend": "Server-side application issues including API endpoints, business logic, microservices, server configuration, application crashes, and backend processing errors",
            "infrastructure": "DevOps and infrastructure issues including Docker containers, Kubernetes deployment, cloud services, AWS configuration, CI/CD pipelines, build failures, and deployment problems",
            "security": "Security vulnerabilities and authentication issues including login problems, authorization failures, permission errors, data breaches, XSS attacks, and security configuration problems",
            "performance": "Performance and optimization issues including slow response times, high memory usage, CPU bottlenecks, latency problems, and system resource optimization needs",
            "bug": "Software defects and errors including application crashes, exceptions, incorrect behavior, broken functionality, and unexpected system failures",
            "feature": "New functionality requests and enhancements including feature additions, improvements to existing functionality, and system capability expansions",
            "ui": "User interface and user experience issues including layout problems, interaction bugs, accessibility issues, and visual design concerns",
            "api": "Application programming interface issues including REST API problems, GraphQL errors, API authentication, rate limiting, and integration difficulties",
            "networking": "Network connectivity and communication issues including timeouts, DNS problems, firewall issues, and service communication failures",
            "testing": "Testing related issues including unit test failures, integration test problems, test environment setup, and quality assurance concerns",
            "documentation": "Documentation issues including missing docs, outdated information, unclear instructions, and documentation maintenance needs",
            "configuration": "Configuration and setup issues including environment variables, application settings, deployment configuration, and system setup problems",
        }

        # Enhanced priority analysis using both semantic and keyword-based approaches
        self.priority_descriptions = {
            "critical": "Critical production outages, system completely down, database failures, deadlocks, data loss, security breaches, blocking all users, urgent business impact, crashes, server failures, complete service unavailability",
            "high": "Major functionality broken, database timeouts, significant errors, affecting many users, blocking important workflows, significant business impact, needs immediate attention, performance degradation",
            "medium": "Moderate impact issues, affecting some users, workarounds available, standard business priority, regular development cycle, minor bugs, slow performance",
            "low": "Minor issues, cosmetic problems, feature requests, enhancements, nice-to-have improvements, low business impact, documentation updates",
        }

        # Keyword-based priority rules as fallback
        self.priority_rules = [
            {
                "keywords": [
                    "production",
                    "outage",
                    "down",
                    "critical",
                    "urgent",
                    "data loss",
                    "security breach",
                ],
                "priority": TicketPriority.CRITICAL,
                "weight": 4,
            },
            {
                "keywords": [
                    "blocking",
                    "blocker",
                    "cannot",
                    "unable",
                    "broken",
                    "major",
                ],
                "priority": TicketPriority.HIGH,
                "weight": 3,
            },
            {
                "keywords": ["performance", "slow", "timeout", "error", "issue"],
                "priority": TicketPriority.MEDIUM,
                "weight": 1,
            },
            {
                "keywords": [
                    "enhancement",
                    "feature",
                    "improvement",
                    "minor",
                    "cosmetic",
                ],
                "priority": TicketPriority.LOW,
                "weight": -1,
            },
        ]

        # Pre-compute embeddings for tag and priority descriptions
        self._precompute_tag_embeddings()

    @staticmethod
    def _c():
        return get_supabase()

    @staticmethod
    def _service_c():
        return get_service_client()

    def _precompute_tag_embeddings(self):
        """Pre-compute embeddings for all tag descriptions for faster classification"""
        logger.info("Pre-computing BERT embeddings for tag descriptions...")

        for tag_name, description in self.tag_descriptions.items():
            embedding = self.model.encode([description])[0]
            self._embeddings_cache[f"tag_{tag_name}"] = embedding

        for priority_name, description in self.priority_descriptions.items():
            embedding = self.model.encode([description])[0]
            self._embeddings_cache[f"priority_{priority_name}"] = embedding

        logger.info(
            f"Cached embeddings for {len(self.tag_descriptions)} tags and {len(self.priority_descriptions)} priority levels"
        )

    def _compute_embedding(self, text: str) -> np.ndarray:
        """Compute sentence embedding for given text with caching"""
        text_hash = hash(text)
        cache_key = f"text_{text_hash}"

        if cache_key in self._embeddings_cache:
            return self._embeddings_cache[cache_key]

        embedding = self.model.encode([text])[0]
        self._embeddings_cache[cache_key] = embedding
        return embedding

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract and normalize keywords from text (kept for fallback priority analysis)"""
        if not text:
            return []

        text = text.lower()
        text = re.sub(r"[^a-z0-9\s\-]", " ", text)
        words = text.split()

        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "can",
            "must",
            "this",
            "that",
            "these",
            "those",
        }

        return [word for word in words if len(word) > 2 and word not in stop_words]

    def _analyze_tags_semantic(
        self, text: str, threshold: float = 0.3, max_tags: int = 6
    ) -> List[Dict[str, Any]]:
        """Use BERT embeddings to analyze text and suggest semantically similar tags"""
        if not text.strip():
            return []

        # Compute embedding for the input text
        text_embedding = self._compute_embedding(text)

        # Calculate similarities with all tag descriptions
        similarities = []
        for tag_name in self.tag_descriptions.keys():
            tag_embedding = self._embeddings_cache[f"tag_{tag_name}"]

            # Compute cosine similarity
            similarity_score = cosine_similarity([text_embedding], [tag_embedding])[0][
                0
            ]

            if similarity_score >= threshold:  # Only include if above threshold
                similarities.append(
                    {
                        "tag_name": tag_name,
                        "confidence": round(
                            similarity_score * 100, 1
                        ),  # Convert to percentage
                        "similarity_score": float(similarity_score),
                        "method": "semantic_bert",
                    }
                )

        # Sort by confidence and take top results
        similarities.sort(key=lambda x: x["confidence"], reverse=True)
        return similarities[:max_tags]

    def _analyze_tags(self, text: str) -> List[Dict[str, Any]]:
        """Primary tag analysis using semantic BERT embeddings"""
        return self._analyze_tags_semantic(text)

    def _analyze_priority_semantic(self, text: str) -> Dict[str, Any]:
        """Use BERT embeddings to analyze text and suggest priority level"""
        if not text.strip():
            return {
                "suggested_priority": TicketPriority.MEDIUM,
                "confidence": 30.0,
                "method": "default",
                "similarities": {},
            }

        # Compute embedding for the input text
        text_embedding = self._compute_embedding(text)

        # Calculate similarities with all priority descriptions
        similarities = {}
        for priority_name in self.priority_descriptions.keys():
            priority_embedding = self._embeddings_cache[f"priority_{priority_name}"]

            # Compute cosine similarity
            similarity_score = cosine_similarity(
                [text_embedding], [priority_embedding]
            )[0][0]

            similarities[priority_name] = float(similarity_score)

        # Find the priority with highest similarity
        best_priority = max(similarities.keys(), key=lambda x: similarities[x])
        best_similarity = similarities[best_priority]

        # Map to TicketPriority enum
        priority_mapping = {
            "critical": TicketPriority.CRITICAL,
            "high": TicketPriority.HIGH,
            "medium": TicketPriority.MEDIUM,
            "low": TicketPriority.LOW,
        }

        suggested_priority = priority_mapping.get(best_priority, TicketPriority.MEDIUM)
        confidence = round(best_similarity * 100, 1)  # Convert to percentage

        return {
            "suggested_priority": suggested_priority,
            "confidence": confidence,
            "method": "semantic_bert",
            "similarities": {k: round(v * 100, 1) for k, v in similarities.items()},
            "best_match": best_priority,
        }

    def _analyze_priority_keywords(
        self, keywords: List[str], title: str
    ) -> Dict[str, Any]:
        """Fallback keyword-based priority analysis"""
        priority_score = 0
        matched_rules = []

        all_text = (title.lower() + " " + " ".join(keywords)).lower()

        for rule in self.priority_rules:
            matches = sum(1 for keyword in rule["keywords"] if keyword in all_text)
            if matches > 0:
                rule_score = matches * rule["weight"]
                priority_score += rule_score
                matched_rules.append(
                    {
                        "keywords": [kw for kw in rule["keywords"] if kw in all_text],
                        "weight": rule["weight"],
                        "score": rule_score,
                    }
                )

        if priority_score >= 4:
            suggested_priority = TicketPriority.CRITICAL
            confidence = min(95, 70 + priority_score * 5)
        elif priority_score >= 3:
            suggested_priority = TicketPriority.HIGH
            confidence = min(90, 60 + priority_score * 5)
        elif priority_score >= 1:
            suggested_priority = TicketPriority.MEDIUM
            confidence = min(80, 50 + priority_score * 10)
        elif priority_score <= -2:
            suggested_priority = TicketPriority.LOW
            confidence = min(80, 40 + abs(priority_score) * 10)
        else:
            suggested_priority = TicketPriority.MEDIUM
            confidence = 30

        return {
            "suggested_priority": suggested_priority,
            "confidence": round(confidence, 1),
            "method": "keyword_matching",
            "score": priority_score,
            "matched_rules": matched_rules,
        }

    def _analyze_priority(self, text: str, title: str = "") -> Dict[str, Any]:
        """Hybrid priority analysis using both semantic and keyword approaches"""
        full_text = f"{title} {text}".strip()

        # Try semantic analysis first
        semantic_result = self._analyze_priority_semantic(full_text)

        # Only fallback to keyword matching if semantic analysis has very low confidence
        if semantic_result["confidence"] < 25:  # Lowered threshold
            keywords = self._extract_keywords(full_text)
            keyword_result = self._analyze_priority_keywords(keywords, title)

            # Use the result with higher confidence, but prefer semantic if close
            if keyword_result["confidence"] > semantic_result["confidence"] + 10:
                return keyword_result

        return semantic_result

    async def auto_tag_ticket(
        self,
        title: str,
        description: str = "",
        user_id: Optional[UUID] = None,
        client=None,
    ) -> Dict[str, Any]:
        """Analyze title and description for automatic tagging and prioritization using BERT embeddings"""
        start_time = time.time()

        try:
            text_content = f"{title} {description}".strip()

            # Use semantic BERT-based analysis
            suggested_tags = self._analyze_tags(text_content)
            priority_analysis = self._analyze_priority(text_content, title)

            # Extract just the tag names and suggested priority
            tag_names = [tag["tag_name"] for tag in suggested_tags]
            suggested_priority = (
                priority_analysis["suggested_priority"].value
                if hasattr(priority_analysis["suggested_priority"], "value")
                else priority_analysis["suggested_priority"]
            )

            # Create confidence scores
            confidence_scores = {}
            for tag_data in suggested_tags:
                confidence_scores[tag_data["tag_name"]] = tag_data["confidence"]
            confidence_scores[f"priority_{suggested_priority}"] = priority_analysis.get(
                "confidence", 50.0
            )

            result = {
                "suggested_tags": tag_names,
                "suggested_priority": suggested_priority,
                "confidence_scores": confidence_scores,
                "tag_analysis": suggested_tags,
                "priority_analysis": priority_analysis,
                "analysis_method": "semantic_bert",
            }

            # Log metrics if we have a client
            c = client or self._c()
            response_time = int((time.time() - start_time) * 1000)

            await MetricsService.log_event(
                event_type="auto_tagging_suggestions_generated",
                user_id=user_id,
                ai_feature="auto_tagging",
                metadata={
                    "suggested_tags": tag_names,
                    "suggested_priority": suggested_priority,
                    "analysis_method": "semantic_bert",
                    "tags_count": len(suggested_tags),
                    "avg_tag_confidence": (
                        sum(tag["confidence"] for tag in suggested_tags)
                        / len(suggested_tags)
                        if suggested_tags
                        else 0
                    ),
                },
                response_time_ms=response_time,
                client=c,
            )

            return result

        except Exception as e:
            logger.error(f"Error in BERT-based auto-tagging analysis: {str(e)}")
            return {
                "suggested_tags": [],
                "suggested_priority": "medium",
                "confidence_scores": {},
                "error": str(e),
                "analysis_method": "error",
            }

    async def analyze_ticket(
        self, ticket_id: UUID, user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Analyze a ticket for automatic tagging and prioritization using BERT embeddings"""
        start_time = time.time()

        try:
            c = self._service_c()
            ticket_resp = exec_query(
                c.table("tickets")
                .select("id, title, description, priority, status")
                .eq("id", str(ticket_id))
                .single()
            )

            if not ticket_resp.data:
                raise Exception("Ticket not found")

            ticket = ticket_resp.data
            title = ticket["title"] or ""
            description = ticket.get("description", "") or ""
            text_content = f"{title} {description}".strip()

            # Use semantic BERT-based analysis
            suggested_tags = self._analyze_tags(text_content)
            priority_analysis = self._analyze_priority(text_content, title)

            # Get existing tags
            existing_tags_resp = exec_query(
                c.table("ticket_tags")
                .select("tags(name)")
                .eq("ticket_id", str(ticket_id))
            )
            existing_tag_names = [
                tag["tags"]["name"]
                for tag in (existing_tags_resp.data or [])
                if tag.get("tags")
            ]

            analysis_result = {
                "ticket_id": str(ticket_id),
                "analysis_timestamp": time.time(),
                "suggested_tags": suggested_tags,
                "priority_analysis": priority_analysis,
                "current_priority": ticket["priority"],
                "existing_tags": existing_tag_names,
                "analysis_method": "semantic_bert",
                "text_analyzed": (
                    text_content[:200] + "..."
                    if len(text_content) > 200
                    else text_content
                ),
            }

            # Log metrics
            response_time = int((time.time() - start_time) * 1000)
            priority_value = (
                priority_analysis["suggested_priority"].value
                if hasattr(priority_analysis["suggested_priority"], "value")
                else str(priority_analysis["suggested_priority"])
            )

            await MetricsService.log_event(
                event_type="auto_tagging_analysis",
                ticket_id=ticket_id,
                user_id=user_id,
                ai_feature="auto_tagging",
                metadata={
                    "tags_suggested": len(suggested_tags),
                    "priority_suggested": priority_value,
                    "priority_confidence": priority_analysis["confidence"],
                    "analysis_method": "semantic_bert",
                    "avg_tag_confidence": (
                        sum(tag["confidence"] for tag in suggested_tags)
                        / len(suggested_tags)
                        if suggested_tags
                        else 0
                    ),
                },
                response_time_ms=response_time,
            )

            return analysis_result

        except Exception as e:
            logger.error(f"Error in BERT-based auto-tagging analysis: {str(e)}")
            response_time = int((time.time() - start_time) * 1000)
            await MetricsService.log_event(
                event_type="auto_tagging_error",
                ticket_id=ticket_id,
                user_id=user_id,
                ai_feature="auto_tagging",
                metadata={"error": str(e), "analysis_method": "semantic_bert"},
                response_time_ms=response_time,
            )
            raise

    async def apply_suggestions(
        self,
        ticket_id: UUID,
        user_id: UUID,
        apply_tags: List[str] = None,
        apply_priority: bool = False,
    ) -> Dict[str, Any]:
        """Apply suggested tags and/or priority to a ticket"""

        results = {
            "ticket_id": str(ticket_id),
            "tags_applied": [],
            "priority_updated": False,
            "errors": [],
        }

        try:
            c = self._c()

            if apply_tags:
                for tag_name in apply_tags:
                    try:
                        # Get or create tag
                        tag_resp = exec_query(
                            c.table("tags")
                            .select("id, name")
                            .eq("name", tag_name)
                            .single()
                        )

                        tag_id = None
                        if tag_resp.data:
                            tag_id = tag_resp.data["id"]
                        else:
                            # Create new tag
                            create_resp = exec_query(
                                c.table("tags").insert(
                                    {"name": tag_name, "is_standard": False},
                                    returning="representation",
                                )
                            )
                            if create_resp.data:
                                tag_id = create_resp.data[0]["id"]

                        if tag_id:
                            try:
                                exec_query(
                                    c.table("ticket_tags").insert(
                                        {"ticket_id": str(ticket_id), "tag_id": tag_id}
                                    )
                                )
                                results["tags_applied"].append(tag_name)
                            except Exception:
                                pass  # Tag already exists on ticket

                    except Exception as e:
                        results["errors"].append(
                            f"Failed to apply tag '{tag_name}': {str(e)}"
                        )

            if apply_priority:
                analysis = await self.analyze_ticket(ticket_id, user_id)
                suggested_priority = analysis["priority_analysis"]["suggested_priority"]

                try:
                    exec_query(
                        c.table("tickets")
                        .update({"priority": suggested_priority.value})
                        .eq("id", str(ticket_id))
                    )
                    results["priority_updated"] = True
                    results["new_priority"] = suggested_priority.value
                except Exception as e:
                    results["errors"].append(f"Failed to update priority: {str(e)}")

            # Log application metrics
            await MetricsService.log_event(
                event_type="auto_tagging_applied",
                ticket_id=ticket_id,
                user_id=user_id,
                ai_feature="auto_tagging",
                metadata={
                    "tags_applied_count": len(results["tags_applied"]),
                    "priority_updated": results["priority_updated"],
                    "errors_count": len(results["errors"]),
                },
            )

            return results

        except Exception as e:
            logger.error(f"Error applying auto-tagging suggestions: {str(e)}")
            raise


# Global instance
auto_tagging_service = AutoTaggingService()

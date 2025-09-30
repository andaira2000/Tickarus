import logging
import numpy as np
import re
import time
from typing import List, Dict, Any, Optional
from uuid import UUID

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from app.models.ticket import TicketPriority
from app.services.metrics_service import MetricsService

logger = logging.getLogger(__name__)


class AutoTaggingService:
    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self._embeddings_cache = {}

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

        # Semantic priority descriptions for BERT-based classification
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

        self._precompute_tag_embeddings()

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
        if not text:
            return []

        text = text.lower()
        text = re.sub(r"[^a-z0-9\s\-]", " ", text)
        words = text.split()

        filtered_words = {
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

        return [word for word in words if len(word) > 2 and word not in filtered_words]

    def _analyze_tags(self, text: str) -> List[Dict[str, Any]]:
        """Use BERT embeddings to analyze text and suggest semantically similar tags"""
        if not text.strip():
            return []

        threshold = 0.3
        max_tags = 6

        text_embedding = self._compute_embedding(text)

        similarities = []
        for tag_name in self.tag_descriptions.keys():
            tag_embedding = self._embeddings_cache[f"tag_{tag_name}"]

            similarity_score = cosine_similarity([text_embedding], [tag_embedding])[0][
                0
            ]

            if similarity_score >= threshold:
                similarities.append(
                    {
                        "tag_name": tag_name,
                        "confidence": round(similarity_score * 100, 1),
                        "similarity_score": float(similarity_score),
                        "method": "semantic_bert",
                    }
                )

        similarities.sort(key=lambda x: x["confidence"], reverse=True)
        return similarities[:max_tags]

    def _analyze_priority_semantic(self, text: str) -> Dict[str, Any]:
        """Use BERT embeddings to analyze text and suggest priority level"""
        if not text.strip():
            return {
                "suggested_priority": TicketPriority.MEDIUM,
                "confidence": 30.0,
                "method": "default",
                "similarities": {},
            }

        text_embedding = self._compute_embedding(text)

        similarities = {}
        for priority_name in self.priority_descriptions.keys():
            priority_embedding = self._embeddings_cache[f"priority_{priority_name}"]

            similarity_score = cosine_similarity(
                [text_embedding], [priority_embedding]
            )[0][0]

            similarities[priority_name] = float(similarity_score)

        best_priority = max(similarities.keys(), key=lambda x: similarities[x])
        best_similarity = similarities[best_priority]

        priority_mapping = {
            "critical": TicketPriority.CRITICAL,
            "high": TicketPriority.HIGH,
            "medium": TicketPriority.MEDIUM,
            "low": TicketPriority.LOW,
        }

        suggested_priority = priority_mapping.get(best_priority, TicketPriority.MEDIUM)
        confidence = round(best_similarity * 100, 1)

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
        if semantic_result["confidence"] < 25:
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
    ) -> Dict[str, Any]:
        """Analyze title and description for automatic tagging and prioritization using BERT embeddings"""
        try:
            start_time = time.time()

            text_content = f"{title} {description}".strip()

            suggested_tags = self._analyze_tags(text_content)
            priority_analysis = self._analyze_priority(text_content, title)

            tag_names = [tag["tag_name"] for tag in suggested_tags]
            suggested_priority = priority_analysis["suggested_priority"].value

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


auto_tagging_service = AutoTaggingService()

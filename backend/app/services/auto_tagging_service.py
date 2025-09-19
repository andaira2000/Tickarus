import time
import re
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
import logging
from app.db.database import get_supabase, get_service_client, exec_query
from app.models.ticket import TicketPriority
from app.services.metrics_service import MetricsService

logger = logging.getLogger(__name__)


class AutoTaggingService:
    """
    Automatic tagging and prioritization service
    Analyzes ticket content to suggest tags and priority levels
    """

    def __init__(self):
        # Tag patterns: category -> (tag_names, keywords)
        self.tag_patterns = {
            "database": (["database", "db"], ["database", "db", "sql", "query", "connection", "timeout", "deadlock"]),
            "frontend": (["frontend", "ui"], ["frontend", "ui", "react", "vue", "angular", "css", "html", "javascript"]),
            "backend": (["backend", "api"], ["backend", "api", "server", "endpoint", "microservice"]),
            "infrastructure": (["infrastructure", "devops"], ["docker", "kubernetes", "aws", "cloud", "deployment", "ci/cd"]),
            "security": (["security"], ["security", "auth", "authentication", "authorization", "vulnerability", "xss"]),
            "performance": (["performance"], ["slow", "performance", "latency", "memory", "cpu", "optimization"]),
            "bug": (["bug"], ["error", "exception", "crash", "fail", "broken", "incorrect"]),
            "feature": (["feature", "enhancement"], ["feature", "enhancement", "improvement", "add", "new"]),
        }

        # Priority scoring rules
        self.priority_rules = [
            {"keywords": ["production", "outage", "down", "critical", "urgent"], "priority": TicketPriority.HIGH, "weight": 3},
            {"keywords": ["blocking", "blocker", "cannot", "unable", "broken"], "priority": TicketPriority.HIGH, "weight": 2},
            {"keywords": ["performance", "slow", "timeout", "error"], "priority": TicketPriority.MEDIUM, "weight": 1},
            {"keywords": ["enhancement", "feature", "improvement", "minor"], "priority": TicketPriority.LOW, "weight": -1},
        ]

    @staticmethod
    def _c():
        return get_supabase()

    @staticmethod
    def _service_c():
        return get_service_client()

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract and normalize keywords from text"""
        if not text:
            return []

        text = text.lower()
        text = re.sub(r'[^a-z0-9\s\-]', ' ', text)
        words = text.split()

        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'must', 'this', 'that', 'these', 'those'}

        return [word for word in words if len(word) > 2 and word not in stop_words]

    def _analyze_tags(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """Analyze keywords to suggest tags"""
        suggested_tags = []

        for category, (tag_names, tag_keywords) in self.tag_patterns.items():
            matches = 0
            matched_keywords = []

            for keyword in keywords:
                for tag_keyword in tag_keywords:
                    if tag_keyword in keyword or keyword in tag_keyword:
                        matches += 1
                        matched_keywords.append(keyword)
                        break

            if matches > 0:
                confidence = min(matches / len(tag_keywords) * 100, 90)

                for tag_name in tag_names:
                    suggested_tags.append({
                        "tag_name": tag_name,
                        "confidence": round(confidence, 1),
                        "matched_keywords": matched_keywords[:3],
                        "category": category
                    })

        # Remove duplicates and sort by confidence
        seen_tags = set()
        unique_tags = []
        for tag in sorted(suggested_tags, key=lambda x: x["confidence"], reverse=True):
            if tag["tag_name"] not in seen_tags:
                seen_tags.add(tag["tag_name"])
                unique_tags.append(tag)

        return unique_tags[:6]

    def _analyze_priority(self, keywords: List[str], title: str) -> Dict[str, Any]:
        """Analyze content to suggest priority level"""
        priority_score = 0
        matched_rules = []

        all_text = (title.lower() + " " + " ".join(keywords)).lower()

        for rule in self.priority_rules:
            matches = sum(1 for keyword in rule["keywords"] if keyword in all_text)
            if matches > 0:
                rule_score = matches * rule["weight"]
                priority_score += rule_score
                matched_rules.append({
                    "keywords": [kw for kw in rule["keywords"] if kw in all_text],
                    "weight": rule["weight"],
                    "score": rule_score
                })

        if priority_score >= 3:
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
            "score": priority_score,
            "matched_rules": matched_rules
        }

    async def analyze_ticket(self, ticket_id: UUID, user_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Analyze a ticket for automatic tagging and prioritization"""
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
            text_content = f"{title} {description}"
            keywords = self._extract_keywords(text_content)

            suggested_tags = self._analyze_tags(keywords)
            priority_analysis = self._analyze_priority(keywords, title)

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
                "keywords_analyzed": keywords[:10]
            }

            # Log metrics
            response_time = int((time.time() - start_time) * 1000)
            await MetricsService.log_event(
                event_type="auto_tagging_analysis",
                ticket_id=ticket_id,
                user_id=user_id,
                ai_feature="auto_tagging",
                metadata={
                    "tags_suggested": len(suggested_tags),
                    "priority_suggested": priority_analysis["suggested_priority"].value,
                    "priority_confidence": priority_analysis["confidence"],
                    "keywords_count": len(keywords)
                },
                response_time_ms=response_time
            )

            return analysis_result

        except Exception as e:
            logger.error(f"Error in auto-tagging analysis: {str(e)}")
            response_time = int((time.time() - start_time) * 1000)
            await MetricsService.log_event(
                event_type="auto_tagging_error",
                ticket_id=ticket_id,
                user_id=user_id,
                ai_feature="auto_tagging",
                metadata={"error": str(e)},
                response_time_ms=response_time
            )
            raise

    async def apply_suggestions(
        self,
        ticket_id: UUID,
        user_id: UUID,
        apply_tags: List[str] = None,
        apply_priority: bool = False
    ) -> Dict[str, Any]:
        """Apply suggested tags and/or priority to a ticket"""

        results = {
            "ticket_id": str(ticket_id),
            "tags_applied": [],
            "priority_updated": False,
            "errors": []
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
                                c.table("tags")
                                .insert({"name": tag_name, "is_standard": False}, returning="representation")
                            )
                            if create_resp.data:
                                tag_id = create_resp.data[0]["id"]

                        if tag_id:
                            try:
                                exec_query(
                                    c.table("ticket_tags")
                                    .insert({"ticket_id": str(ticket_id), "tag_id": tag_id})
                                )
                                results["tags_applied"].append(tag_name)
                            except Exception:
                                pass  # Tag already exists on ticket

                    except Exception as e:
                        results["errors"].append(f"Failed to apply tag '{tag_name}': {str(e)}")

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
                    "errors_count": len(results["errors"])
                }
            )

            return results

        except Exception as e:
            logger.error(f"Error applying auto-tagging suggestions: {str(e)}")
            raise


# Global instance
auto_tagging_service = AutoTaggingService()
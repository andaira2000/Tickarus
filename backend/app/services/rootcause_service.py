import time
import asyncio
from typing import List, Dict, Any, Optional
from uuid import UUID
import logging
from app.db.database import get_supabase, get_service_client, exec_query
from app.services.metrics_service import MetricsService
from app.services.llm_interface import get_llm_service, LLMMessage
from app.services.similarity_service import SimilarityService
from app.services.github_service import github_service

logger = logging.getLogger(__name__)


class RootCauseService:
    """
    Root cause analysis using pattern matching and heuristics
    For dissertation: measures accuracy of root cause suggestions
    """

    def __init__(self):
        self.similarity_service = SimilarityService()
        self.analysis_patterns = [
            {
                "pattern": ["timeout", "connection", "database", "db"],
                "root_cause": "Database connectivity issues",
                "suggestions": [
                    "Check database server status and availability",
                    "Review connection pool configuration",
                    "Verify network connectivity between services",
                    "Check for database locks or long-running queries",
                ],
            },
            {
                "pattern": ["memory", "heap", "oom", "out of memory"],
                "root_cause": "Memory exhaustion",
                "suggestions": [
                    "Analyze memory usage patterns and heap dumps",
                    "Review application memory configuration",
                    "Check for memory leaks in recent code changes",
                    "Scale up instance memory or optimize memory usage",
                ],
            },
            {
                "pattern": ["404", "not found", "missing", "endpoint"],
                "root_cause": "Missing resources or configuration",
                "suggestions": [
                    "Verify API endpoint configuration",
                    "Check routing table and URL mappings",
                    "Ensure required resources are deployed",
                    "Review recent deployment changes",
                ],
            },
            {
                "pattern": ["500", "internal server", "crash", "exception"],
                "root_cause": "Application runtime error",
                "suggestions": [
                    "Review application logs for stack traces",
                    "Check for recent code changes or deployments",
                    "Verify environment configuration",
                    "Test error reproduction in staging environment",
                ],
            },
            {
                "pattern": ["slow", "performance", "latency", "response time"],
                "root_cause": "Performance degradation",
                "suggestions": [
                    "Analyze performance metrics and bottlenecks",
                    "Review database query performance",
                    "Check system resource utilization",
                    "Optimize slow queries or inefficient code paths",
                ],
            },
            {
                "pattern": ["auth", "login", "unauthorized", "permission"],
                "root_cause": "Authentication or authorization issues",
                "suggestions": [
                    "Verify user credentials and permissions",
                    "Check authentication service status",
                    "Review access control configuration",
                    "Validate token expiration and refresh logic",
                ],
            },
        ]

    @staticmethod
    def _c():
        return get_supabase()

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from ticket content"""
        if not text:
            return []

        # Simple keyword extraction - normalize and split
        words = text.lower().replace(",", " ").replace(".", " ").split()
        # Filter out common words and short words
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
        }
        return [word for word in words if len(word) > 2 and word not in stop_words]

    def _match_patterns(self, keywords: List[str]) -> Optional[Dict[str, Any]]:
        """Match keywords against known patterns"""
        best_match = None
        best_score = 0

        for pattern_def in self.analysis_patterns:
            pattern_keywords = pattern_def["pattern"]
            matches = sum(
                1
                for keyword in keywords
                if any(pk in keyword for pk in pattern_keywords)
            )

            if matches > best_score:
                best_score = matches
                best_match = pattern_def

        return best_match if best_score > 0 else None

    async def _get_similar_resolved_tickets(
        self, ticket_text: str, ticket_id: UUID, limit: int = 3, client=None
    ) -> List[Dict[str, Any]]:
        """Find similar resolved tickets using BERT embeddings"""
        try:
            # Use similarity service to find semantically similar tickets
            similar_tickets = await self.similarity_service.find_similar_tickets(
                ticket_text=ticket_text,
                current_ticket_id=ticket_id,
                limit=limit * 3,  # Get more to filter for resolved ones
                user_id=None,  # System operation
                client=client
            )

            # Filter for only resolved/closed tickets
            resolved_tickets = [
                ticket for ticket in similar_tickets
                if ticket.get("status") in ["resolved", "closed"]
            ]

            return resolved_tickets[:limit]

        except Exception as e:
            logger.error(f"Error finding similar resolved tickets: {str(e)}")
            return []

    async def _get_commit_context_if_applicable(self, ticket: Dict, client) -> Dict:
        """Get commit context if this ticket is related to a CI failure"""
        try:
            # Check if this ticket is linked to a CI failure
            ci_failure_resp = exec_query(
                client.table("ci_failures")
                .select("*, github_repositories(full_name)")
                .eq("ticket_id", ticket["id"])
                .limit(1)
            )

            # Check if any CI failure records exist
            if not ci_failure_resp.data or len(ci_failure_resp.data) == 0:
                return {"available": False}

            ci_failure = ci_failure_resp.data[0]
            repo_full_name = ci_failure.get("github_repositories", {}).get("full_name")
            failure_time = ci_failure.get("created_at")

            if not repo_full_name or not failure_time:
                return {"available": False}

            # Parse failure time
            from datetime import datetime
            failure_datetime = datetime.fromisoformat(failure_time.replace('Z', '+00:00'))

            # Get comprehensive commit context
            commit_context = await github_service.get_commit_context_for_rootcause(
                full_name=repo_full_name,
                failure_time=failure_datetime,
                failure_logs=ci_failure.get("logs", "")
            )

            # Add CI failure context
            commit_context.update({
                "available": True,
                "ci_failure": {
                    "workflow": ci_failure.get("workflow_name"),
                    "commit_sha": ci_failure.get("commit_sha"),
                    "branch": ci_failure.get("branch_name"),
                    "failure_reason": ci_failure.get("failure_reason")
                }
            })

            return commit_context

        except Exception as e:
            logger.warning(f"Could not get commit context: {str(e)}")
            return {"available": False, "error": str(e)}

    async def analyze_ticket(
        self,
        ticket_id: UUID,
        user_id: Optional[UUID] = None,
        use_llm: bool = True,
        client=None,
    ) -> Dict[str, Any]:
        """
        Perform root cause analysis on a ticket using LLM or fallback patterns

        Args:
            ticket_id: ID of ticket to analyze
            user_id: User requesting analysis (for metrics)
            use_llm: Whether to use LLM analysis (True) or fallback patterns (False)

        Returns:
            Analysis results with root cause and suggestions
        """
        start_time = time.time()

        try:
            # Get ticket details
            c = client or self._c()
            ticket_resp = exec_query(
                c.table("tickets")
                .select("id, title, description, status, teams(name)")
                .eq("id", str(ticket_id))
                .single()
            )

            if not ticket_resp.data:
                raise Exception("Ticket not found")

            ticket = ticket_resp.data

            # Get recent comments for additional context
            comments_resp = exec_query(
                c.table("comments")
                .select("content, created_at")
                .eq("ticket_id", str(ticket_id))
                .order("created_at", desc=True)
                .limit(3)
            )
            recent_comments = comments_resp.data or []

            # Extract keywords from title and description
            text_content = f"{ticket['title']} {ticket.get('description', '')}"
            keywords = self._extract_keywords(text_content)

            # Get similar resolved tickets using BERT embeddings
            similar_tickets = await self._get_similar_resolved_tickets(
                ticket_text=text_content, ticket_id=ticket_id, client=c
            )

            # Get commit context for enhanced analysis (if this is a CI-created ticket)
            commit_context = await self._get_commit_context_if_applicable(ticket, c)

            analysis = None
            pattern_match = None

            if use_llm:
                try:
                    # Use LLM for analysis with commit context
                    analysis = await self._llm_analyze_ticket(
                        ticket, recent_comments, similar_tickets, commit_context
                    )
                except Exception as e:
                    logger.warning(
                        f"LLM analysis failed: {e}. Falling back to pattern matching."
                    )
                    use_llm = False

            if not use_llm or not analysis:
                # Fallback to pattern matching
                pattern_match = self._match_patterns(keywords)
                analysis = {
                    "root_cause": (
                        pattern_match["root_cause"]
                        if pattern_match
                        else "Unknown - requires manual investigation"
                    ),
                    "confidence_score": 0.8 if pattern_match else 0.2,
                    "suggestions": (
                        pattern_match["suggestions"]
                        if pattern_match
                        else [
                            "Review ticket details and error messages carefully",
                            "Check system logs around the time of the issue",
                            "Contact relevant team members for additional context",
                        ]
                    ),
                    "analysis_method": "pattern_matching",
                    "pattern_matched": (
                        pattern_match["pattern"] if pattern_match else None
                    ),
                }

            # Build final analysis result with commit context metadata
            final_analysis = {
                "ticket_id": str(ticket_id),
                "analysis_timestamp": time.time(),
                "root_cause": analysis["root_cause"],
                "confidence_score": analysis["confidence_score"],
                "suggestions": analysis["suggestions"],
                "similar_resolved_tickets": [
                    {"id": t["id"], "title": t["title"], "status": t["status"]}
                    for t in similar_tickets
                ],
                "keywords_analyzed": keywords[:10],
                "analysis_method": analysis.get("analysis_method", "llm"),
                "llm_used": analysis.get("analysis_method") == "llm",
                "commit_context_used": commit_context and commit_context.get("available", False),
                "commit_analysis_summary": self._summarize_commit_context(commit_context) if commit_context and commit_context.get("available") else None
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
                    "similar_tickets_found": len(similar_tickets),
                },
                response_time_ms=response_time,
                client=c,
            )

            return final_analysis

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
                response_time_ms=response_time,
                client=client or get_service_client(),
            )
            raise

    async def _llm_analyze_ticket(
        self,
        ticket: Dict[str, Any],
        recent_comments: List[Dict[str, Any]],
        similar_tickets: List[Dict[str, Any]],
        commit_context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Use LLM to analyze ticket and provide root cause analysis"""

        # Build comprehensive context for LLM including commit analysis
        context_parts = [
            f"Title: {ticket['title']}",
            f"Description: {ticket.get('description', 'No description provided')}",
            f"Status: {ticket.get('status', 'unknown')}",
            f"Team: {ticket.get('teams', {}).get('name', 'unknown') if ticket.get('teams') else 'unknown'}",
        ]

        # Add commit context if available (this is the key enhancement for Question 2)
        if commit_context and commit_context.get("available"):
            context_parts.append("\n=== CODE ANALYSIS ===")

            # Repository context
            repo_info = commit_context.get("repository", {})
            context_parts.append(f"Repository: {repo_info.get('name', 'unknown')}")
            context_parts.append(f"Primary Language: {repo_info.get('language', 'unknown')}")
            context_parts.append(f"Tech Stack: {', '.join(repo_info.get('tech_stack', []))}")

            # CI failure context
            ci_info = commit_context.get("ci_failure", {})
            if ci_info:
                context_parts.append(f"\nCI Failure Details:")
                context_parts.append(f"- Workflow: {ci_info.get('workflow', 'unknown')}")
                context_parts.append(f"- Commit SHA: {ci_info.get('commit_sha', 'unknown')}")
                context_parts.append(f"- Branch: {ci_info.get('branch', 'unknown')}")
                context_parts.append(f"- Failure Reason: {ci_info.get('failure_reason', 'unknown')}")

            # Commit analysis (the core of the enhancement)
            commit_analysis = commit_context.get("commit_analysis", {})
            if commit_analysis and not commit_analysis.get("error"):
                context_parts.append(f"\nComplete Repository Commit Analysis:")
                context_parts.append(f"- Total commits analyzed: {commit_analysis.get('total_commits', 0)}")

                # Risk indicators
                risk_indicators = commit_analysis.get("risk_indicators", [])
                if risk_indicators:
                    context_parts.append("- Risk Indicators:")
                    for risk in risk_indicators[:3]:  # Top 3 risks
                        context_parts.append(f"  • {risk}")

                # Latest commits details
                commits = commit_analysis.get("commits", [])
                if commits:
                    context_parts.append("- Latest Commits:")
                    for commit in commits[:5]:  # First 5 commits (most recent)
                        context_parts.append(f"  • {commit.get('sha', 'unknown')}: {commit.get('message', 'No message')[:100]}...")

                        # File changes
                        files = commit.get("files", [])
                        if files:
                            high_risk_files = [f for f in files if f.get("risk_level") == "high"]
                            if high_risk_files:
                                context_parts.append(f"    High-risk files: {', '.join([f['filename'] for f in high_risk_files[:3]])}")

            # Log correlation (crucial for root cause)
            correlation = commit_context.get("log_correlation", {})
            culprits = correlation.get("likely_culprits", [])
            if culprits:
                context_parts.append(f"\nLikely Culprit Commits (based on log correlation):")
                for culprit in culprits[:2]:  # Top 2 suspects
                    commit = culprit.get("commit", {})
                    confidence = culprit.get("confidence_score", 0)
                    reasons = culprit.get("reasons", [])
                    context_parts.append(f"- {commit.get('sha', 'unknown')} (confidence: {confidence}%)")
                    context_parts.append(f"  Message: {commit.get('message', 'No message')[:80]}...")
                    context_parts.append(f"  Reasons: {'; '.join(reasons[:2])}")

            # Risk assessment
            risk_assessment = commit_context.get("risk_assessment", {})
            if risk_assessment:
                context_parts.append(f"\nOverall Risk Assessment: {risk_assessment.get('level', 'unknown')} (score: {risk_assessment.get('score', 0)})")

            # Focus areas suggestions
            focus_areas = commit_context.get("suggested_focus_areas", [])
            if focus_areas:
                context_parts.append(f"\nSuggested Focus Areas:")
                for area in focus_areas[:3]:
                    context_parts.append(f"- {area}")

            # Full codebase (for dissertation with small repos)
            full_codebase = commit_context.get("full_codebase")
            if full_codebase and not full_codebase.get("error"):
                context_parts.append(f"\n=== COMPLETE REPOSITORY CODE ===")
                context_parts.append(f"Repository: {full_codebase.get('repository', 'unknown')}")
                context_parts.append(f"Branch: {full_codebase.get('branch', 'unknown')}")
                context_parts.append(f"Total files: {full_codebase.get('total_files', 0)}")
                context_parts.append(f"Total size: {full_codebase.get('total_size', 0)} bytes")

                # Add directory structure
                structure = full_codebase.get("structure", [])
                if structure:
                    context_parts.append(f"\nDirectory Structure:")
                    for item in structure[:20]:  # Show first 20 items
                        context_parts.append(f"  {item}")

                # Add file contents (prioritized by importance)
                files = full_codebase.get("files", {})
                if files:
                    context_parts.append(f"\nFile Contents:")
                    for file_path, file_info in files.items():
                        content = file_info.get("content", "")
                        if content and not content.startswith("["):  # Skip error/truncated messages
                            context_parts.append(f"\n--- {file_path} ---")
                            context_parts.append(content)
                        elif file_info.get("truncated"):
                            context_parts.append(f"\n--- {file_path} (TRUNCATED) ---")

        if recent_comments:
            context_parts.append("\n=== RECENT COMMENTS ===")
            for comment in recent_comments:
                context_parts.append(f"- {comment['content'][:200]}...")

        if similar_tickets:
            context_parts.append("\n=== SIMILAR RESOLVED TICKETS ===")
            for similar in similar_tickets[:2]:
                context_parts.append(f"- {similar['title']}")

        ticket_context = "\n".join(context_parts)

        # Create enhanced LLM prompt that leverages commit context
        has_commit_context = commit_context and commit_context.get("available")

        if has_commit_context:
            system_prompt = """You are a senior software engineer specializing in debugging and root cause analysis. You have access to comprehensive code analysis including recent commits, file changes, CI failure logs, and the COMPLETE REPOSITORY CODEBASE.

Analyze the provided information and provide:
1. A concise root cause analysis (1-2 sentences) leveraging commit history, code changes, and actual source code
2. A confidence score from 0.1 to 1.0 (higher confidence when you can see the exact code causing issues)
3. 3-5 specific, actionable troubleshooting steps based on the actual codebase

IMPORTANT INSTRUCTIONS:
- You have access to the COMPLETE REPOSITORY CODE - use this to understand the exact implementation
- Pay special attention to "Likely Culprit Commits" and cross-reference with the actual code
- Look for specific bugs, misconfigurations, or issues in the provided source code
- Consider dependencies, imports, and interactions between files
- Identify exact lines of code that might be causing issues
- Use the commit changes in context of the full codebase to understand impact
- Reference specific files, functions, and code patterns you can see
- Consider CI/CD configuration files, dependencies, and build processes

Since you can see the entire codebase, you should be able to provide highly specific and accurate root cause analysis.

Respond in JSON format:
{
  "root_cause": "Specific description of the exact code issue/bug with file references",
  "confidence_score": 0.95,
  "suggestions": [
    "Fix specific line/function in specific file",
    "Check specific configuration in specific file",
    "Investigate specific dependency/import issue",
    "Update specific test or CI configuration"
  ]
}"""
        else:
            system_prompt = """You are a senior software engineer specializing in debugging and root cause analysis.

Analyze the provided ticket information and provide:
1. A concise root cause analysis (1-2 sentences)
2. A confidence score from 0.1 to 1.0
3. 3-5 specific, actionable troubleshooting steps

Focus on the most likely technical causes based on the symptoms described. Be practical and specific in your recommendations.

Respond in JSON format:
{
  "root_cause": "Brief description of the likely root cause",
  "confidence_score": 0.85,
  "suggestions": [
    "Specific action item 1",
    "Specific action item 2",
    "Specific action item 3"
  ]
}"""

        user_prompt = f"Please analyze this ticket:\n\n{ticket_context}"

        # Get LLM service and generate response
        llm_service = get_llm_service()
        messages = [
            LLMMessage("system", system_prompt),
            LLMMessage("user", user_prompt),
        ]

        response = await llm_service.generate_response(
            messages=messages,
            max_tokens=500,
            temperature=0.3,  # Lower temperature for more consistent analysis
        )

        # Parse LLM response
        try:
            import json

            analysis_data = json.loads(response.content.strip())

            # Validate response structure
            required_fields = ["root_cause", "confidence_score", "suggestions"]
            if not all(field in analysis_data for field in required_fields):
                raise ValueError("LLM response missing required fields")

            # Ensure suggestions is a list
            if not isinstance(analysis_data["suggestions"], list):
                analysis_data["suggestions"] = [str(analysis_data["suggestions"])]

            # Clamp confidence score
            confidence = float(analysis_data["confidence_score"])
            analysis_data["confidence_score"] = max(0.1, min(1.0, confidence))

            analysis_data["analysis_method"] = "llm"
            analysis_data["token_usage"] = response.usage.get("total_tokens", 0)

            return analysis_data

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(
                f"Failed to parse LLM response: {e}. Response: {response.content[:200]}..."
            )

            # Extract text-based analysis as fallback
            content = response.content.strip()

            return {
                "root_cause": content[:200] + "..." if len(content) > 200 else content,
                "confidence_score": 0.6,  # Medium confidence for unparsed response
                "suggestions": [
                    "Review the full analysis provided by the AI",
                    "Investigate the symptoms described in the ticket",
                    "Check system logs and error messages",
                ],
                "analysis_method": "llm_unparsed",
                "token_usage": response.usage.get("total_tokens", 0),
            }

    async def submit_feedback(
        self,
        ticket_id: UUID,
        user_id: UUID,
        rating: int,
        feedback_text: Optional[str] = None,
    ):
        """Submit user feedback on root cause analysis quality"""
        await MetricsService.log_event(
            event_type="rootcause_feedback",
            ticket_id=ticket_id,
            user_id=user_id,
            ai_feature="rootcause",
            user_rating=rating,
            metadata={"feedback_text": feedback_text} if feedback_text else None,
        )

    def _summarize_commit_context(self, commit_context: Dict) -> Dict:
        """Summarize commit context for metadata"""
        if not commit_context or not commit_context.get("available"):
            return None

        summary = {}

        # Repository info
        repo_info = commit_context.get("repository", {})
        summary["repository"] = repo_info.get("name", "unknown")
        summary["language"] = repo_info.get("language", "unknown")

        # Commit analysis summary
        commit_analysis = commit_context.get("commit_analysis", {})
        if commit_analysis:
            summary["total_commits"] = commit_analysis.get("total_commits", 0)
            summary["risk_indicators_count"] = len(commit_analysis.get("risk_indicators", []))

        # Correlation summary
        correlation = commit_context.get("log_correlation", {})
        culprits = correlation.get("likely_culprits", [])
        if culprits:
            summary["likely_culprits_count"] = len(culprits)
            summary["top_culprit_confidence"] = culprits[0].get("confidence_score", 0)

        # Risk assessment
        risk_assessment = commit_context.get("risk_assessment", {})
        summary["risk_level"] = risk_assessment.get("level", "unknown")
        summary["risk_score"] = risk_assessment.get("score", 0)

        # Full codebase usage
        full_codebase = commit_context.get("full_codebase")
        summary["full_codebase_used"] = bool(full_codebase and not full_codebase.get("error"))
        if summary["full_codebase_used"]:
            summary["codebase_files_count"] = full_codebase.get("total_files", 0)
            summary["codebase_size_bytes"] = full_codebase.get("total_size", 0)

        return summary


# Global instance
rootcause_service = RootCauseService()

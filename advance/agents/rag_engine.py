from typing import List, Dict
from advance.schemas import (EvidenceTier, ConflictSeverity, ConflictResult, ModificationRequest)
from advance.agents.graph_engine import LegalKnowledgeGraph

class LegalComplianceAgent:
    """
    Implements the three-tier reasoning strategy:
    1. Vector Store: Context Generator (simulated here)
    2. Graph Store: Constraint Engine
    3. The Judge: Arbitrator

    This demonstrates the ReAct Loop pattern for legal analysis.
    """

    def __init__(self, graph: LegalKnowledgeGraph):
        self.graph = graph
        self.vector_store = self._simulate_vector_store()

    def _simulate_vector_store(self) -> Dict:
        """
        In production, this would be your actual vector database.
        Here we simulate the "soft guidance" that vector search returns.
        """
        return {
            "industry_standards": [
                {
                    "text": "ISO 27001 suggests data retention periods of up to 7 years for audit purposes.",
                    "source": "ISO_27001",
                    "similarity": 0.89,
                    "evidence_tier": EvidenceTier.INDUSTRY_GUIDANCE
                },
                {
                    "text": "Many SaaS companies retain customer data for 5-7 years for business analytics.",
                    "source": "Industry_Benchmark_Report_2024",
                    "similarity": 0.76,
                    "evidence_tier": EvidenceTier.INDUSTRY_GUIDANCE
                }
            ],
            "current_obligations": [
                {
                    "text": "Vendor A DPA Section 3.2 states retention shall not exceed MSA Section 4.2 duration.",
                    "source": "VEN_A_S3.2",
                    "similarity": 0.92,
                    "evidence_tier": EvidenceTier.CONTRACT_OBLIGATION
                }
            ]
        }

    def analyze_modification(self, request: ModificationRequest) -> Dict:
        """
        THE REACT LOOP:
        Think → Act → Observe → Reason → Conclude
        """
        vector_context = self._vector_search(request)
        graph_conflicts = self.graph.check_compliance(
            clause_id=request.clause_id,
            parameter=request.parameter,
            proposed_value=request.proposed_value
        )
        resolved_analysis = self._arbitrate(
            request=request,
            vector_context=vector_context,
            graph_conflicts=graph_conflicts
        )
        return self._build_provenance_object(
            request=request,
            analysis=resolved_analysis,
            vector_sources=vector_context,
            graph_paths=graph_conflicts
        )

    def _vector_search(self, request: ModificationRequest) -> Dict:
        """Simulate vector search for relevant context."""
        results = {
            "industry_guidance": self.vector_store["industry_standards"],
            "contractual_context": self.vector_store["current_obligations"]
        }
        return results

    def _arbitrate(self,
                   request: ModificationRequest,
                   vector_context: Dict,
                   graph_conflicts: List[ConflictResult]) -> Dict:
        """
        THE KEY INNOVATION: Resolve contradictions using Evidence Hierarchy.
        Rule: Graph Facts (1.0) > Contract Obligations (0.8) > Industry Guidance (0.4)
        """
        analysis = {
            "is_modification_safe": True,
            "overriding_concern": None,
            "contradictions_resolved": [],
            "final_recommendation": ""
        }

        if graph_conflicts:
            analysis["is_modification_safe"] = False
            critical_conflicts = [c for c in graph_conflicts
                                 if c.severity == ConflictSeverity.CRITICAL]

            if critical_conflicts:
                analysis["overriding_concern"] = {
                    "source": "GRAPH_FACT",
                    "tier": EvidenceTier.GRAPH_FACT.value,
                    "finding": critical_conflicts[0].description,
                    "instruction": "IGNORE all vector search results suggesting longer retention. GDPR Art.5 is binding law."
                }

                for industry_guidance in vector_context.get("industry_guidance", []):
                    if "7 year" in industry_guidance["text"].lower():
                        analysis["contradictions_resolved"].append({
                            "vector_claim": industry_guidance["text"],
                            "graph_fact": critical_conflicts[0].description,
                            "resolution": f"Vector result (tier {industry_guidance['evidence_tier'].value}) contradicted by Graph constraint (tier {EvidenceTier.GRAPH_FACT.value}). Graph fact prevails."
                        })

        if not analysis["is_modification_safe"]:
            analysis["final_recommendation"] = (
                f"MODIFICATION REJECTED: Proposed {request.parameter} change to "
                f"{request.proposed_value} creates {len(graph_conflicts)} compliance conflicts. "
                f"Primary issue: {analysis['overriding_concern']['finding']}"
            )
        else:
            analysis["final_recommendation"] = (
                f"MODIFICATION APPROVED: No conflicts detected in graph traversal. "
                f"However, review all vendor agreements referencing {request.clause_id}."
            )

        return analysis

    def _build_provenance_object(self,
                                 request: ModificationRequest,
                                 analysis: Dict,
                                 vector_sources: Dict,
                                 graph_paths: List[ConflictResult]) -> Dict:
        """Return structured provenance, not just text."""
        provenance = {
            "query": {
                "clause": request.clause_id,
                "parameter": request.parameter,
                "proposed_value": request.proposed_value
            },
            "answer": analysis["final_recommendation"],
            "evidence": {
                "graph_paths": [
                    {
                        "path": " → ".join(conflict.path.nodes),
                        "edges": conflict.path.edges,
                        "terminal_entity": conflict.path.terminal_node,
                        "evidence_tier": conflict.path.evidence_tier.value,
                        "severity": conflict.severity.value,
                        "finding": conflict.description,
                        "remediation": conflict.remediation
                    }
                    for conflict in graph_paths
                ],
                "vector_context": [
                    {
                        "source": source.get("source", "unknown"),
                        "excerpt": source.get("text", ""),
                        "similarity": source.get("similarity", 0),
                        "evidence_tier": source.get("evidence_tier", EvidenceTier.INDUSTRY_GUIDANCE).value,
                        "was_overridden": any(
                            source["text"] in c.get("vector_claim", "")
                            for c in analysis.get("contradictions_resolved", [])
                        )
                    }
                    for category in vector_sources.values()
                    for source in category
                ],
                "contradictions_resolved": analysis.get("contradictions_resolved", []),
                "reasoning": (
                    f"Graph traversal detected {len(graph_paths)} constraint violations. "
                    f"Vector search returned industry guidance suggesting longer retention is acceptable, "
                    f"but these were overridden by binding regulatory constraints (Evidence Tier 1.0). "
                    f"Final determination: {'SAFE' if analysis['is_modification_safe'] else 'UNSAFE'}."
                )
            },
            "methodology": {
                "approach": "Hybrid Reasoning Engine (Vector + Graph + Arbitration)",
                "vector_store": "Semantic search for contextual recall",
                "graph_engine": "Bounded traversal for constraint enforcement",
                "arbitration": "Evidence hierarchy: Graph Facts > Contract Obligations > Industry Guidance",
                "stop_conditions": [
                    "Max traversal depth: 3",
                    "Stop on regulatory nodes (GDPR articles)",
                    "Stop on vendor agreement nodes"
                ]
            }
        }
        return provenance
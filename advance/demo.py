"""
Demonstration of the Legal Compliance Graph RAG SDK.
Shows the full workflow: ingest → analyze → provenance.
"""
from advance.schemas import ModificationRequest
from advance.agents.graph_engine import LegalKnowledgeGraph
from advance.agents.rag_engine import LegalComplianceAgent


def main():
    print("=" * 80)
    print("LEGAL GRAPH RAG: Compliance Conflict Detection Engine")
    print("=" * 80)

    kg = LegalKnowledgeGraph()
    agent = LegalComplianceAgent(kg)

    modification = ModificationRequest(
        clause_id="MSA_S4.2",
        parameter="duration_years",
        proposed_value=7,
        current_value=3
    )

    print(f"\nQUERY: Modify {modification.clause_id}")
    print(f"CHANGE: {modification.parameter} from {modification.current_value} to {modification.proposed_value}")
    print()

    result = agent.analyze_modification(modification)

    print("─" * 80)
    print("RESULT:")
    print("─" * 80)
    print(f"\n✅ / ❌ DECISION: {result['answer']}\n")

    print("─" * 80)
    print("GRAPH TRAVERSAL PATHS (The Constraint Engine):")
    print("─" * 80)
    for i, path in enumerate(result['evidence']['graph_paths'], 1):
        print(f"\nPath {i}: {path['path']}")
        print(f"  Severity: {path['severity']}")
        print(f"  Evidence Tier: {path['evidence_tier']}")
        print(f"  Finding: {path['finding']}")
        print(f"  Remediation: {path['remediation']}")

    print("\n" + "─" * 80)
    print("VECTOR SEARCH RESULTS (The Context Generator):")
    print("─" * 80)
    for i, source in enumerate(result['evidence']['vector_context'], 1):
        print(f"\nSource {i}: {source['source']}")
        print(f"  Similarity: {source['similarity']}")
        print(f"  Evidence Tier: {source['evidence_tier']}")
        print(f"  Excerpt: {source['excerpt']}")
        if source['was_overridden']:
            print(f"  ⚠️  OVERRIDDEN by Graph Constraint (higher evidence tier)")

    print("\n" + "─" * 80)
    print("CONTRADICTIONS RESOLVED:")
    print("─" * 80)
    for i, contradiction in enumerate(result['evidence']['contradictions_resolved'], 1):
        print(f"\nContradiction {i}:")
        print(f"  Vector Claim: {contradiction['vector_claim']}")
        print(f"  Graph Fact: {contradiction['graph_fact']}")
        print(f"  Resolution: {contradiction['resolution']}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
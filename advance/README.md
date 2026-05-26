# Copied from other linkedin users guide

A hybrid reasoning engine combining Vector RAG with Graph RAG for legal compliance analysis.

## Features

- **LegalKnowledgeGraph**: Stores and queries structured legal relationships
- **LegalComplianceAgent**: Three-tier reasoning (Vector search → Graph traversal → Arbitration)
- **Evidence Hierarchy**: Graph Facts (1.0) > Contract Obligations (0.8) > Industry Guidance (0.4)
- **Provenance**: Complete audit trail for all analyses

## Quick Start

```python
from advance import LegalKnowledgeGraph, LegalComplianceAgent, ModificationRequest

kg = LegalKnowledgeGraph()
agent = LegalComplianceAgent(kg)

request = ModificationRequest(
    clause_id="MSA_S4.2",
    parameter="duration_years",
    proposed_value=7,
    current_value=3
)

result = agent.analyze_modification(request)
```

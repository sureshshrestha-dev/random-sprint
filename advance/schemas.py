from typing import List, Dict
from dataclasses import dataclass, field
from enum import Enum

class EvidenceTier(Enum):
    """Priority levels for information sources"""
    GRAPH_FACT = 1.0      # Immutable legal constraints
    CONTRACT_OBLIGATION = 0.8  # Binding agreements
    INDUSTRY_GUIDANCE = 0.4    # Soft recommendations

class ConflictSeverity(Enum):
    CRITICAL = "CRITICAL"  # Legal violation
    HIGH = "HIGH"         # Contractual breach
    MEDIUM = "MEDIUM"     # Requires amendment
    LOW = "LOW"           # Advisory notice

@dataclass
class GraphNode:
    """Represents an entity in our knowledge graph"""
    id: str
    type: str  # "clause", "policy", "regulation", "vendor", "threshold"
    properties: Dict = field(default_factory=dict)

@dataclass
class TraversalPath:
    """Records the path taken through the graph"""
    nodes: List[str]
    edges: List[str]
    depth: int
    terminal_node: str
    evidence_tier: EvidenceTier

@dataclass
class ConflictResult:
    """The final structured output - Chain of Evidence"""
    path: TraversalPath
    severity: ConflictSeverity
    description: str
    remediation: str

@dataclass
class ModificationRequest:
    """What the user wants to change"""
    clause_id: str
    parameter: str
    proposed_value: any
    current_value: any = None
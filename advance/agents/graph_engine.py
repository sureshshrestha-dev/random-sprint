import networkx as nx
from typing import List, Dict, Set
from advance.schemas import (EvidenceTier, ConflictSeverity, TraversalPath, ConflictResult)

class LegalKnowledgeGraph:
    """
    Stores the structured relationships between legal entities.
    This is our "Constraint Engine" - it enforces logical relationships.
    """
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self._build_dummy_legal_ecosystem()
    
    def _build_dummy_legal_ecosystem(self):
        """
        Build a realistic but minimal legal contract ecosystem.
        This represents what we'd extract from real documents using Gemini.
        """
        
        # === NODES: The Entities ===
        
        # Master Service Agreement clauses
        self.graph.add_node("MSA_S4.2", 
                           type="clause",
                           title="Data Retention Period",
                           current_duration_years=3,
                           document="Master Service Agreement v2.1")
        
        self.graph.add_node("MSA_S4.3", 
                           type="clause",
                           title="Data Deletion Upon Termination",
                           document="Master Service Agreement v2.1")
        
        # Data Retention Policy
        self.graph.add_node("POL_RET_3.1", 
                           type="policy",
                           title="Data Retention Policy",
                           max_retention_years=3,
                           justification="GDPR Art.5 compliance",
                           document="Internal Policy v3.1")
        
        # Vendor Agreements
        self.graph.add_node("VEN_A_DPA", 
                           type="vendor_agreement",
                           vendor="CloudStorage Corp",
                           title="Data Processing Agreement",
                           document="DPA-2024-001")
        
        self.graph.add_node("VEN_A_S3.2", 
                           type="clause",
                           title="Storage Limitation Clause",
                           retention_limit_years=3,
                           references="MSA_S4.2",
                           document="DPA-2024-001")
        
        self.graph.add_node("VEN_B_DPA", 
                           type="vendor_agreement",
                           vendor="AnalyticsPro Ltd",
                           title="Data Processing Agreement",
                           document="DPA-2024-002")
        
        self.graph.add_node("VEN_B_S2.1", 
                           type="clause",
                           title="Data Processing Duration",
                           retention_limit_years=5,  # Note: Different from Vendor A!
                           references="POL_RET_3.1",
                           document="DPA-2024-002")
        
        # Regulatory Framework
        self.graph.add_node("GDPR_ART5", 
                           type="regulation",
                           title="GDPR Article 5 - Data Minimization",
                           principle="Storage Limitation",
                           max_retention="No longer than necessary",
                           binding=True)
        
        self.graph.add_node("GDPR_ART28", 
                           type="regulation",
                           title="GDPR Article 28 - Processor Obligations",
                           requires_dpa=True,
                           binding=True)
        
        self.graph.add_node("GDPR_SCC", 
                           type="regulation",
                           title="Standard Contractual Clauses",
                           requires_update_on_change=True,
                           binding=True)
        
        # Industry Standards (Soft guidance)
        self.graph.add_node("ISO_27001", 
                           type="guidance",
                           title="ISO 27001 - Data Retention Guidelines",
                           recommended_max_years=7,
                           binding=False)
        
        # === EDGES: The Relationships ===
        # These are the Knowledge Triplets extracted from documents
        
        # Contract references
        self.graph.add_edge("MSA_S4.2", "POL_RET_3.1", 
                           relation="specifies_duration_in",
                           weight=1.0)
        
        self.graph.add_edge("VEN_A_DPA", "VEN_A_S3.2", 
                           relation="contains_clause",
                           weight=1.0)
        
        self.graph.add_edge("VEN_B_DPA", "VEN_B_S2.1", 
                           relation="contains_clause",
                           weight=1.0)
        
        # Cross-references between agreements
        self.graph.add_edge("VEN_A_S3.2", "MSA_S4.2", 
                           relation="mirrors_obligation_of",
                           weight=1.0)
        
        self.graph.add_edge("VEN_B_S2.1", "POL_RET_3.1", 
                           relation="implements",
                           weight=1.0)
        
        # Regulatory compliance
        self.graph.add_edge("POL_RET_3.1", "GDPR_ART5", 
                           relation="must_comply_with",
                           weight=1.0)
        
        self.graph.add_edge("VEN_A_DPA", "GDPR_ART28", 
                           relation="must_comply_with",
                           weight=1.0)
        
        self.graph.add_edge("VEN_B_DPA", "GDPR_ART28", 
                           relation="must_comply_with",
                           weight=1.0)
        
        # Regulatory requirements
        self.graph.add_edge("GDPR_ART28", "GDPR_SCC", 
                           relation="requires",
                           weight=1.0)
        
        # Soft guidance (lower weight)
        self.graph.add_edge("ISO_27001", "GDPR_ART5", 
                           relation="aligns_with",
                           weight=0.4)
        
        # Termination connections
        self.graph.add_edge("MSA_S4.3", "VEN_A_S3.2", 
                           relation="triggers_obligation_in",
                           weight=1.0)
        self.graph.add_edge("MSA_S4.3", "VEN_B_S2.1", 
                           relation="triggers_obligation_in",
                           weight=1.0)
    
    def traverse(self, 
                 start_nodes: List[str], 
                 max_depth: int = 3,
                 allowed_relations: List[str] = None,
                 stop_on_types: List[str] = None) -> List[TraversalPath]:
        """
        Bounded graph traversal with intelligent stopping criteria.
        
        Args:
            start_nodes: Where to begin the traversal
            max_depth: Hard cap on traversal depth (prevents graph explosion)
            allowed_relations: Filter to specific edge types
            stop_on_types: Stop when reaching these node types (e.g., "regulation")
        
        Returns:
            List of discovered paths with evidence
        """
        paths = []
        
        for start_node in start_nodes:
            # Breadth-first traversal with depth limit
            visited = set()
            queue = [(start_node, [start_node], [], 0)]  # (current, node_path, edge_path, depth)
            
            while queue:
                current_node, node_path, edge_path, depth = queue.pop(0)
                
                if depth > max_depth:
                    continue
                
                if current_node in visited:
                    continue
                
                visited.add(current_node)
                
                # Check stopping criteria - have we reached a terminal?
                node_data = self.graph.nodes.get(current_node, {})
                node_type = node_data.get("type", "")
                
                if stop_on_types and node_type in stop_on_types:
                    # We've reached a regulatory anchor or terminal entity
                    tier = self._determine_evidence_tier(node_data)
                    paths.append(TraversalPath(
                        nodes=node_path,
                        edges=edge_path,
                        depth=depth,
                        terminal_node=current_node,
                        evidence_tier=tier
                    ))
                    continue  # Don't traverse further from regulatory nodes
                
                # Explore neighbors
                for neighbor in self.graph.successors(current_node):
                    if neighbor not in visited:
                        edge_data = self.graph.get_edge_data(current_node, neighbor)
                        relation = edge_data.get("relation", "unknown")
                        
                        # Filter by allowed relations if specified
                        if allowed_relations and relation not in allowed_relations:
                            continue
                        
                        new_node_path = node_path + [neighbor]
                        new_edge_path = edge_path + [f"{current_node} --{relation}--> {neighbor}"]
                        queue.append((neighbor, new_node_path, new_edge_path, depth + 1))
        
        return paths
    
    def _determine_evidence_tier(self, node_data: Dict) -> EvidenceTier:
        """Classify the reliability of a graph node"""
        node_type = node_data.get("type", "")
        binding = node_data.get("binding", False)
        
        if node_type == "regulation" and binding:
            return EvidenceTier.GRAPH_FACT
        elif node_type in ["clause", "vendor_agreement", "policy"]:
            return EvidenceTier.CONTRACT_OBLIGATION
        else:
            return EvidenceTier.INDUSTRY_GUIDANCE
    
    def check_compliance(self, 
                         clause_id: str, 
                         parameter: str, 
                         proposed_value: any) -> List[ConflictResult]:
        """
        THE CORE LOGIC: Check if a proposed modification violates any constraints.
        
        This is the "What-If" analysis engine.
        """
        conflicts = []
        
        # Get the current state of the clause
        if clause_id not in self.graph.nodes:
            return [ConflictResult(
                path=TraversalPath([], [], 0, clause_id, EvidenceTier.GRAPH_FACT),
                severity=ConflictSeverity.CRITICAL,
                description=f"Clause {clause_id} not found in knowledge graph",
                remediation="Verify clause ID and document extraction"
            )]
        
        clause_data = self.graph.nodes[clause_id]
        
        # Find all paths from this clause to regulatory constraints
        paths = self.traverse(
            start_nodes=[clause_id],
            max_depth=3,
            stop_on_types=["regulation", "vendor_agreement"]
        )
        
        for path in paths:
            terminal_node = path.terminal_node
            terminal_data = self.graph.nodes.get(terminal_node, {})
            
            # Check GDPR Article 5 - Storage Limitation
            if terminal_node == "GDPR_ART5":
                if parameter == "duration_years" and proposed_value > 3:
                    # This is the critical conflict detection
                    conflicts.append(ConflictResult(
                        path=path,
                        severity=ConflictSeverity.CRITICAL,
                        description=f"Proposed duration ({proposed_value} years) exceeds GDPR Art.5 storage limitation principle. Current limit: {clause_data.get('current_duration_years', 'undefined')} years.",
                        remediation=f"Either (a) reduce retention to ≤3 years and document necessity, or (b) prepare Article 5(1)(e) derogation justification for {proposed_value} years."
                    ))
            
            # Check GDPR Article 28 - Processor obligations
            if terminal_node == "GDPR_ART28":
                # Any modification to clauses referenced by DPAs triggers Art.28 review
                conflicts.append(ConflictResult(
                    path=path,
                    severity=ConflictSeverity.HIGH,
                    description=f"Modification to {clause_id} is referenced by vendor Data Processing Agreements. GDPR Art.28 requires processor obligations to be explicitly defined.",
                    remediation="Review and potentially renegotiate all DPAs that reference this clause. Update GDPR Art.28 compliance documentation."
                ))
            
            # Check vendor-specific constraints
            if terminal_node.startswith("VEN_"):
                vendor_name = terminal_data.get("vendor", "Unknown Vendor")
                conflicts.append(ConflictResult(
                    path=path,
                    severity=ConflictSeverity.HIGH,
                    description=f"Vendor {vendor_name} has contractual obligations linked to this clause. Modification may breach existing DPA terms.",
                    remediation=f"Review DPA with {vendor_name}. Initiate change management process for contract amendment."
                ))
        
        return conflicts

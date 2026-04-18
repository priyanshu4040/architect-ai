from typing import List, Literal, Optional, Dict
from pydantic import BaseModel, Field

class NodeFault(BaseModel):
    fault: str = Field(description="Description of the fault.")
    severity: str = Field(description="Severity of the fault (high/medium/low).")
    evidence: str = Field(description="Evidence from the AST or README.")
    impact: str = Field(description="Impact of the fault.")

class OldVsNew(BaseModel):
    dimension: str
    current_state: str
    proposed_state: str
    benefit: str

class ExpectedImprovement(BaseModel):
    metric: str = Field(description="Metric being improved (e.g. maintainability, scalability)")
    current_baseline: str
    target_outcome: str
    why_it_improves: str

class ComponentDetail(BaseModel):
    component: str = Field(description="Exact name of the component from the architecture graph.")
    functionality: str = Field(description="2-4 sentence concrete behavior/responsibility for the system.")
    inputs: List[str] = Field(description="List of inputs to this component.", default_factory=list)
    outputs: List[str] = Field(description="List of outputs from this component.", default_factory=list)
    dependencies: List[str] = Field(description="List of dependencies for this component.", default_factory=list)

class ComponentLayerMapping(BaseModel):
    component: str
    layer: str = Field(description="The architectural layer (e.g., presentation, business, data, infrastructure, shared, specific domain).")
    reason: str
    confidence: int = Field(ge=0, le=100)

class RecommendedPattern(BaseModel):
    pattern: str
    why: str
    confidence: int = Field(ge=0, le=100)
    tags: List[str] = Field(default_factory=list)

class KeyDecision(BaseModel):
    decision: str
    rationale: str
    alternatives: List[str] = Field(default_factory=list)

class RiskAnalysis(BaseModel):
    risk: str
    severity: str = Field(description="high/medium/low")
    impact: str
    likelihood: str = Field(description="high/medium/low")
    mitigation: str

class EvolutionRoadmap(BaseModel):
    phase: str
    timeframe: str
    goals: List[str] = Field(default_factory=list)
    deliverables: List[str] = Field(default_factory=list)

class IndicatorsNotes(BaseModel):
    scalability: str = ""
    performance: str = ""
    maintainability: str = ""
    security: str = ""

class Indicators(BaseModel):
    scalability: int = Field(ge=0, le=100, default=0)
    performance: int = Field(ge=0, le=100, default=0)
    maintainability: int = Field(ge=0, le=100, default=0)
    security: int = Field(ge=0, le=100, default=0)
    notes: IndicatorsNotes = Field(default_factory=IndicatorsNotes)

class ArchitectureOutput(BaseModel):
    current_codebase_faults: Optional[List[NodeFault]] = Field(default_factory=list)
    comparison_old_vs_new: Optional[List[OldVsNew]] = Field(default_factory=list)
    expected_improvements: Optional[List[ExpectedImprovement]] = Field(default_factory=list)
    component_details: List[ComponentDetail] = Field(default_factory=list)
    component_layer_mapping: List[ComponentLayerMapping] = Field(default_factory=list)
    recommended_patterns: List[RecommendedPattern] = Field(default_factory=list)
    key_decisions: List[KeyDecision] = Field(default_factory=list)
    risk_analysis: List[RiskAnalysis] = Field(default_factory=list)
    evolution_roadmap: List[EvolutionRoadmap] = Field(default_factory=list)
    indicators: Indicators = Field(default_factory=Indicators)

"""
Mode-specific structured API payloads (frontend-friendly sections).
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class SuggestedArchitecture(BaseModel):
    frontend: str = Field(default="")
    backend: str = Field(default="")
    database: str = Field(default="")
    authentication: str = Field(default="")
    deployment: str = Field(default="")


class GreenfieldStructuredOutput(BaseModel):
    project_summary: str = ""
    detected_domain: str = ""
    assumptions: List[str] = Field(default_factory=list)
    functional_requirements: List[str] = Field(default_factory=list)
    non_functional_requirements: List[str] = Field(default_factory=list)
    suggested_architecture: SuggestedArchitecture = Field(default_factory=SuggestedArchitecture)
    modules: List[str] = Field(default_factory=list)
    api_suggestions: List[str] = Field(default_factory=list)
    database_entities: List[str] = Field(default_factory=list)
    security_suggestions: List[str] = Field(default_factory=list)
    scalability_suggestions: List[str] = Field(default_factory=list)
    architecture_flow: List[str] = Field(default_factory=list)
    final_summary: str = ""


# --- Brownfield v2 nested models ---

class StackField(BaseModel):
    value: str = ""
    evidence: List[str] = Field(default_factory=list)


class DetectedStack(BaseModel):
    frontend: str = ""
    backend: str = ""
    database: str = ""
    authentication: str = ""
    deployment: List[str] = Field(default_factory=list)
    api_style: str = ""


class DetectedModuleItem(BaseModel):
    name: str = ""
    type: str = "unknown"
    path: str = ""
    evidence: str = ""
    confidence: str = "high"


class SuggestedModuleItem(BaseModel):
    name: str = ""
    reason: str = ""
    priority: str = "medium"


class FolderAnalysisItem(BaseModel):
    folder: str = ""
    purpose: str = ""
    quality: str = ""
    suggestion: str = ""


class DetectedApiItem(BaseModel):
    method: str = ""
    path: str = ""
    file: str = ""
    purpose: str = ""
    evidence: str = ""


class IssueItem(BaseModel):
    issue: str = ""
    severity: str = ""
    reason: str = ""
    suggested_fix: str = ""
    affected_area: str = ""
    evidence: str = ""
    affected_file_or_folder: str = ""


class SecurityIssueItem(BaseModel):
    issue: str = ""
    severity: str = ""
    reason: str = ""
    suggested_fix: str = ""


class EvolutionPlan(BaseModel):
    immediate_fixes: List[str] = Field(default_factory=list)
    short_term_improvements: List[str] = Field(default_factory=list)
    long_term_improvements: List[str] = Field(default_factory=list)


class BrownfieldLlmEnrichment(BaseModel):
    """LLM fills review fields only — detected_* come from the ZIP parser."""

    project_summary: str = ""
    suggested_modules: List[SuggestedModuleItem] = Field(default_factory=list)
    architecture_issues: List[IssueItem] = Field(default_factory=list)
    security_issues: List[SecurityIssueItem] = Field(default_factory=list)
    scalability_issues: List[SecurityIssueItem] = Field(default_factory=list)
    maintainability_issues: List[SecurityIssueItem] = Field(default_factory=list)
    improvement_suggestions: List[str] = Field(default_factory=list)
    evolution_plan: EvolutionPlan = Field(default_factory=EvolutionPlan)
    final_summary: str = ""


class DetectedTechStackDetail(BaseModel):
    languages: List[str] = Field(default_factory=list)
    language_percentages: Dict[str, float] = Field(default_factory=dict)
    frameworks: List[str] = Field(default_factory=list)
    libraries: List[str] = Field(default_factory=list)
    databases: List[str] = Field(default_factory=list)
    build_tools: List[str] = Field(default_factory=list)
    deployment: List[str] = Field(default_factory=list)
    package_managers: List[str] = Field(default_factory=list)
    evidence: Dict[str, List[str]] = Field(default_factory=dict)
    confidence: Dict[str, str] = Field(default_factory=dict)
    folder_structure: List[str] = Field(default_factory=list)
    validation_message: str = ""


class BrownfieldStructuredOutput(BaseModel):
    project_summary: str = ""
    detected_tech_stack: DetectedTechStackDetail = Field(default_factory=DetectedTechStackDetail)
    detected_stack: DetectedStack = Field(default_factory=DetectedStack)
    folder_analysis: List[FolderAnalysisItem] = Field(default_factory=list)
    detected_modules: List[DetectedModuleItem] = Field(default_factory=list)
    suggested_modules: List[SuggestedModuleItem] = Field(default_factory=list)
    detected_apis: List[DetectedApiItem] = Field(default_factory=list)
    architecture_issues: List[IssueItem] = Field(default_factory=list)
    security_issues: List[SecurityIssueItem] = Field(default_factory=list)
    scalability_issues: List[SecurityIssueItem] = Field(default_factory=list)
    maintainability_issues: List[SecurityIssueItem] = Field(default_factory=list)
    improvement_suggestions: List[str] = Field(default_factory=list)
    evolution_plan: EvolutionPlan = Field(default_factory=EvolutionPlan)
    final_summary: str = ""


class AnalysisInsightOutput(BaseModel):
    project_summary: str = ""
    detected_domain: str = ""
    actors: List[str] = Field(default_factory=list)
    functional_requirements: List[str] = Field(default_factory=list)
    non_functional_requirements: List[str] = Field(default_factory=list)
    expected_traffic: str = ""
    data_entities: List[str] = Field(default_factory=list)
    integrations: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    detected_stack: List[str] = Field(default_factory=list)
    folder_observations: List[str] = Field(default_factory=list)
    detected_routes: List[str] = Field(default_factory=list)
    architecture_smells: List[str] = Field(default_factory=list)
    security_gaps: List[str] = Field(default_factory=list)
    scalability_concerns: List[str] = Field(default_factory=list)


# --- Modification flow ---

class ImpactAnalysis(BaseModel):
    frontend_impact: str = ""
    backend_impact: str = ""
    database_impact: str = ""
    security_impact: str = ""
    deployment_impact: str = ""


class ModifyArchitectureOutput(BaseModel):
    updated_architecture: dict = Field(default_factory=dict)
    changes_applied: List[str] = Field(default_factory=list)
    reasoning: List[str] = Field(default_factory=list)
    impact_analysis: ImpactAnalysis = Field(default_factory=ImpactAnalysis)
    final_summary: str = ""


# --- Greenfield requirement builder ---

class RequirementCompileOutput(BaseModel):
    requirement_source: str = "manual"
    project_type: str = ""
    users: List[str] = Field(default_factory=list)
    functional_requirements: List[str] = Field(default_factory=list)
    non_functional_requirements: List[str] = Field(default_factory=list)
    preferred_stack: str = ""
    project_level: str = ""
    deployment_preference: str = ""
    generated_requirement_summary: str = ""

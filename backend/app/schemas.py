from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    mode: Literal["greenfield", "brownfield"]
    input: str = Field(..., min_length=1, description="Requirements text, code, or path.")


class GreenfieldRequest(BaseModel):
    requirements: str = Field(..., min_length=1)


class BrownfieldRequest(BaseModel):
    input: str = Field(..., min_length=1, description="Code snippet, description, or local path.")


class MemoryTrainRequest(BaseModel):
    path: str = Field(..., min_length=1)


class MemoryForgetRequest(BaseModel):
    path: str = Field(..., min_length=1, description="Exact trained path or 'all'.")


class GraphNode(BaseModel):
    id: str
    label: str
    type: Optional[str] = None
    description: Optional[str] = None
    group: Optional[int] = None


class GraphEdge(BaseModel):
    source: str
    target: str
    label: Optional[str] = None


class GraphPayload(BaseModel):
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    mode: Literal["greenfield", "brownfield"]
    analysis_report: str = ""
    architecture_plan: str = ""
    ast_summary: str = ""
    graph: GraphPayload = Field(default_factory=GraphPayload)
    memory_used: str = ""
    warning: str = ""


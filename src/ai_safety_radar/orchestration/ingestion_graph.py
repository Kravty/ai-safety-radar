from typing import TypedDict, Optional, Any
from langgraph.graph import StateGraph, END
import logging

from ..models.raw_document import RawDocument
from ..models.threat_signature import ThreatSignature
from ..agents.filter_agent import FilterAgent
from ..agents.extraction_agent import ExtractionAgent
from ..persistence.dataset_manager import DatasetManager
from ..utils.llm_client import LLMClient

logger = logging.getLogger(__name__)

class IngestionState(TypedDict):
    doc: RawDocument
    is_relevant: bool
    threat_signature: Optional[ThreatSignature]

class IngestionGraph:
    """Per-document ingestion workflow."""
    
    def __init__(self) -> None:
        llm_client = LLMClient()
        self.filter_agent = FilterAgent(llm_client)
        self.extraction_agent = ExtractionAgent(llm_client)
        self.dataset_manager = DatasetManager()
        
        self.workflow = self._build_graph()
        
    def _build_graph(self) -> Any:
        workflow = StateGraph(IngestionState)
        
        # Nodes
        workflow.add_node("filter", self.filter_node)
        workflow.add_node("extract", self.extraction_node)
        workflow.add_node("save", self.save_node)
        
        # Edges
        workflow.set_entry_point("filter")
        
        workflow.add_conditional_edges(
            "filter",
            self.check_relevance,
            {
                "relevant": "extract",
                "irrelevant": END
            }
        )
        
        workflow.add_conditional_edges(
            "extract",
            self.check_extraction,
            {
                "success": "save",
                "failed": END
            }
        )
        
        workflow.add_edge("save", END)
        
        return workflow.compile()
        
    async def filter_node(self, state: IngestionState) -> IngestionState:
        res = await self.filter_agent.analyze(state["doc"].title, state["doc"].content[:5000])
        return {**state, "is_relevant": res.is_relevant}
        
    async def extraction_node(self, state: IngestionState) -> IngestionState:
        sig = await self.extraction_agent.process(state["doc"])
        return {**state, "threat_signature": sig}
        
    def save_node(self, state: IngestionState) -> IngestionState:
        if state["threat_signature"]:
            self.dataset_manager.save_threats([state["threat_signature"]])
        return state
        
    def check_relevance(self, state: IngestionState) -> str:
        return "relevant" if state["is_relevant"] else "irrelevant"
        
    def check_extraction(self, state: IngestionState) -> str:
        return "success" if state["threat_signature"] else "failed"

    async def run(self, doc: RawDocument) -> None:
        initial_state = IngestionState(doc=doc, is_relevant=False, threat_signature=None)
        await self.workflow.invoke(initial_state)

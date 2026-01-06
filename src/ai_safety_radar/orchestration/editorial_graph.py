from typing import TypedDict, Optional, List, Any, cast
from langgraph.graph import StateGraph, END
import logging

from ..models.threat_signature import ThreatSignature
from ..agents.curator_agent import CuratorAgent, DailyBriefing
from ..agents.critic_agent import CriticAgent, CritiqueResult
from ..utils.llm_client import LLMClient

logger = logging.getLogger(__name__)

class EditorialState(TypedDict):
    threats: List[ThreatSignature]
    previous_summary: str
    current_briefing: Optional[DailyBriefing]
    critique_result: Optional[CritiqueResult]
    retry_count: int
    final_output: Optional[DailyBriefing]

class EditorialGraph:
    """Daily batch editorial workflow."""
    
    MAX_RETRIES = 3
    
    def __init__(self) -> None:
        # Use analysis model (gpt-5-mini) for curator and critic
        analysis_client = LLMClient(role="analysis")
        self.curator_agent = CuratorAgent(analysis_client)
        self.critic_agent = CriticAgent(analysis_client)
        
        self.workflow = self._build_graph()
        
    def _build_graph(self) -> Any:
        workflow = StateGraph(EditorialState)
        
        # Nodes
        workflow.add_node("draft", self.draft_node)
        workflow.add_node("critique", self.critique_node)
        workflow.add_node("revise", self.revise_node)
        
        # Edges
        workflow.set_entry_point("draft")
        
        workflow.add_edge("draft", "critique")
        
        workflow.add_conditional_edges(
            "critique",
            self.check_approval,
            {
                "approved": END,
                "rejected": "revise",
                "max_retries": END
            }
        )
        
        workflow.add_edge("revise", "critique")
        
        return workflow.compile()
        
    async def draft_node(self, state: EditorialState) -> EditorialState:
        briefing = await self.curator_agent.draft_briefing(state["threats"], state["previous_summary"])
        return {**state, "current_briefing": briefing, "retry_count": 0}
        
    async def critique_node(self, state: EditorialState) -> EditorialState:
        if not state["current_briefing"]:
            raise ValueError("No briefing to critique")
        
        result = await self.critic_agent.critique(state["current_briefing"], state["threats"])
        
        if result.is_approved:
            return {**state, "critique_result": result, "final_output": state["current_briefing"]}
        else:
            return {**state, "critique_result": result}
            
    async def revise_node(self, state: EditorialState) -> EditorialState:
        if not state["current_briefing"] or not state["critique_result"]:
            raise ValueError("Missing briefing or critique for revision")
            
        new_briefing = await self.curator_agent.revise_briefing(state["current_briefing"], state["critique_result"].feedback)
        return {**state, "current_briefing": new_briefing, "retry_count": state["retry_count"] + 1}
        
    def check_approval(self, state: EditorialState) -> str:
        if not state["critique_result"]:
            return "max_retries" # Should not happen
            
        if state["critique_result"].is_approved:
            return "approved"
            
        if state["retry_count"] >= self.MAX_RETRIES:
            logger.warning("Max retries reached in Editorial Graph. Accepting last draft despite rejection.")
            # We must set final_output here if we exit, or we handle it in caller.
            # But the graph returns state. We can update it? 
            # Conditional edge function can't modify state.
            # So if we exit, final_output might be None if we didn't set it.
            # However, typically you'd have a node to finalize.
            # For simplicity, if we hit max retries, we just end. Caller uses current_briefing.
            return "max_retries"
            
        return "rejected"

    async def run(self, threats: List[ThreatSignature], previous_summary: str = "") -> Optional[DailyBriefing]:
        initial_state = EditorialState(
            threats=threats,
            previous_summary=previous_summary,
            current_briefing=None,
            critique_result=None,
            retry_count=0,
            final_output=None
        )
        final_state = await self.workflow.ainvoke(initial_state)
        
        # If finalized, return that. If max retries, return current draft.
        return cast(Optional[DailyBriefing], final_state.get("final_output") or final_state.get("current_briefing"))

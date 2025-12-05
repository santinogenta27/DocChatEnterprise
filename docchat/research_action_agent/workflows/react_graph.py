"""LangGraph workflow for ReAct agent."""

from __future__ import annotations

import json
from typing import TypedDict, Sequence, Annotated, Dict, Any, Optional

try:
    from langgraph.graph import StateGraph, END
    from langgraph.graph.message import add_messages
    from langgraph.checkpoint.memory import MemorySaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    print("⚠️ LangGraph no está instalado. Instala con: pip install langgraph")

from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
    SystemMessage
)

from ..tools import TOOLS_REGISTRY


class AgentState(TypedDict):
    """State for the ReAct agent."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    goal: str  # Global goal to remember
    cycle_count: int  # Track ReAct cycles
    max_cycles: int  # Maximum cycles (default: 6)


def build_react_graph(
    model,
    tools: Optional[Dict[str, Any]] = None,
    system_prompt: Optional[str] = None
):
    """
    Build the ReAct LangGraph workflow.
    
    Args:
        model: The LLM model (ChatOpenAI, etc.)
        tools: Dictionary of tools (default: TOOLS_REGISTRY)
        system_prompt: System prompt for the agent
    
    Returns:
        Compiled LangGraph workflow
    """
    if not LANGGRAPH_AVAILABLE:
        raise ImportError("LangGraph no está instalado. Instala con: pip install langgraph")
    
    if tools is None:
        tools = TOOLS_REGISTRY
    
    # Bind tools to model
    model_with_tools = model.bind_tools(list(tools.values()))
    
    # Build prompt template
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    
    if system_prompt is None:
        # Load default prompt
        try:
            prompt_path = __file__.replace("workflows/react_graph.py", "prompts/react_prompt.txt")
            with open(prompt_path, "r", encoding="utf-8") as f:
                system_prompt = f.read()
        except:
            system_prompt = "You are a helpful AI assistant that uses tools when needed."
    
    chat_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="scratch_pad")
    ])
    
    # Create the model chain
    model_chain = chat_prompt | model_with_tools
    
    def call_model(state: AgentState):
        """Call the model with current state."""
        messages = list(state["messages"])
        
        # Increment cycle count
        cycle_count = state.get("cycle_count", 0) + 1
        
        response = model_chain.invoke({"scratch_pad": messages})
        
        return {
            "messages": [response],
            "cycle_count": cycle_count
        }
    
    def tool_node(state: AgentState):
        """Execute all tool calls from the last message."""
        outputs = []
        last_message = state["messages"][-1]
        
        # Get tool calls
        tool_calls = getattr(last_message, "tool_calls", []) or []
        
        for tool_call in tool_calls:
            tool_name = tool_call.get("name", "")
            tool_args = tool_call.get("args", {})
            tool_call_id = tool_call.get("id", "")
            
            # Get tool from registry
            tool_fn = tools.get(tool_name)
            
            if tool_fn is None:
                tool_result = {
                    "error": "tool_not_found",
                    "name": tool_name
                }
            else:
                try:
                    # Invoke tool
                    # Some tools expect a single string arg, others expect dict
                    if isinstance(tool_args, dict) and len(tool_args) == 1:
                        # Single arg - pass as string
                        first_key = list(tool_args.keys())[0]
                        tool_result = tool_fn.invoke(tool_args[first_key])
                    elif isinstance(tool_args, dict):
                        # Multiple args - try to pass as JSON string for action_executor
                        if tool_name == "action_executor":
                            tool_result = tool_fn.invoke(json.dumps(tool_args))
                        else:
                            # For other tools, try invoking with dict unpacking
                            try:
                                tool_result = tool_fn.invoke(**tool_args)
                            except:
                                # Fallback: convert to string
                                tool_result = tool_fn.invoke(str(tool_args))
                    else:
                        # Single string arg
                        tool_result = tool_fn.invoke(str(tool_args))
                        
                except Exception as e:
                    tool_result = {
                        "error": "tool_invocation_failed",
                        "name": tool_name,
                        "exception": str(e)
                    }
            
            # Create ToolMessage
            tool_message = ToolMessage(
                content=json.dumps(tool_result) if not isinstance(tool_result, str) else tool_result,
                name=tool_name,
                tool_call_id=tool_call_id
            )
            outputs.append(tool_message)
        
        return {"messages": outputs}
    
    def should_continue(state: AgentState):
        """Determine whether to continue with tools or end."""
        messages = state["messages"]
        last_message = messages[-1]
        
        # Check cycle limit
        cycle_count = state.get("cycle_count", 0)
        max_cycles = state.get("max_cycles", 6)
        
        if cycle_count >= max_cycles:
            return "end"  # Max cycles reached
        
        # Check if there are tool calls
        tool_calls = getattr(last_message, "tool_calls", []) or []
        
        if not tool_calls:
            return "end"
        else:
            return "continue"
    
    # Build the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)
    
    # Add edges
    workflow.add_edge("tools", "agent")  # After tools, always go back to agent
    
    # Add conditional edge from agent
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "continue": "tools",  # If tools needed, go to tools node
            "end": END,  # If done, end the conversation
        }
    )
    
    # Set entry point
    workflow.set_entry_point("agent")
    
    # Compile with memory
    memory = MemorySaver()
    graph = workflow.compile(checkpointer=memory)
    
    return graph


def initialize_state(query: str, max_cycles: int = 6) -> Dict[str, Any]:
    """Initialize agent state with goal and cycle limits."""
    from langchain_core.messages import HumanMessage
    
    return {
        "messages": [HumanMessage(content=query)],
        "goal": query,
        "cycle_count": 0,
        "max_cycles": max_cycles
    }


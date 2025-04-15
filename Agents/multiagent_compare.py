# compare_workflow.py
from typing import TypedDict, Optional, List, Dict
from langgraph.graph import StateGraph, END
import asyncio
import json
from Agents.websearch_compare import WebSearchComparisonAgent
from Agents.agents_1 import CollegeRecommender
from Agents.college_compare import ComparisonDetector

class ComparisonState(TypedDict):
    user_query: str
    is_college_related: bool
    safety_check_passed: bool
    is_comparison: bool
    colleges_to_compare: List[str]
    comparison_aspects: List[str]
    snowflake_results: List[Dict]
    rag_results: List[Dict]
    web_results: List[Dict]
    final_output: Optional[Dict]
    early_response: Optional[str]
    fallback_used: bool
    fallback_message: Optional[str]

# Initialize agents
college_recommender = CollegeRecommender()
comparison_detector = ComparisonDetector()
web_recommender = WebSearchComparisonAgent()

# Initialize the graph
workflow = StateGraph(ComparisonState)
async def check_prompt_node(state: ComparisonState):
    """Gatekeeper node"""
    STANDARD_RESPONSE = "Sorry I can't help with that. I specialize in college comparisons."
    
    try:
        safety_result = await college_recommender.safety_system.check_query(
            state['user_query'], []
        )
        if not safety_result["safe"]:
            return {
                "is_college_related": False,
                "safety_check_passed": False,
                "early_response": STANDARD_RESPONSE
            }
        
        return {
            "is_college_related": True,
            "safety_check_passed": True
        }
    except Exception as e:
        print(f"⚠️ Gatekeeper error: {e}")
        return {
            "is_college_related": False,
            "safety_check_passed": False,
            "early_response": STANDARD_RESPONSE
        }

async def detect_comparison_node(state: ComparisonState):
    """Call external ComparisonDetector"""
    STANDARD_RESPONSE = "Please ask questions related to comparing colleges. Example: 'Compare MIT and Stanford for computer science programs'"
    
    detection_result = await comparison_detector.detect(state['user_query'])
    
    if not detection_result["is_comparison"]:
        return {
            "is_comparison": False,
            "colleges_to_compare": [],
            "comparison_aspects": [],
            "early_response": STANDARD_RESPONSE  # Add this line
        }
    
    return {
        "is_comparison": detection_result["is_comparison"],
        "colleges_to_compare": detection_result["colleges"],
        "comparison_aspects": detection_result["comparison_aspects"]
    }

async def query_snowflake_node(state: ComparisonState):
    print("🧪 TEST MODE: Forcing empty Snowflake results")
    return {"snowflake_results": []}  # Force empty
'''
    """Fetch comparison data - returns empty if not comparison"""
    if not state["is_comparison"]:
        return {"snowflake_results": []}
    
    try:
        results = []
        for college in state["colleges_to_compare"]:
            data = search_college_data(college)
            results.extend(data) if data else None
        return {"snowflake_results": results or []}
    except Exception as e:
        print(f"❌ Snowflake error: {e}")
        return {"snowflake_results": []}
'''
async def query_rag_node(state: ComparisonState):
    print("🧪 TEST MODE: Forcing empty RAG results") 
    return {"rag_results": []}  # Force empty
'''
    """Fetch comparison docs - returns empty if not comparison"""
    if not state["is_comparison"]:
        return {"rag_results": []}
    
    try:
        query = f"Comparison of {', '.join(state['colleges_to_compare'])} regarding {', '.join(state['comparison_aspects'])}"
        results = get_retriever_output(query)
        return {"rag_results": results or []}
    except Exception as e:
        print(f"❌ RAG error: {e}")
        return {"rag_results": []}
'''
# Simplified check_results_node without should_fallback
async def check_results_node(state: ComparisonState):
    """Check if we need fallback"""
    if not state["is_comparison"]:
        return {"fallback_used": False}
    
    snowflake_empty = not bool(state.get("snowflake_results", []))
    rag_empty = not bool(state.get("rag_results", []))
    
    if snowflake_empty and rag_empty:
        print("⚠️ Both sources empty - triggering fallback")
        return {"fallback_used": True}
    return {"fallback_used": False}



# Updated query_web_node
async def query_web_node(state: ComparisonState):
    """Comparison-specific fallback"""
    if not state.get("fallback_used", False):
        return {"web_results": []}  # Just return empty if not fallback
    
    try:
        comparison_query = (
            f"Compare {', '.join(state['colleges_to_compare'])} "
            f"on aspects: {', '.join(state['comparison_aspects'])}"
        )
        result = await web_recommender.recommend(comparison_query)
        
        return {
            "web_results": [{
                'text': result['response'],
                'metadata': {'source': 'web_search'}
            }],
            "fallback_message": "Used web comparison results"
        }
    except Exception as e:
        print(f"❌ Web search failed: {e}")
        return {"web_results": []}

# Simplified compile_results
def compile_results(state: ComparisonState):
    output = {
        "is_comparison": state["is_comparison"],
        "colleges": state["colleges_to_compare"],
        "aspects": state["comparison_aspects"],
        "response": (
            state["web_results"][0]["text"] 
            if state.get("fallback_used") and state.get("web_results") 
            else "No comparison available"
        ),
        "fallback_used": state.get("fallback_used", False),
        "fallback_message": state.get("fallback_message", "")
    }
    return {"final_output": output}


# Add nodes (ONCE)
workflow.add_node("gatekeeper", check_prompt_node)
workflow.add_node("detect_comparison", detect_comparison_node)
workflow.add_node("snowflake", query_snowflake_node)
workflow.add_node("rag", query_rag_node)
workflow.add_node("check_results", check_results_node)
workflow.add_node("web", query_web_node)
workflow.add_node("compile", compile_results)

# Configure workflow (with SINGLE conditional edges setup)
workflow.set_entry_point("gatekeeper")

# 1. First conditional edge
workflow.add_conditional_edges(
    "gatekeeper",
    lambda state: (
        "early_exit" 
        if not state["is_college_related"] or not state["safety_check_passed"] 
        else "detect_comparison"
    ),
    {"early_exit": END, "detect_comparison": "detect_comparison"}
)

# 2. Second conditional edge
workflow.add_conditional_edges(
    "detect_comparison",
    lambda state: "snowflake" if state["is_comparison"] else "early_exit",
    {"snowflake": "snowflake", "early_exit": END}
)

# 3. Regular edges
workflow.add_edge("snowflake", "rag")
workflow.add_edge("rag", "check_results")

# 4. Final conditional edge (REPLACED to use fallback_used)
workflow.add_conditional_edges(
    "check_results",
    lambda state: "web" if state.get("fallback_used", False) else "compile",
    {"web": "web", "compile": "compile"}
)

workflow.add_edge("web", "compile")
workflow.add_edge("compile", END)

# Compile the graph (ONCE)
app = workflow.compile()

async def test_workflow():
    test_cases = [
        "Tell me about Harvard"  
    ]
    
    for query in test_cases:
        print(f"\n{'='*50}\nTesting: '{query}'")
        result = await app.ainvoke({
            "user_query": query,
            "is_college_related": None,
            "safety_check_passed": None,
            "is_comparison": None,
            "colleges_to_compare": [],
            "comparison_aspects": [],
            "snowflake_results": [],
            "rag_results": [],
            "web_results": [],
            "final_output": None,
            "early_response": None,
            "fallback_used": False,  # Initialize as False
            "fallback_message": None
        })
        
        if result.get("early_response"):
            print(f"RESULT: {result['early_response']}")
        else:
            output = result.get("final_output", {})
            print(f"COMPARISON RESULT: {output.get('response')}")
            if output.get("fallback_used"):
                print(f"⚠️ {output.get('fallback_message')}")

if __name__ == "__main__":
    asyncio.run(test_workflow())
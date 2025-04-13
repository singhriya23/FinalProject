from typing import TypedDict, Optional, List, Dict
from langgraph.graph import StateGraph, END
import asyncio
from datetime import datetime
import json
from snowflake_agent import search_college_data
from rag_agent import get_retriever_output
from websearch_agent import run_websearch_agent

# Define the state structure
class RecommendationState(TypedDict):
    user_query: str
    snowflake_results: List[Dict]
    rag_results: List[Dict]
    web_results: List[Dict]
    final_output: Optional[Dict]

def save_to_markdown(query: str, results: Dict, filename: str = "agent_outputs.md"):
    with open(filename, "w") as f:
        f.write(f"# Agent Outputs Report\n\n")
        f.write(f"**Generated at:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**User Query:** `{query}`\n\n")
        
        # Snowflake Results
        f.write("## Snowflake Results\n")
        f.write(f"Found {len(results['snowflake'])} colleges\n\n")
        for college in results['snowflake']:
            f.write(f"### {college.get('COLLEGE_NAME', 'Unknown')}\n")
            f.write("```json\n")
            f.write(json.dumps(college, indent=2))
            f.write("\n```\n\n")
        
        # RAG Results
        f.write("## RAG Results\n")
        f.write(f"Found {len(results['rag'])} documents\n\n")
        for doc in results['rag']:
            f.write("### Document\n")
            f.write(f"**Text excerpt:** {doc.get('text', '')[:200]}...\n\n")
            f.write("**Metadata:**\n```json\n")
            f.write(json.dumps(doc.get('metadata', {}), indent=2))
            f.write("\n```\n\n")
        
        # Web Results
        f.write("## Web Search Results\n")
        f.write(f"Found {len(results['web'])} results\n\n")
        for result in results['web']:
            f.write("### Result\n")
            f.write(f"```json\n")
            f.write(json.dumps(result, indent=2))
            f.write("\n```\n\n")

# Initialize the graph
workflow = StateGraph(RecommendationState)

# 1. Snowflake Node
async def query_snowflake_node(state: RecommendationState):
    try:
        results = search_college_data(state['user_query'])
        print("\n❄️ Snowflake Raw Output:")
        print(json.dumps(results[:2], indent=2))
        return {"snowflake_results": results}
    except Exception as e:
        print(f"❌ Snowflake error: {e}")
        return {"snowflake_results": []}

# 2. RAG Node
async def query_rag_node(state: RecommendationState):
    try:
        results = get_retriever_output(state['user_query'])
        print("\n📚 RAG Raw Output:")
        print(json.dumps(results[:2], indent=2))
        return {"rag_results": results}
    except Exception as e:
        print(f"❌ RAG error: {e}")
        return {"rag_results": []}

# 3. Web Search Node (corrected version)
async def query_web_node(state: RecommendationState):
    """Process query with Web Search agent"""
    try:
        # Get results from web agent
        results = run_websearch_agent(state['user_query'])
        
        # Properly format the results based on what's returned
        if isinstance(results, str):
            # If it's a single string, wrap it in a list
            formatted_results = [{"text": results}]
        elif isinstance(results, list):
            # If it's already a list, preserve the structure
            formatted_results = [{"text": r} if isinstance(r, str) else r for r in results]
        else:
            # Fallback for other types
            formatted_results = [{"text": str(results)}]
            
        print("\n🌐 Web Search Raw Output:")
        print(json.dumps(formatted_results, indent=2))
        return {"web_results": formatted_results}
    except Exception as e:
        print(f"❌ Web Search error: {e}")
        return {"web_results": []}

# 4. Compilation Node
def compile_results(state: RecommendationState):
    return {
        "final_output": {
            "snowflake": state.get('snowflake_results', []),
            "rag": state.get('rag_results', []),
            "web": state.get('web_results', []),
            "query": state['user_query']
        }
    }

# Add nodes to graph
workflow.add_node("snowflake", query_snowflake_node)
workflow.add_node("rag", query_rag_node)
workflow.add_node("web", query_web_node)
workflow.add_node("compile", compile_results)

# Configure workflow
workflow.set_entry_point("snowflake")
workflow.add_edge("snowflake", "rag")
workflow.add_edge("rag", "web")
workflow.add_edge("web", "compile")
workflow.add_edge("compile", END)

# Compile the graph
app = workflow.compile()

# Test function
async def test_workflow(query: str):
    print(f"\n🔍 Testing query: '{query}'")
    result = await app.ainvoke({
        "user_query": query,
        "snowflake_results": [],
        "rag_results": [],
        "web_results": [],
        "final_output": None
    })
    
    print("\n📊 Final Results Summary:")
    print(json.dumps(result['final_output'], indent=2))
    
    save_to_markdown(query, result['final_output'])
    print(f"\n📄 Saved full results to agent_outputs.md")
    
    return result

# Example usage
if __name__ == "__main__":
    query = "Find top AI colleges in California with tuition under $50k"
    asyncio.run(test_workflow(query))
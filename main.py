# main.py (FastAPI backend)
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime, timezone 
from Agents.multi_agent import app as langgraph_app  # Your existing LangGraph workflow
from Agents.multiagent_compare import app as comparison_workflow
from fastapi import BackgroundTasks
import subprocess
import asyncio
from agents import Agent, Runner
from agents.mcp import MCPServerStdio
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

# Session management in memory (replace with DB in production)
sessions = {}

class UserSession(BaseModel):
    session_id: str
    history: list = []

class RecommendationRequest(BaseModel):
    prompt: str
    session_id: Optional[str] = None

class ComparisonResponse(BaseModel):
    success: bool
    is_comparison: bool
    colleges: list[str]
    aspects: list[str]
    response: str
    fallback_used: bool
    fallback_message: Optional[str] = None

@app.post("/create_session")
async def create_session():
    session_id = str(uuid.uuid4())
    sessions[session_id] = UserSession(session_id=session_id)
    return {"session_id": session_id}

@app.post("/recommend")
async def get_recommendations(request: RecommendationRequest):
    # Validate session
    if request.session_id and request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    # Prepare initial state for LangGraph
    langgraph_state = {
        "user_query": request.prompt,
        "combined_agent_results": None,
        "snowflake_results": [],
        "rag_results": [],
        "web_results": [],
        "final_output": None,
        "is_college_related": False,
        "safety_check_passed": False,
        "early_response": None,
        "fallback_used": False,
        "fallback_message": None
    }

    # Execute the workflow
    try:
        result = await langgraph_app.ainvoke(langgraph_state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {str(e)}")
    
    # Build unified response
    response = {
        "success": True,
        "query": request.prompt,
        "data": None,
        "message": None,
        "fallback_used": False
    }

    # Handle early responses
    if result.get("early_response"):
        response["message"] = result["early_response"]
    else:
        # Handle normal results
        final_output = result.get("final_output", {})
        response.update({
            "data": {
                "combined_output": final_output.get("combined_output"),
                "colleges": final_output.get("snowflake", []),
                "documents": final_output.get("rag", []),
                "web_results": final_output.get("web", [])
            },
            "fallback_used": final_output.get("fallback_used", False),
            "fallback_message": final_output.get("fallback_message", "")
        })

        # Validate we actually got results
        if not (final_output.get("snowflake") or final_output.get("rag") or final_output.get("web")):
            response["success"] = False
            response["message"] = "No results found for your query"

    # Store in session if available
    if request.session_id:
        sessions[request.session_id].history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "prompt": request.prompt,
            "response": response,
            "workflow_metadata": {
                "fallback_used": result.get("fallback_used", False),
                "is_college_related": result.get("is_college_related", False)
            }
        })

    return response

@app.post("/compare")
async def compare_colleges(request: RecommendationRequest):
    """Dedicated endpoint for college comparisons"""
    # Validate session
    if request.session_id and request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    # Prepare initial state for comparison workflow
    initial_state = {
        "user_query": request.prompt,
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
        "fallback_used": False,
        "fallback_message": None
    }

    # Execute the comparison workflow
    result = await comparison_workflow.ainvoke(initial_state)
    
    # Handle early exit responses
    if result.get("early_response"):
        return ComparisonResponse(
            success=False,
            is_comparison=False,
            colleges=[],
            aspects=[],
            response=result["early_response"],
            fallback_used=False
        )

    # Extract final output
    final_output = result.get("final_output", {})
    
    # Build response
    response = ComparisonResponse(
        success=True,
        is_comparison=final_output.get("is_comparison", False),
        colleges=final_output.get("colleges", []),
        aspects=final_output.get("aspects", []),
        response=final_output.get("response", "No comparison available"),
        fallback_used=final_output.get("fallback_used", False),
        fallback_message=final_output.get("fallback_message")
    )

    # Store in session if available
    if request.session_id:
        sessions[request.session_id].history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "prompt": request.prompt,
            "response": response.dict()
        })

    return response

# Add this model class
class RankingRequest(BaseModel):
    question: str

# Add this endpoint
@app.post("/university_rankings")
async def get_university_ranking(request: RankingRequest):
    """
    Endpoint to answer questions about QS World University Rankings.
    
    Example questions:
    - "Which university is ranked 5th?"
    - "What is MIT's ranking?"
    - "Show top 5 universities"
    """
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    try:
        async with MCPServerStdio(
            name="University Rankings Assistant",
            params={
                "command": "python",
                "args": ["server.py"]  # Your simplified server file
            }
        ) as server:
            
            agent = Agent(
                name="University Rankings Expert",
                instructions="""You are an expert on QS World University Rankings with one capability:
                            1. Answer questions about university rankings using get_qs_rankings
                            
                            For ranking questions:
                            - Always verify the university name if provided
                            - For rank number queries (e.g., "5th"), confirm the exact position
                            - When showing top universities, always mention it's from QS rankings
                            - Handle errors gracefully and suggest rephrasing if needed""",
                mcp_servers=[server]
            )
            
            # Process the ranking question
            result = await Runner.run(
                starting_agent=agent,
                input=f"Answer this question about university rankings: {request.question}"
            )
            
            response = {
                "success": True,
                "question": request.question,
                "answer": result.final_output,
                "additional_context": None
            }
            
            # Add OpenAI context for follow-up questions
            if "rank" in result.final_output.lower():
                gpt_response = openai_client.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[{
                        "role": "system",
                        "content": """Provide helpful context about university rankings. 
                        When mentioning a ranked university:
                        - Note its historical ranking trends if significant
                        - Mention 1-2 notable strengths
                        - Suggest similar-ranked institutions
                        Keep responses concise and factual."""
                    }, {
                        "role": "user",
                        "content": f"About this university ranking: {result.final_output}"
                    }]
                )
                response["additional_context"] = gpt_response.choices[0].message.content
                
            return response
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": str(e),
                "message": "Failed to process ranking request"
            }
        )

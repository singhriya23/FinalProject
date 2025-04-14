# main.py (FastAPI backend)
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime, timezone 
from Agents.multi_agent import app as langgraph_app  # Your existing LangGraph workflow

app = FastAPI()

# Session management in memory (replace with DB in production)
sessions = {}

class UserSession(BaseModel):
    session_id: str
    history: list = []

class RecommendationRequest(BaseModel):
    prompt: str
    session_id: Optional[str] = None

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
    result = await langgraph_app.ainvoke(langgraph_state)
    
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
                "colleges": final_output.get("snowflake", []),
                "documents": final_output.get("rag", []),
                "web_results": final_output.get("web", [])
            },
            "fallback_used": final_output.get("fallback_used", False),
            "fallback_message": final_output.get("fallback_message", "")
        })

    # Store in session if available
    if request.session_id:
        sessions[request.session_id].history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),  # Updated this line
            "prompt": request.prompt,
            "response": response
        })

    return response


# main.py (FastAPI backend)
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid
from multi_agent import app as langgraph_app  # Your existing LangGraph workflow

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
    if request.session_id and request.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Call your LangGraph workflow
    result = await langgraph_app.ainvoke({
        "user_query": request.prompt,
        "snowflake_results": [],
        "rag_results": [],
        "web_results": [],
        "final_output": None
    })
    
    # Store in session if available
    if request.session_id:
        sessions[request.session_id].history.append({
            "prompt": request.prompt,
            "result": result['final_output']
        })
    
    return result['final_output']


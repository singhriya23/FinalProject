from mcp.server.fastmcp import FastMCP
import re
import json
from typing import Optional, Dict, Any
from pydantic import BaseModel, ValidationError

# Create MCP server
mcp = FastMCP("EnhancedServer")

# --- Existing Greeting Functions ---
@mcp.resource("hello://world")
def hello_world() -> str:
    """Returns the classic hello world message"""
    return "Hello, World! This is your first MCP resource."

@mcp.tool()
def greet(name: str) -> str:
    """Generates a personalized greeting"""
    return f"Hello, {name}! Welcome to MCP."

# --- New Profiler Functions ---
class UserProfile(BaseModel):
    interests: list[str] = []
    gpa: Optional[float] = None
    budget: Optional[float] = None
    degree: Optional[str] = None
    location: Optional[str] = None

@mcp.tool()
def parse_education_query(query: str) -> Dict[str, Any]:
    """
    Parse educational profile from natural language.
    Example: "AI programs with 3.7 GPA and $50k budget"
    """
    # Rule-based parsing
    def rule_based_parse(q: str):
        result = {}
        if gpa_match := re.search(r'(?:^|\s)gpa\s*[:=]?\s*(\d\.\d)\b', q.lower()):
            result["gpa"] = float(gpa_match.group(1))
        if budget_match := re.search(r'\$\s*(\d+)\s*(?:k|K)?\s*budget', q.lower()):
            result["budget"] = float(budget_match.group(1)) * (1000 if 'k' in budget_match.group(0).lower() else 1)
        return result

    # Hybrid parsing
    def hybrid_parse(q: str):
        q = q.lower()
        result = {}
        if match := re.search(r'(\d\.\d+)\s*(?:gpa|grade)', q):
            result["gpa"] = float(match.group(1))
        if match := re.search(r'(?:budget|around|about|~)\s*(\$?\s*\d+[kK]?)', q):
            amount = match.group(1).replace('$', '').strip()
            result["budget"] = float(amount.replace('k', '000').replace('K', '000'))
        return result

    # Combine results
    combined = {**hybrid_parse(query), **rule_based_parse(query)}
    
    try:
        return UserProfile(**combined).dict()
    except ValidationError:
        return {"error": "Could not parse valid profile", "input": query}

@mcp.resource("parser://capabilities")
def parser_capabilities() -> str:
    """Lists available parsing features"""
    return json.dumps({
        "supports": ["gpa", "budget", "degree", "interests"],
        "example_queries": [
            "Find CS programs with 3.5 GPA",
            "AI masters with $50k budget"
        ]
    })

if __name__ == "__main__":
    print("Starting enhanced MCP server...")
    print("Available tools: greet, parse_education_query")
    print("Available resources: hello://world, parser://capabilities")
    mcp.run()
import re
import json
from typing import Optional, Dict, Any
from openai import OpenAI
from pydantic import BaseModel, ValidationError

# Initialize client

# --- 1. Data Model ---
class UserProfile(BaseModel):
    """Validated user profile schema"""
    interests: list[str] = []
    gpa: Optional[float] = None
    budget: Optional[float] = None
    degree: Optional[str] = None
    location: Optional[str] = None
    
    @classmethod
    def validate_gpa(cls, v):
        if v is not None and not (2.0 <= v <= 4.0):
            raise ValueError("GPA must be 2.0-4.0")
        return v
    
    @classmethod
    def validate_budget(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Budget must be positive")
        return v

# --- 2. Strict Rule-Based Parser ---
def rule_based_parse(query: str) -> Optional[Dict[str, Any]]:
    """Only catches perfect, complete patterns"""
    query = query.lower()
    result = {}
    
    # GPA - must be "GPA 3.5" at start or after space
    if gpa_match := re.search(r'(?:^|\s)gpa\s*[:=]?\s*(\d\.\d)\b', query):
        result["gpa"] = float(gpa_match.group(1))
    
    # Budget - must include dollar sign and "budget"
    if budget_match := re.search(r'\$\s*(\d+)\s*(?:k|K)?\s*budget', query):
        result["budget"] = float(budget_match.group(1)) * (1000 if budget_match.group(0).lower().endswith('k') else 1)
    
    return result  # Only returns if it found GPA or budget in strict format

# --- 3. Enhanced Hybrid Parser ---
def hybrid_keyword_parse(query: str) -> Optional[Dict[str, Any]]:
    """Handles all other cases with flexible matching"""
    query_lower = query.lower()
    result = {}
    
    # GPA - flexible matching
    if not result.get("gpa"):
        if match := re.search(r'(\d\.\d+)\s*(?:gpa|grade)', query_lower):
            result["gpa"] = float(match.group(1))
    
    # Budget - multiple formats
    if not result.get("budget"):
        if match := re.search(r'(?:budget|around|about|~)\s*(\$?\s*\d+[kK]?)', query_lower):
            amount = match.group(1).replace('$', '').strip()
            result["budget"] = float(amount.replace('k', '000').replace('K', '000'))
    
    # Degree - with context
    if "master" in query_lower or "ms" in query_lower or "graduate" in query_lower:
        result["degree"] = "MS"
    elif "bachelor" in query_lower or "bs" in query_lower or "undergrad" in query_lower:
        result["degree"] = "BS"
    elif "phd" in query_lower or "doctorate" in query_lower:
        result["degree"] = "PhD"
    
    # Interests
    interests = []
    if re.search(r'\bai\b|\bartificial intelligence\b', query_lower):
        interests.append("AI")
    if re.search(r'\brobotics\b|\brobots\b', query_lower):
        interests.append("ROBOTICS")
    if re.search(r'\bcs\b|\bcomputer science\b', query_lower):
        interests.append("CS")
    if interests:
        result["interests"] = interests
    
    # Location
    if " in " in query_lower:
        loc = query.split(" in ")[-1].split(" with")[0].split(" for ")[0].strip()
        if 2 <= len(loc.split()) <= 3:  # Basic validation
            result["location"] = loc.title()
    
    return result if result else None

# --- 4. GPT-3.5 Fallback ---
def gpt3_parse(query: str) -> Dict[str, Any]:
    response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        response_format={"type": "json_object"},
        messages=[{
            "role": "system",
            "content": "Extract: interests (list), gpa (2.0-4.0), budget (positive), degree (BS/MS/PhD), location (str). Return valid JSON."
        }, {
            "role": "user",
            "content": query
        }],
        temperature=0.3
    )
    return json.loads(response.choices[0].message.content)

# --- 5. Optimized Profiler Agent ---
def profiler_agent(query: str) -> Dict[str, Any]:
    # Layer 1: Try strict rule-based (only for perfect matches)
    rule_result = rule_based_parse(query)
    
    # Layer 2: Hybrid parser (handles everything else)
    hybrid_result = hybrid_keyword_parse(query) or {}
    
    # Combine results (rule-based takes precedence)
    combined = {**hybrid_result, **rule_result} if rule_result else hybrid_result
    
    if combined:
        try:
            UserProfile(**combined)
            return {
                **combined,
                "parser": "hybrid" if not rule_result else "rules"
            }
        except ValidationError:
            pass
    
    # Final fallback
    result = gpt3_parse(query)
    return {**result, "parser": "gpt3.5"}

# --- 6. Testing ---
if __name__ == "__main__":
    test_queries = [
        "Looking for AI programs with 3.7 GPA",
        "Budget around $50K for MS in Germany",
        "PhD in Robotics with 3.9 GPA",
        "Computer science bachelor's in California",
        "I need suggestions for colleges"
    ]
    
    for query in test_queries:
        print(f"\nInput: {query}")
        result = profiler_agent(query)
        print(json.dumps(result, indent=2))
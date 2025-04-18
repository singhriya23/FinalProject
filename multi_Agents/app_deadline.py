import os
import re
from dotenv import load_dotenv
import snowflake.connector

load_dotenv()

# Snowflake configuration
SNOWFLAKE_CONFIG = {
    "user": os.getenv("SNOWFLAKE_USER"),
    "password": os.getenv("SNOWFLAKE_PASSWORD"),
    "account": os.getenv("SNOWFLAKE_ACCOUNT"),
    "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
    "database": os.getenv("SNOWFLAKE_DATABASE"),
    "schema": "TOP_30"
}

# Table configuration
COLLEGE_TABLE = "UNIVERSITY_LIST"
DEFAULT_COLUMNS = ["COLLEGE_NAME", "APPLICATION_DEADLINE"]

def get_snowflake_connection():
    """Establish connection to Snowflake"""
    return snowflake.connector.connect(**SNOWFLAKE_CONFIG)

def extract_college_name(prompt: str) -> str:
    """
    Extract college name from user prompt using regex patterns
    Handles common variations and abbreviations
    """
    patterns = [
        r"(?:for|of|at)\s+(the\s+)?([A-Za-z\s]+?)(?:\s+university|\s+college|$|\?)",
        r"(Harvard|MIT|Stanford|Yale|Princeton|Columbia|Caltech|Berkeley|UCLA|NYU)",
        r"\b(for|get)\s+([A-Za-z\s]+?)(?:'s)?\s+deadline"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, prompt, re.IGNORECASE)
        if match:
            # Get the last matched group which should contain the college name
            college = match.group(match.lastindex).strip()
            # Standardize common names
            college = college.replace("the ", "").strip()
            if college.upper() == "MIT":
                return "Massachusetts Institute of Technology"
            if college.upper() == "UCLA":
                return "University of California, Los Angeles"
            if college.upper() == "NYU":
                return "New York University"
            if "berkeley" in college.lower():
                return "University of California, Berkeley"
            return college.title()
    
    return ""

def fetch_application_deadline(college_name: str) -> dict:
    """
    Query Snowflake for application deadline of a specific college
    Returns a dictionary with college name and deadline
    """
    if not college_name:
        return {"error": "No college name provided"}
    
    query = f"""
        SELECT COLLEGE_NAME, APPLICATION_DEADLINE
        FROM {COLLEGE_TABLE}
        WHERE COLLEGE_NAME ILIKE %s
        LIMIT 1
    """
    
    try:
        conn = get_snowflake_connection()
        cursor = conn.cursor()
        
        # Use ILIKE for case-insensitive matching and % for partial matches
        cursor.execute(query, (f"%{college_name}%",))
        result = cursor.fetchone()
        
        if result:
            return {
                "college_name": result[0],
                "application_deadline": result[1],
                "status": "success"
            }
        else:
            return {
                "error": f"No deadline found for {college_name}",
                "status": "not_found"
            }
            
    except Exception as e:
        return {
            "error": f"Database error: {str(e)}",
            "status": "error"
        }
    finally:
        if 'conn' in locals():
            conn.close()

def process_deadline_query(prompt: str) -> str:
    """
    Main function to handle deadline queries
    Takes user prompt and returns formatted response
    """
    college_name = extract_college_name(prompt)
    if not college_name:
        return "Please specify which college's deadline you're asking about."
    
    result = fetch_application_deadline(college_name)
    
    if result.get("status") == "success":
        return f"The application deadline for {result['college_name']} is {result['application_deadline']}."
    elif result.get("status") == "not_found":
        return f"Sorry, I couldn't find the deadline for {college_name} in our records."
    else:
        return "There was an error retrieving the deadline information. Please try again later."

if __name__ == "__main__":
    # Example usage
    test_queries = [
        "What is the deadline for MIT?",
        "When is Harvard's application due?",
        "Get me Stanford's deadline",
        "Tell me the application deadline for UCLA",
        "What's the deadline for New York University?"
    ]
    
    print("🎓 College Deadline Lookup\n" + "="*40)
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        response = process_deadline_query(query)
        print(f"Response: {response}")
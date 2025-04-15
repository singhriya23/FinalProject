import os
import re
from dotenv import load_dotenv
import snowflake.connector
from langchain_openai import ChatOpenAI
from langgraph.graph import Graph

load_dotenv()

# ------------------------- CONFIGS --------------------------
COLUMN_MAPPING = {
    "fee": "TUITION_FEES",
    "cost": "TUITION_FEES",
    "price": "TUITION_FEES",
    "tuition": "TUITION_FEES",
    "gpa": "MINIMUM_GPA",
    "graduate enrollment": "GRADUATE_ENROLLMENT",
    "undergraduate enrollment": "UNDERGRADUATE_ENROLLMENT",
    "college": "COLLEGE_NAME",
    "university": "COLLEGE_NAME",
    "location": "LOCATION",
    "setting": "COLLEGE_SETTING",
    "class size": "AVERAGE_CLASS_SIZE",
    "deadline": "APPLICATION_DEADLINE",
    "ranking": "RANKING",
    "sat": "SAT_RANGE",
    "act": "ACT_RANGE",
    "acceptance": "ACCEPTANCE_RATE",
    "salary": "MEDIAN_SALARY_AFTER_GRADUATION",
    "food": "FOOD_AND_HOUSING",
    "housing": "FOOD_AND_HOUSING",
    "graduation": "GRADUATION_RATE",
    "affordable": "TUITION_FEES"
}

COLLEGE_TABLE = "TOP_30.UNIVERSITY_LIST"

SHORT_COLUMN_NAMES = {
    "COLLEGE_NAME": "Name",
    "TUITION_FEES": "Fee",
    "GRADUATION_RATE": "Grad Rate",
    "RANKING": "Rank",
    "SAT_RANGE": "SAT",
    "ACT_RANGE": "ACT",
    "MINIMUM_GPA": "GPA",
    "ACCEPTANCE_RATE": "Acceptance",
    "MEDIAN_SALARY_AFTER_GRADUATION": "Salary"
}

DEFAULT_COLUMNS = [
    "COLLEGE_NAME", "RANKING", "TUITION_FEES", "GRADUATION_RATE",
    "MINIMUM_GPA", "SAT_RANGE", "ACT_RANGE", "ACCEPTANCE_RATE",
    "MEDIAN_SALARY_AFTER_GRADUATION"
]

# ---------------------- SNOWFLAKE QUERY ----------------------
def query_snowflake(query: str) -> list:
    conn = snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema="TOP_30"
    )
    cursor = conn.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    columns = [col[0] for col in cursor.description]
    conn.close()
    return [dict(zip(columns, row)) for row in results]

# ---------------------- UTILITIES ----------------------
def identify_relevant_columns(prompt: str) -> list:
    return [col for word, col in COLUMN_MAPPING.items() if word in prompt.lower()]

def extract_gpa_and_sat(prompt: str):
    gpa_match = re.search(r"\b(\d\.\d{1,2})\b", prompt)
    sat_match = re.search(r"\b(\d{3,4})\b", prompt)
    gpa = float(gpa_match.group(1)) if gpa_match else None
    sat = int(sat_match.group(1)) if sat_match else None
    if gpa and gpa > 4.5:
        gpa = None
    if sat and sat < 800:
        sat = None
    return gpa, sat

def summarize_data_for_prompt(data: list) -> str:
    if not data:
        return "No matching college data found."
    summary = []
    for row in data[:10]:
        line = [f"{SHORT_COLUMN_NAMES.get(col, col)}: {val}" for col, val in row.items() if val]
        summary.append(" | ".join(line))
    return "\n".join(summary)

# ---------------------- MAIN SEARCH ----------------------
def search_and_filter(prompt: str) -> list:
    relevant_columns = identify_relevant_columns(prompt)
    gpa, sat = extract_gpa_and_sat(prompt)

    if not relevant_columns and (gpa or sat):
        relevant_columns = DEFAULT_COLUMNS

    if "COLLEGE_NAME" not in relevant_columns:
        relevant_columns.append("COLLEGE_NAME")
    if "LOCATION" not in relevant_columns:
        relevant_columns.append("LOCATION")

    columns_str = ", ".join(relevant_columns)
    filter_condition = " AND ".join([f"{col} IS NOT NULL" for col in relevant_columns])
    order_by = "ORDER BY RANKING ASC"

    query = f"""
        SELECT {columns_str}
        FROM {COLLEGE_TABLE}
        WHERE {filter_condition}
        {order_by}
        LIMIT 100
    """
    try:
        results = query_snowflake(query)
    except Exception as e:
        return [{"error": f"Query error: {e}"}]

    # GPA or SAT filtering (OR logic)
    if gpa or sat:
        filtered = []
        for row in results:
            gpa_match = False
            sat_match = False

            gpa_str = str(row.get("MINIMUM_GPA", "")).strip()
            match = re.search(r"(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)", gpa_str)
            if match and gpa:
                low, high = float(match.group(1)), float(match.group(2))
                gpa_match = low <= gpa <= high
            elif gpa_str.replace(".", "", 1).isdigit() and gpa:
                gpa_match = gpa >= float(gpa_str)

            sat_str = str(row.get("SAT_RANGE", "")).strip()
            match = re.search(r"(\d{3,4})\s*[-–]\s*(\d{3,4})", sat_str)
            if match and sat:
                low, high = int(match.group(1)), int(match.group(2))
                sat_match = low <= sat <= high

            if gpa_match or sat_match:
                filtered.append(row)
        results = filtered

    return results

# ---------------------- LLM RESPONSE ----------------------
def generate_recommendation(prompt: str, data: list) -> str:
    if not data:
        return "No data in our system match the prompt provided. Please use the web search agent for this query."
    llm = ChatOpenAI(model="gpt-4", temperature=0.3)
    summary = summarize_data_for_prompt(data)
    return llm.invoke(
        f"""You are a helpful assistant.
Use only the following data to respond to the user query:

{summary}

User Prompt: "{prompt}"

Respond concisely using only the colleges in the list above.
"""
    ).content

# ---------------------- LANGGRAPH FLOW ----------------------
def input_node(state):
    prompt = input("\n💬 What kind of colleges are you looking for?\n> ")
    return {"prompt": prompt}

def fetch_recommendation_data(state):
    prompt = state["prompt"]
    data = search_and_filter(prompt)
    return {"prompt": prompt, "data": data}

def generate_response_node(state):
    prompt = state["prompt"]
    data = state["data"]
    reply = generate_recommendation(prompt, data)
    return {"response": reply}

def output_node(state):
    print("\n📘 RECOMMENDED COLLEGES:\n")
    print(state["response"])
    return state

recommendation_graph = Graph()
recommendation_graph.add_node("input", input_node)
recommendation_graph.add_node("fetch_data", fetch_recommendation_data)
recommendation_graph.add_node("generate_response", generate_response_node)
recommendation_graph.add_node("output", output_node)

recommendation_graph.set_entry_point("input")
recommendation_graph.add_edge("input", "fetch_data")
recommendation_graph.add_edge("fetch_data", "generate_response")
recommendation_graph.add_edge("generate_response", "output")

recommendation_agent = recommendation_graph.compile()

if __name__ == "__main__":
    recommendation_agent.invoke({"prompt": ""})

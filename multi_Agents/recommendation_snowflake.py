import os
import re
import datetime
from dotenv import load_dotenv
import snowflake.connector
from langchain_openai import ChatOpenAI
from langgraph.graph import Graph

load_dotenv()

COLUMN_MAPPING = {
    "deadline": "APPLICATION_DEADLINE",
    "gpa": "MINIMUM_GPA",
    "sat": "SAT_RANGE",
    "fee": "TUITION_FEES",
    "ranking": "RANKING",
    "acceptance": "ACCEPTANCE_RATE",
    "graduation": "GRADUATION_RATE",
    "salary": "MEDIAN_SALARY_AFTER_GRADUATION",
    "enrollment": "UNDERGRADUATE_ENROLLMENT",
}

COLLEGE_TABLE = "TOP_30.UNIVERSITY_LIST"

SHORT_COLUMN_NAMES = {
    "COLLEGE_NAME": "Name",
    "APPLICATION_DEADLINE": "Deadline",
    "TUITION_FEES": "Fee",
    "GRADUATION_RATE": "Grad Rate",
    "RANKING": "Rank",
    "SAT_RANGE": "SAT",
    "MINIMUM_GPA": "GPA",
    "ACCEPTANCE_RATE": "Acceptance",
    "MEDIAN_SALARY_AFTER_GRADUATION": "Salary",
    "UNDERGRADUATE_ENROLLMENT": "Undergrad Enrollment",
    "LOCATION": "Location"
}

DEFAULT_COLUMNS = list(SHORT_COLUMN_NAMES.keys())

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

def identify_relevant_columns(prompt: str) -> list:
    return [col for word, col in COLUMN_MAPPING.items() if word in prompt.lower()]

def extract_gpa_and_sat(prompt: str):
    gpa_match = re.search(r"\b(\d\.\d{1,2})\b", prompt)
    sat_match = re.search(r"\b(\d{3,4})\b", prompt)
    gpa = float(gpa_match.group(1)) if gpa_match else None
    sat = int(sat_match.group(1)) if sat_match else None
    return gpa if gpa and gpa <= 4.5 else None, sat if sat and sat >= 800 else None

def extract_location_state_abbr(prompt: str) -> str:
    state_map = {
        "california": "CA", "texas": "TX", "new york": "NY", "massachusetts": "MA",
        "illinois": "IL", "florida": "FL", "georgia": "GA", "pennsylvania": "PA",
        "north carolina": "NC", "michigan": "MI", "virginia": "VA", "washington": "WA",
        "ohio": "OH", "arizona": "AZ", "ca": "CA", "tx": "TX", "ny": "NY", "ma": "MA",
        "il": "IL", "fl": "FL", "ga": "GA", "pa": "PA", "nc": "NC", "mi": "MI",
        "va": "VA", "wa": "WA", "oh": "OH", "az": "AZ"
    }
    for word in prompt.lower().split():
        if word in state_map:
            return state_map[word]
    return ""

def summarize_data_for_prompt(data: list) -> str:
    if not data:
        return ""
    summary = []
    for row in data[:10]:
        line = [f"{SHORT_COLUMN_NAMES.get(col, col)}: {val}" for col, val in row.items() if val]
        summary.append(" | ".join(line))
    return "\n".join(summary)

def parse_date_string(date_str):
    try:
        return datetime.datetime.strptime(date_str.strip(), "%B %d")
    except Exception:
        return None

def parse_numeric_filters(prompt: str):
    numeric_filters = []
    patterns = [
        (r"greater than \$?([\d,]+)", ">", "MEDIAN_SALARY_AFTER_GRADUATION"),
        (r"less than \$?([\d,]+)", "<", "MEDIAN_SALARY_AFTER_GRADUATION"),
        (r"salary.*over \$?([\d,]+)", ">", "MEDIAN_SALARY_AFTER_GRADUATION"),
        (r"undergraduate enrollment less than ([\d,]+)", "<", "UNDERGRADUATE_ENROLLMENT"),
        (r"undergraduate enrollment greater than ([\d,]+)", ">", "UNDERGRADUATE_ENROLLMENT"),
    ]
    for pattern, op, col in patterns:
        match = re.search(pattern, prompt.lower())
        if match:
            num = int(match.group(1).replace(",", ""))
            numeric_filters.append((col, op, num))
    return numeric_filters

def search_and_filter(prompt: str) -> list:
    relevant_columns = identify_relevant_columns(prompt)
    gpa, sat = extract_gpa_and_sat(prompt)
    numeric_filters = parse_numeric_filters(prompt)
    location_abbr = extract_location_state_abbr(prompt)
    check_deadline = "deadline" in prompt.lower() and "after" in prompt.lower()

    if not relevant_columns and (gpa or sat or check_deadline or numeric_filters):
        relevant_columns = DEFAULT_COLUMNS
    if "COLLEGE_NAME" not in relevant_columns:
        relevant_columns.append("COLLEGE_NAME")
    if "LOCATION" not in relevant_columns:
        relevant_columns.append("LOCATION")

    query = f"""
        SELECT {', '.join(relevant_columns)}
        FROM {COLLEGE_TABLE}
        WHERE {" AND ".join([f"{col} IS NOT NULL" for col in relevant_columns])}
        ORDER BY RANKING ASC
        LIMIT 100
    """
    results = query_snowflake(query)

    for row in results:
        for col in ["UNDERGRADUATE_ENROLLMENT", "MEDIAN_SALARY_AFTER_GRADUATION"]:
            try:
                row[col] = float(row[col])
            except:
                row[col] = None

    if check_deadline:
        jan15 = datetime.datetime.strptime("January 15", "%B %d")
        results = [
            row for row in results
            if "APPLICATION_DEADLINE" in row and parse_date_string(str(row["APPLICATION_DEADLINE"])) and
               parse_date_string(str(row["APPLICATION_DEADLINE"])) > jan15
        ]

    if gpa or sat:
        filtered = []
        for row in results:
            gpa_match = True  # ✅ always pass GPA
            sat_match = False

            sat_str = str(row.get("SAT_RANGE", "")).strip()
            match = re.search(r"(\d{3,4})\s*[-–]?\s*(\d{3,4})?", sat_str)
            if match and sat:
                low = int(match.group(1))
                high = int(match.group(2)) if match.group(2) else low
                sat_match = low <= sat <= high

            if gpa_match or sat_match:
                filtered.append(row)
        results = filtered

    if numeric_filters:
        results = [
            row for row in results
            if all(
                isinstance(row.get(col), (int, float)) and
                ((op == ">" and row[col] > val) or (op == "<" and row[col] < val))
                for col, op, val in numeric_filters
            )
        ]

    if location_abbr:
        results = [
            row for row in results
            if "LOCATION" in row and re.search(rf",\s*{location_abbr}\b", row["LOCATION"], flags=re.IGNORECASE)
        ]

    return results

def generate_recommendation(prompt: str, data: list) -> str:
    if not data:
        return ""
    llm = ChatOpenAI(model="gpt-4", temperature=0.3)
    summary = summarize_data_for_prompt(data)
    return llm.invoke(
        f"""You are a helpful assistant.
Use only the following college data to respond:

{summary}

User Prompt: {prompt}

Respond only using the colleges in the data. If none match all conditions, return an empty string.
"""
    ).content

# ---------------------- AGENT FLOW ----------------------
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
    if state["response"]:
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

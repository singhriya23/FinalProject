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
    "act": "ACT_RANGE",
    "fee": "TUITION_FEES",
    "tuition": "TUITION_FEES",
    "salary": "MEDIAN_SALARY_AFTER_GRADUATION",
    "acceptance": "ACCEPTANCE_RATE",
    "graduation": "GRADUATION_RATE",
    "ranking": "RANKING",
    "enrollment": "UNDERGRADUATE_ENROLLMENT",
    "location": "LOCATION",
    "class size": "AVERAGE_CLASS_SIZE",
    "average class size": "AVERAGE_CLASS_SIZE"
}

COLLEGE_TABLE = "TOP_30.UNIVERSITY_LIST"

SHORT_COLUMN_NAMES = {
    "COLLEGE_NAME": "Name",
    "APPLICATION_DEADLINE": "Deadline",
    "TUITION_FEES": "Fee",
    "GRADUATION_RATE": "Grad Rate",
    "RANKING": "Rank",
    "SAT_RANGE": "SAT",
    "ACT_RANGE": "ACT",
    "MINIMUM_GPA": "GPA",
    "ACCEPTANCE_RATE": "Acceptance",
    "MEDIAN_SALARY_AFTER_GRADUATION": "Salary",
    "UNDERGRADUATE_ENROLLMENT": "Undergrad Enrollment",
    "AVERAGE_CLASS_SIZE": "Class Size",
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

def parse_date_string(date_str):
    try:
        return datetime.datetime.strptime(date_str.strip(), "%B %d")
    except Exception:
        return None

def parse_numeric_filters(prompt: str):
    filters = []
    patterns = [
        (r"(greater than|above) (\d+)%", ">", "ACCEPTANCE_RATE"),
        (r"greater than \$?([\d,]+)", ">", "MEDIAN_SALARY_AFTER_GRADUATION"),
        (r"less than \$?([\d,]+)", "<", "MEDIAN_SALARY_AFTER_GRADUATION"),
        (r"undergraduate enrollment less than ([\d,]+)", "<", "UNDERGRADUATE_ENROLLMENT"),
        (r"undergraduate enrollment greater than ([\d,]+)", ">", "UNDERGRADUATE_ENROLLMENT")
    ]
    for pattern, op, col in patterns:
        match = re.search(pattern, prompt.lower())
        if match:
            value = match.group(2) if len(match.groups()) > 1 else match.group(1)
            num = int(value.replace(",", ""))
            filters.append((col, op, num))
    return filters

def search_compare_data(prompt: str) -> list:
    cols = [col for word, col in COLUMN_MAPPING.items() if word in prompt.lower()]
    gpa_match = re.search(r"\b(\d\.\d{1,2})\b", prompt)
    sat_match = re.search(r"\b(\d{3,4})\b", prompt)
    gpa = float(gpa_match.group(1)) if gpa_match else None
    sat = int(sat_match.group(1)) if sat_match else None
    numeric_filters = parse_numeric_filters(prompt)
    check_deadline = "deadline" in prompt.lower() and "after" in prompt.lower()

    if not cols and (gpa or sat or numeric_filters or check_deadline):
        cols = DEFAULT_COLUMNS

    if "COLLEGE_NAME" not in cols:
        cols.append("COLLEGE_NAME")

    if check_deadline and "APPLICATION_DEADLINE" not in cols:
        cols.append("APPLICATION_DEADLINE")

    query = f"SELECT {', '.join(cols)} FROM {COLLEGE_TABLE}"
    results = query_snowflake(query)

    for row in results:
        for key in ["UNDERGRADUATE_ENROLLMENT", "MEDIAN_SALARY_AFTER_GRADUATION"]:
            try:
                row[key] = float(row[key])
            except:
                row[key] = None

        if "ACCEPTANCE_RATE" in row and isinstance(row["ACCEPTANCE_RATE"], str):
            match = re.search(r"(\d+)", row["ACCEPTANCE_RATE"])
            row["ACCEPTANCE_RATE"] = int(match.group(1)) if match else None

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
            gpa_match = sat_match = False
            gpa_str = str(row.get("MINIMUM_GPA", "")).strip()
            match = re.search(r"(\d+(?:\.\d+)?)\s*[-–]?\s*(\d+(?:\.\d+)?)?", gpa_str)
            if match and gpa:
                low = float(match.group(1))
                high = float(match.group(2)) if match.group(2) else low
                gpa_match = low <= gpa <= high
            elif gpa_str.replace(".", "", 1).isdigit():
                gpa_match = gpa >= float(gpa_str)

            sat_str = str(row.get("SAT_RANGE", "")).strip()
            match = re.search(r"(\d{3,4})\s*[-–]?\s*(\d{3,4})?", sat_str)
            if match and sat:
                low = int(match.group(1))
                high = int(match.group(2)) if match.group(2) else low
                sat_match = low <= sat <= high

            if gpa_match or sat_match:
                filtered.append(row)
        results = filtered

    for col, op, val in numeric_filters:
        results = [
            row for row in results
            if isinstance(row.get(col), (int, float)) and (
                (op == ">" and row[col] > val) or (op == "<" and row[col] < val)
            )
        ]

    if "class size" in prompt.lower() and "below" in prompt.lower():
        results = [
            row for row in results
            if "AVERAGE_CLASS_SIZE" in row and any(
                limit in row["AVERAGE_CLASS_SIZE"] for limit in ["10 – 20", "10-20"]
            )
        ]

    if "california" in prompt.lower():
        results = [
            row for row in results
            if "LOCATION" in row and ", ca" in row["LOCATION"].lower()
        ]

    return results

def generate_comparison(prompt: str, data: list) -> str:
    if not data:
        return "❌ No valid comparison found in Snowflake for the given prompt."

    llm = ChatOpenAI(model="gpt-4", temperature=0.3)
    rows = []
    for row in data:
        parts = [f"{SHORT_COLUMN_NAMES.get(k, k)}: {v}" for k, v in row.items() if v]
        rows.append(" | ".join(parts))
    formatted = "\n".join(rows)

    return llm.invoke(
        f"""You are a helpful assistant.
Compare the following colleges using only the data below:

{formatted}

User prompt: {prompt}

Generate a clean, tabular comparison.
"""
    ).content

# ---------------------- AGENT FLOW ----------------------
def input_node(state): prompt = input("\n💬 What would you like to compare?\n> "); return {"prompt": prompt}
def fetch_data_node(state): return {"prompt": state["prompt"], "data": search_compare_data(state["prompt"])}
def generate_response_node(state): return {"response": generate_comparison(state["prompt"], state["data"])}
def output_node(state): print("\n📊 COMPARISON RESULT:\n"); print(state["response"]); return state

compare_graph = Graph()
compare_graph.add_node("input", input_node)
compare_graph.add_node("fetch_data", fetch_data_node)
compare_graph.add_node("generate_response", generate_response_node)
compare_graph.add_node("output", output_node)
compare_graph.set_entry_point("input")
compare_graph.add_edge("input", "fetch_data")
compare_graph.add_edge("fetch_data", "generate_response")
compare_graph.add_edge("generate_response", "output")

compare_agent = compare_graph.compile()

if __name__ == "__main__":
    compare_agent.invoke({"prompt": ""})

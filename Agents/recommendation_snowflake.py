import os
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

COLLEGE_ALIASES = {
    "mit": "Massachusetts Institute of Technology",
    "harvard": "Harvard University",
    "yale": "Yale University",
    "princeton": "Princeton University",
    "upenn": "University of Pennsylvania",
    "penn": "University of Pennsylvania",
    "dartmouth": "Dartmouth College",
    "brown": "Brown University",
    "columbia": "Columbia University",
    "cornell": "Cornell University",
    "stanford": "Stanford University",
    "nyu": "New York University",
    "ucla": "University of California – Los Angeles",
    "uc berkeley": "University of California – Berkeley",
    "ucsd": "University of California – San Diego"
}

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

def get_all_college_names() -> list:
    try:
        query = f"SELECT DISTINCT COLLEGE_NAME FROM {COLLEGE_TABLE}"
        results = query_snowflake(query)
        return [row["COLLEGE_NAME"] for row in results]
    except Exception as e:
        print(f"⚠️ Could not fetch college names: {e}")
        return []

# ---------------------- FILTERING LOGIC ----------------------
def identify_relevant_columns(prompt: str) -> list:
    relevant_cols = []
    prompt_lower = prompt.lower()
    for term, column in COLUMN_MAPPING.items():
        if term in prompt_lower and column not in relevant_cols:
            relevant_cols.append(column)
    return relevant_cols

def extract_college_names(prompt: str) -> list:
    prompt_lower = prompt.lower()
    matched_names = []
    for alias, full_name in COLLEGE_ALIASES.items():
        if alias in prompt_lower:
            matched_names.append(full_name)
    all_colleges = get_all_college_names()
    for name in all_colleges:
        if name.lower() in prompt_lower and name not in matched_names:
            matched_names.append(name)
    return list(set(matched_names))

def summarize_data_for_prompt(data: list) -> str:
    if not data:
        return "No matching college data found."
    summary_lines = []
    for row in data[:10]:
        parts = []
        for col, val in row.items():
            short_col = SHORT_COLUMN_NAMES.get(col, col)
            if val is not None:
                parts.append(f"{short_col}: {val}")
        summary_lines.append(" | ".join(parts))
    return "\n".join(summary_lines)

def search_and_filter(prompt: str) -> list:
    relevant_columns = identify_relevant_columns(prompt)
    college_names = extract_college_names(prompt)
    prompt_lower = prompt.lower()

    # Dynamic fallback guard
    if not relevant_columns:
        vague_but_valid = any(kw in prompt_lower for kw in [
            "top", "best", "affordable", "value", "cheap", "expensive", "ranking", "low fee"
        ])
        if not vague_but_valid:
            return []
        relevant_columns = DEFAULT_COLUMNS

    if "COLLEGE_NAME" not in relevant_columns:
        relevant_columns.append("COLLEGE_NAME")
    if "LOCATION" not in relevant_columns:
        relevant_columns.append("LOCATION")
    columns_str = ", ".join(relevant_columns)

    college_filter = ""
    if college_names:
        name_filter = " OR ".join([f"COLLEGE_NAME ILIKE '%{name}%'" for name in college_names])
        college_filter = f"({name_filter})"

    location_filter = ""
    if "texas" in prompt_lower:
        location_filter = "LOCATION ILIKE '%texas%' OR LOCATION ILIKE '%TX%'"

    if college_filter and location_filter:
        filter_condition = f"{college_filter} AND ({location_filter})"
    elif college_filter:
        filter_condition = college_filter
    elif location_filter:
        filter_condition = location_filter
    else:
        filter_condition = " AND ".join([f"{col} IS NOT NULL" for col in relevant_columns])

    if "salary" in prompt_lower:
        order_by = "ORDER BY MEDIAN_SALARY_AFTER_GRADUATION DESC"
    elif "affordable" in prompt_lower or "lowest tuition" in prompt_lower:
        order_by = "ORDER BY TUITION_FEES ASC"
    elif "graduation rate" in prompt_lower and "highest" in prompt_lower:
        order_by = "ORDER BY GRADUATION_RATE DESC"
    else:
        order_by = "ORDER BY RANKING ASC"

    query = f"""
        SELECT {columns_str}
        FROM {COLLEGE_TABLE}
        WHERE {filter_condition}
        {order_by}
        LIMIT 50
    """
    try:
        return query_snowflake(query)
    except Exception as e:
        return [{"error": f"Error querying Snowflake: {e}"}]

# ---------------------- RESPONSE LOGIC ----------------------
def generate_recommendation(prompt: str, data: list) -> str:
    if not data or isinstance(data[0], dict) and (
        "error" in data[0] or all((v is None or v == "") for v in data[0].values())
    ):
        return "No data in our system match the prompt provided. Please use the web search agent for this query."

    llm = ChatOpenAI(model="gpt-4", temperature=0.3)
    summarized = summarize_data_for_prompt(data)
    response = llm.invoke(
        f"""You are a helpful college recommendation assistant.

        ONLY use the following summarized college data stored in Snowflake. DO NOT suggest universities not present in the data:
        {summarized}

        User prompt: \"{prompt}\"

        Be concise, specific, and avoid recommending colleges that are not in the provided list.
        """
    )
    return response.content

# ---------------------- AGENT NODES ----------------------
def input_node(state):
    prompt = input("\U0001F4AC What kind of colleges are you looking for? ")
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

# ---------------------- WORKFLOW ----------------------
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

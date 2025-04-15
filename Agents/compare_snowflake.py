import os
from dotenv import load_dotenv
import snowflake.connector
from langchain_openai import ChatOpenAI
from langgraph.graph import Graph

load_dotenv()

# ------------------------- CONFIGS --------------------------
COLUMN_MAPPING = {
    "fee": "TUITION_FEES",
    "tuition": "TUITION_FEES",
    "salary": "MEDIAN_SALARY_AFTER_GRADUATION",
    "acceptance": "ACCEPTANCE_RATE",
    "graduation": "GRADUATION_RATE",
    "gpa": "MINIMUM_GPA",
    "sat": "SAT_RANGE",
    "act": "ACT_RANGE",
    "ranking": "RANKING"
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
    query = f"SELECT DISTINCT COLLEGE_NAME FROM {COLLEGE_TABLE}"
    results = query_snowflake(query)
    return [row["COLLEGE_NAME"] for row in results]

# ---------------------- HELPERS ----------------------
def extract_college_names(prompt: str) -> list:
    prompt_lower = prompt.lower()
    matched = []
    for alias, full in COLLEGE_ALIASES.items():
        if alias in prompt_lower:
            matched.append(full)
    all_names = get_all_college_names()
    for name in all_names:
        if name.lower() in prompt_lower and name not in matched:
            matched.append(name)
    return list(set(matched))

def identify_relevant_columns(prompt: str) -> list:
    cols = []
    lower = prompt.lower()
    for keyword, column in COLUMN_MAPPING.items():
        if keyword in lower and column not in cols:
            cols.append(column)
    return cols

def search_compare_data(prompt: str) -> list:
    colleges = extract_college_names(prompt)
    if not colleges or len(colleges) < 2:
        return []

    columns = identify_relevant_columns(prompt)
    prompt_lower = prompt.lower()

    # Dynamically block clearly irrelevant prompts
    junk_keywords = ["vibes", "weather", "cafeteria", "dean", "president", "location", "scenery", "dorm", "food", "ranking algorithm"]
    if not columns and any(kw in prompt_lower for kw in junk_keywords):
        return []

    # Allow general comparisons with default metrics
    if not columns:
        columns = ["TUITION_FEES", "ACCEPTANCE_RATE", "GRADUATION_RATE", "MEDIAN_SALARY_AFTER_GRADUATION"]

    if "COLLEGE_NAME" not in columns:
        columns.append("COLLEGE_NAME")

    name_filter = " OR ".join([f"COLLEGE_NAME ILIKE '%{c}%'" for c in colleges])
    query = f"""
        SELECT {", ".join(columns)}
        FROM {COLLEGE_TABLE}
        WHERE {name_filter}
    """
    try:
        return query_snowflake(query)
    except:
        return []

def generate_comparison(prompt: str, data: list) -> str:
    if not data or isinstance(data[0], dict) and (
        "error" in data[0] or all((v is None or v == "") for v in data[0].values())
    ):
        return "No data in our system match the prompt provided. Please use the web search agent for this query."

    llm = ChatOpenAI(model="gpt-4", temperature=0.3)
    table = []
    for row in data:
        parts = [f"{SHORT_COLUMN_NAMES.get(k, k)}: {v}" for k, v in row.items() if v]
        table.append(" | ".join(parts))
    formatted = "\n".join(table)

    response = llm.invoke(
        f"""You are a helpful college comparison agent.
        The user wants to compare colleges based on the following data from Snowflake:

        {formatted}

        Prompt: "{prompt}"

        Return a clear, tabular comparison based only on the above data.
        If the data is missing or irrelevant, advise the user to use a web search agent.
        """
    )
    return response.content

# ---------------------- AGENT NODES ----------------------
def input_node(state):
    prompt = input("🔍 What would you like to compare? ")
    return {"prompt": prompt}

def fetch_data_node(state):
    prompt = state["prompt"]
    data = search_compare_data(prompt)
    return {"prompt": prompt, "data": data}

def generate_response_node(state):
    prompt = state["prompt"]
    data = state["data"]
    return {"response": generate_comparison(prompt, data)}

def output_node(state):
    print("\n📊 COMPARISON RESULT:\n")
    print(state["response"])
    return state

# ---------------------- GRAPH ----------------------
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

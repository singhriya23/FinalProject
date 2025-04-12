import os
import json
from dotenv import load_dotenv
import snowflake.connector

load_dotenv()

# Mapping prompt terms to Snowflake columns
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
    "stanford": "Stanford University"
}

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

def identify_relevant_columns(prompt: str) -> list:
    relevant_cols = []
    prompt_lower = prompt.lower()
    for term, column in COLUMN_MAPPING.items():
        if term in prompt_lower and column not in relevant_cols:
            relevant_cols.append(column)
    return relevant_cols if relevant_cols else ["COLLEGE_NAME", "TUITION_FEES", "RANKING"]

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

def search_college_data(prompt: str) -> list:
    relevant_columns = identify_relevant_columns(prompt)
    if "COLLEGE_NAME" not in relevant_columns:
        relevant_columns.append("COLLEGE_NAME")
    columns_str = ", ".join(relevant_columns)

    college_names = extract_college_names(prompt)

    if college_names:
        filter_condition = " OR ".join([f"COLLEGE_NAME ILIKE '%{name}%'" for name in college_names])
    else:
        filter_condition = " OR ".join([f"{col} IS NOT NULL" for col in relevant_columns])

    if "TUITION_FEES" in relevant_columns and "GRADUATION_RATE" in relevant_columns:
        order_by = "ORDER BY TUITION_FEES ASC"
    else:
        order_by = ""

    query = f"""
        SELECT {columns_str}
        FROM {COLLEGE_TABLE}
        WHERE {filter_condition}
        {order_by}
        LIMIT 50
    """
    try:
        results = query_snowflake(query)
        return results
    except Exception as e:
        print(f"❌ Error querying Snowflake: {e}")
        return []

def save_results_to_file(results: list, filename: str = "retrieved_college_data.json"):
    with open(filename, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n📁 Data saved to {filename}")

if __name__ == "__main__":
    user_prompt = input("💬 What college information are you looking for? ")
    retrieved_data = search_college_data(user_prompt)
    save_results_to_file(retrieved_data)

import os
import json
import re
from typing import List
from dotenv import load_dotenv
from langchain.schema import Document
from langchain.chat_models import ChatOpenAI

# ---- Load environment variables for OpenAI ----
load_dotenv(dotenv_path="Agents/.env")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o"

# ---- STRUCTURED VALIDATION ----
COLUMN_VALIDATION_RULES = {
    "COLLEGE_NAME": {"type": "varchar", "required": True},
    "TUITION_FEES": {"type": "number", "required": True},
    "GRADUATION_RATE": {"type": "varchar", "required": True},
    "ACCEPTANCE_RATE": {"type": "varchar"},
    "ACT_RANGE": {"type": "varchar"},
    "APPLICATION_DEADLINE": {"type": "varchar"},
    "AVERAGE_CLASS_SIZE": {"type": "varchar"},
    "COLLEGE_SETTING": {"type": "varchar"},
    "FOOD_AND_HOUSING": {"type": "number"},
    "GRADUATE_ENROLLMENT": {"type": "varchar"},
    "LOCATION": {"type": "varchar"},
    "MEDIAN_SALARY_AFTER_GRADUATION": {"type": "number"},
    "MINIMUM_GPA": {"type": "varchar"},
    "RANKING": {"type": "number"},
    "SAT_RANGE": {"type": "varchar"},
    "UNDERGRADUATE_ENROLLMENT": {"type": "varchar"}
}

def parse_percentage(value: str) -> float:
    try:
        if isinstance(value, str):
            number = re.sub(r"[^\d.]", "", value)
            return float(number)
        elif isinstance(value, (int, float)):
            return float(value)
    except:
        return None

def validate_college(college: dict, max_tuition: float, min_grad_rate: float) -> bool:
    for col_name, rules in COLUMN_VALIDATION_RULES.items():
        value = college.get(col_name)

        if rules.get("required") and (value in [None, "", "N/A"]):
            return False

        if col_name == "TUITION_FEES":
            try:
                if float(value) > max_tuition:
                    return False
            except:
                return False

        if col_name == "GRADUATION_RATE":
            percent_val = parse_percentage(value)
            if percent_val is not None and percent_val < min_grad_rate:
                return False

    return True

def load_college_data(path="retrieved_college_data.json") -> List[dict]:
    with open(path, "r") as f:
        return json.load(f)

# ---- UNSTRUCTURED VALIDATION ----
def load_unstructured_docs(path="retriever_output.json") -> (str, List[Document]):
    with open(path, "r") as f:
        data = json.load(f)
    query = data["query"]
    docs = [Document(page_content=d["text"], metadata=d["metadata"]) for d in data["results"]]
    return query, docs

def validate_with_gpt(query: str, docs: List[Document]) -> (bool, str):
    llm = ChatOpenAI(model_name=OPENAI_MODEL, temperature=0.3, openai_api_key=OPENAI_API_KEY)

    # Combine docs as plain text without labeling them as Doc 1, Doc 2, etc.
    context = "\n\n".join([d.page_content for d in docs])

    validation_prompt = f"""
You are a validation agent. Your task is to assess whether the following unstructured information is relevant and helpful in answering the user's query.

User Query:
\"{query}\"

Unstructured Context:
\"\"\"
{context}
\"\"\"

Please analyze the context and determine if it contains useful and relevant information to answer the query.

Return a valid JSON object:
{{
  "verdict": "pass" or "fail",
  "reason": "Explain why the content is or isn't useful, without referring to document numbers."
}}
"""

    response = llm.predict(validation_prompt).strip()

    # Remove markdown formatting if GPT wrapped the response in triple backticks
    if response.startswith("```") and response.endswith("```"):
        response = "\n".join(response.split("\n")[1:-1]).strip()

    try:
        result = json.loads(response)
        return result.get("verdict", "").lower() == "pass", result.get("reason", "No reason provided")
    except Exception as e:
        return False, f"Failed to parse JSON: {str(e)}\nRaw response: {response}"

# ---- COMBINED VALIDATION LOGIC ----
def combined_validator(query: str, max_tuition: float, min_grad_rate: float):
    # Structured
    structured_data = load_college_data()
    valid_structured = [college for college in structured_data if validate_college(college, max_tuition, min_grad_rate)]

    # Unstructured
    query_text, docs = load_unstructured_docs()
    gpt_passed, reason = validate_with_gpt(query, docs)

    print("\n🎯 Combined Validation Report:")
    print(f"✅ Structured Valid Colleges Found: {len(valid_structured)}")
    print(f"{'✅' if gpt_passed else '❌'} GPT Validation: {'Passed' if gpt_passed else 'Failed'}")
    print(f"🧠 GPT Reason: {reason}")

    if gpt_passed:
        print("\n🎓 Final Validated Colleges:")
        for c in valid_structured:
            print(f" - {c['COLLEGE_NAME']}")
    else:
        print("\n📌 No final answer generated due to GPT validation failure.")

# ---- CLI ----
if __name__ == "__main__":
    query_input = input("Enter your prompt/query: ")
    try:
        max_fee = float(input("Max Tuition ($): "))
        min_grad = float(input("Min Graduation Rate (%): "))
        combined_validator(query_input, max_fee, min_grad)
    except ValueError:
        print("❌ Please enter valid numbers for tuition and graduation rate.")

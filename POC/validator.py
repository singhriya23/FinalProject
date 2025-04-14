import json
import re

# Define the schema (same as before, without hardcoded rules)
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

def load_data(filename: str = "retrieved_college_data.json") -> list:
    with open(filename, "r") as f:
        return json.load(f)

def parse_percentage(value: str) -> float:
    """Convert '82%' or '82' or even '82.5%' into float"""
    try:
        if isinstance(value, str):
            number = re.sub(r"[^\d.]", "", value)
            return float(number)
        elif isinstance(value, (int, float)):
            return float(value)
    except:
        return None

def validate_college(college: dict, max_tuition: float, min_grad_rate: float) -> dict:
    issues = []

    for col_name, rules in COLUMN_VALIDATION_RULES.items():
        value = college.get(col_name)

        # Required field check
        if rules.get("required") and (value in [None, "", "N/A"]):
            issues.append(f"Missing required field: {col_name}")
            continue

        if value is None:
            continue  # Skip optional checks

        if col_name == "TUITION_FEES":
            try:
                num_val = float(value)
                if num_val > max_tuition:
                    issues.append(f"{col_name} too high: {num_val}")
            except:
                issues.append(f"{col_name} is not a valid number")

        if col_name == "GRADUATION_RATE":
            percent_val = parse_percentage(value)
            if percent_val is not None and percent_val < min_grad_rate:
                issues.append(f"{col_name} too low: {percent_val}%")

    return {
        "college": college.get("COLLEGE_NAME", "Unknown"),
        "status": "valid" if not issues else "invalid",
        "issues": issues
    }

def validate_colleges(data: list, max_tuition: float, min_grad_rate: float) -> list:
    return [validate_college(college, max_tuition, min_grad_rate) for college in data]

def save_valid_colleges(results: list, filename: str = "valid_colleges.json"):
    valid_colleges = [r for r in results if r["status"] == "valid"]
    with open(filename, "w") as f:
        json.dump(valid_colleges, f, indent=2)
    print(f"✅ {len(valid_colleges)} valid colleges saved to {filename}")

def show_summary(results: list):
    print("\n🎓 Validation Summary:")
    for r in results:
        status = "✅" if r["status"] == "valid" else "❌"
        print(f"{status} {r['college']}")
        if r["issues"]:
            for issue in r["issues"]:
                print(f"   - {issue}")
    print()

if __name__ == "__main__":
    # Get dynamic thresholds from user
    try:
        max_tuition = float(input("Enter max tuition ($): "))
        min_grad_rate = float(input("Enter min graduation rate (%): "))
    except ValueError:
        print("❌ Invalid input. Please enter numeric values.")
        exit(1)

    data = load_data()
    validation_results = validate_colleges(data, max_tuition, min_grad_rate)
    show_summary(validation_results)
    save_valid_colleges(validation_results)

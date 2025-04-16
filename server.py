from mcp.server.fastmcp import FastMCP
from google.cloud import storage
import tempfile
from pathlib import Path
from PyPDF2 import PdfReader
import os
import signal
from functools import wraps
from datetime import datetime
import snowflake.connector
from bs4 import BeautifulSoup
import requests
from typing import Dict

# Create MCP server with timeout
mcp = FastMCP("EnhancedServer", request_timeout=60)
QS_RANKINGS_CACHE = None




# Timeout handler
def timeout_handler(signum, frame):
    raise TimeoutError("Operation timed out")

def timeout(seconds=30):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
                signal.alarm(0)
                return result
            except Exception as e:
                signal.alarm(0)
                raise
        return wrapper
    return decorator


@mcp.tool()
@timeout(60)
def get_qs_rankings(question: str) -> Dict:
    """
    Improved version that better handles ranking questions like:
    - "Which university is ranked 1st?"
    - "Who is number 1 in QS rankings?"
    - "Top ranked university?"
    """
    global QS_RANKINGS_CACHE

    try:
        # Load data if not cached
        if QS_RANKINGS_CACHE is None:
            url = "https://www.topuniversities.com/sites/default/files/qs-rankings-data/en/3740566_indicators.txt"
            headers = {"User-Agent": "Mozilla/5.0"}
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            QS_RANKINGS_CACHE = []
            for entry in response.json()["data"]:
                soup = BeautifulSoup(entry["uni"], "html.parser")
                name = soup.select_one(".uni-link").get_text(strip=True)
                rank = entry["overall_rank"]
                QS_RANKINGS_CACHE.append({"name": name, "rank": rank})

        question_lower = question.lower()

        # 1. Direct rank queries (e.g., "1st", "2nd", "ranked 5th")
        rank_words = ["1st", "2nd", "3rd", "4th", "5th", "first", "second", "third"]
        for i, word in enumerate(rank_words, 1):
            if word in question_lower:
                for uni in QS_RANKINGS_CACHE:
                    if uni["rank"] == str(i):
                        return {
                            "status": "success",
                            "answer": f"The #{i} ranked university is {uni['name']}"
                        }

        # 2. "Top university?" or "Who is number 1?"
        if any(keyword in question_lower for keyword in ["top university", "number 1", "ranked 1st"]):
            top_uni = next(uni for uni in QS_RANKINGS_CACHE if uni["rank"] == "1")
            return {
                "status": "success",
                "answer": f"The top-ranked university is {top_uni['name']}"
            }

        # 3. University name search (e.g., "MIT ranking")
        for uni in QS_RANKINGS_CACHE:
            if uni["name"].lower() in question_lower:
                return {
                    "status": "success",
                    "answer": f"{uni['name']} is ranked #{uni['rank']}"
                }

        # 4. Fallback: Return top 5 if no specific match
        top_5 = "\n".join([f"#{uni['rank']}: {uni['name']}" for uni in QS_RANKINGS_CACHE[:5]])
        return {
            "status": "success",
            "answer": f"Top 5 QS Rankings:\n{top_5}"
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

if __name__ == "__main__":
    print("Starting enhanced MCP server with timeout handling...")
    mcp.run()
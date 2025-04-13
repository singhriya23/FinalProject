from langchain.agents import Tool, initialize_agent
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search.tool import TavilySearchResults
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda
from dotenv import load_dotenv
import os
from typing import List, Dict

load_dotenv()

# Initialize GPT-3.5
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3)

# Tavily search tool
tavily_tool = TavilySearchResults(k=4, tavily_api_key=os.getenv("TAVILY_API_KEY"))

# Optional: LLM summarization prompt for polishing Tavily results
summary_prompt = PromptTemplate.from_template(
    """
You are an expert assistant. Summarize the search results below into 3–5 bullet points.
Focus on college name, tuition, and specialization in Artificial Intelligence. Be concise and helpful.

Search Results:
{raw_results}

Summary:
"""
)

# Chain: LLM + prompt → final clean output
summarize_chain = summary_prompt | llm

# This tool wraps Tavily + LLM summarization
def search_and_summarize(user_prompt: str) -> str:
    raw_results = tavily_tool.run(user_prompt)
    summary = summarize_chain.invoke({"raw_results": raw_results})
    return [line.strip("• ").strip() for line in summary.content.split("\n") if line.strip()]

# LangChain tool wrapper
tools = [
    Tool.from_function(
        func=search_and_summarize,
        name="Web Search",
        description="Use this to find recent college rankings, tuition, and programs based on the user prompt"
    )
]

# Agent setup
websearch_agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent="chat-zero-shot-react-description",
    verbose=True
)

def run_websearch_agent(user_prompt: str) -> List[Dict]:
    print(f"🌐 Web Query: {user_prompt}")
    raw_results = tavily_tool.run(user_prompt)
    summary = summarize_chain.invoke({"raw_results": raw_results})
    
    # Return structured results instead of plain text
    return [
        {
            "summary": line.strip("• ").strip(),
            "raw_results": raw_results,
            "source": "web_search"
        }
        for line in summary.content.split("\n") 
        if line.strip()
    ]

# CLI Test
if __name__ == "__main__":
    query = input("💬 What are you looking for? ")
    result = run_websearch_agent(query)
    print("\n✅ Final Answer:")
    print(result)

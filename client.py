import asyncio
import os
import json
from openai import OpenAI
from agents import Agent, Runner
from agents.mcp import MCPServerStdio
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

async def run_conversation():
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    async with MCPServerStdio(
        name="University Rankings Assistant",
        params={
            "command": "python",
            "args": ["server.py"]  # Your simplified server file
        }
    ) as server:
        
        agent = Agent(
            name="University Rankings Expert",
            instructions="""You are an expert on QS World University Rankings with one capability:
                        1. Answer questions about university rankings using get_qs_rankings
                        
                        For ranking questions:
                        - Always verify the university name if provided
                        - For rank number queries (e.g., "5th"), confirm the exact position
                        - When showing top universities, always mention it's from QS rankings
                        - Handle errors gracefully and suggest rephrasing if needed""",
            mcp_servers=[server]
        )
        
        while True:
            user_input = input("\nYour question about university rankings (or 'quit'): ").strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            
            try:
                # Process all queries through the rankings tool
                result = await Runner.run(
                    starting_agent=agent,
                    input=f"Answer this question about university rankings: {user_input}"
                )
                
                print("\nAssistant:", result.final_output)
                
                # Add OpenAI context for follow-up questions
                if "rank" in result.final_output.lower():
                    gpt_response = openai_client.chat.completions.create(
                        model="gpt-4-turbo",
                        messages=[{
                            "role": "system",
                            "content": """Provide helpful context about university rankings. 
                            When mentioning a ranked university:
                            - Note its historical ranking trends if significant
                            - Mention 1-2 notable strengths
                            - Suggest similar-ranked institutions
                            Keep responses concise and factual."""
                        }, {
                            "role": "user",
                            "content": f"About this university ranking: {result.final_output}"
                        }]
                    )
                    print("\nAdditional Context:", gpt_response.choices[0].message.content)
                    
            except Exception as e:
                print(f"\nError: {str(e)}")
                print("Please try again or rephrase your question.")

def display_welcome():
    print(f"""
    Welcome to QS University Rankings Assistant!
    
    You can ask about:
    - Specific rankings (e.g., "Which university is ranked 5th?")
    - University positions (e.g., "What is MIT's ranking?")
    - Top institutions (e.g., "Show top 10 universities")
    - Comparisons (e.g., "How does Oxford compare to Cambridge?")
    
    All data comes from the latest QS World University Rankings.
    """)

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("Please set OPENAI_API_KEY in .env file")
        exit(1)
        
    display_welcome()
    asyncio.run(run_conversation())
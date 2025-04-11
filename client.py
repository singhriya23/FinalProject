import asyncio
import os
import json
from openai import OpenAI
from agents import Agent, Runner
from agents.mcp import MCPServerStdio
from dotenv import load_dotenv

load_dotenv()

async def run_conversation():
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    async with MCPServerStdio(
        name="Education Assistant Server",
        params={
            "command": "python",
            "args": ["server.py"]  # Your enhanced server file
        }
    ) as server:
        
        agent = Agent(
            name="Education Advisor",
            instructions="""You have two capabilities:
                        1. Greet people using the greet tool
                        2. Parse education queries using parse_education_query
                        
                        For greeting requests, add a friendly follow-up.
                        For education queries, extract key parameters and suggest next steps.""",
            mcp_servers=[server]
        )
        
        while True:
            user_input = input("\nYour request (or 'quit'): ").strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            
            try:
                # First check if it's a greeting
                if any(keyword in user_input.lower() for keyword in ['hello', 'hi', 'greet']):
                    result = await Runner.run(
                        starting_agent=agent,
                        input=f"Greet the user and respond to: {user_input}"
                    )
                else:
                    # Process as education query
                    result = await Runner.run(
                        starting_agent=agent,
                        input=f"Parse and analyze: {user_input}"
                    )
                
                print("\nAssistant:", result.final_output)
                
                # For education queries, add OpenAI suggestions
                if "gpa" in result.final_output.lower() or "budget" in result.final_output.lower():
                    gpt_response = openai_client.chat.completions.create(
                        model="gpt-4-turbo",
                        messages=[{
                            "role": "system",
                            "content": "Suggest 2-3 relevant educational programs based on these parameters"
                        }, {
                            "role": "user",
                            "content": result.final_output
                        }]
                    )
                    print("\nRecommendations:", gpt_response.choices[0].message.content)
                    
            except Exception as e:
                print(f"\nError: {str(e)}")

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("Please set OPENAI_API_KEY in .env file")
        exit(1)
        
    print("""
    Welcome to Education Advisor!
    You can:
    - Get greeted (try 'Hello' or 'Greet me')
    - Parse education queries (try 'AI programs with 3.5 GPA')
    """)
    asyncio.run(run_conversation())
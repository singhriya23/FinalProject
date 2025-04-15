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
        name="Education Assistant Server",
        params={
            "command": "python",
            "args": ["server.py"]  # Your enhanced server file
        }
    ) as server:
        
        agent = Agent(
            name="Education Advisor",
            instructions="""You have four main capabilities:
                        1. Greet people using the greet tool
                        2. Check college application deadlines using get_college_deadline
                        3. Summarize files from Google Cloud Storage using summarize_gcs_file
                        4. List files in GCS buckets using list_gcs_files
                        
                        For greeting requests, add a friendly follow-up.
                        For deadline checks, verify the college name and provide deadline details.
                        For file operations, always confirm the bucket and file name before proceeding.
                        Handle errors gracefully and suggest alternatives when needed.""",
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
                # Check for deadline request
                elif any(keyword in user_input.lower() for keyword in ['deadline', 'due date', 'application date']):
                    result = await Runner.run(
                        starting_agent=agent,
                        input=f"Check the college application deadline for: {user_input}"
                    )
                # Check for file listing request
                elif any(keyword in user_input.lower() for keyword in ['list files', 'list documents', 'show files']):
                    result = await Runner.run(
                        starting_agent=agent,
                        input=f"List GCS files as requested: {user_input}"
                    )
                # Check for file summary request
                elif any(keyword in user_input.lower() for keyword in ['summarize', 'gcs', 'bucket', 'file']):
                    result = await Runner.run(
                        starting_agent=agent,
                        input=f"Summarize the GCS file as requested: {user_input}"
                    )
                else:
                    # Process as general education query
                    result = await Runner.run(
                        starting_agent=agent,
                        input=f"Analyze and respond to: {user_input}"
                    )
                
                print("\nAssistant:", result.final_output)
                
                # For education queries, add OpenAI suggestions
                if any(keyword in result.final_output.lower() for keyword in ['gpa', 'budget', 'deadline', 'college']):
                    gpt_response = openai_client.chat.completions.create(
                        model="gpt-4-turbo",
                        messages=[{
                            "role": "system",
                            "content": """Provide helpful educational advice based on the context. 
                            For deadlines: mention timeline strategies if approaching.
                            For colleges: suggest similar institutions if relevant.
                            Keep responses concise and actionable."""
                        }, {
                            "role": "user",
                            "content": result.final_output
                        }]
                    )
                    print("\nAdditional Recommendations:", gpt_response.choices[0].message.content)
                    
            except Exception as e:
                print(f"\nError: {str(e)}")
                print("Please try again or rephrase your request.")

def display_welcome():
    current_year = datetime.now().year
    next_year = current_year + 1
    
    print(f"""
    Welcome to Education Advisor {current_year}-{next_year}!
    
    You can:
    - Get greeted (try 'Hello' or 'Greet me')
    - Check college deadlines (try 'When is MIT's deadline?' or 'Stanford application date')
    - List GCS files (try 'Show files in my-documents-bucket')
    - Summarize documents (try 'Summarize syllabus.pdf from course-materials')
    - Get general advice (try 'Best CS schools with 3.5 GPA')
    
    Note: For file operations, specify both bucket and filename.
    """)

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("Please set OPENAI_API_KEY in .env file")
        exit(1)
        
    display_welcome()
    asyncio.run(run_conversation())
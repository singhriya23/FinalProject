import asyncio
from intents.profile_analyze import CollegeAgent

async def run_tests():
    agent = CollegeAgent()
    
    test_cases = [
        ("Hi there", "UNRELATED"),
        ("Find CS colleges in California", "COLLEGE_RELATED"),
        ("What's the weather?", "UNRELATED"),
        ("Best engineering schools for 3.5 GPA", "COLLEGE_RELATED"),
        ("Tell me a joke", "UNRELATED"),
        ("Universities with AI programs", "COLLEGE_RELATED")
    ]
    
    for query, expected_type in test_cases:
        print(f"\n🔹 Testing: '{query}'")
        response = await agent.handle_query(query)
        
        # Verify response type
        if "college recommendation" in response.lower():
            detected_type = "COLLEGE_RELATED"
        else:
            detected_type = "UNRELATED"
            
        print(f"Expected: {expected_type} | Got: {detected_type}")
        print(f"Response: {response}")

if __name__ == "__main__":
    asyncio.run(run_tests())
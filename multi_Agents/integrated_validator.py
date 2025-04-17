import os
from typing import Dict, Optional
from dotenv import load_dotenv
from openai import OpenAI
from multi_Agents.compare_snowflake import search_compare_data, generate_comparison
from multi_Agents.compareRAG import CollegeDocumentRetriever, GPT4CollegeComparator, resolve_college, index

# ---------- Load environment ----------
load_dotenv("Agents/.env")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ---------- Setup ----------
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# ---------- Custom Exceptions ----------
class ComparisonValidationError(Exception):
    """Base exception for comparison validation"""
    pass

class NoRelevantDataError(ComparisonValidationError):
    """When neither agent provides relevant data"""
    pass

class ValidationProcessingError(ComparisonValidationError):
    """When there's an error processing the validation"""
    pass

# ---------- Snowflake Agent ----------
def _get_snowflake_response(prompt: str) -> Optional[str]:
    try:
        data = search_compare_data(prompt)
        return generate_comparison(prompt, data) if data else None
    except Exception as e:
        raise ValidationProcessingError(f"Snowflake agent error: {str(e)}")

# ---------- RAG Agent ----------
def _get_rag_response(prompt: str) -> Optional[str]:
    try:
        retriever = CollegeDocumentRetriever(index)
        comparator = GPT4CollegeComparator()

        # Simple extraction of two college names (first and second occurrence)
        prompt_lower = prompt.lower()
        found = [c for c in retriever.known_colleges if c.lower() in prompt_lower]
        if len(found) < 2:
            return None

        clg1_resolved = resolve_college(found[0], retriever.known_colleges, retriever.alias_map)
        clg2_resolved = resolve_college(found[1], retriever.known_colleges, retriever.alias_map)

        if not clg1_resolved or not clg2_resolved:
            return None

        docs1 = retriever.get_documents_for_college(clg1_resolved)
        docs2 = retriever.get_documents_for_college(clg2_resolved)
        college_docs = {clg1_resolved: docs1, clg2_resolved: docs2}

        return comparator.compare(clg1_resolved, clg2_resolved, prompt, college_docs)
    except Exception as e:
        raise ValidationProcessingError(f"RAG agent error: {str(e)}")

# ---------- Validator Agent ----------
def compare_validate(prompt: str) -> Dict[str, Optional[str]]:
    """
    Enhanced comparison validator that returns structured results
    
    Returns:
        Dict with keys:
        - 'content': The comparison text (None if no relevant data)
        - 'source': Which sources contributed ('snowflake', 'rag', 'both', or None)
        - 'error': Error message if applicable (None if successful)
    """
    result = {
        'content': None,
        'source': None,
        'error': None
    }

    try:
        snowflake_output = _get_snowflake_response(prompt)
        rag_output = _get_rag_response(prompt)

        if not snowflake_output and not rag_output:
            raise NoRelevantDataError("Neither agent provided relevant comparison data")

        combined_prompt = f"""
You are a university comparison validator.

USER PROMPT:
{prompt}

SNOWFLAKE AGENT OUTPUT:
{snowflake_output if snowflake_output else '[No result]'}

RAG AGENT OUTPUT:
{rag_output if rag_output else '[No result]'}

TASK:
Review the outputs. If either contains relevant comparison information, combine them and return a clean, helpful comparison.
If neither provides relevant data, return an empty string.
"""

        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": combined_prompt}],
            temperature=0.5
        )
        
        validated_content = response.choices[0].message.content.strip()
        if validated_content in ('""', "''"):
            validated_content = ""
        
        if not validated_content:
            raise NoRelevantDataError("Validator returned empty content")

        # Determine which sources contributed
        sources = []
        if snowflake_output:
            sources.append("snowflake")
        if rag_output:
            sources.append("rag")
        
        result.update({
            'content': validated_content,
            'source': 'both' if len(sources) == 2 else sources[0] if sources else None
        })

    except NoRelevantDataError as e:
        result['error'] = str(e)
    except Exception as e:
        result['error'] = f"Validation processing error: {str(e)}"
    
    return result

# ---------- CLI ----------
if __name__ == "__main__":
    prompt = input("\n> ").strip()
    result = compare_validate(prompt)
    
    if result['content']:
        print("\n📊 COMPARISON RESULT:\n")
        print(f"Source: {result['source']}")
        print(result['content'])
    else:
        print(f"\n❌ No valid comparison: {result['error']}")
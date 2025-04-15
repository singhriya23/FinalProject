from mcp.server.fastmcp import FastMCP
from google.cloud import storage
from google.api_core import client_options
import tempfile
from pathlib import Path
from PyPDF2 import PdfReader
import os
import signal
from functools import wraps
from datetime import datetime
import snowflake.connector

# Create MCP server with timeout
mcp = FastMCP("EnhancedServer", request_timeout=60)

# Constants for your Snowflake structure
COLLEGE_TABLE = "TOP_30.UNIVERSITY_LIST"
COLLEGE_NAME_COL = "COLLEGE_NAME"
DEADLINE_COL = "APPLICATION_DEADLINE"

def get_snowflake_connection():
    """Establish connection to Snowflake using env variables"""
    return snowflake.connector.connect(
        user=os.getenv('SNOWFLAKE_USER'),
        password=os.getenv('SNOWFLAKE_PASSWORD'),
        account=os.getenv('SNOWFLAKE_ACCOUNT'),
        warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
        database=os.getenv('SNOWFLAKE_DATABASE', 'COLLEGE_DB'),
        schema=os.getenv('SNOWFLAKE_SCHEMA', 'TOP_30')
    )

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
@timeout(45)  # 45 second timeout for listing
def list_gcs_files(bucket_name: str) -> list:
    """List files with proper timeout handling"""
    try:
        # Create client with default timeout
        storage_client = storage.Client()
        
        # Set timeout for the operation
        blobs = storage_client.list_blobs(
            bucket_name,
            timeout=30  # 30 second timeout for GCS operation
        )
        
        # Convert to list with additional timeout
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(30)  # Extra timeout for processing
        try:
            return [blob.name for blob in blobs]
        finally:
            signal.alarm(0)
            
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
@timeout(120)  # 2 minute timeout for downloads
def summarize_gcs_file(bucket_name: str, blob_name: str) -> dict:
    """Download and summarize with proper timeouts"""
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        # Create temp file
        temp_dir = tempfile.mkdtemp()
        local_path = Path(temp_dir) / blob_name
        
        # Download with timeout
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(60)  # 1 minute download timeout
        try:
            blob.download_to_filename(local_path)
        finally:
            signal.alarm(0)
        
        # Process file
        if blob_name.lower().endswith('.pdf'):
            with open(local_path, 'rb') as f:
                reader = PdfReader(f)
                content = " ".join(page.extract_text() for page in reader.pages[:3])  # First 3 pages
        else:
            with open(local_path, 'r', encoding='utf-8') as f:
                content = f.read(500000)  # Read first 500KB
        
        # Clean up
        os.unlink(local_path)
        
        # Generate summary
        sentences = [s.strip() for s in content.split('.') if s.strip()]
        summary = '. '.join(sentences[:3]) + '.'
        
        return {
            "status": "success",
            "summary": summary,
            "truncated": len(content) >= 500000
        }
        
    except TimeoutError:
        return {"status": "error", "error": "Operation timed out"}
    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        if 'local_path' in locals() and os.path.exists(local_path):
            os.unlink(local_path)



@mcp.tool()
@timeout(30)  # Add timeout decorator
def get_college_deadline(college_name: str) -> dict:
    """
    Get application deadlines for a specific college from the UNIVERSITY_LIST table.
    Handles string-formatted dates like "January 2".
    
    Args:
        college_name: Name of the college to search for
        
    Returns:
        dict: College deadline information with structure:
        {
            "status": "success"|"error",
            "college": college_name,
            "deadline": str (formatted date),
            "days_remaining": int (None if can't calculate),
            "is_past_due": bool (None if can't determine),
            "raw_deadline": str (original value),
            "error": str (only if status="error")
        }
    """
    try:
        conn = get_snowflake_connection()
        cursor = conn.cursor()
        
        query = f"""
        SELECT {DEADLINE_COL}
        FROM {COLLEGE_TABLE}
        WHERE {COLLEGE_NAME_COL} ILIKE %s
        """
        cursor.execute(query, (f"%{college_name}%",))
        
        result = cursor.fetchone()
        
        if not result:
            return {
                "status": "success",
                "college": college_name,
                "message": "No deadline found for this college"
            }
        
        raw_deadline = result[0]
        today = datetime.now().date()
        days_remaining = None
        is_past_due = None
        formatted_deadline = raw_deadline
        
        # Try to parse string dates (like "January 2")
        if isinstance(raw_deadline, str):
            try:
                # Parse month day format (assumes current year)
                deadline_date = datetime.strptime(raw_deadline, "%B %d").date()
                # Set year to current year (or next year if date already passed)
                deadline_date = deadline_date.replace(year=today.year)
                if deadline_date < today:
                    deadline_date = deadline_date.replace(year=today.year + 1)
                
                days_remaining = (deadline_date - today).days
                is_past_due = days_remaining < 0
                formatted_deadline = deadline_date.strftime("%B %d, %Y")
            except ValueError:
                # If parsing fails, keep original string
                pass
        
        return {
            "status": "success",
            "college": college_name,
            "deadline": formatted_deadline,
            "days_remaining": days_remaining,
            "is_past_due": is_past_due,
            "raw_deadline": raw_deadline
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "college": college_name
        }
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("Starting enhanced MCP server with timeout handling...")
    mcp.run()
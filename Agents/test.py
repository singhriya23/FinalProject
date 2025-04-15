import sys
from pathlib import Path

# Add this before your imports
project_root = Path(__file__).parent.parent  # Goes up to FinalProject
sys.path.insert(0, str(project_root))  # Insert at start of path

# Now your imports will work
from newintent.dynamic_handler import DynamicIntentHandler
print("✓ Import successful!")
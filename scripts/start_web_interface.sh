#!/bin/bash
# Start the web interface (Streamlit)

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "Starting LLM Web Interface (Streamlit)..."
echo "The interface will open in your browser at http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop"
echo ""

if [ ! -f "web_interface.py" ]; then
    echo "❌ Error: web_interface.py not found in $PROJECT_DIR"
    exit 1
fi

streamlit run web_interface.py

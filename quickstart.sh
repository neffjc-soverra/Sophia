#!/bin/bash

echo "🏥 Hospital L&D Verification - Quick Start"

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found"
    exit 1
fi

python3 -m venv venv
source venv/bin/activate || source venv/Scripts/activate

pip install -r requirements.txt

mkdir -p temp_uploads
mkdir -p .streamlit

echo "✓ Setup complete!"
streamlit run app.py

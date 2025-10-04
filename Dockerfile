
# Use official lightweight Python image
FROM python:3.11-slim

# Set workdir
WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir fastapi uvicorn[standard] openpyxl

# Copy app files
COPY app.py app.py
COPY api.py api.py
COPY verification_helper.py verification_helper.py
COPY hospital_verification_config.json hospital_verification_config.json

# Expose ports (Streamlit 8501, API 8000)
EXPOSE 8501 8000

# Start both services with a simple process manager
CMD bash -lc "uvicorn api:app --host 0.0.0.0 --port 8000 & streamlit run app.py --server.port 8501 --server.address 0.0.0.0"

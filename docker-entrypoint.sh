#!/bin/bash

echo "Starting services..."

uvicorn api:app --host 0.0.0.0 --port 8000 &
API_PID=$!

sleep 2

streamlit run app.py --server.port 8501 --server.address 0.0.0.0 &
STREAMLIT_PID=$!

shutdown() {
    kill $API_PID $STREAMLIT_PID 2>/dev/null
    exit 0
}

trap shutdown SIGTERM SIGINT
wait -n
exit $?

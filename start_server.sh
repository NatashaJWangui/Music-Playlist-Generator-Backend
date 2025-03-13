#!/bin/bash

PORT=${PORT:-8000}  # Default to 8000 if PORT is not set

echo "Starting FastAPI server on port $PORT..."
uvicorn main:app --host 0.0.0.0 --port $PORT --reload

echo "Server is running. Logs are being written to server.log."
tail -f server.log

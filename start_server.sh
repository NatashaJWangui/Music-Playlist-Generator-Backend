#!/bin/bash

echo "Starting FastAPI server..."
uvicorn main:app --host 0.0.0.0 --port 8000 --reload


echo "Server is running. Logs are being written to server.log."
tail -f server.log
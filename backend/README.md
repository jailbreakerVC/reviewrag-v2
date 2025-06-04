### How to invoke API

# sample POST request


curl -X POST "http://localhost:8000/ask" \
     -H "Content-Type: application/json" \
     -d '{"question": "What is the camera specification for Nord ce4 lite?"}'

# Health check
curl "http://localhost:8000/health"

# Get status
curl "http://localhost:8000/status"

How test code directly

python langchaincode.py

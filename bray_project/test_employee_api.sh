#!/bin/bash
# Test script to call the /api/employee/ endpoint using curl

API_URL="http://localhost:8000/api/employee/"

echo "Calling endpoint: $API_URL"
echo "=================================================================================="

curl -s -X GET "$API_URL" | python -m json.tool

echo ""
echo "=================================================================================="

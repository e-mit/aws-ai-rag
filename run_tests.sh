#!/bin/bash

export DB_TABLE_NAME=testTable
export TEST=true
export LLM_LAMBDA_ARN=test

# Prevent terminal output waiting:
export AWS_PAGER=""

docker run --rm --name dynamodb_test_local -d -p 8000:8000 amazon/dynamodb-local
sleep 5
./create_test_db_table.sh

pytest tests

docker stop -t 0 dynamodb_test_local

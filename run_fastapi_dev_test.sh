#!/bin/bash

# Run the fastapi app locally.
# This uses the testing database and mocks out the query lambda.

export DB_TABLE_NAME=testTable
export TEST=true
export LLM_LAMBDA_ARN=test

export AUTH_SECRET_KEY='define this'
export AUTH_TOKEN_EXPIRE_MINS=2
export AUTH_USER_PASSWORD_HASH='define this'
export AUTH_ADMIN_PASSWORD_HASH='define this'

docker run --rm --name dynamodb_test_local -d -p 8000:8000 amazon/dynamodb-local
sleep 5
./create_test_db_table.sh

python fastapi_dev_test.py

echo "NOTE: Stop and delete the test database container with:"
echo "docker stop -t 0 dynamodb_test_local"
#!/bin/bash

# Run the fastapi app locally, for interactive manual testing.
# This uses a containerised test dynamoDB instance, and mocks out the query lambda.

export DB_TABLE_NAME=testTable
export TEST=true
export QUERY_LAMBDA_ARN=test
export OPENSEARCH_URL='https://search-osstest5-oss-domain-jepwdv34ir766dffssua7prvh4.eu-west-3.es.amazonaws.com'
export OSS_INDEX_NAME=news
export AWS_REGION=eu-west-3

source auth_dev.sh

docker run --rm --name dynamodb_test_local -d -p 8000:8000 amazon/dynamodb-local
sleep 5
./create_test_db_table.sh

echo ""
echo "Log in with temporary password: $TEMP_PWORD"
echo "Stop and delete the test dynamoDB container with:"
echo "docker stop -t 0 dynamodb_test_local"
echo ""

python fastapi_dev_test.py

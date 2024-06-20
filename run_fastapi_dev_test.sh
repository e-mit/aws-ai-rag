#!/bin/bash

# Run the fastapi app locally.
# This uses the testing database and mocks out the query lambda.

export DB_TABLE_NAME=testTable
export TEST=true
export LLM_LAMBDA_ARN=test

TEMP_PWORD=$(tr -dc A-Za-z0-9 </dev/urandom | head -c 7; echo)
BCRYPT_HASH=$(echo $TEMP_PWORD | python3 -c \
"import sys
from passlib.context import CryptContext
print(CryptContext(schemes=['bcrypt'], deprecated='auto').hash(sys.stdin.read().strip()))")
export AUTH_SECRET_KEY=$(openssl rand -hex 32)
export AUTH_TOKEN_EXPIRE_MINS=2
export AUTH_USER_PASSWORD_HASH=$BCRYPT_HASH
export AUTH_ADMIN_PASSWORD_HASH=$BCRYPT_HASH

docker run --rm --name dynamodb_test_local -d -p 8000:8000 amazon/dynamodb-local
sleep 5
./create_test_db_table.sh

echo ""
echo "Log in with temporary password: $TEMP_PWORD"
echo "Stop and delete the test database container with:"
echo "docker stop -t 0 dynamodb_test_local"
echo ""

python fastapi_dev_test.py

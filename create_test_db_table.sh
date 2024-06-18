#!/bin/bash

# Make a table in the local dynamodb test system

aws dynamodb create-table \
    --table-name $DB_TABLE_NAME \
    --attribute-definitions \
        AttributeName=id,AttributeType=S \
    --key-schema AttributeName=id,KeyType=HASH \
    --provisioned-throughput ReadCapacityUnits=3,WriteCapacityUnits=3 \
    --table-class STANDARD \
    --endpoint-url http://localhost:8000 &> /dev/null

sleep 5

aws dynamodb update-time-to-live \
    --table-name $DB_TABLE_NAME \
    --time-to-live-specification "Enabled=true,AttributeName=expiryTimestamp" \
    --endpoint-url http://localhost:8000 &> /dev/null

#!/bin/bash

export AWS_REGION=eu-west-3

export STACK_NAME=osstest1
export OSS_DOMAIN_NAME=${STACK_NAME}-domain


aws cloudformation deploy \
--template-file template.yml \
--stack-name $STACK_NAME \
--capabilities CAPABILITY_NAMED_IAM \
--parameter-overrides ossDomainName=$OSS_DOMAIN_NAME

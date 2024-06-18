#!/bin/bash

# A script to create a Cloudformation stack.

# Define STACK_NAME, then run this script like:
# ./stack.sh <stack name> <command> <3rd argument>

# Where "command" is one of the following:
entryFuncs=("delete" "create" "update_function" "update_layer" "loglevel")

# "delete": Delete the existing stack and all of its resources.
# "create": Create the stack. An error occurs if a stack already
#           exists with the provided name, and no update occurs.
# "update_function": Update just the lambda definitions.
# "update_layer": Update just the python dependency package layer.
# "loglevel": Change the lambda logging levels.

# Possible 3rd arguments:
#   "create": Optional 3rd argument is a space-separated list
#            of parameter-overrides to pass to cloudformation
#            deploy, which become template parameters.
#   "loglevel": Mandatory 3rd argument is a log level string
#               e.g. INFO, DEBUG, ERROR, etc.

############################################################

STACK_NAME=$1
ARG3=$3

if [[ -z $STACK_NAME ]]; then
    echo ERROR: Please set STACK_NAME
    return 1
else
    # Convert to lower-case
    STACK_NAME_LOWER="$(echo $STACK_NAME | tr '[A-Z]' '[a-z]')"
fi

# Prevent terminal output waiting:
export AWS_PAGER=""

_make_names() {
    MAIN_FUNCTION_NAME="${STACK_NAME}-lambda-main-scrape"
    NEWS_FUNCTION_NAME="${STACK_NAME}-lambda-news-scrape"
    # Note: bucket name must be lower case only, and globally unique
    RAND_ID=$(dd if=/dev/random bs=3 count=6 2>/dev/null \
              | od -An -tx1 | tr -d ' \t\n')
    BUCKET_NAME="${STACK_NAME_LOWER}-bucket-${RAND_ID}"
    LAYER_NAME="${STACK_NAME}-layer"
}

_delete_files() {
    rm -rf main_scrape_lambda/__pycache__ news_scrape_lambda/__pycache__
    rm -f main_scrape_lambda/*.pyc news_scrape_lambda/*.pyc out.yml *.zip
}

delete() {
    _delete_files
    _make_names
    echo "Deleting stack $STACK_NAME and its resources..."

    aws cloudformation delete-stack --stack-name $STACK_NAME
    if [[ "$?" -eq 0 ]]; then
        echo "Deleted $STACK_NAME"
    fi

    # Note that the layer(s) are not included in the stack.
    while true; do
    VERSION=$(aws lambda list-layer-versions \
    --layer-name $LAYER_NAME | \
    python3 -c \
"import sys, json
try:
    print(json.load(sys.stdin)['LayerVersions'][0]['Version'])
except:
    exit(1)")
    if [[ "$?" -ne 0 ]]; then
        break
    fi
    aws lambda delete-layer-version \
    --layer-name $LAYER_NAME \
    --version-number $VERSION
    echo "Deleted layer $LAYER_NAME:$VERSION"
    done
}

_prepare_packages() {
    rm -rf package venv
    /usr/bin/python3 -m venv venv
    source venv/bin/activate
    pip3 install --target package/python -r requirements.txt &> /dev/null
    pip3 install -r requirements.txt &> /dev/null
    pip3 install -r requirements-test.txt &> /dev/null
}

create() {
    _make_names
    _prepare_packages
    echo "Creating $STACK_NAME..."

    aws s3 mb s3://$BUCKET_NAME
    echo Made temporary S3 bucket $BUCKET_NAME

    aws cloudformation package \
    --template-file template.yml \
    --s3-bucket $BUCKET_NAME \
    --output-template-file out.yml &> /dev/null

    aws cloudformation deploy \
    --template-file out.yml \
    --stack-name $STACK_NAME \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides stackName=$STACK_NAME $ARG3

    if [[ "$?" -ne 0 ]]; then
        aws cloudformation describe-stack-events \
        --stack-name $STACK_NAME
    fi

    aws s3 rb --force s3://$BUCKET_NAME
    echo Deleted the temporary S3 bucket
}

loglevel() {
    # Set same log level for both lambda functions
    _make_names

    if [[ -z $ARG3 ]]; then
        echo "ERROR: log level string is required (INFO, DEBUG, etc.)"
        return 1
    fi

    export ARG3
    ENV_VARS=$(aws lambda get-function-configuration \
    --function-name $MAIN_FUNCTION_NAME | \
    python3 -c \
    "import sys, json, os
environment = json.load(sys.stdin)['Environment']
environment['Variables']['LOG_LEVEL'] = os.environ['ARG3']
print(json.dumps(environment))")

    aws lambda update-function-configuration \
    --function-name $MAIN_FUNCTION_NAME \
    --environment "$ENV_VARS" &> /dev/null

    if [[ "$?" -eq 0 ]]; then
        echo "Log level set to $ARG3 for $MAIN_FUNCTION_NAME"
    fi

    ENV_VARS=$(aws lambda get-function-configuration \
    --function-name $NEWS_FUNCTION_NAME | \
    python3 -c \
    "import sys, json, os
environment = json.load(sys.stdin)['Environment']
environment['Variables']['LOG_LEVEL'] = os.environ['ARG3']
print(json.dumps(environment))")

    aws lambda update-function-configuration \
    --function-name $NEWS_FUNCTION_NAME \
    --environment "$ENV_VARS" &> /dev/null

    if [[ "$?" -eq 0 ]]; then
        echo "Log level set to $ARG3 for $NEWS_FUNCTION_NAME"
    fi
}

update_function() {
    # Update both lambda functions
    _make_names
    _delete_files

    zip -r function.zip main_scrape_lambda
    aws lambda update-function-code \
    --function-name $MAIN_FUNCTION_NAME \
    --zip-file fileb://function.zip &> /dev/null
    if [[ "$?" -eq 0 ]]; then
        echo Updated Lambda $MAIN_FUNCTION_NAME
    fi

    rm -f *.zip
    zip -r function.zip news_scrape_lambda
    aws lambda update-function-code \
    --function-name $NEWS_FUNCTION_NAME \
    --zip-file fileb://function.zip &> /dev/null
    if [[ "$?" -eq 0 ]]; then
        echo Updated Lambda $NEWS_FUNCTION_NAME
    fi
}

update_layer() {
    # Apply same layer to both lambdas
    _make_names
    _prepare_packages
    rm -f *.zip
    cd package
    zip -r ../package.zip . &> /dev/null
    cd ..
    LAYER_ARN=$(aws lambda publish-layer-version \
    --layer-name $LAYER_NAME \
    --description "Python package layer" \
    --zip-file fileb://package.zip \
    --compatible-runtimes python3.10 \
    --compatible-architectures "x86_64" | jq -r '.LayerVersionArn')

    aws lambda update-function-configuration \
    --function-name $MAIN_FUNCTION_NAME \
    --layers $LAYER_ARN &> /dev/null

    if [[ "$?" -eq 0 ]]; then
        echo "Created and assigned layer $LAYER_ARN for $MAIN_FUNCTION_NAME"
    fi

    aws lambda update-function-configuration \
    --function-name $NEWS_FUNCTION_NAME \
    --layers $LAYER_ARN &> /dev/null

    if [[ "$?" -eq 0 ]]; then
        echo "Created and assigned layer $LAYER_ARN for $NEWS_FUNCTION_NAME"
    fi
}

################################################

ok=0
for i in "${entryFuncs[@]}"
do
    if [ "$i" == "$2" ]; then
        echo "Executing $i()"
        $i
        ok=1
    fi
done

if (( ok == 0 )); then
    echo "Error: command not recognised"
fi

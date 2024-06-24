#!/bin/bash

# A script to create a Cloudformation stack.

# Define STACK_NAME, then run this script like:
# ./stack.sh <stack name> <command> <3rd argument>

# Where "command" is one of the following:
entryFuncs=("delete" "create" "update_functions" "update_layer" "loglevel")

# "delete": Delete the existing stack and all of its resources.
# "create": Create the stack. An error occurs if a stack already
#           exists with the provided name, and no update occurs.
# "update_functions": Update just the lambda definitions.
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
MAIN_LAMBDA="main_scrape_lambda"
NEWS_LAMBDA="news_scrape_lambda"
FASTAPI_LAMBDA="fastapi_lambda"
QUERY_LAMBDA="query_lambda"

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
    # Note: bucket name must be lower case only, and globally unique
    RAND_ID=$(dd if=/dev/random bs=3 count=6 2>/dev/null \
              | od -An -tx1 | tr -d ' \t\n')
    BUCKET_NAME="${STACK_NAME_LOWER}-bucket-${RAND_ID}"
    LAYER_NAME="${STACK_NAME}-layer"
    LAMBDAS=($MAIN_LAMBDA $NEWS_LAMBDA $FASTAPI_LAMBDA $QUERY_LAMBDA)
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
    rm -rf layer
    pip3 install --target layer/python -r requirements.txt &> /dev/null
}

create() {
    _make_names
    _prepare_packages
    echo "Creating $STACK_NAME..."

    aws s3 mb s3://$BUCKET_NAME
    echo Made temporary S3 bucket $BUCKET_NAME

    for LAMBDA_NAME in "${LAMBDAS[@]}"
    do
        rm -rf $LAMBDA_NAME/__pycache__
        zip -r function.zip $LAMBDA_NAME &> /dev/null
        aws s3 cp function.zip s3://${BUCKET_NAME}/$LAMBDA_NAME
    done

    cd layer
    zip -r ../layer.zip . &> /dev/null
    cd ..
    aws s3 cp layer.zip s3://${BUCKET_NAME}/layer

    aws cloudformation deploy \
    --template-file template.yml \
    --stack-name $STACK_NAME \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides bucketName=$BUCKET_NAME $ARG3

    if [[ "$?" -ne 0 ]]; then
        aws cloudformation describe-stack-events \
        --stack-name $STACK_NAME
    fi

    echo "Waiting for stack creation to complete..."
    aws cloudformation wait stack-create-complete \
        --stack-name $STACK_NAME --no-paginate

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

    for LAMBDA_NAME in "${LAMBDAS[@]}"
    do
        ENV_VARS=$(aws lambda get-function-configuration \
        --function-name $STACK_NAME-$LAMBDA_NAME | \
        python3 -c \
        "import sys, json, os
environment = json.load(sys.stdin)['Environment']
environment['Variables']['LOG_LEVEL'] = os.environ['ARG3']
print(json.dumps(environment))")

        aws lambda update-function-configuration \
        --function-name $STACK_NAME-$LAMBDA_NAME \
        --environment "$ENV_VARS" &> /dev/null

        if [[ "$?" -eq 0 ]]; then
            echo "Log level set to $ARG3 for $STACK_NAME-$LAMBDA_NAME"
        fi
    done
}

update_functions() {
    # Update all lambda functions in the stack
    _make_names
    _delete_files
    for LAMBDA_NAME in "${LAMBDAS[@]}"
    do
        rm -f *.zip
        rm -rf $LAMBDA_NAME/__pycache__
        zip -r function.zip $LAMBDA_NAME
        aws lambda update-function-code \
        --function-name $STACK_NAME-$LAMBDA_NAME \
        --zip-file fileb://function.zip &> /dev/null
        if [[ "$?" -eq 0 ]]; then
            echo Updated Lambda $STACK_NAME-$LAMBDA_NAME
        fi
    done
}

update_layer() {
    # Apply same layer to all lambdas
    _make_names
    _prepare_packages
    rm -f *.zip
    cd layer
    zip -r ../layer.zip . &> /dev/null
    cd ..
    LAYER_ARN=$(aws lambda publish-layer-version \
    --layer-name $LAYER_NAME \
    --description "Python package layer" \
    --zip-file fileb://layer.zip \
    --compatible-runtimes python3.10 \
    --compatible-architectures "x86_64" | jq -r '.LayerVersionArn')

    for LAMBDA_NAME in "${LAMBDAS[@]}"
    do
        aws lambda update-function-configuration \
        --function-name $STACK_NAME-$LAMBDA_NAME \
        --layers $LAYER_ARN &> /dev/null

        if [[ "$?" -eq 0 ]]; then
            echo "Created and assigned layer $LAYER_ARN for $STACK_NAME-$LAMBDA_NAME"
        fi
    done
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

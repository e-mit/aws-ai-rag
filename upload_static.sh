#!/bin/bash

# Upload the contents of the /static/ directory to the website S3 storage bucket

# This uploads files in subfolders into a single folder by putting slashes in the
# uploaded filenames.

WEB_BUCKET_NAME=webapigw-bucket-40a1092d615b28af1720762b

FOLDER="static"

#############################################

# Ensure the folder path ends with a slash
FOLDER="${FOLDER%/}/"

find "$FOLDER" -type f | while IFS= read -r file; do
    relative_path="${file#$FOLDER}"
    echo "Uploading: $relative_path"
    aws s3 cp $file s3://${WEB_BUCKET_NAME}/$relative_path
done

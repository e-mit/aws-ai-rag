"""Gather the results of all GitHub action workflows, or timeout.

Optional command line input: a space-separated list of workflows to ignore.
"""

import os
import sys
import time
from typing import Any
from pathlib import Path
from io import BytesIO, TextIOWrapper
from zipfile import ZipFile
import requests


TIMEOUT_SECONDS: int = 600
PAUSE_SECONDS: int = 5
GH_API_VERSION: str = "2022-11-28"
ARTIFACT_FILENAME: str = "data.txt"
PASS_RETURN_VALUE: int = 0
FAIL_RETURN_VALUE: int = 1
WORKFLOW_SUCCESS: str = "success"
WORKFLOW_PATH: str = ".github/workflows"

GITHUB_SHA: str = os.environ['GITHUB_SHA']
REPO_PATH: str = os.environ['REPO_PATH']
GH_TOKEN: str = os.environ['GH_TOKEN']
BASE_URL = f"https://api.github.com/repos/{REPO_PATH}/actions/runs"
HEADERS = {"Accept": "application/vnd.github+json",
           "Authorization": f"Bearer {GH_TOKEN}",
           "X-GitHub-Api-Version": GH_API_VERSION}


def list_all_yaml_files(directory: Path | str) -> set[str]:
    """Get stem names of all yaml files in the specified directory."""
    files = set()
    for file in os.listdir(directory):
        if file.lower().endswith(".yaml") or file.lower().endswith(".yml"):
            files.add(str(Path(file).stem))
    return files


def list_exclude_files(input_list: list[str]) -> set[str]:
    """Get stem names of all files in the input list."""
    files = set()
    for file in input_list:
        if file.lower().endswith(".yaml") or file.lower().endswith(".yml"):
            files.add(str(Path(file).stem))
        else:
            files.add(file)
    return files


def get_workflows() -> list[dict[str, Any]]:
    """List all workflow names for the current commit."""
    workflow_query = f"{BASE_URL}?head_sha={GITHUB_SHA}"
    return requests.get(url=workflow_query, timeout=TIMEOUT_SECONDS,
                        headers=HEADERS).json()['workflow_runs']


def get_artifacts(workflow_id: str) -> list[dict[str, Any]]:
    """List all artifacts for the workflow with the input ID."""
    artifact_query = f"{BASE_URL}/{workflow_id}/artifacts"
    return requests.get(url=artifact_query, timeout=TIMEOUT_SECONDS,
                        headers=HEADERS).json()['artifacts']


def workflow_pass(archive_download_url: str) -> bool:
    """Open the data file in the artifact and check contents."""
    data = requests.get(url=archive_download_url, headers=HEADERS,
                        timeout=TIMEOUT_SECONDS)
    with ZipFile(BytesIO(data.content)) as z:
        with TextIOWrapper(z.open(ARTIFACT_FILENAME), encoding="utf-8") as f:
            if f.read().strip() == WORKFLOW_SUCCESS:
                return True
    return False


def wait_for_workflow_completion(exclude_workflow_files: list[str]) -> int:
    """Wait for all required workflow completion artifacts."""
    required_workflows = (list_all_yaml_files(Path(WORKFLOW_PATH))
                          - list_exclude_files(exclude_workflow_files))
    print(f"  Required workflows: {required_workflows}")
    start_time = time.time()
    while (time.time() - start_time) < TIMEOUT_SECONDS:
        passed_workflows: set[str] = set()
        for workflow in get_workflows():
            if workflow['name'] in required_workflows:
                expected_artifact_name = f"{workflow['name']}_{GITHUB_SHA}"
                for artifact in get_artifacts(workflow['id']):
                    if artifact['name'] == expected_artifact_name:
                        if workflow_pass(artifact['archive_download_url']):
                            passed_workflows.add(workflow['name'])
        if passed_workflows == required_workflows:
            print("Success: all required workflows have passed.")
            return PASS_RETURN_VALUE
        time.sleep(PAUSE_SECONDS)
    print("Fail: timeout.")
    print(f"  Passing workflows: {passed_workflows}")
    bad_workflows = required_workflows - passed_workflows  # type: ignore
    print(f"  Failed/incomplete workflows: {bad_workflows}")
    return FAIL_RETURN_VALUE


def wait_for_artifacts(required_artifact_names: list[str]) -> int:
    """Wait for chosen artifact(s)."""
    required_artifacts = set(required_artifact_names)
    print(f"  Required artifacts: {required_artifacts}")
    start_time = time.time()
    while (time.time() - start_time) < TIMEOUT_SECONDS:
        obtained_artifacts: set[str] = set()
        for workflow in get_workflows():
            for artifact in get_artifacts(workflow['id']):
                if artifact['name'] in required_artifacts:
                    obtained_artifacts.add(artifact['name'])
        if obtained_artifacts == required_artifacts:
            print("Success: all required artifacts were found.")
            return PASS_RETURN_VALUE
        time.sleep(PAUSE_SECONDS)
    print("Fail: timeout.")
    print(f"  Found: {obtained_artifacts}")
    missing = required_artifacts - obtained_artifacts  # type: ignore
    print(f"  Missing: {missing}")
    return FAIL_RETURN_VALUE


if __name__ == "__main__":
    if '-' in sys.argv[1:]:
        print("Wait for artifact(s).")
        sys.argv.remove('-')
        sys.exit(wait_for_artifacts(sys.argv[1:]))
    else:
        print("Wait for workflow completion.")
        sys.exit(wait_for_workflow_completion(sys.argv[1:]))

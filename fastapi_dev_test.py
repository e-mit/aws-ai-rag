"""Run the fastapi app locally.

This uses the testing database and mocks/replaces the AWS call of the
query lambda with a direct function call. Ensure that the
test dynamoDB docker container is running before running this script.
If the query text contains 'completed', then the database record will
simulate a completed response, else it will be a pending response.
"""

import uvicorn
from mypy_boto3_lambda.client import LambdaClient
from mypy_boto3_lambda.type_defs import InvocationResponseTypeDef

from fastapi_lambda import app_main, models, database
from query_lambda import lambda_function


class LambdaClientMock(LambdaClient):
    """Replace the client which invokes the query lambda.

    Simply fakes the query lambda response, either leaving the
    request in the pending state, or immediately moving it to completed.
    """

    def __init__(self):  # pylint: disable=W0231
        """Do nothing."""

    def invoke(self, *_args, **kwargs) -> InvocationResponseTypeDef:
        """Optionally update the database record."""
        query = models.LlmQuery.model_validate_json(kwargs['Payload'])
        if "completed" in query.query:
            # Add a fake LLM response
            database.update(
                query.id, database.LlmResponse(
                    answer="This is the answer.",
                    article_refs=["http://www.eg.com", "https://hi.net"]))
        return {}  # type: ignore


class QueryLambdaDirect(LambdaClient):
    """Replace the client which invokes the query lambda via AWS.

    This invokes the query lambda locally, via direct function call.
    Note that this is blocking, unlike the actual AWS lambda call.
    """

    def __init__(self):  # pylint: disable=W0231
        """Do nothing."""

    def invoke(self, *_args, **kwargs) -> InvocationResponseTypeDef:
        """Call the query lambda."""
        query = models.LlmQuery.model_validate_json(kwargs['Payload'])
        lambda_function.lambda_handler(
            {'id': query.id, 'query': query.query}, None)
        return {}  # type: ignore


# Mock-out the client used to call the query lambda
app_main.lambda_client = QueryLambdaDirect()


if __name__ == "__main__":
    uvicorn.run(app_main.app, host="0.0.0.0", port=8080)  # nosec

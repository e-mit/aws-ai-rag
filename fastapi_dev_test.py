"""Run the fastapi app locally.

This uses the testing database and mocks out the query lambda. Ensure the
test dynamoDB docker container is running before running this script.
If the query text contains 'completed', then the database record will
simulate a completed response, else it will be a pending response.
"""

import uvicorn
from mypy_boto3_lambda.client import LambdaClient
from mypy_boto3_lambda.type_defs import InvocationResponseTypeDef

from fastapi_lambda import app_main, models, database


class LambdaClientMock(LambdaClient):
    """Replace the client which invokes the LLM lambda."""

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


app_main.lambda_client = LambdaClientMock()


if __name__ == "__main__":
    uvicorn.run(app_main.app, host="0.0.0.0", port=8080)  # nosec

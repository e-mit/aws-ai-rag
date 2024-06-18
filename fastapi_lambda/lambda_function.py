"""Define the AWS Lambda using Mangum to call the FastAPI app."""

import logging
import os

from mangum import Mangum

from .app_main import app

LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG')
logger = logging.getLogger()
logger.setLevel(LOG_LEVEL)
logger.info('Starting.')

lambda_handler = Mangum(app)

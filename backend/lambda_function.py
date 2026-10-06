"""Keep the existing AWS handler name while routing requests through FastAPI."""
from mangum import Mangum

from main import app

lambda_handler = Mangum(app, lifespan="off")

import mlflow
from mlflow import autolog
from src.utils.env import MLFLOW_TRACKING_URI
from src.utils.log_manager import logger


def mlflow_autolog():
    try:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.set_experiment("ragscope")
        autolog()
    except Exception as e:
        logger.error(f"Error setting up MLflow: {e}")
        raise

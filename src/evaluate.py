import logging
from datetime import datetime

from langchain_ollama import ChatOllama
from mlflow.genai import evaluate
from mlflow.genai.scorers import Correctness, Safety
from mlflow.genai.scorers.deepeval import AnswerRelevancy, Hallucination

import mlflow
from src.config import OLLAMA_JUDGE_MODEL

logger = logging.getLogger(__name__)

_judge_llm: ChatOllama | None = None


def run_judge_evaluations(
    question: str,
    answer: str,
    context: str,
) -> dict[str, float]:
    scores: dict[str, float] = {}

    if mlflow.active_run():
        mlflow.end_run()

    run_name = datetime.now().strftime("%d-%m-%Y--%H-%M-%S")
    mlflow.start_run(run_name=run_name)
    scorers = [
        Correctness(model=f"ollama:/{OLLAMA_JUDGE_MODEL}"),
        AnswerRelevancy(model=f"ollama:/{OLLAMA_JUDGE_MODEL}"),
        Hallucination(model=f"ollama:/{OLLAMA_JUDGE_MODEL}"),
        Safety(model=f"ollama:/{OLLAMA_JUDGE_MODEL}"),
    ]

    eval_data = [
        {
            "inputs": {"question": question},
            "outputs": {"outputs": answer},
            "expectations": {
                "expected_response": [chunk for chunk in context.split("\n\n")]
            },
        },
    ]

    evaluate(data=eval_data, scorers=scorers)

    mlflow.end_run()

    return scores

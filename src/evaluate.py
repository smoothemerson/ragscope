from mlflow.genai import evaluate
from mlflow.genai.scorers import Correctness, Safety
from mlflow.genai.scorers.deepeval import AnswerRelevancy, Hallucination

from src.utils.env import OLLAMA_JUDGE_MODEL


def run_judge_evaluations(
    question: str,
    answer: str,
    context: str,
) -> None:
    judge_llm = f"ollama:/{OLLAMA_JUDGE_MODEL}"

    scorers = [
        Correctness(model=judge_llm),
        AnswerRelevancy(model=judge_llm),
        Hallucination(model=judge_llm),
        Safety(model=judge_llm),
    ]

    eval_data = [
        {
            "inputs": {"question": question},
            "outputs": {"outputs": answer},
            "expectations": {"expected_response": context.split("\n\n")},
        },
    ]

    evaluate(data=eval_data, scorers=scorers)

    return

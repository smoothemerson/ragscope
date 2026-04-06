from mlflow.genai import evaluate
from mlflow.genai.scorers import Safety
from mlflow.genai.scorers.deepeval import AnswerRelevancy, Hallucination

from src.utils.env import OLLAMA_JUDGE_MODEL
from src.utils.log_manager import logger


def run_judge_evaluations(
    question: str,
    answer: str,
    context_chunks: list[str],
) -> None:
    judge_llm = f"ollama:/{OLLAMA_JUDGE_MODEL}"

    scorers = [
        AnswerRelevancy(model=judge_llm),
        Hallucination(model=judge_llm),
        Safety(model=judge_llm),
    ]

    eval_data = [
        {
            "inputs": {"question": question},
            "outputs": {"outputs": answer},
            "expectations": {"context": "\n\n".join(context_chunks)},
        },
    ]

    try:
        evaluate(data=eval_data, scorers=scorers)
    except Exception as exc:
        logger.warning(f"Judge evaluation failed (answer still returned): {exc}")

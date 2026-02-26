import logging
import re

import mlflow
from langchain_ollama import OllamaLLM

from app.config import OLLAMA_BASE_URL, OLLAMA_JUDGE_MODEL
from app.prompts import ANSWER_RELEVANCE_PROMPT, CONTEXT_RELEVANCE_PROMPT, FAITHFULNESS_PROMPT

logger = logging.getLogger(__name__)

_judge_llm: OllamaLLM | None = None


def get_judge_llm() -> OllamaLLM:
    global _judge_llm
    if _judge_llm is None:
        _judge_llm = OllamaLLM(model=OLLAMA_JUDGE_MODEL, base_url=OLLAMA_BASE_URL)
    return _judge_llm


def _parse_score(text: str) -> float:
    match = re.search(r"(\d+\.?\d*)", text.strip())
    if match:
        value = float(match.group(1))
        if 0.0 <= value <= 1.0:
            return value
    return -1.0


def run_judge_evaluations(
    question: str,
    answer: str,
    context: str,
    run_id: str,
) -> dict[str, float]:
    judge = get_judge_llm()
    scores: dict[str, float] = {}

    prompts = {
        "faithfulness_score": FAITHFULNESS_PROMPT.format(
            context=context, question=question, answer=answer
        ),
        "answer_relevance_score": ANSWER_RELEVANCE_PROMPT.format(
            question=question, answer=answer
        ),
        "context_relevance_score": CONTEXT_RELEVANCE_PROMPT.format(
            question=question, context=context
        ),
    }

    with mlflow.start_run(run_id=run_id):
        for metric_name, prompt in prompts.items():
            try:
                response = judge.invoke(prompt)
                score = _parse_score(response)
                if score == -1.0:
                    mlflow.set_tag(f"{metric_name}_parse_warning", "true")
                    logger.warning("Could not parse score for %s: %r", metric_name, response)
            except Exception as exc:
                logger.warning("Judge evaluation failed for %s: %s", metric_name, exc)
                score = -1.0
                mlflow.set_tag(f"{metric_name}_parse_warning", "true")
            scores[metric_name] = score
            mlflow.log_metric(metric_name, score)

    return scores

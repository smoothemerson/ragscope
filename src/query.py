import logging

from fastapi import HTTPException
from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence
from langchain_ollama import ChatOllama, OllamaEmbeddings

import mlflow
from src.config import (
    CHROMA_PERSIST_DIR,
    MLFLOW_TRACKING_URI,
    OLLAMA_BASE_URL,
    OLLAMA_EMBED_MODEL,
    OLLAMA_MODEL,
)
from src.evaluate import run_judge_evaluations
from src.models import QueryRequest, QueryResponse

logger = logging.getLogger(__name__)


_llm: ChatOllama | None = None

TEMPLATE = """
Você é um especialista em QA. Responda a pergunta abaixo utilizando o contexto informado.

Contexto: {contexto}

Pergunta: {question}
"""


def get_llm() -> ChatOllama:
    global _llm
    if _llm is None:
        _llm = ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL, temperature=0)
    return _llm


def _get_vectorstore() -> Chroma:
    embeddings = OllamaEmbeddings(model=OLLAMA_EMBED_MODEL, base_url=OLLAMA_BASE_URL)
    return Chroma(
        embedding_function=embeddings,
        persist_directory=CHROMA_PERSIST_DIR,
    )


async def handle_query(request: QueryRequest) -> QueryResponse:
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment("ragscope")
    mlflow.autolog()

    answer = ""
    sources: list[str] = []
    error_occurred = False

    try:
        vectorstore = _get_vectorstore()

        try:
            collection_count = vectorstore._collection.count()
        except Exception:
            collection_count = 0

        if collection_count == 0:
            raise HTTPException(
                status_code=404,
                detail="No documents found. Please ingest documents first.",
            )

        retriever = vectorstore.as_retriever(search_kwargs={"k": request.top_k})
        llm = get_llm()

        source_docs = retriever.invoke(request.question)
        sources = [doc.page_content for doc in source_docs]
        context = "\n\n".join(sources)

        prompt = PromptTemplate(
            input_variables=["contexto", "question"], template=TEMPLATE
        )
        sequence = RunnableSequence(prompt | llm)
        response = sequence.invoke({"contexto": context, "question": request.question})
        answer = response.content

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Query pipeline error: %s", exc)
        error_occurred = True
        answer = f"Error: {exc}"

    if not error_occurred and sources:
        run_judge_evaluations(
            question=request.question,
            answer=answer,
            context=context,
        )

    if error_occurred:
        raise HTTPException(status_code=500, detail=answer)

    return QueryResponse(answer=answer, sources=sources)

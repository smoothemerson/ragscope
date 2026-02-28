from datetime import datetime

from fastapi import HTTPException
from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence
from langchain_ollama import ChatOllama, OllamaEmbeddings

import mlflow
from src.evaluate import run_judge_evaluations
from src.models import QueryRequest, QueryResponse
from src.utils.env import (
    CHROMA_PERSIST_DIR,
    MLFLOW_TRACKING_URI,
    OLLAMA_BASE_URL,
    OLLAMA_EMBED_MODEL,
    OLLAMA_MODEL,
)
from src.utils.log_manager import logger

_llm: ChatOllama | None = None

TEMPLATE = """
You are a QA expert. Answer the question below using the provided context. Always respond in Brazilian Portuguese (pt-br).

Context: {contexto}

Question: {question}
"""


def get_llm() -> ChatOllama:
    global _llm
    if _llm is None:
        _llm = ChatOllama(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL, temperature=0)
    return _llm


def _get_vectorstore() -> Chroma:
    embeddings = OllamaEmbeddings(model=OLLAMA_EMBED_MODEL, base_url=OLLAMA_BASE_URL)
    return Chroma(
        collection_name="ragscope_collection",
        embedding_function=embeddings,
        persist_directory=CHROMA_PERSIST_DIR,
    )


async def handle_query(request: QueryRequest) -> QueryResponse:
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment("ragscope")

    if mlflow.active_run():
        mlflow.end_run()

    run_name = datetime.now().strftime("%d-%m-%Y--%H-%M-%S")
    mlflow.start_run(run_name=run_name)

    mlflow.autolog()

    answer = ""
    sources: list[str] = []

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

        if sources:
            run_judge_evaluations(
                question=request.question,
                answer=answer,
                context=context,
            )

        return QueryResponse(answer=answer, sources=sources)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Query pipeline error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    finally:
        mlflow.end_run()

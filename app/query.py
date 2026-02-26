import logging
import time
import uuid

import chromadb
from fastapi import HTTPException
from langchain.chains import RetrievalQA
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, OllamaLLM

import mlflow
from app.config import (
    CHROMA_COLLECTION,
    CHROMA_HOST,
    CHROMA_PORT,
    MLFLOW_TRACKING_URI,
    OLLAMA_BASE_URL,
    OLLAMA_EMBED_MODEL,
    OLLAMA_JUDGE_MODEL,
    OLLAMA_MODEL,
)
from app.evaluate import run_judge_evaluations
from app.models import QueryRequest, QueryResponse

logger = logging.getLogger(__name__)

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

_llm: OllamaLLM | None = None


def get_llm() -> OllamaLLM:
    global _llm
    if _llm is None:
        _llm = OllamaLLM(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL)
    return _llm


def _get_vectorstore() -> Chroma:
    chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    embeddings = OllamaEmbeddings(model=OLLAMA_EMBED_MODEL, base_url=OLLAMA_BASE_URL)
    return Chroma(
        client=chroma_client,
        collection_name=CHROMA_COLLECTION,
        embedding_function=embeddings,
    )


async def handle_query(request: QueryRequest) -> QueryResponse:
    query_id = str(uuid.uuid4())
    start_time = time.monotonic()

    mlflow.set_experiment("rag-evaluation")
    run = mlflow.start_run()
    run_id = run.info.run_id
    mlflow.end_run()

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
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            retriever=retriever,
            return_source_documents=True,
        )

        result = qa_chain.invoke({"query": request.question})
        answer = result["result"]
        source_docs = result.get("source_documents", [])
        sources = [doc.page_content for doc in source_docs]

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Query pipeline error: %s", exc)
        error_occurred = True
        answer = f"Error: {exc}"

    latency_ms = (time.monotonic() - start_time) * 1000

    with mlflow.start_run(run_id=run_id):
        mlflow.set_tag("query_id", query_id)
        mlflow.set_tag("generation_model", OLLAMA_MODEL)
        mlflow.set_tag("judge_model", OLLAMA_JUDGE_MODEL)
        if error_occurred:
            mlflow.set_tag("error", "true")
        mlflow.log_param("question", request.question)
        mlflow.log_param("top_k", request.top_k)
        mlflow.log_param("model_name", OLLAMA_MODEL)
        mlflow.log_param("query_id", query_id)
        mlflow.log_metric("latency_ms", latency_ms)
        mlflow.log_metric("num_chunks_retrieved", len(sources))
        mlflow.log_metric("answer_length_chars", len(answer))
        mlflow.log_text(answer, "answer.txt")

    if not error_occurred and sources:
        context = "\n\n".join(sources)
        run_judge_evaluations(
            question=request.question,
            answer=answer,
            context=context,
            run_id=run_id,
        )

    if error_occurred:
        raise HTTPException(status_code=500, detail=answer)

    return QueryResponse(answer=answer, sources=sources, query_id=query_id)

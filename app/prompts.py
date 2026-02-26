FAITHFULNESS_PROMPT = """You are evaluating an AI answer. Rate how well the answer is supported by the provided context.

Context: {context}

Question: {question}

Answer: {answer}

Output only a single number between 0.0 and 1.0. Example: 0.85
Score:"""

ANSWER_RELEVANCE_PROMPT = """You are evaluating an AI answer. Rate how well the answer addresses the question asked.

Question: {question}

Answer: {answer}

Output only a single number between 0.0 and 1.0. Example: 0.85
Score:"""

CONTEXT_RELEVANCE_PROMPT = """You are evaluating retrieved context. Rate how relevant the retrieved context is to answering the question.

Question: {question}

Context: {context}

Output only a single number between 0.0 and 1.0. Example: 0.85
Score:"""

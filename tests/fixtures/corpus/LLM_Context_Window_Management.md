---
title: "LLM Context Window Management Strategies"
type: reference
domain: ai-system
level: advanced
status: active
version: v1.0
tags: [llm, context-window, token-management, retrieval, ai-system]
related:
  - "[[Prompt_Engineering_Techniques_for_Structured_Output]]"
  - "[[Chain_of_Thought_Reasoning]]"
  - "[[LLM_Output_Validation_Pipeline_Architecture]]"
created: 2026-03-10
updated: 2026-03-10
---

## Purpose

Reference for strategies to manage LLM context windows effectively — covering token budgeting, retrieval augmentation, context compression, and sliding window techniques.

## Context Window Overview

| Model | Context Window | Effective Reasoning Depth |
|-------|---------------|--------------------------|
| GPT-4o | 128K tokens | ~60K (attention degrades) |
| Claude 3.5 Sonnet | 200K tokens | ~100K |
| Gemini 1.5 Pro | 1M tokens | ~500K |
| Llama 3.3 70B | 128K tokens | ~60K |

**Key insight:** Large context windows do not mean unlimited reasoning. Models exhibit "lost in the middle" — attention on information in the middle of long contexts degrades.

## Token Budget Allocation

```
Total context budget: 8,000 tokens (example)
├── System prompt: 500 tokens
├── Retrieved context: 3,000 tokens
├── Conversation history: 2,000 tokens
├── Current user message: 500 tokens
└── Output reserve: 2,000 tokens
```

**Rule:** Reserve at least 20% of context for model output.

## Strategy 1: Retrieval-Augmented Generation (RAG)

Retrieve only relevant context from a knowledge base instead of loading everything:

```python
from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer("all-MiniLM-L6-v2")

def retrieve_relevant_context(query: str, documents: list[str], top_k: int = 5) -> list[str]:
    query_embedding = model.encode([query])
    doc_embeddings = model.encode(documents)
    similarities = np.dot(query_embedding, doc_embeddings.T)[0]
    top_indices = np.argsort(similarities)[::-1][:top_k]
    return [documents[i] for i in top_indices]
```

## Strategy 2: Sliding Window (Conversation History)

For multi-turn conversations, keep only recent turns:

```python
MAX_HISTORY_TOKENS = 2000

def trim_history(messages: list[dict], max_tokens: int) -> list[dict]:
    total = 0
    trimmed = []
    for msg in reversed(messages):
        tokens = estimate_tokens(msg["content"])
        if total + tokens > max_tokens:
            break
        trimmed.insert(0, msg)
        total += tokens
    return trimmed
```

## Strategy 3: Summarization-Based Compression

Compress older conversation turns into summaries:

```python
def compress_history(messages: list[dict], llm) -> str:
    conversation_text = "\n".join(
        f"{m['role']}: {m['content']}" for m in messages
    )
    return llm.generate(
        f"Summarize this conversation in 2-3 sentences:\n{conversation_text}",
        system_prompt="Be concise. Preserve key decisions and facts.",
    )
```

## Strategy 4: Hierarchical Context

Structure context by relevance tier:

```
Tier 1 (always included):  System prompt, current task, schema
Tier 2 (conditionally):    Relevant retrieved documents
Tier 3 (if space allows):  Background reference material
Tier 4 (excluded):         Historical context, examples
```

## Token Estimation

```python
def estimate_tokens(text: str) -> int:
    # Rule of thumb: ~1.3 tokens per word for English
    return int(len(text.split()) * 1.3)

# More precise: use tiktoken for OpenAI models
import tiktoken
enc = tiktoken.encoding_for_model("gpt-4o")
def count_tokens(text: str) -> int:
    return len(enc.encode(text))
```

## Placement Best Practices

- **Important instructions:** Place at beginning and end of context
- **Reference documents:** Middle (use explicitly in instruction)
- **Examples:** Immediately before the task
- **History:** Most recent turns closest to current message

## Anti-Patterns

- Loading entire codebases into context (use RAG instead)
- Including irrelevant conversation history
- Embedding full documentation when summary suffices
- Not reserving tokens for output

## Conclusion

Context window management is a discipline — not an afterthought. Budget tokens explicitly, retrieve rather than load, and position critical instructions at context boundaries where attention is strongest.

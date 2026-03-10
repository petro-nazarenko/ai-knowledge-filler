---
title: "Chain-of-Thought Reasoning in AI Agents"
type: concept
domain: ai-system
level: advanced
status: active
tags: [chain-of-thought, reasoning, ai-agents, prompting, llm]
related:
  - "[[Prompt_Engineering_Techniques_for_Structured_Output|supersedes]]"
  - "[[LLM_Context_Window_Management]]"
  - "[[LLM_Output_Validation_Pipeline_Architecture|references]]"
created: 2026-03-10
updated: 2026-03-10
---

## Overview

Chain-of-thought (CoT) prompting is a technique that encourages LLMs to decompose complex reasoning into intermediate steps before producing a final answer. It significantly improves accuracy on multi-step tasks and makes model reasoning transparent and auditable.

## Core Mechanism

Without CoT:
```
Q: A train travels 120km in 2 hours, then 90km in 1.5 hours. What is the average speed?
A: 72 km/h
```

With CoT:
```
Q: A train travels 120km in 2 hours, then 90km in 1.5 hours. What is average speed?
A: Let me think step by step.
   Total distance = 120 + 90 = 210 km
   Total time = 2 + 1.5 = 3.5 hours
   Average speed = 210 / 3.5 = 60 km/h
   The answer is 60 km/h.
```

## CoT Variants

### Zero-Shot CoT
Add "Let's think step by step" to the prompt. No examples required.

```python
prompt = f"""
{user_question}

Let's think step by step.
"""
```

### Few-Shot CoT
Provide 2–3 worked examples demonstrating the reasoning pattern.

```markdown
Q: [Example question]
A: Step 1: [reasoning]
   Step 2: [reasoning]
   Answer: [conclusion]

Q: [New question]
A:
```

### Self-Consistency
Generate multiple CoT responses and select the majority answer. Reduces variance.

```python
def self_consistent_answer(question: str, n: int = 5) -> str:
    answers = [generate_cot(question) for _ in range(n)]
    final_answers = [extract_final_answer(a) for a in answers]
    return max(set(final_answers), key=final_answers.count)
```

### Tree of Thoughts (ToT)
Explore multiple reasoning paths simultaneously. Backtrack on dead ends.

```
Root question
├── Path A: [reasoning] → [sub-answer A]
├── Path B: [reasoning] → [sub-answer B]  ← selected
└── Path C: [reasoning] → [dead end, backtrack]
```

## Application in AI Agents

### Planning Agent

```python
AGENT_SYSTEM_PROMPT = """
Before taking any action:
1. Analyze the current state
2. Identify what needs to be accomplished
3. List possible approaches
4. Select the best approach with rationale
5. Execute the selected approach
6. Verify the result

Think through each step explicitly.
"""
```

### Validation Agent

```python
VALIDATION_PROMPT = """
Review this document for compliance:
1. Check each required field individually
2. For each field: state what was found vs what was expected
3. Classify each issue as blocking (error) or non-blocking (warning)
4. Summarize: VALID or INVALID with reason

Document:
{document}
"""
```

## When CoT Helps

- **Multi-step arithmetic** — decomposing calculations
- **Logical reasoning** — if-then chains
- **Planning tasks** — step sequencing
- **Code generation** — algorithm design before implementation
- **Classification with rationale** — explaining categorization decisions

## When CoT Doesn't Help

- Simple factual lookup (adds latency without benefit)
- Creative generation (interrupts flow)
- Very short outputs where reasoning chain exceeds output length

## CoT and Structured Output

CoT can conflict with structured output requirements. Pattern: reason first, then output:

```markdown
Think through the appropriate domain and type for this document:
- Content topic: [analysis]
- Closest domain: ai-system (matches AI pipeline content)
- Appropriate type: reference (specification-like content)

Now output the structured file:
---
title: "..."
type: reference
domain: ai-system
...
```

## Conclusion

Chain-of-thought prompting is one of the highest-leverage techniques in LLM engineering. For complex reasoning tasks, CoT improves accuracy by 15–40% over direct prompting. Use zero-shot CoT for general reasoning and few-shot CoT for domain-specific structured tasks.

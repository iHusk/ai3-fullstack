"""
tasks.py -- Pipeline task closures for Phoenix experiments.

A Phoenix "task" is a function that takes one dataset example (a dict) and
returns a dict of output that evaluators will grade. Each task runs a full
RAG pipeline end-to-end: retrieval + prompt assembly + generation.

We expose multiple tasks so Phoenix can run the same golden set through each
and produce a side-by-side comparison in the UI.

    client.experiments.run_experiment(dataset=..., task=naive_task, ...)
    client.experiments.run_experiment(dataset=..., task=hyde_task, ...)
    client.experiments.run_experiment(dataset=..., task=rewrite_only_task, ...)

Students explore by:
    - Reading the symmetric structure (tasks share helpers)
    - Adding their own task (e.g., `enriched_task`) once they've built
      `enriched_retrieve()` in Session 1.1
    - Inspecting what `naive_task({"question": "..."})` returns locally
"""

from pathlib import Path

from pipeline.retrieval.naive import naive_retrieve, build_prompt
from pipeline.generation.generate import call_claude_with_usage
from pipeline.context.assembler import (
    contextualize_query,
    assemble_context,
    naive_assemble,
)
from pipeline.observability.logger import PipelineLogger, StageTimer

_LOG_DIR = str(Path(__file__).resolve().parent.parent.parent / "logs")

# Note: hyde_retrieve is imported lazily inside hyde_task() because students
# build it during Session 1.1. On a fresh clone before 1.1, this module would
# fail to import at top level. Lazy import lets naive_task work regardless.


# The number of chunks each retrieval strategy pulls. 5 is a reasonable default
# for this corpus — small enough to keep context tight, large enough that
# multi-doc queries have a chance to find all their sources.
TOP_K = 5


# Mirrors app/rag.py:74-77 so the Session 2.2 context-management experiments
# measure exactly the prompt the chat app uses in production.
_CONTEXT_SYSTEM_PROMPT = (
    "You are a helpful assistant for Northbrook Partners employees.\n"
    "Answer questions using ONLY the provided source documents.\n"
    "If the sources don't contain enough information, say so.\n"
    "If prior conversation is shown, build on it — don't repeat previous answers."
)


def _run_pipeline(question: str, retrieve_fn, strategy: str = "unknown") -> dict:
    """Shared helper: retrieve chunks, build the RAG prompt, call Claude.

    Both naive_task and hyde_task use this — the only difference between
    them is which retrieve function they pass in. This keeps the task
    surface symmetric so comparisons are apples-to-apples.

    Args:
        question: The user query to answer.
        retrieve_fn: A function with the same contract as `naive_retrieve`
            (takes a question + top_k, returns list of {text, metadata, score}).
        strategy: Label written to pipeline.jsonl for Tableau slicing.

    Returns:
        A dict with `chunks` (what retrieval found) and `answer` (what
        generation produced). This shape is what Phoenix passes to evaluators
        as the `output` parameter.
    """
    _log = PipelineLogger(query=question, strategy=strategy)

    # Step 1: retrieval — get the top_k chunks for this question
    with StageTimer() as _ret:
        chunks = retrieve_fn(question, TOP_K)
    _log.log_retrieve(
        latency_ms=_ret.elapsed_ms,
        n_results=len(chunks),
        scores=[c.get("score", 0.0) for c in chunks],
        sources=[c.get("metadata", {}).get("source", "") for c in chunks],
    )

    # Step 2: prompt assembly — format chunks as a context block for Claude
    system_prompt, user_message = build_prompt(question, chunks)

    # Step 3: generation — call Claude with temperature=0.0 for reproducibility
    # (so scores are stable across runs of the same experiment)
    with StageTimer() as _gen:
        result = call_claude_with_usage(
            prompt=user_message,
            system_prompt=system_prompt,
            temperature=0.0,
        )
    _log.log_generate(
        latency_ms=_gen.elapsed_ms,
        model=result.get("model", "claude-sonnet-4-5"),
        input_tokens=result.get("input_tokens", 0),
        output_tokens=result.get("output_tokens", 0),
        stop_reason=result.get("stop_reason", ""),
    )
    _log.finalize(log_dir=_LOG_DIR)

    return {
        "chunks": chunks,           # Evaluators inspect this for retrieval quality
        "answer": result["text"],   # Evaluators inspect this for answer quality
    }


def _run_pipeline_with_context(
    question: str,
    history: list[dict],
    use_contextualize: bool,
    use_assemble: bool,
) -> dict:
    """Run the multi-turn RAG pipeline with toggleable context-management levers.

    Mirrors the production prompt structure in `app/rag.py:149-168`
    (Conversation So Far / Sources / Current Question sections) so the
    Session 2.2 experiments measure what the live chat app actually does —
    not the bare `build_prompt` path used by `_run_pipeline`.

    Args:
        question: The user's current question.
        history: Prior {role, content} messages. Empty list for single-turn cases.
        use_contextualize: If True, rewrite the query for retrieval using history.
            Note: this is a no-op when history is empty (assembler.py:55-56).
        use_assemble: If True, use `assemble_context` (group by source, sort by
            chunk_index, insert gap markers). If False, use `naive_assemble`
            (similarity-order concat with --- separators) as the off-state control.

    Returns:
        {"chunks": [...], "answer": "..."} — same shape as `_run_pipeline`.
    """
    # Step 1: optionally rewrite query for retrieval
    retrieval_query = (
        contextualize_query(history, question) if use_contextualize else question
    )

    # Step 2: retrieve
    chunks = naive_retrieve(retrieval_query, TOP_K)
    if not chunks:
        return {
            "chunks": [],
            "answer": "I couldn't find relevant information in the Northbrook documents.",
        }

    # Step 3: assemble (full vs naive baseline)
    assembled = assemble_context(chunks) if use_assemble else naive_assemble(chunks)

    # Step 4: build prompt mirroring app/rag.py:150-168
    sections = []
    recent = history[-6:] if history else []
    if recent:
        convo = "\n\n".join(
            f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
            for m in recent
        )
        sections.append("## Conversation So Far\n" + convo)
    sections.append("## Sources\n" + assembled)
    # Use the original question, not the rewritten query (matches app/rag.py:163-166)
    sections.append("## Current Question\n" + question)

    user_message = "\n\n".join(sections)

    result = call_claude_with_usage(
        prompt=user_message,
        system_prompt=_CONTEXT_SYSTEM_PROMPT,
        temperature=0.0,
    )

    return {"chunks": chunks, "answer": result["text"]}


def naive_task(input: dict) -> dict:
    """Run the naive RAG pipeline on one dataset example.

    Phoenix calls this once per row in the dataset. The `input` parameter
    is bound BY NAME to the row's inputs dict — whatever we put in
    `inputs[i]` when we created the dataset. For us: {"question": "..."}.

    The returned dict becomes the `output` parameter that evaluators receive.

    Args:
        input: A dict like {"question": "What is the vacation policy?"}.

    Returns:
        {"question": ..., "chunks": [...], "answer": ...}
    """
    question = input["question"]
    result = _run_pipeline(question, naive_retrieve, strategy="naive")
    return {"question": question, **result}


def hyde_task(input: dict) -> dict:
    """Run the HyDE RAG pipeline on one dataset example.

    Identical to `naive_task` except it uses `hyde_retrieve` — which first
    asks Claude to generate a hypothetical answer, then embeds THAT answer
    (not the question) to do the vector search. See Session 1.1 for why.

    Args:
        input: A dict like {"question": "What is the vacation policy?"}.

    Returns:
        {"question": ..., "chunks": [...], "answer": ...}
    """
    from pipeline.retrieval.hyde import hyde_retrieve  # lazy — see note at top

    question = input["question"]
    result = _run_pipeline(question, hyde_retrieve, strategy="hyde")
    return {"question": question, **result}


def rrf_task(input: dict) -> dict:
    """Run the RRF RAG pipeline on one dataset example.

    Fuses naive_retrieve and enriched_retrieve ranked lists via
    Reciprocal Rank Fusion (k=60). Chunks confirmed by both strategies
    score higher than those appearing in only one list.

    Requires the enriched collection to be seeded first.
    See pipeline/retrieval/rrf.py for the seed command.
    """
    from pipeline.retrieval.rrf import rrf_retrieve

    question = input["question"]
    result = _run_pipeline(question, rrf_retrieve, strategy="rrf")
    return {"question": question, **result}


# ─── SESSION 2.2 CONTEXT-MANAGEMENT EXPERIMENTS ─────────────────────────
# Three task variants that toggle contextualize_query and assemble_context
# independently. All three use naive_retrieve; the differences are isolated
# to the context-management layer. See plan: .planning/... or the Session 2.2
# notebook for the full experiment design.


def rewrite_only_task(input: dict) -> dict:
    """contextualize_query=ON, assemble_context=OFF (naive_assemble for chunks)."""
    question = input["question"]
    history = input.get("history", [])
    result = _run_pipeline_with_context(
        question, history, use_contextualize=True, use_assemble=False
    )
    return {"question": question, **result}


def assemble_only_task(input: dict) -> dict:
    """contextualize_query=OFF, assemble_context=ON."""
    question = input["question"]
    history = input.get("history", [])
    result = _run_pipeline_with_context(
        question, history, use_contextualize=False, use_assemble=True
    )
    return {"question": question, **result}


def rewrite_and_assemble_task(input: dict) -> dict:
    """Both levers ON — matches what app/rag.py runs in production."""
    question = input["question"]
    history = input.get("history", [])
    result = _run_pipeline_with_context(
        question, history, use_contextualize=True, use_assemble=True
    )
    return {"question": question, **result}


# ---------------------------------------------------------------------------
# Safety task — runs the full guardrail pipeline (Session 3.1)
# ---------------------------------------------------------------------------
# Lazy imports: pipeline/safety/guard.py is built by students during
# Session 3.1. Before that session, this module would fail at top level.
# Lazy import lets naive_task and hyde_task work regardless.

def safety_task(input: dict) -> dict:
    """Run adversarial input through the full guardrail pipeline.

    Unlike naive_task and hyde_task which test retrieval quality, this task
    tests DEFENSIVE quality. It runs the input through every guardrail layer:

        1. validate_input  — pattern matching, length limits
        2. retrieve        — standard RAG retrieval (if input passes)
        3. build_hardened_prompt — boundary markers, refusal rules
        4. call_claude     — generation with the hardened prompt
        5. validate_output — compromise indicators, prompt leakage

    The output dict is shaped differently from the correctness tasks because
    the safety_check evaluator needs to know WHICH layer caught the attack
    (or didn't).

    Args:
        input: A dict like {"question": "Ignore all previous instructions..."}.

    Returns:
        {
            "question": str,        — the original attack string
            "response": str,        — what the user would see (answer or block msg)
            "input_blocked": bool,  — True if input validation rejected it
            "output_blocked": bool, — True if output validation caught it
            "block_reason": str,    — why the input/output was blocked ("" if not)
        }
    """
    from pipeline.safety.guard import (  # lazy — built in Session 3.1
        validate_input,
        build_hardened_prompt,
        validate_output,
    )

    question = input["question"]

    # ── Layer 1: Input validation ──────────────────────────────────
    input_ok, input_reason = validate_input(question)
    if not input_ok:
        return {
            "question": question,
            "response": input_reason,
            "input_blocked": True,
            "output_blocked": False,
            "block_reason": input_reason,
        }

    # ── Layer 2: Retrieval ─────────────────────────────────────────
    chunks = naive_retrieve(question, TOP_K)

    # ── Layer 3: Hardened prompt assembly ──────────────────────────
    # Format chunks as context for the hardened prompt template.
    context_blocks = []
    source_names = []
    for chunk in chunks:
        source_name = chunk["metadata"].get("source", "Unknown")
        source_names.append(source_name)
        context_blocks.append(
            f"[Source: {source_name}, Score: {chunk['score']:.3f}]\n{chunk['text']}"
        )
    context_section = "\n\n---\n\n".join(context_blocks)

    system_prompt = build_hardened_prompt(context_section)

    # ── Layer 4: Generation ────────────────────────────────────────
    result = call_claude_with_usage(
        prompt=question,
        system_prompt=system_prompt,
        temperature=0.0,
    )
    response_text = result["text"]

    # ── Layer 5: Output validation ─────────────────────────────────
    output_ok, output_reason = validate_output(response_text, source_names)
    if not output_ok:
        return {
            "question": question,
            "response": output_reason,
            "input_blocked": False,
            "output_blocked": True,
            "block_reason": output_reason,
        }

    # ── All layers passed ──────────────────────────────────────────
    return {
        "question": question,
        "response": response_text,
        "input_blocked": False,
        "output_blocked": False,
        "block_reason": "",
    }

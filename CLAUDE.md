# AI-3 Full Stack AI Engineering -- Northbrook Partners Q&A Application

This is a Streamlit-based Q&A application built on a RAG pipeline over the Northbrook Partners corpus. Students customize, extend, and harden this application across Sessions 1.1 through 4.2.

---

## File Ownership (Post-Session 3.1)

After Session 3.1, the instructor no longer pushes changes to existing files. You own the files listed below and are responsible for customizing them for Lab 2.

### Student-Owned (customize freely)

- `app/rag.py` -- Your pipeline integration. 7 marked customization sections for Lab 2.
- `app/branding.py` -- Your app's appearance (logo, CSS, favicon, page config)
- `app/main.py` -- Your chat interface (Steps 1 and 5 are yours)
- `student_config.yaml` -- App name, tagline, welcome message
- `.streamlit/config.toml` -- Theme configuration
- `.streamlit/static/` -- Your logo and static assets
- `pipeline/eval/student_attacks.py` -- Your adversarial test cases (create this file)

### Infrastructure (modify with care)

- `pipeline/safety/guard.py` -- Customize patterns, add defenses
- `pipeline/context/assembler.py` -- Customize context assembly
- `pipeline/context/manager.py` -- Customize history management
- `pipeline/retrieval/` -- All three strategies (naive, hyde, enriched)
- `pipeline/eval/` -- Evaluators, tasks, golden set, adversarial set

### Do Not Modify

- `pipeline/generation/generate.py` -- Claude API wrapper
- `pipeline/embeddings/embed.py` -- Voyage AI wrapper
- `pipeline/ingestion/` -- Chunking and storage
- `data/northbrook/` -- Source corpus
- `scripts/` -- Utility scripts
- `.env` -- API keys (never commit)

---

## Lab 2 -- Application Improvements

### The 7 Customization Sections in rag.py

Each section is marked with a comment block in `app/rag.py`.

1. **Retrieval Strategy** -- Change the import: naive -> hyde -> enriched
2. **System Prompt** -- Customize the hardened prompt
3. **History Management** -- Adjust max_messages, implement different strategies
4. **Query Rewriting** -- Customize how follow-up questions are rewritten
5. **Retrieval Parameters** -- Adjust top_k, add score thresholds
6. **Context Assembly** -- Change chunk ordering, gap detection
7. **Generation Settings** -- Adjust temperature, max_tokens

### Extending the Adversarial Test Set

Create `pipeline/eval/student_attacks.py`:

```python
STUDENT_ATTACKS = [
    {
        "id": "my_attack_1",
        "question": "Your attack string here",
        "attack_type": "instruction_override",
        "expected_behavior": "blocked_input",
        "severity": "high",
        "description": "What this attack tests"
    },
]
```

Push with: `uv run python scripts/push_adversarial_set.py --include-student`

### Running Evaluations

- Golden set: `uv run python scripts/run_experiment.py`
- Safety: `uv run python scripts/run_experiment.py --safety`
- Both: `uv run python scripts/run_experiment.py --safety`

### Smoke Tests

- Free check: `uv run python scripts/check.py`
- Pipeline check (~$0.01): `uv run python scripts/check_pipeline.py`

---

## Working with Claude Code

When using Claude Code to customize your app:

1. Start with `uv run python scripts/check.py` to verify setup
2. After changes, run `uv run python scripts/check_pipeline.py` to verify pipeline works
3. Run `uv run pytest tests/test_safety.py` to verify safety guards still work
4. If something breaks badly, reset to the working baseline: `git checkout working-baseline -- <file>`

### Safe Prompts for Claude Code

- "Change my retrieval strategy to HyDE" -- modifies rag.py import
- "Add a new adversarial test case for [attack type]" -- adds to student_attacks.py
- "Customize my system prompt to be more [description]" -- modifies rag.py system prompt
- "Run the safety experiment" -- executes run_experiment.py --safety

---

## Important Constraints

- In `app/branding.py`, `st.set_page_config()` MUST remain the first `st.*` call. Do not add any Streamlit commands above it.
- Do not rename `app/main.py` -- it is the Streamlit entry point.
- Keep the `ChatResponse` dataclass interface stable: `answer`, `sources`, `rewritten_query`, `span_id`.
- The `get_response(question, messages)` signature must stay the same -- `main.py` depends on it.
- In `student_config.yaml`, always wrap string values in double quotes (e.g., `app_name: "My App"`) to avoid YAML parsing issues with colons, #, or special characters.

## Secrets

1Password (account `tkhllc`) is the only source of truth for secrets. This repo reads: homelab-ai, homelab-apps (see .env.tpl).

- Local dev: `op inject -i .env.tpl -o .env` (rendered `.env` is gitignored, mode 600).
- One-offs: `op run --env-file .env.tpl -- <cmd>`.
- Never hand-write a secret value into a file, chat or argv. Create the 1Password item first, then reference it as `op://<vault>/<item>/<field>` in `.env.tpl`.
- On homelab hosts the `op-render` manifest owns the rendered file.
- Before committing: `gitleaks detect --no-git --redact --source .` must report 0.
- Convention: homelab-main `docs/security/secrets-management-1password.md`.

# Suggested GitHub Issues (Drafts)

Below are draft GitHub issues you can copy to create tracked work in your repository. Each issue includes a description, acceptance criteria, and suggested labels.

---

## 1) Add provider adapters: `openai_compat`, `openrouter`, `huggingface`
- **Description**: Add a small adapter layer under `ai/providers/` to normalize external LLM provider payloads and responses. Implement `openai_compat`, `openrouter`, and `huggingface` adapters and a factory.
- **Acceptance criteria**:
  - `ai/providers/*` contains adapters and a `factory.get_provider(name)`.
  - Unit tests exist for each adapter mocking HTTP responses.
  - `ai/external_llm.py` uses the factory to obtain the provider and normalize responses.
- **Labels**: `enhancement`, `ml`, `backend`

---

## 2) Create unseen eval dataset and update `scripts/evaluate.py`
- **Description**: Split `data/intents.json` into `data/intents_train.json` and `data/intents_eval.json`, and update the evaluation script to use the held-out eval file by default.
- **Acceptance criteria**:
  - New eval file exists with held-out examples.
  - `scripts/evaluate.py` accepts `--eval-file` and uses it for evaluation.
  - CI uses the eval file when running the evaluation workflow.
- **Labels**: `enhancement`, `ml`, `data`

---

## 3) Split backend dependencies
- **Description**: Break `requirements.txt` into purpose-specific files (base, ai, desktop, cloud) and update Dockerfiles to install only needed sets for each image variant.
- **Acceptance criteria**:
  - New `requirements-*.txt` files created.
  - Dockerfiles updated and build successfully locally.
- **Labels**: `devops`, `performance`

---

## 4) Add CI job to run backend API security tests
- **Description**: Add a GitHub Actions job that runs pytest for tests covering API security and settings. Use repository secrets and mocked providers for networked tests.
- **Acceptance criteria**:
  - Workflow step added and green on PRs.
  - Secrets referenced through `secrets.*` where needed.
- **Labels**: `ci`, `tests`

---

## 5) Public demo mode and secrets rotation
- **Description**: Implement a `WEB_SAFE_DEMO` mode that serves a static or mocked backend for any public demos; rotate and invalidate any keys accidentally posted publicly.
- **Acceptance criteria**:
  - Demo mode returns mock LLM responses and disables local desktop actions.
  - Document key rotation steps and verification.
- **Labels**: `security`, `feature`

---

You can copy these templates into issues and assign relevant team members or milestones.

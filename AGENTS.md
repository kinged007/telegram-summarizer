# AGENTS.md — telegram-summarizer

## Purpose

Telegram Summarizer collects recent messages from Telegram chats, builds an LLM prompt (with optional prompt/job templates from `Templates.txt`), calls an LLM via LiteLLM, and displays or forwards the summary. It is a Python CLI tool run via `python summarize.py` or `sh run.sh`.

## Stack

- Python 3.10+, no build step
- Dependencies: `python-dotenv`, `telethon`, `litellm`, `rich`, `loguru` (see `requirements.txt`)
- Dev: `pytest`, `ruff`, `mypy` (see `requirements-dev.txt`)

## How to run checks

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest -q
ruff check .
mypy src --ignore-missing-imports
# or single entry:
# ruff and mypy are non-blocking in CI; pytest must pass
```

Mock mode exercises the full pipeline without Telegram or LLM credentials:

```bash
python summarize.py --chats John --mock
```

## Project layout

- `summarize.py` — entry point (async main, wires config/templates/telegram/LLM)
- `src/config.py` — env loading and argparse
- `src/templates.py` — `Templates.txt` parsing and name resolution
- `src/telegram_utils.py` — Telethon client, message collection, send
- `src/llm_utils.py` — LiteLLM call and cost tracking
- `src/` — `message_utils.py`, `job_utils.py`, `logging_utils.py`, `console_utils.py`
- `Templates.sample.txt` — example templates; copy to `Templates.txt` for local use
- `sample.env` — placeholder env; copy to `.env` and fill `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`

## Branch and PR workflow

- Default branch: `master`.
- Do not push directly to `master` for code changes. Create a feature branch, push, and open a pull request.
- Commit authorship must use `kinged007 <599286+kinged007@users.noreply.github.com>` (verified noreply address).
- `.mailmap` is present so `git log --format='%an <%ae>' | sort -u` shows the verified identity for all history. Keep it.
- CI (`.github/workflows/ci.yml`) runs `pytest` + `ruff` + `mypy` on pushes and PRs to `master`.

## Permissions and secrets

- Never commit `.env`, `Templates.txt`, `*.session`, or any token. They are in `.gitignore`. The `.env` that was once in history contained only placeholders.
- Do not copy or publish anything from private `tenantflex` org repos.
- Use `.env` from `sample.env` for local runs; `LOGS` and `venv/` are local only.

## Skills

- Use the repo's skills where they exist. Keep changes small and follow existing patterns in `src/`.

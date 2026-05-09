# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

This repository is in early initialization — no application code exists yet. The project is intended to be a React + LangGraph application (inferred from the directory name and course context: `llm-app/react-langgraph`).

## Installed Skills

The following skills are available via the `Skill` tool (defined in `skills-lock.json`, sourced from `mattpocock/skills`):

- `prototype` — rapid prototyping workflow
- `tdd` — test-driven development
- `diagnose` — debugging/diagnosis workflow
- `to-prd` — convert ideas to a product requirements document
- `to-issues` — convert a PRD to tracked issues
- `triage` — triage and prioritize issues
- `improve-codebase-architecture` — architectural improvement workflow
- `zoom-out` — high-level codebase review
- `caveman`, `grill-me`, `grill-with-docs`, `write-a-skill` — productivity skills

## Agent skills

### Issue tracker

Issues live in GitHub Issues (uses the `gh` CLI). See `docs/agents/issue-tracker.md`.

### Triage labels

Default label vocabulary: needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

## When Code Exists

Once the stack is established, update this file with:
- Build, dev, lint, and test commands
- Architecture overview (frontend/backend split, graph definition location, state schema)
- How LangGraph state flows through the React UI

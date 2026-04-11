# SASY Demo — Airline Policy Enforcement
#
# Prerequisites:
#   1. pip install sasy   (or: uv pip install sasy)
#   2. Copy .env.example to .env and fill in your keys
#
# Quick start:
#   make setup            # Install dependencies
#   make translate        # English → Datalog via SDK
#   make upload           # Upload policy to SASY
#   make demo             # Run all 9 scenarios
#   make demo-step        # Interactive walkthrough

.PHONY: setup translate upload demo demo-step \
        scenario-1 scenario-2 scenario-3 \
        scenario-4 scenario-5 scenario-6 \
        scenario-7 scenario-8 scenario-9 \
        docs docs-build test

# ── Setup ──────────────────────────────────────────

setup:
	uv sync
	@echo "✓ Dependencies installed"
	@echo "Next: copy .env.example to .env and add your keys"

# ── Policy Translation ─────────────────────────────
# Translates policy_english.md → policy_compiled.dl
# via the SASY cloud service. Takes ~5-10 minutes.
# Results include verification artifacts.

translate:
	@echo "Translating policy_english.md → Datalog ..."
	@uv run python -c "\
	from sasy.policy import write_policy; \
	english = open('policy_english.md').read(); \
	r = write_policy(english=english, poll_interval=15.0, \
	    on_progress=lambda s,e: print(f'  {s} ({e:.0f}s)')); \
	r.print_summary(); \
	r.save_datalog('policy_compiled.dl'); \
	r.save_truth_table('truth_table.tsv'); \
	print(f'\nSaved: policy_compiled.dl, truth_table.tsv')"

# ── Policy Upload ──────────────────────────────────
# Uploads Datalog to the SASY policy engine.

upload:
	uv run python -m demo.main --upload-only

# Upload the translated (compiled) policy
upload-compiled:
	@uv run python -c "\
	import os; \
	from pathlib import Path; \
	from dotenv import load_dotenv; \
	load_dotenv(Path('.env')); \
	from sasy.auth.hooks import APIKeyAuthHook; \
	from sasy.config import configure; \
	api_key = os.environ.get('SASY_API_KEY', ''); \
	if not api_key: \
	    sfx = os.environ.get('SASY_API_KEY_SUFFIX', ''); \
	    api_key = f'demo-key-{sfx}' if sfx else ''; \
	sasy_url = os.environ.get('SASY_URL', 'sasy.fly.dev:443'); \
	configure(url=sasy_url, ca_path='', cert_path='', key_path='', \
	    auth_hook=APIKeyAuthHook(api_key=api_key)); \
	from sasy.policy import upload_policy; \
	dl = open('policy_compiled.dl').read(); \
	r = upload_policy(policy_source=dl, hot_reload=True); \
	print('Accepted' if r.accepted else f'Failed: {r.error_output}')"

# ── Demo Scenarios ─────────────────────────────────
# Run agent scenarios with live policy enforcement.
# Uploads the hand-written policy.dl first.

demo:
	uv run python -m demo.main --all

demo-step:
	STEP_MODE=1 uv run python -m demo.main --all

# ── Run with compiled (translated) policy ──────────
# Uploads policy_compiled.dl then runs scenarios.

demo-compiled:
	@cp policy.dl policy.dl.bak 2>/dev/null || true
	@cp policy_compiled.dl policy.dl
	uv run python -m demo.main --all
	@mv policy.dl.bak policy.dl 2>/dev/null || true

demo-compiled-step:
	@cp policy.dl policy.bak 2>/dev/null || true
	@cp policy_compiled.dl policy.dl
	STEP_MODE=1 uv run python -m demo.main --all
	@mv policy.dl.bak policy.dl 2>/dev/null || true

# ── Individual Scenarios ───────────────────────────

scenario-1:
	uv run python -m demo.main --scenario 1

scenario-2:
	uv run python -m demo.main --scenario 2

scenario-3:
	uv run python -m demo.main --scenario 3

scenario-4:
	uv run python -m demo.main --scenario 4

scenario-5:
	uv run python -m demo.main --scenario 5

scenario-6:
	uv run python -m demo.main --scenario 6

scenario-7:
	uv run python -m demo.main --scenario 7

scenario-8:
	uv run python -m demo.main --scenario 8

scenario-9:
	uv run python -m demo.main --scenario 9

# ── Individual Scenarios (interactive) ─────────────

scenario-1-step:
	STEP_MODE=1 uv run python -m demo.main --scenario 1

scenario-2-step:
	STEP_MODE=1 uv run python -m demo.main --scenario 2

scenario-3-step:
	STEP_MODE=1 uv run python -m demo.main --scenario 3

# ── Validation ─────────────────────────────────────

test:
	uv run pytest tests/ -xvs

# ── Documentation ──────────────────────────────────

docs:
	cd docs-site && npm run dev

docs-build:
	cd docs-site && npm run build

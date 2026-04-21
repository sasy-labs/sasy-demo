# SASY Demo — Airline Policy Enforcement
#
# Prerequisites:
#   1. Copy .env.example to .env and fill in your keys
#   2. make setup
#
# Quick start (hand-written reference policy):
#   make demo             # Run all 9 scenarios
#   make demo-step        # Interactive walkthrough
#
# Translate an English policy via the SASY cloud service:
#   make translate        # primary: agent-aware Datalog translation
#   make upload-translated
#   make demo-translated

.PHONY: setup \
        translate upload-translated demo-translated demo-translated-step \
        translate-experimental upload-compiled demo-compiled demo-compiled-step \
        demo demo-step upload \
        scenario-1 scenario-2 scenario-3 \
        scenario-4 scenario-5 scenario-6 \
        scenario-7 scenario-8 scenario-9 \
        scenario-1-step scenario-2-step scenario-3-step \
        docs docs-build docs-install test

# ── Setup ──────────────────────────────────────────

setup:
	uv sync
	@echo "✓ Dependencies installed"
	@echo "Next: copy .env.example to .env and add your keys"

# ── Primary Policy Translation ─────────────────────
# Translates policy_english.md + src/demo/ (your agent) → Datalog
# via the sasy-translate cloud service. Takes ~5–15 min. Writes
# output/airline_policy.dl + output/agent_summary.md, plus
# output/airline_functors.cpp if the policy needs custom C++
# helpers (the demo policy doesn't, so the file is omitted).
UV_RUN_SDK := uv run

# Silence gRPC's noisy INFO/WARN messages (e.g. "FD from fork parent
# still in poll list") emitted when agent traffic spawns subprocesses.
# Demo/scenario recipes export this so the CLI output stays readable.
export GRPC_VERBOSITY ?= ERROR

translate:
	@echo "Translating policy_english.md + src/demo/ → Datalog ..."
	@$(UV_RUN_SDK) python -c "\
	from sasy.policy import translate; \
	policy = open('policy_english.md').read(); \
	r = translate(policy, codebase_paths=['src/demo'], codebase_root='.', \
	    on_progress=lambda s,e: print(f'  {s} ({e:.0f}s)')); \
	r.print_summary(); \
	saved = r.save_all('output/', base_name='airline'); \
	print('\nSaved: ' + ', '.join(str(p) for p in saved.values()))"

upload-translated:
	@$(UV_RUN_SDK) python -c "\
	import os; \
	from sasy.policy import upload_policy_file; \
	path = 'output/airline_policy.dl'; \
	size = os.path.getsize(path); \
	print(f'Uploading {path} ({size:,} bytes) ...'); \
	r = upload_policy_file(path); \
	print(f'  ✓ {r.message}' if r.accepted else f'  ✗ Failed: {r.error_output}')"

demo-translated:
	@echo "→ Swapping policy.dl ← output/airline_policy.dl (translated)"
	@cp policy.dl policy.dl.bak 2>/dev/null || true
	@cp output/airline_policy.dl policy.dl
	$(UV_RUN_SDK) python -m demo.main --all
	@mv policy.dl.bak policy.dl 2>/dev/null || true
	@echo "→ Restored hand-written policy.dl"

demo-translated-step:
	@echo "→ Swapping policy.dl ← output/airline_policy.dl (translated)"
	@cp policy.dl policy.dl.bak 2>/dev/null || true
	@cp output/airline_policy.dl policy.dl
	STEP_MODE=1 $(UV_RUN_SDK) python -m demo.main --all
	@mv policy.dl.bak policy.dl 2>/dev/null || true
	@echo "→ Restored hand-written policy.dl"

# ── Policy Upload (hand-written reference) ─────────

upload:
	$(UV_RUN_SDK) python -m demo.main --upload-only

# ── Demo Scenarios ─────────────────────────────────
# Run agent scenarios with live policy enforcement.
# Uploads the hand-written policy.dl first.

demo:
	$(UV_RUN_SDK) python -m demo.main --all

demo-step:
	STEP_MODE=1 $(UV_RUN_SDK) python -m demo.main --all

# ── Individual Scenarios ───────────────────────────

scenario-1:
	$(UV_RUN_SDK) python -m demo.main --scenario 1

scenario-2:
	$(UV_RUN_SDK) python -m demo.main --scenario 2

scenario-3:
	$(UV_RUN_SDK) python -m demo.main --scenario 3

scenario-4:
	$(UV_RUN_SDK) python -m demo.main --scenario 4

scenario-5:
	$(UV_RUN_SDK) python -m demo.main --scenario 5

scenario-6:
	$(UV_RUN_SDK) python -m demo.main --scenario 6

scenario-7:
	$(UV_RUN_SDK) python -m demo.main --scenario 7

scenario-8:
	$(UV_RUN_SDK) python -m demo.main --scenario 8

scenario-9:
	$(UV_RUN_SDK) python -m demo.main --scenario 9

# ── Individual Scenarios (interactive) ─────────────

scenario-1-step:
	STEP_MODE=1 $(UV_RUN_SDK) python -m demo.main --scenario 1

scenario-2-step:
	STEP_MODE=1 $(UV_RUN_SDK) python -m demo.main --scenario 2

scenario-3-step:
	STEP_MODE=1 $(UV_RUN_SDK) python -m demo.main --scenario 3

# ── Experimental translator (write_policy) ─────────
# Uses sasy.policy.write_policy — a prototype with extended
# verification (truth table + adversarial checks) but no
# codebase awareness. See docs-site /policy/confidence.

translate-experimental:
	@echo "Translating policy_english.md → Datalog (experimental) ..."
	@uv run python -c "\
	from sasy.policy import write_policy; \
	policy = open('policy_english.md').read(); \
	r = write_policy(policy=policy, poll_interval=15.0, \
	    on_progress=lambda s,e: print(f'  {s} ({e:.0f}s)')); \
	r.print_summary(); \
	r.save_datalog('policy_compiled.dl'); \
	r.save_truth_table('truth_table.tsv'); \
	print(f'\nSaved: policy_compiled.dl, truth_table.tsv')"

upload-compiled:
	@uv run python -c "from sasy.policy import upload_policy_file; \
	r = upload_policy_file('policy_compiled.dl'); \
	print('Accepted' if r.accepted else f'Failed: {r.error_output}')"

demo-compiled:
	@cp policy.dl policy.dl.bak 2>/dev/null || true
	@cp policy_compiled.dl policy.dl
	$(UV_RUN_SDK) python -m demo.main --all
	@mv policy.dl.bak policy.dl 2>/dev/null || true

demo-compiled-step:
	@cp policy.dl policy.dl.bak 2>/dev/null || true
	@cp policy_compiled.dl policy.dl
	STEP_MODE=1 $(UV_RUN_SDK) python -m demo.main --all
	@mv policy.dl.bak policy.dl 2>/dev/null || true

# ── Validation ─────────────────────────────────────

test:
	$(UV_RUN_SDK) pytest tests/ -xvs

# ── Documentation ──────────────────────────────────

# Installs docs-site npm deps on first use (idempotent).
docs-install:
	@if [ ! -d docs-site/node_modules ]; then \
	    cd docs-site && npm install; \
	fi

docs: docs-install
	cd docs-site && npm run dev

docs-build: docs-install
	cd docs-site && npm run build

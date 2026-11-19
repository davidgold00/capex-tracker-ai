PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
GUIDANCE = PYTHONPATH=src "$(PYTHON)" -m capex_tracker.guidance

.PHONY: demo demo-policy demo-guard explain apply-decisions

demo:
	@$(GUIDANCE).demo demo

demo-policy:
	@$(GUIDANCE).demo policy

demo-guard:
	@$(GUIDANCE).demo guard

explain:
	@$(GUIDANCE).demo explain "$(ID)"

apply-decisions:
	@$(GUIDANCE).review

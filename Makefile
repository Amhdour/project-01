.PHONY: fmt test verify

PYTHONPATH := addon:backend:$(PYTHONPATH)

fmt:
	@echo "[placeholder] formatting workspace"

test:
	@echo "[test] addon unit tests"
	PYTHONPATH=$(PYTHONPATH) python -m pytest -q backend/tests/addon
	@echo "[test] schema validation tests"
	python -m pytest -q trust-evidence/sidecar/schemas/tests/test_schema_examples.py

verify:
	@echo "[verify] unit checks"
	PYTHONPATH=$(PYTHONPATH) python -m pytest -q backend/tests/addon/test_compat.py backend/tests/addon/test_api_authz.py
	@echo "[verify] schema checks"
	python -m pytest -q trust-evidence/sidecar/schemas/tests/test_schema_examples.py
	@echo "[verify] integration checks (placeholder)"
	python -c "print('integration checks placeholder: OK')"

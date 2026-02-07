.PHONY: fmt test verify

PYTHONPATH := addon:backend:$(PYTHONPATH)
SIDECAR_PYTHONPATH := trust-evidence/sidecar:$(PYTHONPATH)

fmt:
	@echo "[placeholder] formatting workspace"

test:
	@echo "[test] addon unit tests"
	PYTHONPATH=$(PYTHONPATH) python -m pytest -q backend/tests/addon
	@echo "[test] schema validation tests"
	python -m pytest -q trust-evidence/sidecar/schemas/tests/test_schema_examples.py
	@echo "[test] sidecar auth/app scaffold tests"
	PYTHONPATH=$(SIDECAR_PYTHONPATH) python -m pytest -q trust-evidence/sidecar/tests/test_auth_and_routes.py

verify:
	@echo "[verify] unit checks"
	PYTHONPATH=$(PYTHONPATH) python -m pytest -q backend/tests/addon/test_compat.py backend/tests/addon/test_api_authz.py
	@echo "[verify] schema checks"
	python -m pytest -q trust-evidence/sidecar/schemas/tests/test_schema_examples.py
	@echo "[verify] sidecar auth/app checks"
	PYTHONPATH=$(SIDECAR_PYTHONPATH) python -m pytest -q trust-evidence/sidecar/tests/test_auth_and_routes.py
	@echo "[verify] sidecar app import smoke"
	PYTHONPATH=$(SIDECAR_PYTHONPATH) python -c "from app.main import app; print(app.title)"
	@echo "[verify] integration checks (placeholder)"
	python -c "print('integration checks placeholder: OK')"

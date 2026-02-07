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
	@echo "[test] sidecar store+auth scaffold tests"
	PYTHONPATH=$(SIDECAR_PYTHONPATH) python -m pytest -q trust-evidence/sidecar/tests/test_auth_and_routes.py trust-evidence/sidecar/tests/test_store_repository.py trust-evidence/sidecar/tests/test_app_persistence.py trust-evidence/sidecar/tests/test_integrity.py trust-evidence/sidecar/tests/test_audit_pack_export.py trust-evidence/sidecar/tests/test_retention_legal_hold.py

verify:
	@echo "[verify] unit checks"
	PYTHONPATH=$(PYTHONPATH) python -m pytest -q backend/tests/addon/test_compat.py backend/tests/addon/test_api_authz.py
	@echo "[verify] schema checks"
	python -m pytest -q trust-evidence/sidecar/schemas/tests/test_schema_examples.py
	@echo "[verify] sidecar auth+store checks"
	PYTHONPATH=$(SIDECAR_PYTHONPATH) python -m pytest -q trust-evidence/sidecar/tests/test_auth_and_routes.py trust-evidence/sidecar/tests/test_store_repository.py trust-evidence/sidecar/tests/test_app_persistence.py trust-evidence/sidecar/tests/test_integrity.py trust-evidence/sidecar/tests/test_audit_pack_export.py trust-evidence/sidecar/tests/test_retention_legal_hold.py
	@echo "[verify] sidecar app import smoke"
	PYTHONPATH=$(SIDECAR_PYTHONPATH) python -c "from app.main import app; print(app.title)"
	@echo "[verify] migration smoke"
	PYTHONPATH=$(SIDECAR_PYTHONPATH) python -c "from store import SidecarStore; import tempfile, os; s=SidecarStore(); s.db_path=os.path.join(tempfile.gettempdir(),'sidecar_mig_smoke.db'); cm=s.connection(); cm.__enter__(); cm.__exit__(None,None,None); print('migrations_ok')"
	@echo "[verify] integration checks (placeholder)"
	python -c "print('integration checks placeholder: OK')"

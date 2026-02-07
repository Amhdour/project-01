.PHONY: fmt test verify

PYTHONPATH := addon:backend:$(PYTHONPATH)

fmt:
	@echo "[placeholder] formatting workspace"

test:
	@echo "[placeholder] unit tests"
	PYTHONPATH=$(PYTHONPATH) python -m pytest -q backend/tests/addon

verify:
	@echo "[verify] unit checks"
	PYTHONPATH=$(PYTHONPATH) python -m pytest -q backend/tests/addon/test_compat.py backend/tests/addon/test_api_authz.py
	@echo "[verify] schema checks (placeholder)"
	python -c "print('schema checks placeholder: OK')"
	@echo "[verify] integration checks (placeholder)"
	python -c "print('integration checks placeholder: OK')"

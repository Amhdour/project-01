from __future__ import annotations

from trust_evidence_addon.store.postgres import PostgresEvidenceStore


class _Cur:
    def __init__(self) -> None:
        self.queries = []
        self._fetchall = []
        self._fetchone = None
        self.rowcount = 1

    def execute(self, q, params):
        self.queries.append((q, params))

    def fetchall(self):
        return self._fetchall

    def fetchone(self):
        return self._fetchone

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None


class _Conn:
    def __init__(self, cur):
        self.cur = cur

    def cursor(self):
        return self.cur

    def commit(self):
        return None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None


def test_postgres_store_sql_paths():
    cur = _Cur()
    cur._fetchall = [('{"a":1}',)]
    cur._fetchone = ("YmxvYg==", '{"m":1}')  # base64(blob), manifest
    store = PostgresEvidenceStore(lambda: _Conn(cur))
    store.put_event("t", {"a": 1})
    events = store.list_events("t")
    assert events == [{"a": 1}]
    store.put_audit_pack("t", b"blob", {"m": 1})
    blob, manifest = store.get_audit_pack("t")
    assert blob == b"blob"
    assert manifest == {"m": 1}
    assert len(cur.queries) >= 4

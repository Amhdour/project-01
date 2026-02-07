from __future__ import annotations

import argparse
from datetime import datetime

from store import SidecarStore


def run_retention_job(store: SidecarStore, retention_days: int) -> dict[str, int]:
    return store.run_retention(retention_days=retention_days, now=datetime.utcnow())


def main() -> None:
    parser = argparse.ArgumentParser(prog="sidecar-retention")
    parser.add_argument("--retention-days", type=int, default=30)
    parser.add_argument("--trace-id", type=str, default=None)
    parser.add_argument("--legal-hold", choices=["on", "off"], default=None)
    args = parser.parse_args()

    store = SidecarStore()

    if args.trace_id and args.legal_hold:
        store.set_legal_hold(args.trace_id, enabled=args.legal_hold == "on")
        print(f"trace_id={args.trace_id} legal_hold={args.legal_hold}")
        return

    result = run_retention_job(store, retention_days=args.retention_days)
    print(result)


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
from datetime import datetime
from datetime import timezone

from trust_evidence_addon.compat import check_compat
from trust_evidence_addon.config import AddonConfig
from trust_evidence_addon.service import build_store


def main() -> None:
    parser = argparse.ArgumentParser(prog="trust-addon")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("gc")
    sub.add_parser("compat")
    args = parser.parse_args()

    if args.cmd == "gc":
        cfg = AddonConfig.from_env()
        deleted = build_store(cfg).gc(
            retention_days=cfg.retention_days,
            now=datetime.now(timezone.utc),
        )
        print(f"deleted={deleted}")
    elif args.cmd == "compat":
        status = check_compat()
        print(
            f"onyx_version={status.onyx_version or 'unknown'} supported={status.supported} reason={status.reason}"
        )

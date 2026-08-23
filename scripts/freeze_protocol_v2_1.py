#!/usr/bin/env python
"""CLI to create/verify the v2.1 CODE_FROZEN manifest (Task 10).

Requires a clean worktree and an annotated git tag at HEAD (section 12:
"CODE_FROZEN solo podrá crearse después de un commit y tag anotado").
Never writes a receipt or generates a holdout by itself -- that is
scripts/run_confirmatory_v2_1.py's job, and only after this manifest
exists.

    uv run python scripts/freeze_protocol_v2_1.py            # create
    uv run python scripts/freeze_protocol_v2_1.py --verify    # verify
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from erp_agent_os.freeze_v2_1 import (
    REPO_ROOT,
    CodeFreezeManifest,
    FreezeV21Error,
    create_code_freeze,
    verify_code_freeze,
)

DEFAULT_MANIFEST_PATH = (
    REPO_ROOT / "data" / "protocol_v2_1" / "code_freeze_manifest.json"
)


def _load_manifest(path: Path) -> CodeFreezeManifest:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return CodeFreezeManifest(**payload)


def _verify(manifest_path: Path) -> int:
    if not manifest_path.exists():
        print(f"no manifest at {manifest_path}")
        return 1
    manifest = _load_manifest(manifest_path)
    drift = verify_code_freeze(manifest)
    if drift:
        print(f"DRIFT DETECTED in: {', '.join(sorted(drift))}")
        return 1
    print("code freeze intact: no drift")
    print(f"git_commit={manifest.git_commit} git_tag={manifest.git_tag}")
    print(f"manifest_hash={manifest.manifest_hash}")
    return 0


def _create(manifest_path: Path) -> int:
    if manifest_path.exists():
        print(
            f"a manifest already exists at {manifest_path}; refusing to overwrite "
            "a frozen manifest (delete it explicitly if you really intend to "
            "re-freeze, which invalidates any run recorded against the old one)"
        )
        return 1
    try:
        manifest = create_code_freeze()
    except FreezeV21Error as exc:
        print(f"cannot create CODE_FROZEN manifest: {exc}")
        return 1
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(manifest.to_json(), encoding="utf-8")
    print(f"wrote {manifest_path}")
    print(f"git_commit={manifest.git_commit} git_tag={manifest.git_tag}")
    print(f"manifest_hash={manifest.manifest_hash}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verify",
        action="store_true",
        help="verify the existing manifest instead of creating a new one",
    )
    parser.add_argument("--manifest-path", type=Path, default=DEFAULT_MANIFEST_PATH)
    args = parser.parse_args(argv)

    if args.verify:
        return _verify(args.manifest_path)
    return _create(args.manifest_path)


if __name__ == "__main__":
    raise SystemExit(main())

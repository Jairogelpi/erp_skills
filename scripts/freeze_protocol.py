"""Write the freeze manifest (CLAUDE.md §19, roadmap P9.1).

    uv run python scripts/freeze_protocol.py          # freeze
    uv run python scripts/freeze_protocol.py --verify # check for drift

Freezing is a deliberate act: run it once, commit the manifest, and from
then on any change to the test split, the catalog or the seed is detected
by --verify instead of silently invalidating the comparison.
"""

import sys

from erp_agent_os.freeze import verify_freeze, write_manifest


def main() -> int:
    if "--verify" in sys.argv:
        drift = verify_freeze()
        if drift:
            print("FROZEN ARTEFACTS DRIFTED: " + ", ".join(drift), file=sys.stderr)
            print(
                "Results computed now are NOT comparable to the frozen "
                "protocol and must be labelled exploratory (CLAUDE.md §19).",
                file=sys.stderr,
            )
            return 1
        print("freeze intact: test split, dataset, catalog and seed unchanged")
        return 0

    manifest = write_manifest()
    print(f"froze {manifest.n_test_cases} test cases of {manifest.n_total_cases}")
    print(f"  test split hash : {manifest.test_split_hash}")
    print(f"  catalog hash    : {manifest.catalog_hash}")
    print(f"  seed            : {manifest.seed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

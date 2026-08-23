"""Release gate for evidence labels and result citations."""

from pathlib import Path

from erp_agent_os.claims import validate_claims


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    errors = validate_claims(root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print("Claim contract valid: no confirmatory conclusion is asserted.")


if __name__ == "__main__":
    main()

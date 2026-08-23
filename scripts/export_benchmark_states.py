"""Export deterministic ERP observations without modifying frozen annotations."""

from pathlib import Path

from erp_agent_os.bench_generator import generate_cases
from erp_agent_os.observed_states import write_observed_state_archive


def main() -> None:
    data_dir = Path(__file__).resolve().parents[1] / "data"
    output = write_observed_state_archive(generate_cases(), data_dir)
    print(output)


if __name__ == "__main__":
    main()

"""State machine, hash coverage and atomic receipts for the v2.1
one-shot confirmatory protocol (Task 10).

docs/tfm-closure-no-human-v2.1.md section 12: a prose promise that
"the protocol is frozen" cannot enforce anything. This module hashes
every component section 12 names, enforces the exact state graph
section 12 draws, and requires the full-corpus oracle concordance
check (Task 3/`oracle_concordance_v2_1`) and evidence-completeness gate
(Task 6/7B) to pass BEFORE the manifest transitions to the next state
-- not as an afterthought reported alongside a run that already
happened.

**Git operations are injectable, not hardcoded to `subprocess`.** Every
function that needs the current commit, tag or worktree cleanliness
takes that as a resolver callable with a default real implementation --
tests exercise the state machine and hash logic without needing an
actual annotated git tag in the test environment, and the real CLI
scripts (scripts/freeze_protocol_v2_1.py, scripts/run_confirmatory_v2_1.py)
supply the real resolvers.

**Two-tier manifest, chained by hash.** `CodeFreezeManifest` is
computed once, at `CODE_FROZEN`, from code/config/lockfile bytes only
-- it cannot depend on anything generated afterward (section 12: "evita
hashes autorreferenciales"). `HoldoutManifest` is computed once, at
`HOLDOUT_GENERATED_NOT_EVALUATED`, and embeds `code_manifest_hash` so a
holdout can never be silently re-paired with a different code freeze.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from erp_agent_os.evidence_v2_1 import (
    ObservationV21,
    load_observations_v21_jsonl,
    validate_arm_semantics,
)
from erp_agent_os.oracle_concordance_v2_1 import validate_full_corpus_concordance
from erp_agent_os.scenarios_v2_1 import ScenarioSpec, generate_scenarios
from erp_agent_os.security_scenarios_v2_1 import generate_security_population

REPO_ROOT = Path(__file__).resolve().parents[2]


class FreezeV21Error(RuntimeError):
    pass


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


# ================================================================ states


class RunState(str, Enum):
    DRAFT_PROTOCOL = "DRAFT_PROTOCOL"
    CODE_FROZEN = "CODE_FROZEN"
    HOLDOUT_GENERATED_NOT_EVALUATED = "HOLDOUT_GENERATED_NOT_EVALUATED"
    RUN_STARTED = "RUN_STARTED"
    RUN_INTERRUPTED_RESUMABLE = "RUN_INTERRUPTED_RESUMABLE"
    RUN_COMPLETED = "RUN_COMPLETED"
    REPORT_PUBLISHED = "REPORT_PUBLISHED"
    RUN_FAILED_EXTERNAL = "RUN_FAILED_EXTERNAL"


ALLOWED_TRANSITIONS: dict[RunState, frozenset[RunState]] = {
    RunState.DRAFT_PROTOCOL: frozenset({RunState.CODE_FROZEN}),
    RunState.CODE_FROZEN: frozenset({RunState.HOLDOUT_GENERATED_NOT_EVALUATED}),
    RunState.HOLDOUT_GENERATED_NOT_EVALUATED: frozenset({RunState.RUN_STARTED}),
    RunState.RUN_STARTED: frozenset(
        {
            RunState.RUN_INTERRUPTED_RESUMABLE,
            RunState.RUN_COMPLETED,
            RunState.RUN_FAILED_EXTERNAL,
        }
    ),
    RunState.RUN_INTERRUPTED_RESUMABLE: frozenset(
        {RunState.RUN_STARTED, RunState.RUN_FAILED_EXTERNAL}
    ),
    RunState.RUN_COMPLETED: frozenset({RunState.REPORT_PUBLISHED}),
    RunState.REPORT_PUBLISHED: frozenset(),
    RunState.RUN_FAILED_EXTERNAL: frozenset(),  # terminal
}


class InvalidTransitionError(FreezeV21Error):
    pass


def transition(current: RunState, target: RunState) -> RunState:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidTransitionError(f"{current} -> {target}")
    return target


# ========================================================= hash coverage

# Section 12's ten named components (spec, protocol JSON, lockfile,
# generator, oracle, evaluator, catalog, prompt, provider, analysis
# code) plus the two content-addressed harness artifacts it also lists
# (power analysis, mutation-harness config/runner/report). Paths are
# REPO-RELATIVE, resolved against whatever `repo_root` a caller passes
# to `compute_component_hashes` -- storing them pre-joined to the fixed
# module-level REPO_ROOT would silently ignore that parameter and hash
# the real repository even when a caller (a test, a dry run against a
# staged tree) explicitly asked for a different root.
COMPONENT_FILES: dict[str, tuple[Path, ...]] = {
    "spec": (Path("docs") / "tfm-closure-no-human-v2.1.md",),
    "protocol": (Path("config") / "protocol_v2_1.json",),
    "lockfile": (Path("uv.lock"),),
    "generator": (
        Path("src") / "erp_agent_os" / "scenarios_v2_1.py",
        Path("src") / "erp_agent_os" / "surfaces_v2_1.py",
        Path("src") / "erp_agent_os" / "security_scenarios_v2_1.py",
    ),
    "oracle": (
        Path("src") / "erp_agent_os" / "reference_policy_oracle.py",
        Path("src") / "erp_agent_os" / "reference_state_oracle.py",
        Path("src") / "erp_agent_os" / "oracle_concordance_v2_1.py",
    ),
    "evaluator": (
        Path("src") / "erp_agent_os" / "evaluator_v2_1.py",
        Path("src") / "erp_agent_os" / "audit_reconstruction.py",
    ),
    # Not one of section 12's explicitly named categories, but a real
    # gap closed here rather than left open: this is the code that
    # decides WHAT gets executed and HOW (which arms exist, exact plan
    # sizes, per-unit fields) -- a post-freeze change here would
    # otherwise go completely undetected by every other component hash.
    "runner": (
        Path("src") / "erp_agent_os" / "experiment_v2_1.py",
        Path("src") / "erp_agent_os" / "evidence_v2_1.py",
    ),
    "catalog": (Path("src") / "erp_agent_os" / "catalog.py",),
    "prompt": (Path("src") / "erp_agent_os" / "llm_client.py",),
    "provider": (
        Path("src") / "erp_agent_os" / "groq_client.py",
        Path("src") / "erp_agent_os" / "gemini_client.py",
        Path("src") / "erp_agent_os" / "openrouter_client.py",
    ),
    "analysis": (
        Path("src") / "erp_agent_os" / "statistics_v2_1.py",
        Path("src") / "erp_agent_os" / "cost_scenarios_v2_1.py",
        Path("src") / "erp_agent_os" / "power_v2_1.py",
    ),
    "harness": (
        Path("config") / "targeted_mutations_v2_1.json",
        Path("scripts") / "run_targeted_mutations_v2_1.py",
    ),
}


def _hash_files(paths: Sequence[Path]) -> str:
    hasher = hashlib.sha256()
    for path in paths:
        if not path.exists():
            raise FreezeV21Error(f"missing component file: {path}")
        hasher.update(path.read_bytes())
    return hasher.hexdigest()


def _single_content_addressed_file(directory: Path, prefix: str) -> Path:
    """Exactly one `{prefix}_<sha256>.json` must exist -- zero means the
    artifact was never generated, more than one means an ambiguous
    freeze (which specific run does this manifest point at?)."""
    matches = sorted(directory.glob(f"{prefix}_*.json"))
    if len(matches) != 1:
        raise FreezeV21Error(
            f"expected exactly one {prefix}_*.json in {directory}, found {len(matches)}"
        )
    return matches[0]


def component_paths(*, repo_root: Path = REPO_ROOT) -> dict[str, tuple[Path, ...]]:
    """Resolves COMPONENT_FILES' repo-relative paths against `repo_root`
    -- the one place that join happens, so `compute_component_hashes`
    and any test/tool inspecting exact file paths agree on it."""
    return {
        name: tuple(repo_root / rel for rel in relatives)
        for name, relatives in COMPONENT_FILES.items()
    }


def compute_component_hashes(*, repo_root: Path = REPO_ROOT) -> dict[str, str]:
    hashes = {
        name: _hash_files(paths)
        for name, paths in component_paths(repo_root=repo_root).items()
    }
    data_dir = repo_root / "data" / "protocol_v2_1"
    hashes["power"] = _hash_files(
        (_single_content_addressed_file(data_dir, "power_analysis"),)
    )
    report_path = _single_content_addressed_file(data_dir, "targeted_mutation_report")
    hashes["harness"] = hashlib.sha256(
        (hashes["harness"] + _hash_files((report_path,))).encode("utf-8")
    ).hexdigest()
    return hashes


def load_selected_sample_sizes(*, repo_root: Path = REPO_ROOT) -> dict[str, int]:
    """Reads the frozen power analysis' own "selected" block (the
    max(protocol floor, power-search result) sample sizes -- e.g. H1b's
    real n=1184, far above the plan's stated n=120 floor). The one place
    a script needs "how many main/security units to plan" reads this
    instead of re-deriving or hardcoding a number that could drift from
    what was actually frozen."""
    data_dir = repo_root / "data" / "protocol_v2_1"
    path = _single_content_addressed_file(data_dir, "power_analysis")
    payload = json.loads(path.read_text(encoding="utf-8"))
    selected = payload.get("selected")
    if not isinstance(selected, dict):
        raise FreezeV21Error(f"{path} has no 'selected' sample-size block")
    return {
        "n_main": int(selected["n_main"]),
        "n_security_dangerous": int(selected["n_security_dangerous"]),
        "n_security_safe": int(selected["n_security_safe"]),
    }


# ----------------------------------------------------------------- git


def resolve_git_commit(*, repo_root: Path = REPO_ROOT) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def worktree_is_clean(*, repo_root: Path = REPO_ROOT) -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip() == ""


def resolve_annotated_tag(*, repo_root: Path = REPO_ROOT) -> str | None:
    result = subprocess.run(
        ["git", "describe", "--tags", "--exact-match"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


# ============================================================ manifests


@dataclass(frozen=True)
class CodeFreezeManifest:
    schema_version: str
    git_commit: str
    git_tag: str
    component_hashes: dict[str, str]
    frozen_at: str

    @property
    def manifest_hash(self) -> str:
        payload = json.dumps(
            {"git_commit": self.git_commit, "component_hashes": self.component_hashes},
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True) + "\n"


def create_code_freeze(
    *,
    repo_root: Path = REPO_ROOT,
    git_commit_resolver: Callable[..., str] = resolve_git_commit,
    worktree_clean_checker: Callable[..., bool] = worktree_is_clean,
    tag_resolver: Callable[..., str | None] = resolve_annotated_tag,
    clock: Callable[[], str] = _now_iso,
) -> CodeFreezeManifest:
    """CODE_FROZEN can only be created after a commit AND an annotated
    tag (section 12) on a clean worktree -- a dirty worktree would let
    the manifest hash code that is not actually what the tag points at."""
    if not worktree_clean_checker(repo_root=repo_root):
        raise FreezeV21Error(
            "CODE_FROZEN requires a clean worktree (no tracked changes)"
        )
    tag = tag_resolver(repo_root=repo_root)
    if tag is None:
        raise FreezeV21Error("CODE_FROZEN requires an annotated git tag at HEAD")
    commit = git_commit_resolver(repo_root=repo_root)
    return CodeFreezeManifest(
        schema_version="2.1",
        git_commit=commit,
        git_tag=tag,
        component_hashes=compute_component_hashes(repo_root=repo_root),
        frozen_at=clock(),
    )


def verify_code_freeze(
    manifest: CodeFreezeManifest, *, repo_root: Path = REPO_ROOT
) -> list[str]:
    """Returns the names of components that drifted since freezing --
    empty means intact. Never raises on drift itself; callers decide
    whether drift blocks a transition (it always should, for a run)."""
    current = compute_component_hashes(repo_root=repo_root)
    return [
        name
        for name, recorded_hash in manifest.component_hashes.items()
        if current.get(name) != recorded_hash
    ]


def _scenario_payload(scenario: ScenarioSpec) -> str:
    return (
        f"{scenario.scenario_id}|{scenario.expected_skill}|{scenario.expected_decision}|"
        f"{json.dumps(scenario.arguments, sort_keys=True)}|"
        f"{json.dumps(scenario.expected_state_delta, sort_keys=True)}"
    )


@dataclass(frozen=True)
class HoldoutManifest:
    schema_version: str
    code_manifest_hash: str
    dataset_hash: str
    seed: int
    n_main: int
    n_security_dangerous: int
    n_security_safe: int
    generated_at: str

    @property
    def manifest_hash(self) -> str:
        payload = json.dumps(
            {
                "code_manifest_hash": self.code_manifest_hash,
                "dataset_hash": self.dataset_hash,
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True) + "\n"


ScenarioTuple = tuple[ScenarioSpec, ...]


def generate_holdout(
    code_manifest: CodeFreezeManifest,
    *,
    seed: int,
    clock: Callable[[], str] = _now_iso,
) -> tuple[HoldoutManifest, ScenarioTuple, ScenarioTuple, ScenarioTuple]:
    """Step 3/4: the holdout cannot be generated before CODE_FROZEN
    (enforced by requiring a CodeFreezeManifest as input -- there is no
    code path that produces a HoldoutManifest without one), and the
    full-corpus oracle concordance gate runs BEFORE this function
    returns a manifest -- a mismatch raises, nothing downstream ever
    sees a holdout whose gold the independent oracles disagree with."""
    if not isinstance(code_manifest, CodeFreezeManifest):
        raise FreezeV21Error(
            "generate_holdout requires a real CodeFreezeManifest -- the "
            "holdout cannot be generated before CODE_FROZEN"
        )
    sizes = load_selected_sample_sizes()
    main = generate_scenarios(seed=seed, n_main=sizes["n_main"])
    dangerous, safe = generate_security_population(
        n_dangerous=sizes["n_security_dangerous"]
    )
    validate_full_corpus_concordance((*main, *dangerous, *safe))

    all_scenarios = sorted((*main, *dangerous, *safe), key=lambda s: s.scenario_id)
    payload = "\n".join(_scenario_payload(s) for s in all_scenarios)
    dataset_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    manifest = HoldoutManifest(
        schema_version="2.1",
        code_manifest_hash=code_manifest.manifest_hash,
        dataset_hash=dataset_hash,
        seed=seed,
        n_main=len(main),
        n_security_dangerous=len(dangerous),
        n_security_safe=len(safe),
        generated_at=clock(),
    )
    return manifest, main, dangerous, safe


# ============================================================== receipts


@dataclass(frozen=True)
class RunReceipt:
    state: str
    holdout_manifest_hash: str
    provider: str
    provider_config_hash: str
    recorded_at: str
    checkpoint_path: str | None = None
    n_planned_units: int | None = None
    n_completed_units: int | None = None
    error_class: str | None = None
    error_message: str | None = None

    def to_json_line(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)


def append_receipt(log_path: Path, receipt: RunReceipt) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(receipt.to_json_line() + "\n")


def load_receipts(log_path: Path) -> list[RunReceipt]:
    if not log_path.exists():
        return []
    receipts = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        receipts.append(RunReceipt(**json.loads(line)))
    return receipts


def current_state(log_path: Path) -> RunState:
    receipts = load_receipts(log_path)
    if not receipts:
        return RunState.DRAFT_PROTOCOL
    return RunState(receipts[-1].state)


def record_code_frozen(
    log_path: Path,
    code_manifest: CodeFreezeManifest,
    *,
    clock: Callable[[], str] = _now_iso,
) -> RunReceipt:
    """First real receipt in a campaign's log -- `holdout_manifest_hash`
    is empty because no holdout exists yet at CODE_FROZEN (section 12's
    ordering: code is frozen strictly before any holdout is generated)."""
    current = current_state(log_path)
    transition(current, RunState.CODE_FROZEN)
    receipt = RunReceipt(
        state=RunState.CODE_FROZEN.value,
        holdout_manifest_hash="",
        provider="",
        provider_config_hash=code_manifest.manifest_hash,
        recorded_at=clock(),
    )
    append_receipt(log_path, receipt)
    return receipt


def record_holdout_generated(
    log_path: Path,
    holdout_manifest: HoldoutManifest,
    *,
    clock: Callable[[], str] = _now_iso,
) -> RunReceipt:
    current = current_state(log_path)
    transition(current, RunState.HOLDOUT_GENERATED_NOT_EVALUATED)
    receipt = RunReceipt(
        state=RunState.HOLDOUT_GENERATED_NOT_EVALUATED.value,
        holdout_manifest_hash=holdout_manifest.manifest_hash,
        provider="",
        provider_config_hash="",
        recorded_at=clock(),
    )
    append_receipt(log_path, receipt)
    return receipt


def start_run(
    log_path: Path,
    holdout_manifest: HoldoutManifest,
    *,
    provider: str,
    provider_config_hash: str,
    checkpoint_path: Path,
    n_planned_units: int,
    clock: Callable[[], str] = _now_iso,
) -> RunReceipt:
    if n_planned_units <= 0:
        raise FreezeV21Error("cannot start a run with a missing/empty raw-unit plan")
    current = current_state(log_path)
    transition(current, RunState.RUN_STARTED)  # raises if not an allowed edge

    if current is RunState.RUN_INTERRUPTED_RESUMABLE:
        previous = load_receipts(log_path)[-1]
        if previous.holdout_manifest_hash != holdout_manifest.manifest_hash:
            raise FreezeV21Error(
                "cannot resume: the holdout manifest does not match the "
                "interrupted run's -- a resume must never select a new seed "
                "or regenerate cases"
            )
        if (
            previous.provider != provider
            or previous.provider_config_hash != provider_config_hash
        ):
            raise FreezeV21Error(
                "resume must use the same provider and configuration as the "
                "interrupted run"
            )
        if previous.checkpoint_path != str(checkpoint_path):
            raise FreezeV21Error("resume must reuse the same checkpoint path")

    receipt = RunReceipt(
        state=RunState.RUN_STARTED.value,
        holdout_manifest_hash=holdout_manifest.manifest_hash,
        provider=provider,
        provider_config_hash=provider_config_hash,
        recorded_at=clock(),
        checkpoint_path=str(checkpoint_path),
        n_planned_units=n_planned_units,
    )
    append_receipt(log_path, receipt)
    return receipt


def mark_interrupted(
    log_path: Path,
    *,
    error_class: str,
    error_message: str,
    n_completed_units: int,
    clock: Callable[[], str] = _now_iso,
) -> RunReceipt:
    current = current_state(log_path)
    transition(current, RunState.RUN_INTERRUPTED_RESUMABLE)
    previous = load_receipts(log_path)[-1]
    receipt = RunReceipt(
        state=RunState.RUN_INTERRUPTED_RESUMABLE.value,
        holdout_manifest_hash=previous.holdout_manifest_hash,
        provider=previous.provider,
        provider_config_hash=previous.provider_config_hash,
        recorded_at=clock(),
        checkpoint_path=previous.checkpoint_path,
        n_planned_units=previous.n_planned_units,
        n_completed_units=n_completed_units,
        error_class=error_class,
        error_message=error_message,
    )
    append_receipt(log_path, receipt)
    return receipt


def mark_failed_external(
    log_path: Path,
    *,
    error_class: str,
    error_message: str,
    n_completed_units: int,
    clock: Callable[[], str] = _now_iso,
) -> RunReceipt:
    """Terminal (section 12): no further transition is ever allowed out
    of RUN_FAILED_EXTERNAL. Preserves provider, error, checkpoint and
    completed-unit count from whichever state it failed out of, per
    section 12's own requirement that a failure receipt "conservará
    proveedor, error, checkpoint y unidades completadas"."""
    current = current_state(log_path)
    transition(current, RunState.RUN_FAILED_EXTERNAL)
    previous = load_receipts(log_path)[-1]
    receipt = RunReceipt(
        state=RunState.RUN_FAILED_EXTERNAL.value,
        holdout_manifest_hash=previous.holdout_manifest_hash,
        provider=previous.provider,
        provider_config_hash=previous.provider_config_hash,
        recorded_at=clock(),
        checkpoint_path=previous.checkpoint_path,
        n_planned_units=previous.n_planned_units,
        n_completed_units=n_completed_units,
        error_class=error_class,
        error_message=error_message,
    )
    append_receipt(log_path, receipt)
    return receipt


def validate_run_completion(
    observations: Sequence[ObservationV21],
    archive_path: Path,
    *,
    expected_unit_count: int,
) -> None:
    """Step 4's evidence gate before RUN_COMPLETED: exact planned-unit
    count, no duplicate unit key, every row's arm-specific semantic
    completeness (Task 7B), and the archive's own content-hash integrity
    (load_observations_v21_jsonl already rejects a filename whose hash
    does not match its bytes, and a row_count mismatch against its own
    manifest).

    The unit key MUST include `surface_id`: h3a_stability legitimately
    runs the SAME (scenario_id, system, arm, repetition_index) across
    three surfaces (S1/S2/S3) -- that is the whole point of a stability
    arm across paraphrase/surface variants, not a duplicate. Without
    surface_id here, a real, fully-checkpointed 21460-unit h3a_stability
    run was rejected as "21460 duplicate unit keys" (only 3576 of its
    10728 rows are unique under the coarser tuple) -- found by running
    the real campaign to completion, not by a test, because the only
    prior regression test compared an observation to an exact copy of
    itself (same surface_id included), which this bug could not fail."""
    if len(observations) != expected_unit_count:
        raise FreezeV21Error(
            f"expected {expected_unit_count} completed units, got {len(observations)}"
        )
    keys = [
        (o.scenario_id, o.system, o.arm, o.surface_id, o.repetition_index)
        for o in observations
    ]
    if len(set(keys)) != len(keys):
        raise FreezeV21Error("duplicate unit key(s) among completed observations")
    for observation in observations:
        validate_arm_semantics(observation)

    loaded = load_observations_v21_jsonl(archive_path)
    if loaded.observations != list(observations):
        raise FreezeV21Error(
            "the content-addressed archive does not match the in-memory "
            "completed observations"
        )


def complete_run(
    log_path: Path,
    *,
    observations: Sequence[ObservationV21],
    archive_path: Path,
    clock: Callable[[], str] = _now_iso,
) -> RunReceipt:
    current = current_state(log_path)
    transition(current, RunState.RUN_COMPLETED)
    previous = load_receipts(log_path)[-1]
    if previous.n_planned_units is None:
        raise FreezeV21Error(
            "cannot complete a run with no recorded planned-unit count"
        )

    validate_run_completion(
        observations, archive_path, expected_unit_count=previous.n_planned_units
    )

    receipt = RunReceipt(
        state=RunState.RUN_COMPLETED.value,
        holdout_manifest_hash=previous.holdout_manifest_hash,
        provider=previous.provider,
        provider_config_hash=previous.provider_config_hash,
        recorded_at=clock(),
        checkpoint_path=previous.checkpoint_path,
        n_planned_units=previous.n_planned_units,
        n_completed_units=len(observations),
    )
    append_receipt(log_path, receipt)
    return receipt


def publish_report(
    log_path: Path, *, clock: Callable[[], str] = _now_iso
) -> RunReceipt:
    current = current_state(log_path)
    transition(current, RunState.REPORT_PUBLISHED)
    previous = load_receipts(log_path)[-1]
    receipt = RunReceipt(
        state=RunState.REPORT_PUBLISHED.value,
        holdout_manifest_hash=previous.holdout_manifest_hash,
        provider=previous.provider,
        provider_config_hash=previous.provider_config_hash,
        recorded_at=clock(),
        checkpoint_path=previous.checkpoint_path,
        n_planned_units=previous.n_planned_units,
        n_completed_units=previous.n_completed_units,
    )
    append_receipt(log_path, receipt)
    return receipt


# ------------------------------------------------- external-failure claims


def force_claims_after_external_failure(
    hypotheses: Iterable[str], *, has_partial_data: Mapping[str, bool]
) -> dict[str, str]:
    """Section 12: under RUN_FAILED_EXTERNAL every hypothesis becomes
    `not_measured` (no data at all reached it) or
    `confirmatory_inconclusive` (some partial rows exist but coverage is
    incomplete) -- NEVER `confirmatory`/`supported`, regardless of what
    the partial data happens to show. There is no code path here that
    can return anything else for any hypothesis name it is given."""
    return {
        name: (
            "confirmatory_inconclusive"
            if has_partial_data.get(name, False)
            else "not_measured"
        )
        for name in hypotheses
    }


# --------------------------------------------------------------- H2 cache


def assert_h2_arm_uses_no_cache(llm: Any) -> None:
    """Section 12: the runner must reject "caché activa en H2". Checked
    by class identity rather than duck-typing a `.cache` attribute,
    which a future refactor could rename without this guard noticing --
    an isinstance check against the one caching wrapper this project
    has cannot be silently bypassed that way."""
    from erp_agent_os.llm_client import CachingLLMClient

    if isinstance(llm, CachingLLMClient):
        raise FreezeV21Error("the H2 arm must never be run with a cached LLM client")


# ------------------------------------------------------------- dry run


@dataclass(frozen=True)
class DryRunResult:
    ok: bool
    mismatches: tuple[str, ...]
    n_planned_units: int
    provider: str


def dry_run_check(
    *,
    code_manifest: CodeFreezeManifest,
    provider: str,
    provider_config_hash: str,
    expected_provider: str,
    expected_provider_config_hash: str,
    n_planned_units: int,
    repo_root: Path = REPO_ROOT,
) -> DryRunResult:
    """Step 6: verifies hashes, unit counts and provider configuration
    WITHOUT printing anything (that is the caller script's job) and
    WITHOUT calling A/B/C or writing a single receipt -- this function
    reads and hashes only; it has no path that appends to a receipt log
    or generates a holdout, so it structurally cannot consume one."""
    mismatches: list[str] = []
    if provider != expected_provider:
        mismatches.append(f"provider mismatch: {provider!r} != {expected_provider!r}")
    if provider_config_hash != expected_provider_config_hash:
        mismatches.append("provider_config_hash mismatch")
    if n_planned_units <= 0:
        mismatches.append("n_planned_units is missing/empty")

    drifted = verify_code_freeze(code_manifest, repo_root=repo_root)
    mismatches.extend(f"component drifted: {name}" for name in drifted)

    return DryRunResult(
        ok=not mismatches,
        mismatches=tuple(mismatches),
        n_planned_units=n_planned_units,
        provider=provider,
    )

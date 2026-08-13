$ErrorActionPreference = "Stop"

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][scriptblock]$Command
    )

    Write-Host "`n=== $Name ===" -ForegroundColor Cyan
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

Invoke-Checked "Full test suite" { uv run pytest -q }
Invoke-Checked "Coverage reset" { uv run coverage erase }
Invoke-Checked "Coverage test suite" { uv run coverage run --source=erp_agent_os -m pytest -q }
Invoke-Checked "Coverage threshold" { uv run coverage report --fail-under=95 }
Invoke-Checked "Ruff lint" { uv run ruff check . }
Invoke-Checked "Ruff format check" { uv run ruff format --check . }
Invoke-Checked "Mypy" { uv run mypy src }
Invoke-Checked "Evidence audit" { uv run python scripts/audit_evidence_status.py }
Invoke-Checked "Documentation audit" { uv run python scripts/audit_docs_coherence.py }
Invoke-Checked "Legacy freeze verification" { uv run python scripts/freeze_protocol.py --verify }
Invoke-Checked "Adversarial harness tests" {
    uv run pytest tests/test_adversarial.py tests/test_injection_resistance.py tests/test_injecagent_stress_test.py -q
}
Invoke-Checked "Video asset generation" { uv run python scripts/make_video_assets.py }
Invoke-Checked "Video asset tests" { uv run pytest tests/test_video_assets.py -q }

if (Test-Path -LiteralPath "data/bench_v2.jsonl") {
    Invoke-Checked "ERP-Skills-Bench v2 validation" {
        uv run python scripts/validate_bench_v2.py
    }
    if (Test-Path -LiteralPath "data/bench_v2_freeze_manifest.json") {
        Invoke-Checked "V2 freeze verification" {
            uv run python scripts/freeze_protocol_v2.py --verify
        }
    }
    else {
        Write-Host "V2 dataset valid; freeze manifest still pending" -ForegroundColor Yellow
    }
}
else {
    Write-Host "V2 pending: dataset and freeze manifest are absent" -ForegroundColor Yellow
}

Write-Host "`nCOMPETITION READINESS GATE PASSED" -ForegroundColor Green

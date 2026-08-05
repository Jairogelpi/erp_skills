# Optional developer assistance

This is developer tooling only, not an application/runtime dependency; it does
not implement FakeERP, skills, or runtime work.

## Ponytail

`.ponytail/ponytail.md` is a verbatim official skill. Its immutable source, MIT
license, retrieval date, and SHA-256 manifest are in
[`.ponytail/UPSTREAM.md`](../.ponytail/UPSTREAM.md). Verify with its documented
`sha256sum` or `Get-FileHash` command; never run an installer or substitute
`main`.

## Codebase Memory MCP

After Git is initialized, manually verify official `v0.9.1-rc.1` against
`checksums.txt`, place its binary at `.mcp/local/bin/codebase-memory-mcp`, then:

```sh
make bootstrap-codebase-memory
```

The template pins source commit `4bbe0984f785b097956fe95f976111b043122848`,
MIT license, and official checksum-manifest digest
`4f7c514f6a384950a2f72c4bd3507b9ab9de57704e7342bf1f695b07534b1429`. Bootstrap
writes only ignored `.mcp/local/codebase-memory.json`; import it into your MCP
client yourself. It never downloads software or edits global/client config.

Working directory, `CBM_ALLOWED_ROOT`, and cache are checkout-bound; diagnostics
are disabled. Git absence, invalid pin/template, root mismatch, or external
state path fails closed. This workspace has no `.git`, so bootstrap must fail.

This is **read-mostly**, not strict read-only: upstream exposes index/delete/ADR/
trace tools and has no server read-only flag. Its cache may write under
`.mcp/local/`; checkout files (including ignored files) may be read. Do not keep
secrets/private data here; review the third-party binary.

```sh
make remove-codebase-memory
```

Removal affects only ignored `.mcp/local/` state. Remove your client import
separately; this project never changed it.

### Standing convention: always use and re-index

When an MCP client already has a `codebase-memory-mcp` server connected
(independent of the project-local bootstrap above), the convention for this
repository is:

1. Before code exploration, prefer `search_graph`/`trace_path`/
   `get_code_snippet`/`query_graph`/`get_architecture` over ad-hoc grep.
2. After any SDD work unit that adds or changes source files, re-run
   `index_repository(repo_path=<repo root>, mode="full", persistence=true)`
   so the graph and `.codebase-memory/graph.db.zst` artifact stay current.
3. `detect_changes` may be used to scope a review to what a given commit
   range actually touched.

This is optional developer assistance per the read-mostly caveat above; it
never gates a gate, a test, or a CI check.

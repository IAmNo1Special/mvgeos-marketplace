# okf-bridge

Official Open Knowledge Format (OKF v0.2) and MADR 3.0 knowledge bridge for MvgeOS.

## Features
- Discovers `.okf/` knowledge bundles in workspace and global `~/.agents/.okf/`.
- Conforms strictly to the OKF v0.2 normative specification (§11, §5 trust/provenance/lifecycle, §10 attestation, §13 migration).
- Parses and lints MADR 3.0 Architectural Decision Records in `docs/adr/`.
- Dynamic prompt injection: provides compact `<knowledge_catalog>` XML in `<project_context>` via `BEFORE_MVGE_START` and `CONTEXT_TRANSFORM`.
- Spells: `okf_search`, `okf_get`, `okf_validate`, `adr_list`, `adr_get`.
- CLI: `mvgeos okf` and `mvgeos adr` subcommands with cp1252-safe ASCII output.

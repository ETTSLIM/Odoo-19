---
trigger: always_on
description: Mandatory Graphify-First Protocol — Every turn must query the graphify knowledge graph before any action.
---

## graphify — Universal P0 Invariant

This project has an authoritative AST knowledge graph at `graphify-out/graph.json`.

### Non-Negotiable Turn-Level Invariants:
1. **TOOL CALL #1 MUST BE GRAPHIFY**: For EVERY single turn — including planning, clarifying, follow-ups, container testing, bug diagnosing, and code modifications — the AI assistant MUST execute `graphify query "<topic>"` or `graphify explain "<Symbol>"` via `run_command` BEFORE executing any other tool call (`docker exec`, `read_file`, `write_file`, or answering).
2. **ZERO ASSUMPTIONS & ZERO SKIP**: Never assume "Graphify was already run in a previous turn". Every turn must explicitly re-anchor its scope via Graphify.
3. **RELATIONSHIP & PATH LOOKUPS**: Use `graphify path "<A>" "<B>"` for inter-model relations and `graphify explain "<concept>"` for focused AST definitions.
4. **FALLBACK & WIKI**: If graphify CLI is missing, navigate `graphify-out/wiki/index.md` or `graphify-out/GRAPH_REPORT.md`.
5. **MANDATORY POST-MODIFICATION AST SYNC**: Immediately after editing or creating any Python, XML, SCSS, or JS file, run `graphify update .` to synchronize the AST graph, and verify downstream impacts before running tests.

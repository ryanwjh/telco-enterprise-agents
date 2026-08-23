# Seed data for this logical agent

Add one CSV file per BigQuery table this agent's `data_insights` sub-agent needs to reference.
Each file must have a header row; sample rows should be representative enough to answer
realistic questions, not production-scale.

**Before adding a table, register this agent (and this table) in `_shared/table_registry.yaml`.**
All domain agents share one BigQuery dataset (`retail_ent_agents`). Collisions are prevented
structurally: every domain gets a fixed 4-letter `domain_id` (under `domains:`, e.g. `merc`) and
every agent gets a fixed 4-letter `agent_id` (under `agents:`, e.g. `aspl`), and the loader
physically names each table `<domain_id>_<agent_id>_<this_csv's_file_stem>` (e.g.
`merc_aspl_sales_by_sku`) — so it's fine for two agents to each use the same logical CSV name
(e.g. both calling something `sales_by_sku`). List your agent's logical (unprefixed) table names
under its entry in the registry; the loader refuses to load a table that isn't listed there.

**It's fine — often the right call — to duplicate another agent's data content into your own
table.** E.g. if your agent also needs a product catalog, don't try to read another agent's
`product_catalog` table cross-agent (no agent's service account has IAM on another agent's
tables); instead add your own `data/product_catalog.csv` with the same/similar rows, as your own
independent, physically separate table. Each agent's data stays self-contained and decoupled from
every other agent's data lifecycle and IAM scope, even when the real-world content overlaps.

When you do duplicate or reference another agent's entity (e.g. a product), reuse its exact
identifier values (e.g. the same SKU id) rather than inventing new ones, and when generating
synthetic date-based data, anchor it to the same real-world timeline other agents already use
(the same "today" reference constant, with historical windows overlapping theirs) rather than an
arbitrary independent date range. This keeps agents' tables physically independent while still
letting them read as one consistent business/timeline when used together in the same conversation
or demo.

Load these into the shared dev BigQuery dataset with:

    uv run python _shared/scripts/load_agent_data.py --domain <domain> --name <logical_agent> --project <dev_project_id> --dataset retail_ent_agents

See docs/superpowers/specs/2026-07-25-retail-merchandising-adk-agents-design.md section 6a for
the full rationale (shared dataset, table-level IAM scoping via
`_shared/scripts/grant_table_access.py`). That file is local-only, gitignored, not on a fresh
clone.

# TB-US-096: Port — versioning schema + `versioned_component.py` base class to stalite3

**Status**: Completed 2026-11-07 — stalite3 commit `619e08c`
**Created**: 2026-11-07
**Author**: Jesse Eversole
**Depends on**: TB-US-094 (agents foundation, committed in
stalite3 as `fb14db2`)
**Blocks**: TB-US-097 (6 version-manager subclasses), and every
subsequent port that needs versioned storage

## Story

Port TB's versioning primitives (the 6 `*_versions` tables, the
`agent_components` promotion-mapping table, and the
`VersionedComponentManager` base class) into stalite3. This is
step 2 of the TB-US-094-rooted arc; it's the foundation every
subsequent manager subclass (training-set, prompt, RAG, route,
adapter, harness) depends on.

## Scope

- [x] R1: Add `migrate_versioning_tables()` to
      `backend/api/schema_migrations.py`. Migration tracker ID
      `stalite-02-versioning-tables`. Creates 7 tables verbatim
      from TrainingBench's TB-US-051 schema:
      training_set_versions, rag_versions, adapter_versions,
      prompt_versions, route_versions, harness_versions,
      agent_components.
- [x] R2: Port `backend/api/versioned_component.py` verbatim from
      TB-US-052 with `DEFAULT_DB_PATH` adjusted to
      `backend/db/stalite.db`.
- [x] R3: Wire the migration into `main.py` boot alongside the
      TB-US-094 agents migration.
- [x] R4: Verify: first boot creates all 7 tables + tracker row;
      second boot returns `already_applied=True`.

### Not in scope

- Subclass managers — those are TB-US-097.
- Endpoints or UI — later port stories.

## Acceptance Criteria

- [x] AC1: `backend/db/stalite.db` contains all 7 versioning
      tables after boot.
- [x] AC2: Migration tracker row for `stalite-02-versioning-tables`
      exists after first boot.
- [x] AC3: `VersionedComponentManager` + `VersionedComponentError`
      importable from `api.versioned_component`.
- [x] AC4: Existing stalite3 functionality unchanged; migration is
      strictly additive.

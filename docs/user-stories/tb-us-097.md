# TB-US-097: Port — six `*_version_manager` subclasses to stalite3

**Status**: Completed 2026-11-07 — stalite3 commit `7baaf99`
**Created**: 2026-11-07
**Depends on**: TB-US-096 (base class + 7 versioning tables)
**Blocks**: TB-US-098 (experiment_manager + harness_runner)

## Scope

- [x] Port verbatim (no path changes needed; managers inherit
      `stalite.db` from `VersionedComponentManager.DEFAULT_DB_PATH`):
  - `training_set_version_manager.py` (TB-US-052; 121 lines)
  - `prompt_version_manager.py` (TB-US-055; 49 lines)
  - `rag_version_manager.py` (TB-US-053; 161 lines)
  - `route_version_manager.py` (TB-US-055; 50 lines)
  - `adapter_version_manager.py` (TB-US-054; 150 lines)
  - `harness_version_manager.py` (TB-US-056; 120 lines, `promotable=False`)
- [x] Smoke-test each manager: `list_versions(agent_id=1)` returns
      empty list for the seeded `stalite` agent.

## Acceptance Criteria

- [x] All 6 managers import + instantiate.
- [x] Each manager's `table_name` resolves to its expected
      versioned table.
- [x] stalite3's existing functionality unchanged.

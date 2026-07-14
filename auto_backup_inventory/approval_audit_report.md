# Approval Engine Audit Report

Date: 2026-07-10
Scope: `auto_backup_inventory/inventory` app (primary), repo-wide quick scan for write/update/delete/raw-SQL patterns.

Summary:
- Grep scan targets: `\.save(`, `objects.create(`, `update_or_create(`, `cursor.execute(`, `\.delete(`, `bulk_create(`, `\.update(`
- Quick counts (inventory app):
  - `.save(` matches: ~101
  - `objects.create(` matches: ~106
  - `update_or_create(` matches: 6
  - `.update(` matches: 13
  - `cursor.execute(` matches: 3

High-level findings:
- The majority of production-write sites are concentrated in `inventory/views.py` (many POST handlers and workflow endpoints).
- Other write sites include: `inventory/admin.py` (user admin save / `CourierProfile` create), `inventory/admin_bank_branch.py` (branch import + `update_or_create`), `inventory/apps.py` (seed/update role & feature entries), `inventory/forms.py` (multiple `form.save()` call sites), and `inventory/models.py` (model `save()` overrides).
- Tests contain many create/save operations; those remain as test fixtures and are not targeted for refactor unless they exercise production paths.
- Raw SQL execution and schema changes detected in a few places (`cursor.execute` in `views.py` and `tests.py`) — these require manual review before automated refactor.

Module mapping and priority (suggested order already agreed):
1. Inventory / Tape Management — heavy use of `form.save()` and `Tape.objects.update_or_create` (sensitive)
2. Shipments — many direct `Shipment.objects.create` and status updates (sensitive)
3. Warehouse Operations — `scan_status` updates, reassignment counts, tape lifecycle (sensitive)
4. Reconciliation — reconciliation completion & result writes (sensitive)
5. Exceptions — `ExceptionCloseRequest` flows and direct exception state changes (sensitive)
6. Retention — retention modifications and legal/audit holds (sensitive)
7. User & Role Management — admin user saves, role assignment, `RoleFeature` updates (sensitive for privileges)
8. Feature Management — `Feature`/`RoleFeature` create/update (approval-worthy)
9. System Administration — imports, schema-sync, raw SQL, and other powerful actions (must be manual-review heavy)

Detailed next steps I will take (per your requirements):
- Produce per-module, per-file CSV-style breakdown of every detected write occurrence (file, function, line, snippet, operation type).
- For each entry classify: Create/Update/Delete/Import/Schema/Approval/Assignment/StatusChange and mark whether it currently bypasses `PendingApproval` (Yes/No/Partial).
- Stop and report any operation that cannot be safely refactored automatically (raw SQL, schema migration code, complex transactions involving external systems).
- After you review this audit, I will begin module `Inventory/Tape Management` refactor, creating small, tested patches.

Files flagged for manual review before any automated refactor:
- `inventory/views.py` — endpoints that run raw SQL (`cursor.execute`) and complex multi-model transactions.
- `inventory/admin_bank_branch.py` — branch import uses file parsing + `update_or_create`; potential for large bulk changes.
- `inventory/apps.py` — post-migrate seeders (idempotency handled, but changes to role/feature may have global effects).
- Any code executing `schema` changes or `ALTER TABLE` operations.

Artifacts produced in this step:
- This human-readable audit: `approval_audit_report.md` (you are reading it now).
- Planned: `approval_audit_detailed.csv` (per-line exhaustive report) to be generated next.

Next immediate action (with your go-ahead):
- Generate the detailed per-line CSV `approval_audit_detailed.csv` under project root and then start the first-module refactor (`Inventory/Tape Management`).

If you want any additional filters (e.g., include tests or exclude test-only fixtures), tell me now. Otherwise I will proceed to generate the detailed CSV and then begin the Tape Management refactor.

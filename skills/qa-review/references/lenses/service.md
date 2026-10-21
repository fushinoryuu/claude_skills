---
name: service
description: Extra checks for server-side request handling, data access, and database migrations. Example lens.
applies_when:
  paths: ["**/migrations/**", "**/*.sql", "**/routes/**", "**/controllers/**", "**/handlers/**", "**/services/**", "**/repositories/**"]
  touches: "server-side request handling, persistence, or database schema changes"
---

# Service lens (example)

Extra checks on top of `references/qa-core.md` for changes to a server-side service. Apply the items that are relevant to the change.

## Step 4: Requirements and implementation

- **Input validation.** Input that arrives from outside the service is validated, and invalid input produces a client error instead of a crash or silent acceptance. *Evidence:* a new or changed request body, query parameter, or header that is used without a check.
- **Authorization.** A new or changed operation checks that the caller is permitted to perform it, not only that the caller is logged in.
- **Idempotency and retries.** An operation that clients may retry does not duplicate its side effects.
- **Migrations.** When a migration backfills a column and then adds a stricter constraint (`FOREIGN KEY`, `CHECK`, `NOT NULL`) in the same step, the backfill's match condition covers the column's full historical value space, not only freshly seeded reference data. The migration is reversible or has a recovery path, and is safe to run against a large table.

## Step 5: Test coverage

- New or changed core logic (factories, utilities, helpers, sub-resource handlers) has unit tests.
- New data-access code has a happy-path test, a unique-constraint-violation test, and a test that unexpected errors are rethrown. Skip this item if the project has no database layer.

## Step 6: Higher-level tests (`final` mode only)

- Observable behavior that the acceptance criteria describe is covered by tests in the project's designated integration test location: response shape, status codes, filtering, pagination, and error responses.

---
name: api-spec
description: Extra checks when a project documents an HTTP API with an OpenAPI or Swagger spec. Example lens.
applies_when:
  paths: ["**/openapi*.yaml", "**/openapi*.yml", "**/openapi*.json", "**/swagger*.yaml", "**/swagger*.yml", "**/swagger*.json", "**/routes/**", "**/controllers/**"]
  touches: "an HTTP API that is described by an OpenAPI or Swagger spec"
---

# API spec lens (example)

Extra checks on top of `references/qa-core.md` for a project that documents its HTTP API in a spec file. If the project has no spec, this lens does not apply and Step 7 is reported as not applicable.

## Step 7: Interfaces and documentation

- **Spec updated for the change.** The spec source files for the routes or domains the change touches are updated where necessary. Edit the source files, not a generated bundle. *Evidence:* a changed or new route with no matching change in the spec.
- **New surface documented.** New query parameters, request body fields, and response codes (including error responses) are documented.
- **Spec validation.** If the project has a spec validation script or linter (for example spectral), run it. It must finish with 0 errors.
- **By mode.** In `initial` mode, report gaps only. In `final` mode, fix the spec files where needed and re-run validation.

---
name: security
description: Extra security checks for server-side code, authentication, dependencies and build or pipeline files. Example lens.
applies_when:
  paths:
    - "**/auth/**"
    - "**/authn/**"
    - "**/authz/**"
    - "**/security/**"
    - "**/middleware/**"
    - "**/routes/**"
    - "**/handlers/**"
    - "**/controllers/**"
    - "**/iam/**"
    - "**/.github/workflows/**"
    - "**/Dockerfile*"
    - "**/*.tf"
    - "**/package.json"
    - "**/pyproject.toml"
    - "**/requirements*.txt"
    - "**/go.mod"
    - "**/pom.xml"
  touches: "who may do what, handling of untrusted input or secrets, dependencies, or the permissions of a service or pipeline"
---

# Security lens (example)

Extra checks on top of the "Security and privacy" section of `references/qa-core.md`, for a change to a server-side service, its sign-in, its dependencies, or its pipeline. The core items always apply. This lens goes deeper and names the concrete failures. Apply the items that are relevant to the change, and skip the rest.

**Project conventions come first.** Before you report a missing check, look for the project's own middleware, validation library or policy layer. A check made there is not a gap.

## Step 4: Requirements and implementation

- **Injection and unsafe interpretation.** A query, command, template or file path is built by joining input, where a parameterized query or an allow-list would be safe. Also look for data from outside that is deserialized without a check, a URL that a caller supplied and the server then fetches, a redirect to an address a caller supplied, and path traversal in an upload or download. _Evidence:_ string joining, formatting or concatenation that carries a request value into one of these.
- **Authentication details.** Tokens are checked for signature, expiry and audience. Passwords use a slow, salted hash. There is no home-made cryptography. Random values for tokens come from a secure generator. Tokens and passwords never reach a log. _Evidence:_ a token that is decoded but not verified, a fast hash such as MD5 or SHA-1 on a password, or a general-purpose random function used for a token.
- **Authorization depth.** Access to one item is checked per item, so a caller cannot read another caller's record by changing an id. Admin operations are checked per operation. In a multi-tenant service, every data access is scoped to the tenant. A request body is not copied whole onto a record that has privileged fields. _Evidence:_ a lookup by id with no owner or tenant condition, or a model built straight from the request body that has a `role` or `is_admin` field.
- **Web exposure.** Cross-origin settings are not a wildcard when credentials are sent. Cookies carry the protective flags (`HttpOnly`, `Secure`, `SameSite`). A state-changing request that uses cookie sign-in has forgery protection. Sign-in and other costly operations have a rate limit. Stack traces and debug pages are off outside local use. _Evidence:_ a wildcard origin next to `credentials: true`, a cookie set with no flags, or a debug flag set to true in a committed settings file.
- **Pipeline and infrastructure files.** A workflow has the least permissions it needs. It does not run code from an untrusted branch with write access or secrets, and does not print secrets. Third-party actions are pinned to a commit or a version. A container does not run as root without a reason. _Evidence:_ `permissions: write-all`, a trigger on `pull_request_target` that checks out the pull request's code, an action pinned to a moving branch, or no `USER` line in a new Dockerfile.
- **Dependencies.** A new package has a clear reason, a pinned version and a known maintainer. When the project has its own audit command, ask for its result. A dependency taken from a git URL or `latest` is a gap. _Evidence:_ a new line in the manifest with a range such as `*` or `latest`, or a URL in place of a version.
- **Files and data.** Uploads have a size limit and a type check. Personal data has a retention rule, or a note that there is none. _Evidence:_ a new upload route that reads the whole body with no limit.

## Step 5: Test coverage

- A test where the caller is not allowed. A test where the item belongs to someone else. A test with hostile input. A test with an expired or missing token. The test asserts that the response does not leak details.

## Step 6: Higher-level tests (`final` mode only)

- The permission matrix (each role against each operation) is covered at the project's higher test level. Users and tokens a test creates are removed afterwards.

## Step 7: Interfaces and documentation

- The documentation says how each new or changed route is protected: the spec's security scheme, or the README. The 401 and 403 responses are documented. A new setting or variable that holds a secret says how to supply it. A change that makes sign-in stricter is called out as breaking.

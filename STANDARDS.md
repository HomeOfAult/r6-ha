# Engineering standards

These rules apply to every change in this repository, by people and by automated coding sessions. The automated reviewer checks pull requests against them.

## Git workflow
- Never push to the default branch. Work on a feature branch and open a pull request. Automated coder sessions use `claude/<session-id>` branches.
- Do not change git identity or authentication.

## Commits and pull requests
- Commit messages and PR titles follow `<type>(<scope>): <message>`, for example `feat(auth): add refresh token support` or `fix(renovate): scope kubernetes manager to apps/*/manifests`.
- Every commit made by `clault-developers[bot]` carries a `Session: <session-id>` trailer.
- Open the PR ready for review and add the `needs-review` label. A draft is reviewed only when `needs-review` is added; after a failed review on a draft, re-add `needs-review` after pushing.
- Labels used by the reviewer: `changes-requested` (fix and push), `needs-human` (stop and ask thault), `ready-to-merge` (approved, waiting for thault; do not push more unless asked).
- Nobody merges except thault.

## Testing and CI
- Every application repo has CI that builds and tests on pull requests and on pushes to the default branch.
- New behavior and bug fixes come with tests. Follow the repo's own lint and format tooling.

## Releases and artifacts
- Semantic Versioning (`MAJOR.MINOR.PATCH`); stay in `0.y.z` until the API is declared stable.
- CI that builds artifacts publishes them under the semver version taken from the git tag (`v0.3.1` publishes `:0.3.1`). A `latest` tag is optional, but anything that deploys or depends on an artifact pins a semver version, never `latest`.

## Logging
- Log startup, shutdown and loaded configuration. Log unexpected errors and failed external calls (HTTP, DB, subprocess) with enough context to diagnose them.
- Use log levels properly. Prefer structured logging. Follow the repo's existing logging library.
- Never log secrets, tokens, passwords or full credentials.

## Dependencies
- Every repo has a `renovate.json` extending `config:recommended` (or the repo's established convention), added in its own PR if missing.

## Secrets
- Never commit real secret values; never put them in chat, commits or logs.
- Application repos that ship Kubernetes manifests use plain `kind: Secret` manifests with placeholder values only. They must not contain `ExternalSecret` resources or External Secrets configuration.
- Secrets for deployed apps are managed outside application repositories and never appear in them.

## Deployment
- Deployment configuration lives in a separate infrastructure repository. Changes to what runs in production are made there by pull request; never change production directly.
- Do not reference machine-local paths (for example under a home directory) in this repository.

## APIs
- A project with an API contract (for example an OpenAPI spec) serves its documentation at `/docs`.

## Language
- Backend services are written in Go unless the repo already uses another language or there is a strong reason not to.

## Review
A review fails (blocking) on: correctness, security, data loss, broken build or tests, committed secrets, any violation of this document, missing or inadequate tests, a repo without CI or `renovate.json` (unless the PR adds one), a PR title not matching `<type>(<scope>): <message>`, bot commits that are not conventional or lack the `Session:` trailer, logging-rule violations, `latest` pins, `ExternalSecret` resources in this repo, real values in `kind: Secret`, machine-local paths, and production changes made outside the infrastructure repo. Style nits are reported as non-blocking.

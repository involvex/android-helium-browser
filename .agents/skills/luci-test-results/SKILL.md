---
name: luci-test-results
description: >
  Triage and analyze LUCI build results (including tests and compile).
  Fetches a list of test failures by querying ResultDB directly.
  Can also be used to check results of specific tests.
  Use this when you need to investigate specific test failures.
---

# LUCI Triage Cheat Sheet

## 1. Resolve Build ID

If you have a builder + build number, get the long `<BUILD_ID>`:

```bash
scripts/luci_triage.py resolve-build-id \
  --builder "<BUILDER>" \
  --build-number <NUMBER> \
  --project <PROJECT> \
  --bucket <BUCKET>
```
for a builder URL that starts with
```
https://ci.chromium.org/ui/p/<PROJECT>/builders/<BUCKET>/<BUILDER>/<NUMBER>/...
```

For the URL
https://ci.chromium.org/ui/p/chromium/builders/try/linux-chromeos-rel/2769679/overview
you should run the script for this skill with the following arguments:
```bash
scripts/luci_triage.py resolve-build-id \
  --builder "linux-chromeos-rel" \
  --build-number 2769679 \
  --project chromium \
  --bucket try
```

## 2. Find Builds for Gerrit CL

Find builds for a specific CL and patchset (defaults to non-successful builds):

```bash
scripts/luci_triage.py find-cl-builds \
  --cl <CL_NUMBER> \
  [--patchset <PATCHSET>] \
  [--all] \
  [--host <HOST>]
```

> [!NOTE]
> - By default, this command only returns builds that did not succeed
>   (e.g., FAILURE, INFRA_FAILURE). Use `--all` to include SUCCESSFUL builds.
> - If `--patchset` is omitted, the script tries to auto-detect the
>   latest patchset via Gerrit.
> - **Gerrit Auth Issue**: Auto-detecting patchset for internal CLs
>   (on `chromium-review.git.corp.google.com`) might fail with auth errors.
>   Workaround: Provide `--patchset` explicitly.
> - **Patchset Mismatch**: If you expect builds but get none, try
>   specifying an earlier patchset number where the tryjobs were actually
>   triggered.

## 3. Get Build Details

Get status, summary markdown, and output properties of a build:

```bash
scripts/luci_triage.py get-build \
  --build-id <BUILD_ID>
```

## 4. List Unexpected Failures

Get a clean list of tests that failed unexpectedly, deduplicated by test ID and
grouped by Swarming task:

```bash
scripts/luci_triage.py list-failures \
  --build-id <BUILD_ID>
```

- **Triage Priority:** If multiple tests share a `task` ID, triage **one**
  result first.

## 5. Fetch Log Snippet

Retrieve a filtered failure log snippet using the result name (`res`) from step
4:

```bash
scripts/luci_triage.py fetch-log \
  --res "<RES_NAME>"
```

## 6. Check Specific Test

Check if a specific test (or tests matching a regex) ran in a build, and see
its status:

```bash
scripts/luci_triage.py check-test \
  --build-id <BUILD_ID> \
  --test-regex "<TEST_REGEX>"
```

- **Efficiency:** This command uses server-side filtering via `QueryTestResults`
  and automatically wraps your regex with `.*` for partial matching. It fetches
  all results (expected and unexpected) for matching tests.

## 7. Get Test History

Query LUCI Analysis for the historical verdicts of a specific test variant:

```bash
scripts/luci_triage.py test-history \
  --project <PROJECT> \
  --test-id "<TEST_ID>" \
  [--limit <LIMIT>] \
  [--builder <BUILDER>] \
  [--bucket <BUCKET>] \
  [--device-os <DEVICE_OS>] \
  [--device-type <DEVICE_TYPE>] \
  [--os <OS>] \
  [--test-suite <TEST_SUITE>]
```

## Implementation Notes

1. **Task-Based Triage:** A shard crash often manifests as
   `CascadingFailureException`. Triage the root failure in that shard first by
   checking the first failure in a task group.
2. **Log Filtering:** The `fetch-log` command automatically filters for
   `AssertionError`, `FATAL`, `Exception`, and `FAIL` to keep the context
   window clean.

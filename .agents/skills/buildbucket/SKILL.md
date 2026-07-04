---
name: buildbucket
description: >
  A wrapper around the 'bb' (buildbucket) tool designed for low-context
  agentic usage without overly verbose logs. Good for a high-level
  overview of builder failures across a patchset, and for surfacing
  non-test failures (e.g., compile and profile merge failures). For
  detailed, complete, and actionable test failures, use the
  'luci-test-results' skill which queries ResultDB directly for comprehensive
  information about failures.
---

## Overview

This skill provides a Python wrapper (`bb_wrapper.py`) around the `bb` CLI tool.
It is designed to handle large outputs gracefully by parsing JSON and saving
logs to files, providing summaries instead of dumping everything to stdout.

Key features:

- List try bot results for a Gerrit CL URL.
- Easily find the latest build for a builder.
- List build steps with status clearly visible.
- Fetch logs safely and view the tail.

## Usage

The main entry point is the `bb_wrapper.py` script located in the `scripts`
directory of this skill.

### Commands

1. **List CL Build Results**

   ```bash
   agents/skills/buildbucket/scripts/bb_wrapper.py cl <cl_url> [--patchset <N>] [--all] [--verbose] [--logs]
   ```

   - `cl_url`: The full URL to the Gerrit CL.
   - `--patchset` (`-p`): The patchset number. If not provided, the script looks
     for it in the URL. If still missing, it attempts to find the latest
     patchset via Gerrit REST API.
   - `--all` (`-a`): Show all builds for the specified patchset (including
     retries and successful ones). If no patchset is specified, it fetches and
     shows builds for **all** patchsets found for the CL.
   - `--verbose` (`-v`): Show full failure summaries (Markdown).
   - `--logs` (`-l`): Automatically fetch and show the tail of logs for failed
     steps.

2. **Get Latest Build Info for a Builder**

   ```bash
   agents/skills/buildbucket/scripts/bb_wrapper.py latest <builder_path>
   ```

   - `builder_path`: format `project/bucket/builder` (e.g.,
     `chromium/try/linux-rel`)

3. **List Build Steps**

   ```bash
   agents/skills/buildbucket/scripts/bb_wrapper.py steps <build_id>
   ```

   - `build_id`: The ID of the build.

4. **Fetch Logs for a Step**

   ```bash
   agents/skills/buildbucket/scripts/bb_wrapper.py logs <build_id> <step_name> <log_name> [-o output_file]
   ```

   - `step_name`: Name of the step (e.g., `compile`, `browser_tests`).
   - `log_name`: Name of the log (e.g., `stdout`, `failure_summary`).
   - `-o`: Optional output file path. Defaults to
     `/tmp/bb_<id>_<step>_<log>.log`.

## Examples

### Check CL try bot results (URL includes patchset)

```bash
agents/skills/buildbucket/scripts/bb_wrapper.py cl https://chromium-review.googlesource.com/c/chromium/src/+/123456/3
```

### Check all builds for a CL (no patchset specified)

```bash
agents/skills/buildbucket/scripts/bb_wrapper.py cl https://chromium-review.googlesource.com/c/chromium/src/+/123456 --all
```

### Inspect steps of a failed build

```bash
agents/skills/buildbucket/scripts/bb_wrapper.py steps 876543210987654321
```

### Get the compile log

```bash
agents/skills/buildbucket/scripts/bb_wrapper.py logs 876543210987654321 compile stdout
```

## Best Practices

- **No Builds Found**: If `bb_wrapper.py cl` reports "No builds found" for a
  patchset:
  - Check if you have the correct patchset number. Patchsets are often
    re-uploaded, and older ones might not have been run.
  - Try listing builds for _all_ patchsets by omitting the patchset number from
    the URL and using the `--all` flag.
  - If the CL is very new, builds might still be in the `SCHEDULED` state and
    not yet associated with the `buildset` tag used for searching.
  - You can try to trigger a dry run in Gerrit to start the try bots.
- **Invalid Results**: If a test step fails with "invalid results" or "Did a
  shard fail early?", it often means the test runner crashed or exited
  unexpectedly before it could write the results. In these cases, check the
  `stdout` or `json.output` log of that step instead of `failure_summary`.
- **Swarming Details**: For test steps, the `chromium_swarming.summary` log
  contains critical metadata such as the `bot_id`, `task_id`, `exit_code`, and
  actual `duration`. Use this to determine if failures are bot-specific or
  related to task timeouts.
- **Analyzing Builder Health**: Use the raw `bb` tool to get a high-level
  overview of a builder's recent history:
  ```bash
  bb ls -n 50 project/bucket/builder
  ```
  This can be combined with `rg FAILURE | wc -l` to calculate failure rates.
- **Piping Results**: If you pipe `bb_wrapper.py` output into `rg` or `head` and
  see a `BrokenPipeError`, it means the tool you are piping to closed the
  connection while `bb_wrapper.py` was still writing. This is usually harmless
  but you can avoid it by using less aggressive filters or saving to a file
  first.
- **Direct bb fallback**: If `bb_wrapper.py` is too restrictive (e.g. you want
  to see all patchsets), use the raw `bb` tool:
  ```bash
  bb ls -cl https://chromium-review.googlesource.com/c/chromium/src/+/123456 -n 20
  ```
- **Authentication**: If you see errors like `Login required: run bb auth-login` while
  trying to use the `bb` tool, you cannot perform interactive authentication yourself.
  You MUST ask the user to run `bb auth-login` in their terminal to authorize the tool.
- **Corp URLs**: If the URL contains `.git.corp.google.com`, replace it with `.googlesource.com`
  instead, as automated agents often fail to authenticate on the corp host.
- **Do not** `cat` entire log files if they are large. The wrapper prints the
  tail automatically. Use `rg` or `tail` on the saved file if needed.

## Directory Structure

```
agents/skills/buildbucket/
├── scripts/
│   └── bb_wrapper.py*
├── OWNERS
└── SKILL.md
```

#!/usr/bin/env vpython3
# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Helper wrapper for buildbucket (bb) tool."""

import argparse
import subprocess
import json
import sys
import os
import re

from pathlib import Path

# Add depot_tools to path for importing git_cl and gerrit_util
depot_tools_dir = Path(__file__).resolve().parents[4]
sys.path.append(str(depot_tools_dir))
import git_cl
import gerrit_util


class BuildbucketError(Exception):
    """Error raised when buildbucket command fails."""


def run_bb(args):
    """Runs a bb command and returns the output."""
    cmd = ["bb"] + args
    try:
        result = subprocess.run(cmd,
                                capture_output=True,
                                text=True,
                                check=True,
                                timeout=60)
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise BuildbucketError(
            f"Error running bb command: {e}\nStderr: {e.stderr}")
    except subprocess.TimeoutExpired as e:
        raise BuildbucketError(
            f"Error: bb command timed out after 60 seconds: {' '.join(cmd)}")


def get_latest_build(builder_path):
    """Gets the latest build for a given builder path."""
    output = run_bb(["ls", "-n", "1", "-json", builder_path])
    try:
        builds = [
            json.loads(line) for line in output.strip().split("\n")
            if line.strip()
        ]
        if not builds:
            print(f"No builds found for {builder_path}")
            return None
        return builds[0]
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON output: {e}", file=sys.stderr)
        return None


def list_steps(build_id):
    """Lists steps for a build, highlighting failures."""
    output = run_bb(["get", "-A", "-json", build_id])
    try:
        build = json.loads(output)
    except json.JSONDecodeError:
        print("Failed to parse build JSON", file=sys.stderr)
        return

    builder_name = build.get("builder", {}).get("builder")
    print(f"Build: {builder_name} Number: {build.get('number')} "
          f"ID: {build.get('id')}")
    print(f"Status: {build.get('status')}")
    print("-" * 40)

    steps = build.get("steps", [])
    for step in steps:
        name = step.get("name")
        status = step.get("status")
        logs = step.get("logs", [])

        status_str = status
        if status != "SUCCESS":
            status_str = f"*** {status} ***"

        print(f"{name:<50} {status_str}")
        if logs:
            log_names = [l.get("name") for l in logs]
            print(f"  Logs: {', '.join(log_names)}")


def get_log(build_id, step_name, log_name, output_file):
    """Fetches a log and saves it to a file."""
    print(f"Fetching log '{log_name}' for step '{step_name}'\n"
          f"    of build {build_id}...")
    output = run_bb(["log", "-nocolor", build_id, step_name, log_name])

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(output)
    except IOError as e:
        print(f"Error writing log output to {output_file}: {e}",
              file=sys.stderr)
        sys.exit(1)

    print(f"Log saved to {output_file}")

    line_count = len(output.splitlines())
    size_bytes = os.path.getsize(output_file)
    print(f"Lines: {line_count}, Size: {size_bytes} bytes")

    print("-" * 20 + " Last 20 lines " + "-" * 20)
    print("\n".join(output.splitlines()[-20:]))
    print("-" * 60)


def parse_gerrit_url(url, explicit_patchset=None, project="chromium/src"):
    """Parses a Gerrit URL and returns (host, change, patchset, project)."""
    parsed = git_cl.ParseIssueNumberArgument(url)

    if parsed.valid:
        host = parsed.hostname
        if "review.git.corp.google.com" in url:
            host = url.split("://")[1].split("/")[0]
    else:
        if "review.git.corp.google.com" in url:
            public_url = url.replace("review.git.corp.google.com",
                                     "review.googlesource.com")
            parsed = git_cl.ParseIssueNumberArgument(public_url)
            if parsed.valid:
                host = url.split("://")[1].split("/")[0]
            else:
                return None, None, None, None
        else:
            return None, None, None, None

    change = str(parsed.issue)
    patchset = str(parsed.patchset) if parsed.patchset else None
    if explicit_patchset:
        patchset = str(explicit_patchset)
    return host, change, patchset, project


def get_patchsets(host, project, change):
    """Finds available patchsets for a CL using Gerrit API via gerrit_util."""
    try:
        data = gerrit_util.CallGerritApi(
            host, f"changes/{change}/detail?o=ALL_REVISIONS")
        revisions = data.get("revisions", {})
        if revisions:
            return sorted([rev.get("_number", 1) for rev in revisions.values()])
    except Exception as e:
        print(f"Warning: Failed to get patchsets from Gerrit: {e}",
              file=sys.stderr)
    return []


def list_cl_builds(cl_url,
                   patchset=None,
                   show_all=False,
                   verbose=False,
                   show_logs=False,
                   project="chromium/src"):
    """Lists builds for a CL."""
    host, change, ps, project = parse_gerrit_url(cl_url, patchset, project)
    if not host or not change:
        print(f"Error: Could not parse URL '{cl_url}'.", file=sys.stderr)
        sys.exit(1)

    all_ps = []
    if not ps:
        all_ps = get_patchsets(host, project, change)
        if not all_ps:
            print(
                f"Error: Missing patchset and could not find any "
                f"for change {change}.",
                file=sys.stderr,
            )
            sys.exit(1)
        if show_all:
            print(f"No patchset specified, fetching builds for ALL "
                  f"patchsets ({min(all_ps)} to {max(all_ps)})...")
        else:
            ps = str(max(all_ps))
            print(f"No patchset specified, using latest: {ps}")

    if ps and not (show_all and not patchset):
        print(f"Fetching builds for {host} change {change} patchset {ps}...")
        predicates = [
            json.dumps({
                "tags": [{
                    "key": "buildset",
                    "value": f"patch/gerrit/{host}/{change}/{ps}",
                }]
            })
        ]
    else:
        if not all_ps:
            all_ps = get_patchsets(host, project, change)
        predicates = [
            json.dumps({
                "tags": [{
                    "key": "buildset",
                    "value": f"patch/gerrit/{host}/{change}/{p}",
                }]
            }) for p in all_ps
        ]

    cmd = [
        "bb",
        "ls",
        "-n",
        "100",
        "-json",
        "-fields",
        "summary_markdown,status,builder,id,create_time,input",
    ]
    for p in predicates:
        cmd.extend(["-predicate", p])

    try:
        output = subprocess.run(cmd,
                                capture_output=True,
                                text=True,
                                timeout=60,
                                check=False)
    except subprocess.TimeoutExpired:
        print("Error: bb command timed out after 60 seconds", file=sys.stderr)
        return

    if output.returncode != 0:
        print(f"Error fetching builds: {output.stderr}")
        return

    try:
        builds = [
            json.loads(line) for line in output.stdout.strip().split("\n")
            if line.strip()
        ]
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON output: {e}", file=sys.stderr)
        return

    if not builds:
        if ps:
            print(f"No builds found for patchset {ps}")
        else:
            print(f"No builds found for change {change}")
        return

    status_priority = {
        "FAILURE": 0,
        "INFRA_FAILURE": 1,
        "CANCELED": 2,
        "STARTED": 3,
        "SCHEDULED": 4,
        "SUCCESS": 5,
    }

    unique_builders = {}
    other_builds = []

    for b in builds:
        builder = b.get("builder", {}).get("builder")
        status = b.get("status")
        build_id = b.get("id")

        if builder not in unique_builders:
            unique_builders[builder] = b

            print(f"[{status:13}] {builder}")
            print(f"  ID: {build_id}  Created: {b.get('createTime')}")

            if status in ["FAILURE", "INFRA_FAILURE"] or verbose:
                _print_build_details(b, show_logs, verbose)
            print()

        else:
            other_builds.append(b)

    if other_builds:
        if show_all:
            print("OTHER BUILDS:")
            for b in other_builds:
                status = b.get("status")
                builder = b.get("builder", {}).get("builder")
                build_id = b.get("id")
                print(f"  [{status:13}] {builder}")
                print(f"    ID: {build_id}  Created: {b.get('createTime')}")
        else:
            counts = {}
            for b in other_builds:
                s = b.get("status")
                counts[s] = counts.get(s, 0) + 1
            sorted_statuses = sorted(counts.keys(),
                                     key=lambda s: status_priority.get(s, 10))
            counts_str = ", ".join(f"{counts[s]} {s}" for s in sorted_statuses)
            print(f"Other builders: {counts_str} "
                  f"(use --all to show all builds/builders)")


def _print_build_details(b, show_logs, verbose):
    """Prints detailed information for a build."""
    build_id = b.get("id")

    if verbose:
        summary_markdown = b.get("summaryMarkdown", "")
        if summary_markdown:
            print("  Summary:")
            lines = summary_markdown.splitlines()
            for line in lines[:10]:
                print(f"    {line}")
            if len(lines) > 10:
                print(f"    ... and {len(lines) - 10} more lines.")

    if not (show_logs or verbose):
        return

    try:
        res = subprocess.run(
            ["bb", "get", build_id, "-json", "-A"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if res.returncode != 0:
            return

        full_build = json.loads(res.stdout)
        steps = full_build.get("steps", [])
        failed_steps = [
            s for s in steps if s.get("status") in ["FAILURE", "INFRA_FAILURE"]
        ]

        for step in failed_steps:
            print(f"    Failed Step: {step.get('name')}")
            if show_logs:
                _fetch_and_print_log(build_id, step)
    except Exception as e:
        print(f"    Error fetching detailed info: {e}")


def _fetch_and_print_log(build_id, step):
    """Fetches and prints the log for a failed step."""
    logs = step.get("logs", [])
    # Log fallback strategy: prioritize failure_summary, then stdout, then step_metadata.
    target_log = next(
        (l for l in logs if l.get("name") == "failure_summary"),
        None,
    )
    if not target_log:
        target_log = next(
            (l for l in logs if l.get("name") == "stdout"),
            None,
        )
    if not target_log:
        target_log = next(
            (l for l in logs if l.get("name") == "step_metadata"),
            None,
        )
    if not target_log and logs:
        target_log = logs[0]

    if not target_log:
        return

    step_name = step.get("name")
    log_name = target_log.get("name")
    print(f"      Fetching tail of log '{log_name}'...")
    try:
        log_res = subprocess.run(
            ["bb", "log", "-nocolor", build_id, step_name, log_name],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if log_res.returncode == 0:
            last_lines = log_res.stdout.splitlines()[-50:]
            for line in last_lines:
                print(f"      {line}")
        else:
            print(f"      Error fetching log: {log_res.stderr.strip()[:100]}")
    except Exception as e:
        print(f"      Exception fetching log: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Helper wrapper for buildbucket (bb) tool.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    latest_parser = subparsers.add_parser(
        "latest", help="Get latest build info for a builder")
    latest_parser.add_argument(
        "builder", help="Builder path (e.g., chromium/ci/Linux Builder)")

    steps_parser = subparsers.add_parser("steps", help="List steps of a build")
    steps_parser.add_argument(
        "build_id", help="Build ID or Number (if used with builder path)")

    logs_parser = subparsers.add_parser("logs", help="Fetch logs for a step")
    logs_parser.add_argument("build_id", help="Build ID")
    logs_parser.add_argument("step_name", help="Step name")
    logs_parser.add_argument("log_name", help="Log name (e.g., stdout)")
    logs_parser.add_argument("--out", "-o", help="Output file", default=None)

    cl_parser = subparsers.add_parser("cl", help="List builds for a Gerrit CL")
    cl_parser.add_argument("cl_url", help="Gerrit CL URL")
    cl_parser.add_argument(
        "--project",
        help="Gerrit project (default: chromium/src)",
        default="chromium/src",
    )
    cl_parser.add_argument(
        "--patchset",
        "-p",
        help="Patchset number. If not provided, script looks for it in URL. "
        "Fails if missing.",
    )
    cl_parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="Show all builds (including retries and successful ones)",
    )
    cl_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show full summary markdown for failed builds",
    )
    cl_parser.add_argument(
        "--logs",
        "-l",
        action="store_true",
        help="Show tail of logs for failed steps in failed builds",
    )

    args = parser.parse_args()

    if args.command == "latest":
        build = get_latest_build(args.builder)
        if build:
            print(f"Latest Build ID: {build.get('id')}")
            print(f"Build Number: {build.get('number')}")
            print(f"Status: {build.get('status')}")
            print(f"Created: {build.get('createTime')}")

    elif args.command == "steps":
        list_steps(args.build_id)

    elif args.command == "logs":
        if not args.out:
            safe_step = args.step_name.replace(" ", "_").replace("/", "_")
            safe_log = args.log_name.replace(" ", "_").replace("/", "_")
            args.out = os.path.join(
                "/tmp", f"bb_{args.build_id}_{safe_step}_{safe_log}.log")

        get_log(args.build_id, args.step_name, args.log_name, args.out)

    elif args.command == "cl":
        list_cl_builds(
            args.cl_url,
            patchset=args.patchset,
            show_all=args.all,
            verbose=args.verbose,
            show_logs=args.logs,
            project=args.project,
        )


if __name__ == "__main__":
    try:
        main()
    except BuildbucketError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)
    except BrokenPipeError:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        sys.exit(1)

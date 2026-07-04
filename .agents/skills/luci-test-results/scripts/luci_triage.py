#!/usr/bin/env python3
# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""CLI tool for triaging LUCI test failures."""

import argparse
import json
import re
import subprocess
import sys


def run_prpc(service, method, payload):
    """Calls a pRPC service and returns the parsed JSON response."""
    cmd = ['prpc', 'call', service, method]
    with subprocess.Popen(cmd,
                          stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          text=True) as process:
        stdout, stderr = process.communicate(input=json.dumps(payload))
        if process.returncode != 0:
            print(f"Error calling {service}.{method}: {stderr}",
                  file=sys.stderr)
            return None
        return json.loads(stdout)


def resolve_build_id(project, bucket, builder, build_number):
    """Resolves a builder and build number to a Buildbucket ID."""
    payload = {
        'builder': {
            'project': project,
            'bucket': bucket,
            'builder': builder
        },
        'buildNumber': int(build_number)
    }
    result = run_prpc('cr-buildbucket.appspot.com',
                      'buildbucket.v2.Builds.GetBuild', payload)
    return result.get('id') if result else None


def get_build(build_id):
    """Retrieves detailed information about a build."""
    if build_id.startswith('b'):
        build_id = build_id[1:]
    payload = {
        'id': build_id,
        'mask': {
            'fields': 'id,builder,number,status,summaryMarkdown,output'
        }
    }
    return run_prpc('cr-buildbucket.appspot.com',
                    'buildbucket.v2.Builds.GetBuild', payload)


def find_cl_builds(cl_number, patchset=None, host=None, show_all=False):
    """Finds builds for a specific CL and patchset."""
    if not host:
        host = 'chromium-review.googlesource.com'

    if not patchset:
        # Get latest patchset
        base_url = f"https://{host}/changes"
        cmd = ['curl', '-s', f"{base_url}/{cl_number}?o=CURRENT_REVISION"]
        try:
            output = subprocess.check_output(cmd).decode(
                'utf-8').splitlines()[1:]
            data = json.loads('\n'.join(output))
            patchset = data['revisions'][data['current_revision']]['_number']
        except Exception as e:
            print(f"Error getting latest patchset: {e}", file=sys.stderr)
            return []

    payload = {
        'predicate': {
            'gerritChanges': [{
                'host': host,
                'change': int(cl_number),
                'patchset': int(patchset)
            }]
        }
    }
    result = run_prpc('cr-buildbucket.appspot.com',
                      'buildbucket.v2.Builds.SearchBuilds', payload)
    if not result or 'builds' not in result:
        return []

    return [{
        'builder': b['builder']['builder'],
        'status': b['status'],
        'id': b['id']
    } for b in result['builds']
            if show_all or b['status'] not in ('SUCCESS', 'STARTED')]


def list_failures(build_id, limit=None):
    """Lists failing and flaky test variants for a build, grouped by task."""
    if build_id.startswith('b'):
        build_id = build_id[1:]

    payload = {
        'invocations': [f'invocations/build-{build_id}'],
        'predicate': {
            'status': 'UNEXPECTED_MASK'
        },
        'pageSize': 1000
    }

    test_variants = []
    while True:
        result = run_prpc('results.api.luci.app',
                          'luci.resultdb.v1.ResultDB.QueryTestVariants',
                          payload)
        if not result:
            break

        test_variants.extend(result.get('testVariants', []))

        if 'nextPageToken' not in result or (limit is not None
                                             and len(test_variants) >= limit):
            break
        payload['pageToken'] = result['nextPageToken']

    tasks = {}
    for tv in test_variants:
        if 'results' not in tv:
            continue

        # Find a failed result to report for this variant.
        results = [r['result'] for r in tv['results']]
        failed_results = [r for r in results if r.get('status') != 'PASS']
        first_result = failed_results[0] if failed_results else results[0]
        res_name = first_result['name']
        task_id = res_name.split('/')[1].replace('task-', '')

        failure = {
            'id':
            tv['testId'],
            'res':
            res_name,
            'err':
            first_result.get('failureReason', {}).get('primaryErrorMessage',
                                                      'No error'),
            'flaky':
            tv.get('status') == 'FLAKY'
        }

        if task_id not in tasks:
            tasks[task_id] = []
        tasks[task_id].append(failure)

    return tasks


def fetch_log_snippet(res_name, raw=False):
    """Fetches a filtered snippet of the failure log."""
    payload = {'parent': res_name}
    result = run_prpc('results.api.luci.app',
                      'luci.resultdb.v1.ResultDB.ListArtifacts', payload)
    if not result or 'artifacts' not in result:
        return "No artifacts found."

    # Prefer "Test Log" or similar
    artifacts = result['artifacts']
    target = next((a for a in artifacts
                   if a['artifactId'] in ('test_log', 'stdout', 'logs')),
                  artifacts[0])

    url = target['fetchUrl']
    cmd = ['curl', '-sL', url]
    try:
        output = subprocess.check_output(cmd).decode('utf-8', errors='ignore')
    except Exception as e:
        return f"Error fetching log: {e}"

    if raw:
        return output

    # Filter for interesting lines
    lines = output.splitlines()
    # Prioritize certain errors
    patterns = [
        r"AssertionError", r"FATAL", r"Exception", r"FAILED", r"FAIL",
        r"Leaking"
    ]
    combined_pattern = "|".join(patterns)

    interesting_indices = [
        i for i, line in enumerate(lines)
        if re.search(combined_pattern, line, re.I)
    ]

    if not interesting_indices:
        return "\n".join(lines[:100])  # Fallback to first 100 lines

    # Get windows around interesting lines
    output_lines = []
    last_idx = -1
    # If too many matches, prioritize the ones with "AssertionError" or "Exception"
    primary_indices = [
        i for i in interesting_indices
        if re.search(r"AssertionError|Exception", lines[i], re.I)
    ]
    if primary_indices:
        interesting_indices = primary_indices

    for idx in interesting_indices[:5]:  # limit to first 5 matches
        start = max(0, idx - 15)
        end = min(len(lines), idx + 10)
        if start > last_idx + 1 and last_idx != -1:
            output_lines.append("...")
        output_lines.extend(lines[max(last_idx + 1, start):end])
        last_idx = end - 1

    return "\n".join(output_lines[:200])


def check_test(build_id, test_regex):
    """Checks if a test matching regex ran in the build using QueryTestResults."""
    if build_id.startswith('b'):
        build_id = build_id[1:]

    # Ensure regex matches partially by wrapping with .* if not already anchored
    if not test_regex.startswith('.*'):
        test_regex = '.*' + test_regex
    if not test_regex.endswith('.*'):
        test_regex = test_regex + '.*'

    payload = {
        'invocations': [f'invocations/build-{build_id}'],
        'predicate': {
            'testIdRegexp': test_regex,
            'expectancy': 'ALL'
        },
        'pageSize': 1000
    }

    test_results = []
    while True:
        result = run_prpc('results.api.luci.app',
                          'luci.resultdb.v1.ResultDB.QueryTestResults', payload)
        if not result:
            print("Error: Failed to query ResultDB", file=sys.stderr)
            break

        test_results.extend(result.get('testResults', []))

        if 'nextPageToken' not in result:
            break
        payload['pageToken'] = result['nextPageToken']

    matching_tests = []
    for tr in test_results:
        matching_tests.append({
            'id': tr['testId'],
            'status': tr.get('status'),
            'expected': tr.get('expected')
        })

    return matching_tests


def test_history(project,
                 test_id,
                 limit=None,
                 builder=None,
                 bucket=None,
                 device_os=None,
                 device_type=None,
                 os=None,
                 test_suite=None):
    """Queries LUCI Analysis for the test history of a specific test variant."""
    variant_def = {}
    if builder: variant_def['builder'] = builder
    if bucket: variant_def['bucket'] = bucket
    if device_os: variant_def['device_os'] = device_os
    if device_type: variant_def['device_type'] = device_type
    if os: variant_def['os'] = os
    if test_suite: variant_def['test_suite'] = test_suite

    predicate = {}
    if variant_def:
        predicate['variantPredicate'] = {'contains': {'def': variant_def}}

    payload = {
        'project': project,
        'testId': test_id,
        'predicate': predicate,
    }
    if limit:
        payload['pageSize'] = int(limit)

    result = run_prpc('analysis.api.luci.app',
                      'luci.analysis.v1.TestHistory.Query', payload)
    if not result or 'verdicts' not in result:
        return []
    return result['verdicts']


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')

    # resolve-build-id
    p = subparsers.add_parser('resolve-build-id')
    p.add_argument('--project', default='chromium')
    p.add_argument('--bucket', default='ci')
    p.add_argument('--builder', required=True)
    p.add_argument('--build-number', required=True)

    # get-build
    p = subparsers.add_parser('get-build')
    p.add_argument('--build-id', required=True)

    # find-cl-builds
    p = subparsers.add_parser('find-cl-builds')
    p.add_argument('--cl', required=True)
    p.add_argument('--patchset')
    p.add_argument('--host', default='chromium-review.googlesource.com')
    p.add_argument('--all',
                   action='store_true',
                   help='Show all builds, not just failures')

    # list-failures
    p = subparsers.add_parser('list-failures')
    p.add_argument('--build-id', required=True)
    p.add_argument('--limit', type=int, default=None)

    # fetch-log
    p = subparsers.add_parser('fetch-log')
    p.add_argument('--res', required=True)
    p.add_argument('--raw',
                   action='store_true',
                   help='Return full log without filtering')

    # check-test
    p = subparsers.add_parser('check-test')
    p.add_argument('--build-id', required=True)
    p.add_argument('--test-regex', required=True)

    # test-history
    p = subparsers.add_parser('test-history')
    p.add_argument('--project', default='chromium')
    p.add_argument('--test-id', required=True)
    p.add_argument('--limit', type=int, default=10)
    p.add_argument('--builder')
    p.add_argument('--bucket')
    p.add_argument('--device-os')
    p.add_argument('--device-type')
    p.add_argument('--os')
    p.add_argument('--test-suite')

    args = parser.parse_args()

    if args.command == 'resolve-build-id':
        print(
            resolve_build_id(args.project, args.bucket, args.builder,
                             args.build_number))
    elif args.command == 'get-build':
        print(json.dumps(get_build(args.build_id), indent=2))
    elif args.command == 'find-cl-builds':
        print(
            json.dumps(find_cl_builds(args.cl, args.patchset, args.host,
                                      args.all),
                       indent=2))
    elif args.command == 'list-failures':
        print(json.dumps(list_failures(args.build_id, args.limit), indent=2))
    elif args.command == 'fetch-log':
        print(fetch_log_snippet(args.res, args.raw))
    elif args.command == 'check-test':
        print(json.dumps(check_test(args.build_id, args.test_regex), indent=2))
    elif args.command == 'test-history':
        verdicts = test_history(args.project,
                                args.test_id,
                                args.limit,
                                builder=args.builder,
                                bucket=args.bucket,
                                device_os=args.device_os,
                                device_type=args.device_type,
                                os=args.os,
                                test_suite=args.test_suite)
        print(json.dumps(verdicts, indent=2))


if __name__ == '__main__':
    main()

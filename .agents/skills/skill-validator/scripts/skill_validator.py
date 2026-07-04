#!/usr/bin/env vpython3
# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Validates SKILL.md files against the agentskills.io specification."""

import argparse
import os
import re
import sys
import yaml


def _parse_frontmatter(lines):
    """Parses YAML frontmatter from a list of lines.

    Returns (frontmatter_dict, error_string). On failure, frontmatter_dict
    is None and error_string describes the problem.
    """
    if not lines or lines[0] != '---':
        return None, 'Missing opening --- delimiter'

    # Find the closing --- delimiter.
    end = None
    for i in range(1, len(lines)):
        if lines[i] == '---':
            end = i
            break

    if end is None:
        return None, 'Missing closing --- delimiter'

    yaml_str = '\n'.join(lines[1:end])
    try:
        data = yaml.safe_load(yaml_str)
    except yaml.YAMLError as e:
        return None, f'Invalid YAML: {e}'

    if not isinstance(data, dict):
        return None, 'Frontmatter must be a YAML mapping'

    return data, None


# Pattern:
# 1. Lowercase alphanumeric and single hyphens only.
# 2. No leading or trailing hyphens.
# 3. No consecutive hyphens.
_NAME_RE = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')

# Table-driven type checks for optional fields.
_STRING_FIELDS = [
    'license', 'allowed-tools', 'argument-hint', 'model', 'context', 'agent'
]
_BOOL_FIELDS = ['user-invocable', 'disable-model-invocation']
_DICT_FIELDS = ['hooks']


def _validate_optional_fields(data):
    """Validates optional frontmatter fields. Returns list of warnings."""
    warnings = []

    # Table-driven type checks.
    for field in _STRING_FIELDS:
        value = data.get(field)
        if value is not None and not isinstance(value, str):
            warnings.append(f'{field} field must be a string, '
                            f'got {type(value).__name__}')

    for field in _BOOL_FIELDS:
        value = data.get(field)
        if value is not None and not isinstance(value, bool):
            warnings.append(f'{field} field must be a boolean (true/false), '
                            f'got {type(value).__name__}')

    for field in _DICT_FIELDS:
        value = data.get(field)
        if value is not None and not isinstance(value, dict):
            warnings.append(f'{field} field must be a dict, '
                            f'got {type(value).__name__}')

    # compatibility: string + max 500 chars.
    compatibility = data.get('compatibility')
    if compatibility is not None:
        if not isinstance(compatibility, str):
            warnings.append(f'compatibility field must be a string, '
                            f'got {type(compatibility).__name__}')
        elif len(compatibility) > 500:
            warnings.append(f'compatibility must be at most 500 chars, '
                            f'got {len(compatibility)}')

    # metadata: dict + all values must be strings.
    metadata = data.get('metadata')
    if metadata is not None:
        if not isinstance(metadata, dict):
            warnings.append(f'metadata field must be a dict, '
                            f'got {type(metadata).__name__}')
        else:
            for key, value in metadata.items():
                if not isinstance(key, str):
                    warnings.append(f'metadata keys must be strings, '
                                    f'got {type(key).__name__} for key {key!r}')
                    break
                if not isinstance(value, str):
                    warnings.append(
                        f'metadata values must be strings, '
                        f'got {type(value).__name__} for key "{key}"')
                    break

    # Deprecated field.
    if 'arguments' in data:
        warnings.append(
            'arguments field is deprecated, use argument-hint instead')

    return warnings


def _validate_name(name, dir_name):
    """Validates the skill name field. Returns list of error strings."""
    errors = []

    if not isinstance(name, str):
        return ['name field must be a string']

    if len(name) < 1 or len(name) > 64:
        errors.append(f'name must be 1-64 chars, got {len(name)}')

    if not _NAME_RE.match(name):
        errors.append('name must be lowercase alphanumeric and single hyphens '
                      'only (no leading/trailing hyphens)')

    if name != dir_name:
        errors.append(
            f'name "{name}" does not match directory name "{dir_name}"')

    return errors


def validate_skill(file_path):
    """Validates a single SKILL.md file.

    Returns (errors, warnings, info) where each is a list of strings.
    info contains passing details for display purposes.
    """
    errors = []
    warnings = []
    info = []

    dir_name = os.path.basename(os.path.dirname(file_path))

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except OSError as e:
        return [f'Could not read file: {e}'], [], []

    lines = content.splitlines()
    line_count = len(lines)

    if line_count > 500:
        errors.append(f'File has {line_count} lines (max 500). '
                      'Move content to references/ directory')

    # Parse frontmatter.
    data, parse_error = _parse_frontmatter(lines)
    if parse_error:
        return [f'Invalid YAML frontmatter: {parse_error}'], warnings, info

    info.append('Frontmatter is valid YAML')

    # Validate name.
    name = data.get('name')
    if name is None:
        errors.append(f"Missing required 'name' field. "
                      f"Add 'name: {dir_name}' to frontmatter")
    else:
        name_errors = _validate_name(name, dir_name)
        errors.extend(name_errors)
        if not name_errors:
            info.append(f'Skill name valid: {name}')
            info.append('name matches directory name')

    # Validate description.
    description = data.get('description')
    if description is None:
        errors.append("Missing required 'description' field. "
                      "Add a description explaining what the skill does")
    elif not isinstance(description, str):
        errors.append(f'description field must be a string, '
                      f'got {type(description).__name__}')
    else:
        desc_len = len(description)
        if desc_len < 1 or desc_len > 1024:
            errors.append(f'description must be 1-1024 chars, got {desc_len}')
        else:
            if desc_len < 20:
                warnings.append(f'description is short ({desc_len} chars, '
                                'consider adding more detail)')
            info.append(f'description field present ({desc_len} chars)')

    info.append(f'File length: {line_count} lines')

    # Validate optional fields (warnings only, don't block presubmit).
    warnings.extend(_validate_optional_fields(data))

    return errors, warnings, info


def _find_all_skills(skills_dir):
    """Finds all SKILL.md files under the given directory."""
    skill_files = []
    for entry in sorted(os.listdir(skills_dir)):
        skill_md = os.path.join(skills_dir, entry, 'SKILL.md')
        if os.path.isfile(skill_md):
            skill_files.append(skill_md)
    return skill_files


def main(argv):
    """Entrypoint for the validator script."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', nargs='*', help='SKILL.md files to validate.')
    parser.add_argument(
        '--all',
        metavar='DIR',
        help='Validate all SKILL.md files under the given directory.')
    args = parser.parse_args(argv[1:])

    if args.all:
        files = _find_all_skills(args.all)
    elif args.files:
        files = args.files
    else:
        parser.error('Provide SKILL.md file paths or use --all.')
        return 1

    total = 0
    passed = 0
    warned = 0
    failed = 0
    failed_details = []

    for file_path in files:
        total += 1
        skill_dir = os.path.dirname(file_path)
        print(f'\nValidating: {skill_dir}/')

        if not os.path.isfile(file_path):
            print('  [FAIL] SKILL.md does not exist')
            failed += 1
            failed_details.append((skill_dir, ['SKILL.md does not exist']))
            continue

        print('  [PASS] SKILL.md exists')

        file_errors, file_warnings, file_info = validate_skill(file_path)

        for w in file_warnings:
            print(f'  [WARN] {w}')
        for e in file_errors:
            print(f'  [FAIL] {e}')

        if file_errors:
            failed += 1
            failed_details.append((skill_dir, file_errors))
        elif file_warnings:
            warned += 1
        else:
            passed += 1

        # Print passing details when no errors.
        if not file_errors:
            for detail in file_info:
                print(f'  [PASS] {detail}')

    # Summary.
    print('\nSkill Validation Results')
    print('========================')
    print(f'\nSkills checked: {total}')
    print(f'  Passed: {passed}')
    print(f'  Warnings: {warned}')
    print(f'  Failed: {failed}')

    if failed_details:
        print('\nFailed skills:')
        for skill_dir, reasons in failed_details:
            reason_str = ', '.join(reasons)
            print(f'  - {skill_dir}: {reason_str}')

    if failed:
        print('\n[ISSUES FOUND]')
        return 1

    print('\n[READY TO COMMIT]')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

#!/usr/bin/env vpython3
# Copyright 2026 The Chromium Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Tests for skill_validator.py."""

import os
import tempfile
import unittest

from skill_validator import main
from skill_validator import _parse_frontmatter
from skill_validator import _validate_name
from skill_validator import _validate_optional_fields
from skill_validator import validate_skill


class ParseFrontmatterTest(unittest.TestCase):

    def test_valid_frontmatter(self):
        content = '---\nname: foo\ndescription: A test skill\n---\n# Hello'
        data, error = _parse_frontmatter(content.splitlines())
        self.assertIsNone(error)
        self.assertEqual(data['name'], 'foo')
        self.assertEqual(data['description'], 'A test skill')

    def test_missing_opening_delimiter(self):
        content = 'name: foo\n---\n'
        data, error = _parse_frontmatter(content.splitlines())
        self.assertIsNone(data)
        self.assertIn('Missing opening ---', error)

    def test_missing_closing_delimiter(self):
        content = '---\nname: foo\n'
        data, error = _parse_frontmatter(content.splitlines())
        self.assertIsNone(data)
        self.assertIn('Missing closing ---', error)

    def test_invalid_yaml(self):
        content = '---\n: bad:\n  yaml\n---\n'
        data, error = _parse_frontmatter(content.splitlines())
        self.assertIsNone(data)
        self.assertIn('Invalid YAML', error)

    def test_non_mapping_frontmatter(self):
        content = '---\n- a list\n- not a mapping\n---\n'
        data, error = _parse_frontmatter(content.splitlines())
        self.assertIsNone(data)
        self.assertIn('must be a YAML mapping', error)

    def test_value_can_contain_triple_dash(self):
        content = ('---\n'
                   'name: foo\n'
                   'description: "contains --- inside"\n'
                   '---\n'
                   '# Hello\n')
        data, error = _parse_frontmatter(content.splitlines())
        self.assertIsNone(error)
        self.assertEqual(data['description'], 'contains --- inside')


class ValidateNameTest(unittest.TestCase):

    def test_valid_name(self):
        self.assertEqual(_validate_name('fuzzing', 'fuzzing'), [])

    def test_valid_name_with_hyphens(self):
        self.assertEqual(_validate_name('skill-validator', 'skill-validator'),
                         [])

    def test_single_char_name(self):
        self.assertEqual(_validate_name('a', 'a'), [])

    def test_too_long_name(self):
        long_name = 'a' * 65
        errors = _validate_name(long_name, long_name)
        self.assertTrue(any('1-64 chars' in e for e in errors))

    def test_uppercase_name(self):
        errors = _validate_name('Fuzzing', 'Fuzzing')
        self.assertTrue(any('lowercase alphanumeric' in e for e in errors))

    def test_underscore_name(self):
        errors = _validate_name('my_skill', 'my_skill')
        self.assertTrue(any('lowercase alphanumeric' in e for e in errors))

    def test_consecutive_hyphens(self):
        errors = _validate_name('my--skill', 'my--skill')
        self.assertTrue(any('lowercase alphanumeric' in e for e in errors))

    def test_leading_hyphen(self):
        errors = _validate_name('-skill', '-skill')
        self.assertTrue(any('lowercase alphanumeric' in e for e in errors))

    def test_trailing_hyphen(self):
        errors = _validate_name('skill-', 'skill-')
        self.assertTrue(any('lowercase alphanumeric' in e for e in errors))

    def test_multi_segment_name(self):
        self.assertEqual(_validate_name('aa-b-c', 'aa-b-c'), [])

    def test_name_cannot_end_with_double_hyphen(self):
        errors = _validate_name('aa-b--', 'aa-b--')
        self.assertTrue(any('lowercase alphanumeric' in e for e in errors))

    def test_name_cannot_end_with_hyphen(self):
        errors = _validate_name('aa-b-', 'aa-b-')
        self.assertTrue(any('lowercase alphanumeric' in e for e in errors))

    def test_name_dir_mismatch(self):
        errors = _validate_name('foo', 'bar')
        self.assertTrue(any('does not match directory' in e for e in errors))

    def test_non_string_name(self):
        errors = _validate_name(123, 'foo')
        self.assertTrue(any('must be a string' in e for e in errors))


def _write_skill(tmpdir, dir_name, content):
    """Helper: creates <tmpdir>/<dir_name>/SKILL.md with content."""
    skill_dir = os.path.join(tmpdir, dir_name)
    os.makedirs(skill_dir, exist_ok=True)
    path = os.path.join(skill_dir, 'SKILL.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return path


class ValidateSkillTest(unittest.TestCase):

    def test_valid_skill(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _write_skill(
                tmpdir, 'my-skill', '---\nname: my-skill\n'
                'description: A valid test skill for testing.\n---\n'
                '# My Skill\n')
            errors, warnings, info = validate_skill(path)
            self.assertEqual(errors, [])
            self.assertEqual(warnings, [])
            self.assertTrue(any('Skill name valid' in i for i in info))

    def test_missing_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _write_skill(
                tmpdir, 'foo',
                '---\ndescription: Some description here.\n---\n')
            errors, _, _ = validate_skill(path)
            self.assertTrue(any("'name'" in e for e in errors))

    def test_missing_description(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _write_skill(tmpdir, 'foo', '---\nname: foo\n---\n')
            errors, _, _ = validate_skill(path)
            self.assertTrue(any("'description'" in e for e in errors))

    def test_description_too_long(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            long_desc = 'x' * 1025
            path = _write_skill(
                tmpdir, 'foo',
                f'---\nname: foo\ndescription: {long_desc}\n---\n')
            errors, _, _ = validate_skill(path)
            self.assertTrue(any('1-1024 chars' in e for e in errors))

    def test_short_description_warning(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _write_skill(tmpdir, 'foo',
                                '---\nname: foo\ndescription: Short.\n---\n')
            errors, warnings, _ = validate_skill(path)
            self.assertEqual(errors, [])
            self.assertTrue(any('short' in w for w in warnings))

    def test_file_over_500_lines_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            body = '\n'.join([f'Line {i}' for i in range(501)])
            path = _write_skill(
                tmpdir, 'foo', '---\nname: foo\n'
                'description: A long skill file for testing.\n---\n' + body +
                '\n')
            errors, warnings, _ = validate_skill(path)
            self.assertTrue(any('max 500' in e for e in errors))
            self.assertEqual(warnings, [])

    def test_invalid_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _write_skill(tmpdir, 'foo', 'no frontmatter here\n')
            errors, _, _ = validate_skill(path)
            self.assertTrue(any('frontmatter' in e for e in errors))

    def test_name_dir_mismatch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _write_skill(
                tmpdir, 'my-dir', '---\nname: wrong-name\n'
                'description: A test skill description.\n---\n')
            errors, _, _ = validate_skill(path)
            self.assertTrue(any('does not match directory' in e
                                for e in errors))

    def test_nonexistent_file(self):
        errors, _, _ = validate_skill('/nonexistent/path/SKILL.md')
        self.assertTrue(any('Could not read' in e for e in errors))


_VALID_FRONTMATTER = ('---\nname: {dir_name}\n'
                      'description: A valid test skill for testing.\n'
                      '{extra}'
                      '---\n')


class ValidateOptionalFieldsTest(unittest.TestCase):
    """Tests for optional field validation in validate_skill()."""

    def _validate(self, dir_name, extra_yaml):
        """Helper: write a SKILL.md with extra frontmatter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            content = _VALID_FRONTMATTER.format(dir_name=dir_name,
                                                extra=extra_yaml)
            path = _write_skill(tmpdir, dir_name, content)
            errors, warnings, _ = validate_skill(path)
            return errors, warnings

    # -- Happy path --

    def test_valid_optional_string_fields(self):
        extra = ('license: MIT\n'
                 'allowed-tools: Bash Read\n'
                 'argument-hint: "[issue-number]"\n'
                 'model: sonnet\n'
                 'context: fork\n'
                 'agent: plan\n')
        errors, warnings = self._validate('my-skill', extra)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_valid_optional_bool_fields(self):
        extra = ('user-invocable: false\n'
                 'disable-model-invocation: true\n')
        errors, warnings = self._validate('my-skill', extra)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_valid_optional_dict_fields(self):
        extra = 'hooks:\n  pre: echo hi\n'
        errors, warnings = self._validate('my-skill', extra)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_valid_compatibility(self):
        extra = 'compatibility: Works with Chrome 100+\n'
        errors, warnings = self._validate('my-skill', extra)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_valid_metadata(self):
        extra = 'metadata:\n  author: test\n  version: "1.0"\n'
        errors, warnings = self._validate('my-skill', extra)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_minimal_skill_no_optional_fields(self):
        errors, warnings = self._validate('my-skill', '')
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    # -- Type mismatches (warnings, not errors) --

    def test_string_field_type_warning(self):
        extra = 'license: 123\n'
        errors, warnings = self._validate('my-skill', extra)
        self.assertEqual(errors, [])
        self.assertTrue(
            any('license field must be a string' in w for w in warnings))

    def test_bool_field_type_warning(self):
        extra = 'user-invocable: "yes"\n'
        errors, warnings = self._validate('my-skill', extra)
        self.assertEqual(errors, [])
        self.assertTrue(
            any('user-invocable field must be a boolean' in w
                for w in warnings))

    def test_dict_field_type_warning(self):
        extra = 'hooks: not-a-dict\n'
        errors, warnings = self._validate('my-skill', extra)
        self.assertEqual(errors, [])
        self.assertTrue(any('hooks field must be a dict' in w
                            for w in warnings))

    # -- Special cases (warnings, not errors) --

    def test_compatibility_too_long(self):
        long_compat = 'x' * 501
        extra = f'compatibility: {long_compat}\n'
        errors, warnings = self._validate('my-skill', extra)
        self.assertEqual(errors, [])
        self.assertTrue(any('500 chars' in w for w in warnings))

    def test_compatibility_type_warning(self):
        extra = 'compatibility: 42\n'
        errors, warnings = self._validate('my-skill', extra)
        self.assertEqual(errors, [])
        self.assertTrue(
            any('compatibility field must be a string' in w for w in warnings))

    def test_metadata_non_string_values(self):
        extra = 'metadata:\n  count: 42\n'
        errors, warnings = self._validate('my-skill', extra)
        self.assertEqual(errors, [])
        self.assertTrue(
            any('metadata values must be strings' in w for w in warnings))

    def test_metadata_non_string_key(self):
        extra = 'metadata:\n  123: value\n'
        errors, warnings = self._validate('my-skill', extra)
        self.assertEqual(errors, [])
        self.assertTrue(
            any('metadata keys must be strings' in w for w in warnings))

    def test_metadata_type_warning(self):
        extra = 'metadata: not-a-dict\n'
        errors, warnings = self._validate('my-skill', extra)
        self.assertEqual(errors, [])
        self.assertTrue(
            any('metadata field must be a dict' in w for w in warnings))

    def test_deprecated_arguments_warning(self):
        extra = 'arguments:\n  - name: foo\n'
        errors, warnings = self._validate('my-skill', extra)
        self.assertEqual(errors, [])
        self.assertTrue(
            any('arguments field is deprecated' in w for w in warnings))


class ValidateOptionalFieldsDirectTest(unittest.TestCase):
    """Direct unit tests for _validate_optional_fields()."""

    def test_empty_data(self):
        self.assertEqual(_validate_optional_fields({}), [])

    def test_valid_fields(self):
        data = {
            'license': 'MIT',
            'user-invocable': True,
            'hooks': {
                'pre': 'echo hi'
            },
            'compatibility': 'Chrome 100+',
            'metadata': {
                'author': 'test'
            },
        }
        self.assertEqual(_validate_optional_fields(data), [])

    def test_string_field_wrong_type(self):
        warnings = _validate_optional_fields({'license': 123})
        self.assertEqual(len(warnings), 1)
        self.assertIn('license', warnings[0])
        self.assertIn('int', warnings[0])

    def test_bool_field_wrong_type(self):
        warnings = _validate_optional_fields({'user-invocable': 'yes'})
        self.assertEqual(len(warnings), 1)
        self.assertIn('user-invocable', warnings[0])
        self.assertIn('str', warnings[0])

    def test_dict_field_wrong_type(self):
        warnings = _validate_optional_fields({'hooks': 42})
        self.assertEqual(len(warnings), 1)
        self.assertIn('hooks', warnings[0])
        self.assertIn('int', warnings[0])

    def test_multiple_bad_fields(self):
        data = {
            'license': 123,
            'user-invocable': 'yes',
            'hooks': 42,
        }
        warnings = _validate_optional_fields(data)
        self.assertEqual(len(warnings), 3)

    def test_deprecated_arguments(self):
        warnings = _validate_optional_fields({'arguments': [{'name': 'x'}]})
        self.assertEqual(len(warnings), 1)
        self.assertIn('deprecated', warnings[0])


class MainTest(unittest.TestCase):

    def test_all_requires_explicit_directory(self):
        with self.assertRaises(SystemExit):
            main(['skill_validator.py', '--all'])

    def test_all_accepts_explicit_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _write_skill(
                tmpdir, 'my-skill', '---\nname: my-skill\n'
                'description: A valid test skill for testing.\n---\n')
            self.assertEqual(main(['skill_validator.py', '--all', tmpdir]), 0)


if __name__ == '__main__':
    unittest.main()

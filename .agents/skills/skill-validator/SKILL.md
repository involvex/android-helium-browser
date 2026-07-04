---
name: skill-validator
description: Validate skill files specification. Run before committing to ensure SKILL.md files have correct format, required fields, and naming conventions.
argument-hint: "[directory or file path]"
---

# Skill Validator

Validate skill files against the [agentskills.io specification](https://agentskills.io/specification).

## Usage

```
/skill-validator
```

## Instructions

To validate all SKILL.md files under a directory:

```bash
agents/skills/skill-validator/scripts/skill_validator.py --all <directory>
```

To validate specific files:

```bash
agents/skills/skill-validator/scripts/skill_validator.py path/to/SKILL.md
```

Present the script output to the user. If there are failures, help the user
understand and fix the issues based on the error messages.

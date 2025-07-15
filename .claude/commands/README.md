# Claude Custom Commands

This directory contains custom slash commands for Claude Code that provide specialized functionality for this project.

## Available Commands

- `/refine-prompt` - Analyzes and improves existing prompts
- `/craft-prompt` - Creates new prompts from task descriptions
- `/commands-list` - Shows all available commands

## Command Structure

Each command file follows this template:

```markdown
# Command Name

## Usage
`/command-name <ARGUMENTS>`

## Context
- Description of inputs: $ARGUMENTS
- Additional context about when to use

## Your Role
Detailed description of what Claude should do when this command is invoked

## Output Format
Clear specification of what the command returns
```

## Creating New Commands

1. Create a new `.md` file in this directory
2. Follow the structure template above
3. Name the file to match the command (e.g., `analyze-code.md` for `/analyze-code`)
4. The command is immediately available in Claude

## Best Practices

- Keep commands focused on a single purpose
- Provide clear output format specifications
- Include examples when helpful
- Make commands reusable across sessions

## Project-Specific Notes

For this AWS Spot Deployer project, remember:
- All deployment changes require full teardown/recreate
- Never patch running instances
- Follow immutable infrastructure principles
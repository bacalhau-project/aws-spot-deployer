# Available Claude Commands

## Project-Specific Commands

### `/refine-prompt <PROMPT_TO_REFINE>`
Analyzes and improves an existing prompt using prompt engineering best practices.
- Identifies weaknesses in current prompts
- Provides refined version with clear structure
- Includes usage examples and variations

### `/craft-prompt <TASK_DESCRIPTION>`
Creates a new prompt from scratch based on your task description.
- Transforms vague requests into precision-engineered prompts
- Provides multiple versions (quick start, primary, advanced)
- Includes customization guide

## How to Use Commands

1. Type the command followed by your input
2. Claude will process according to the command's specialized role
3. Receive structured output optimized for that command's purpose

## Adding New Commands

To add a new command:
1. Create a new `.md` file in `.claude/commands/`
2. Follow the structure:
   - ## Usage
   - ## Context
   - ## Your Role
   - ## Output Format

Commands are automatically available after creation.

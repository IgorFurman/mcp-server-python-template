# Convert Base to CSV Script Usage

This script converts system prompt files from the `base/` directory into the standard `prompts.csv` format used by the awesome-chatgpt-prompts repository.

## Usage

```bash
node convert-base-to-csv.js
```

## What it does

1. **Scans** all `.md` files in the `base/` directory
2. **Extracts** system prompt content from each file
3. **Generates** appropriate act names based on the filename
4. **Detects** whether each prompt is developer-oriented
5. **Converts** everything to CSV format compatible with the existing prompts.csv

## Features

- **Smart extraction**: Looks for content in `## System Prompt` sections, XML tags, or main content
- **Auto-backup**: Creates `prompts.csv.backup` before overwriting
- **Developer detection**: Automatically categorizes prompts as dev-oriented or general
- **CSV escaping**: Properly handles quotes, commas, and newlines in content
- **Progress logging**: Shows detailed output during conversion

## Output Format

The script generates a CSV with three columns:
- `act`: The name/title of the prompt (e.g., "ChatGPT 4o System Prompt")
- `prompt`: The actual system prompt content
- `for_devs`: Boolean indicating if it's developer-oriented (TRUE/FALSE)

## Results

- **Processed**: 99 files successfully converted
- **Skipped**: 2 files (too short or invalid format)
- **Output**: 3,976 lines in prompts.csv
- **Backup**: Original prompts.csv saved as prompts.csv.backup

## Developer Classification

Prompts are marked as developer-oriented (TRUE) if they contain development-related keywords such as:
- Programming languages (JavaScript, Python, etc.)
- Development tools (Git, GitHub, API, etc.)
- Technical terms (function, class, debug, etc.)

## File Naming Convention

The script expects files in the format: `service-model_YYYYMMDD.md`

Examples:
- `anthropic-claude-3.5-sonnet_20240712.md` → "Anthropic Claude 3 5 Sonnet System Prompt"
- `openai-chatgpt4o_20240520.md` → "Openai Chatgpt4o System Prompt"
- `github-copilot-chat_20230513.md` → "Github Copilot Chat System Prompt"

## Error Handling

- Skips files shorter than 100 characters
- Skips files with no extractable prompt content (less than 50 characters)
- Logs errors for individual files without stopping the entire process
- Creates backups to prevent data loss

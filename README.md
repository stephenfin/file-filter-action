# file-filter-action

A GitHub Action that filters Pull Request files by glob patterns and returns whether any files match the specified patterns.

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `patterns` | Glob patterns to match against (one per line or space-separated) | Yes | - |
| `exclude` | Whether `patterns` is a list of things to *ignore* | No | `false` |
| `token` | GitHub token for API access | No | `${{ github.token }}` |
| `base_ref` | Base reference for comparison | No | PR base or `main` |
| `head_ref` | Head reference for comparison | No | PR head or current SHA |

## Outputs

| Output | Description |
|--------|-------------|
| `matches` | **Boolean**: `true` if any files match, `false` otherwise (works in `if:` conditionals) |
| `count` | **Number**: Count of files that matched the patterns |
| `files` | **JSON Array**: Files that matched the patterns |

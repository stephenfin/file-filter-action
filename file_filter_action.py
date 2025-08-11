#!/usr/bin/env python3

import fnmatch
import json
import os
import sys

import github


def parse_patterns(patterns_input: str) -> list[str]:
    """Parse glob patterns from newline- or space-separated string input."""
    if not patterns_input:
        return []

    patterns = [p.strip() for p in patterns_input.split() if p.strip()]

    if not patterns:
        raise ValueError('No valid patterns found in input')

    return patterns


def get_changed_files(
    github_client: github.Github,
    repo_name: str,
    base_ref: str | None = None,
    head_ref: str | None = None,
) -> list[str]:
    """Get list of changed files between base and head refs."""
    try:
        repo = github_client.get_repo(repo_name)

        # Try to get PR context first
        if 'GITHUB_EVENT_PATH' in os.environ:
            try:
                with open(os.environ['GITHUB_EVENT_PATH']) as f:
                    event_data = json.load(f)

                if 'pull_request' in event_data:
                    pr_number = event_data['pull_request']['number']
                    pr = repo.get_pull(pr_number)
                    files = pr.get_files()
                    return [f.filename for f in files]
            except (FileNotFoundError, KeyError, json.JSONDecodeError):
                pass

        # Fallback to comparing refs
        if not base_ref:
            base_ref = os.environ.get('GITHUB_BASE_REF', 'main')

        if not head_ref:
            head_ref = os.environ.get('GITHUB_HEAD_REF', os.environ.get('GITHUB_SHA'))

        if head_ref:
            comparison = repo.compare(base_ref, head_ref)
            return [f.filename for f in comparison.files]

        print('Warning: Could not determine changed files', file=sys.stderr)
        return []
    except github.GithubException as e:
        print(f'GitHub API error: {e}', file=sys.stderr)
        return []
    except Exception as e:
        print(f'Error getting changed files: {e}', file=sys.stderr)
        return []


def match_files(files: list[str], patterns: list[str]) -> list[str]:
    """Match files against glob patterns."""
    matches = []

    for file_path in files:
        for pattern in patterns:
            if fnmatch.fnmatch(file_path, pattern):
                matches.append(file_path)
                break

    return matches


def set_output(name: str, value: str) -> None:
    """Set GitHub Actions output."""
    if 'GITHUB_OUTPUT' in os.environ:
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write(f'{name}={value}\n')
    else:
        # Fallback for older runners
        print(f'::set-output name={name}::{value}')


def main() -> None:
    """Main function."""
    try:
        patterns_input = os.environ.get('INPUT_PATTERNS', '')
        token = os.environ.get('INPUT_TOKEN', os.environ.get('GITHUB_TOKEN', ''))
        base_ref = os.environ.get('INPUT_BASE_REF')
        head_ref = os.environ.get('INPUT_HEAD_REF')
        repo_name = os.environ.get('GITHUB_REPOSITORY', '')

        if not patterns_input:
            print('Error: No patterns provided', file=sys.stderr)
            sys.exit(1)

        if not token:
            print('Error: No GitHub token provided', file=sys.stderr)
            sys.exit(1)

        if not repo_name:
            print('Error: No repository name found', file=sys.stderr)
            sys.exit(1)

        patterns = parse_patterns(patterns_input)
        print(f'Parsed patterns: {patterns}')

        github_client = github.Github(token)
        changed_files = get_changed_files(github_client, repo_name, base_ref, head_ref)
        matched_files = match_files(changed_files, patterns)

        print(f'Matched files: {matched_files}')
        print(f'Has matches: {bool(matched_files)}')

        set_output('matches', 'true' if matched_files else 'false')
        set_output('count', str(len(matched_files)))
        set_output('files', json.dumps(matched_files))
        sys.exit(0)
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

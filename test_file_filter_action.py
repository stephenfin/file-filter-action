import json
import os
import tempfile
from unittest import mock

import pytest

import file_filter_action


def test_parse_patterns():
    """Test pattern parsing functionality."""
    patterns = file_filter_action.parse_patterns('*.py *.js *.md')
    assert patterns == ['*.py', '*.js', '*.md']

    patterns = file_filter_action.parse_patterns('')
    assert patterns == []

    patterns = file_filter_action.parse_patterns('*.py')
    assert patterns == ['*.py']

    with pytest.raises(ValueError):
        file_filter_action.parse_patterns('   ')


def test_file_matching():
    """Test file matching functionality."""
    files = [
        'src/main.py',
        'tests/test_main.py',
        'docs/README.md',
        'package.json',
        'src/components/Button.js',
    ]

    patterns = ['*.py', 'docs/**']
    matched_files = file_filter_action.match_files(files, patterns)

    assert 'src/main.py' in matched_files
    assert 'tests/test_main.py' in matched_files
    assert 'docs/README.md' in matched_files
    assert 'package.json' not in matched_files


def test_file_matching_no_matches():
    """Test file matching when no files match patterns."""
    files = ['package.json', 'yarn.lock', 'webpack.config.js']
    patterns = ['*.py', '*.md']

    matched_files = file_filter_action.match_files(files, patterns)

    assert matched_files == []


def test_file_matching_complex_patterns():
    """Test file matching with complex glob patterns."""
    files = [
        'src/backend/api/views.py',
        'src/frontend/components/Button.tsx',
        'tests/unit/test_api.py',
        'tests/integration/test_full_flow.py',
        'docs/api/endpoints.md',
    ]

    # Test nested directory patterns
    patterns = ['src/backend/**/*.py', 'tests/**/*.py']
    matched_files = file_filter_action.match_files(files, patterns)

    assert 'src/backend/api/views.py' in matched_files
    assert 'tests/unit/test_api.py' in matched_files
    assert 'tests/integration/test_full_flow.py' in matched_files
    assert 'src/frontend/components/Button.tsx' not in matched_files


def test_set_output_with_github_output(tmp_path):
    """Test set_output function with GITHUB_OUTPUT environment variable."""
    output_file = tmp_path / 'github_output'

    with mock.patch.dict(os.environ, {'GITHUB_OUTPUT': str(output_file)}):
        file_filter_action.set_output('test_key', 'test_value')
        file_filter_action.set_output('matches', 'true')

    content = output_file.read_text()
    assert 'test_key=test_value\n' in content
    assert 'matches=true\n' in content


def test_set_output_without_github_output(capsys):
    """Test set_output function without GITHUB_OUTPUT environment variable."""
    # Ensure GITHUB_OUTPUT is not set
    with mock.patch.dict(os.environ, {}, clear=True):
        file_filter_action.set_output('test_key', 'test_value')

    captured = capsys.readouterr()
    assert '::set-output name=test_key::test_value' in captured.out


@mock.patch('file_filter_action.github.Github')
def test_get_changed_files_pr_context(mock_github):
    """Test get_changed_files with PR context."""
    # Setup mocks
    mock_repo = mock.MagicMock()
    mock_pr = mock.MagicMock()
    mock_files = [
        mock.MagicMock(filename='src/main.py'),
        mock.MagicMock(filename='README.md'),
        mock.MagicMock(filename='package.json'),
    ]
    mock_pr.get_files.return_value = mock_files
    mock_repo.get_pull.return_value = mock_pr
    mock_github.return_value.get_repo.return_value = mock_repo

    # Create temporary event file
    event_data = {'pull_request': {'number': 123}}
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        json.dump(event_data, f)
        event_file = f.name

    try:
        with mock.patch.dict(os.environ, {'GITHUB_EVENT_PATH': event_file}):
            github_client = mock_github.return_value
            changed_files = file_filter_action.get_changed_files(
                github_client, 'test/repo'
            )

        assert changed_files == ['src/main.py', 'README.md', 'package.json']
        mock_repo.get_pull.assert_called_once_with(123)
    finally:
        os.unlink(event_file)


@mock.patch('file_filter_action.github.Github')
def test_get_changed_files_ref_comparison(mock_github):
    """Test get_changed_files with ref comparison fallback."""
    # Setup mocks
    mock_repo = mock.MagicMock()
    mock_comparison = mock.MagicMock()
    mock_files = [
        mock.MagicMock(filename='src/main.py'),
        mock.MagicMock(filename='tests/test_main.py'),
    ]
    mock_comparison.files = mock_files
    mock_repo.compare.return_value = mock_comparison
    mock_github.return_value.get_repo.return_value = mock_repo

    # Test without PR context
    with mock.patch.dict(os.environ, {'GITHUB_SHA': 'abc123'}, clear=True):
        github_client = mock_github.return_value
        changed_files = file_filter_action.get_changed_files(github_client, 'test/repo')

    assert changed_files == ['src/main.py', 'tests/test_main.py']
    mock_repo.compare.assert_called_once_with('main', 'abc123')


@mock.patch('file_filter_action.github.Github')
def test_main_function(mock_github, tmp_path):
    """Test main function with mocked GitHub API - integration test."""
    event_file = tmp_path / 'event'
    output_file = tmp_path / 'output'
    output_file.touch()

    with event_file.open('w') as f:
        json.dump({'pull_request': {'number': 123}}, f)

    mock_repo = mock.MagicMock()
    mock_pr = mock.MagicMock()
    mock_pr.get_files.return_value = [
        mock.MagicMock(filename='src/main.py'),
        mock.MagicMock(filename='README.md'),
        mock.MagicMock(filename='package.json'),
    ]
    mock_repo.get_pull.return_value = mock_pr
    mock_github.return_value.get_repo.return_value = mock_repo

    with mock.patch.dict(
        os.environ,
        {
            'INPUT_PATTERNS': '*.py *.md',
            'INPUT_TOKEN': 'fake_token',
            'GITHUB_REPOSITORY': 'test/repo',
            'GITHUB_OUTPUT': str(output_file),
            'GITHUB_EVENT_PATH': str(event_file),
        },
    ):
        with pytest.raises(SystemExit) as exc_info:
            file_filter_action.main()

    assert exc_info.value.code == 0

    with output_file.open() as f:
        output_content = f.read()
        assert 'matches=true' in output_content
        # src/main.py and README.md match *.py and *.md
        assert 'count=2' in output_content
        assert 'src/main.py' in output_content
        assert 'README.md' in output_content


@mock.patch('file_filter_action.github.Github')
def test_main_function_no_matches(mock_github, tmp_path):
    """Test main function when no files match patterns."""
    event_file = tmp_path / 'event'
    output_file = tmp_path / 'output'
    output_file.touch()

    with event_file.open('w') as f:
        json.dump({'pull_request': {'number': 123}}, f)

    mock_repo = mock.MagicMock()
    mock_pr = mock.MagicMock()
    mock_pr.get_files.return_value = [
        mock.MagicMock(filename='package.json'),
        mock.MagicMock(filename='yarn.lock'),
    ]
    mock_repo.get_pull.return_value = mock_pr
    mock_github.return_value.get_repo.return_value = mock_repo

    with mock.patch.dict(
        os.environ,
        {
            'INPUT_PATTERNS': '*.py',
            'INPUT_TOKEN': 'fake_token',
            'GITHUB_REPOSITORY': 'test/repo',
            'GITHUB_OUTPUT': str(output_file),
            'GITHUB_EVENT_PATH': str(event_file),
        },
    ):
        with pytest.raises(SystemExit) as exc_info:
            file_filter_action.main()

    assert exc_info.value.code == 0

    with output_file.open() as f:
        output_content = f.read()
        assert 'matches=false' in output_content
        assert 'count=0' in output_content
        assert 'files=[]' in output_content


@pytest.mark.parametrize(
    'missing_env',
    [
        'INPUT_PATTERNS',
        'INPUT_TOKEN',
        'GITHUB_REPOSITORY',
    ],
)
def test_main_function_missing_required_env(missing_env):
    """Test main function with missing required environment variables."""
    mock_env = {
        'INPUT_PATTERNS': '*.py',
        'INPUT_TOKEN': 'fake_token',
        'GITHUB_REPOSITORY': 'test/repo',
    }

    # Remove the specified environment variable
    del mock_env[missing_env]

    with mock.patch.dict(os.environ, mock_env, clear=True):
        with pytest.raises(SystemExit) as exc_info:
            file_filter_action.main()

        assert exc_info.value.code == 1

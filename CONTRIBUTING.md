# Contributing

## Welcome

Thank you for considering a contribution to Reviewable HTML Workbench. This project provides shared scripts and plugin packaging for generating reviewable HTML documents, previewing them locally, and processing review comments.

Contributions in English or Japanese are welcome.

## Development Setup

1. Clone the repository.

   ```bash
   git clone https://github.com/u-ichi/reviewable-html-workbench.git
   cd reviewable-html-workbench
   ```

2. Use Python 3.11 or newer.

   ```bash
   python3 --version
   ```

3. Install no external dependencies.

   The project is designed to run with the Python standard library for local development and tests.

## Running Tests

Run the full test suite before opening a pull request.

```bash
PYTHONPYCACHEPREFIX="$PWD/tmp/python-pycache" python3 -m unittest discover -s tests
```

## Plugin Validation

Validate plugin manifests and JSON syntax after changing plugin metadata.

```bash
claude plugins validate .
python3 -m json.tool .claude-plugin/plugin.json >/dev/null
python3 -m json.tool .codex-plugin/plugin.json >/dev/null
```

## PR Guidelines

- Keep one commit to one logical change.
- Make sure tests pass before submitting.
- Include a clear summary, change list, and test plan.
- Japanese pull requests and comments are welcome.
- Do not commit secrets, credentials, API keys, or local environment files.

## Reporting Issues

Use GitHub Issues for bug reports, feature requests, and questions about expected behavior.

# Development

This section provides information for developers who want to contribute to the project.

## Setting Up the Development Environment

You can use `uv` to set up a virtual environment for development.

```console
uv sync --dev
```

## Running Tests

To run the test suite, use the following command:

```console
uv run pytest tests/
```

## Documentation

The documentation is built using MkDocs with the Material theme.

To build the documentation, execute the following command:

```console
uv run mkdocs build
```

Or to get live updates while editing the documentation:

```console
uv run mkdocs serve
```

This will start a development server at `http://127.0.0.1:8000` with automatic reload when you make changes to the documentation files.
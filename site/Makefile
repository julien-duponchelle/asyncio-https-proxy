# Minimal makefile for MkDocs documentation
#

# Default target
help:
	@echo "Available targets:"
	@echo "  build     - Build the documentation"
	@echo "  serve     - Serve the documentation with live reload"
	@echo "  clean     - Clean build artifacts"

.PHONY: help build serve clean

build:
	@cd .. && uv run mkdocs build

serve:
	@cd .. && uv run mkdocs serve

clean:
	@cd .. && rm -rf site


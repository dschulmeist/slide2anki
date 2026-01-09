# Contributing to slide2anki

Thank you for your interest in contributing to slide2anki! This document provides guidelines and information for contributors.

## Getting Started

1. Fork the repository
2. Clone your fork locally
3. Set up the development environment (see README.md)
4. Create a new branch for your work

## Development Setup

```bash
# Start infrastructure
./infra/scripts/dev.sh

# Or manually:
docker-compose -f infra/docker/docker-compose.yml up -d
cd apps/web && npm install && npm run dev
cd apps/api && uv pip install -e ".[dev]" && uvicorn app.main:app --reload
cd workers/runner && uv pip install -e ".[dev]" && python -m runner.worker
```

## Project Structure

- `apps/web/` - Next.js frontend
- `apps/api/` - FastAPI backend
- `packages/core/` - Core pipeline logic (LangGraph)
- `packages/shared/` - Shared OpenAPI specs
- `workers/runner/` - Background job worker
- `infra/` - Docker and deployment configs

## Code Style

### Python

- Use [Black](https://black.readthedocs.io/) for formatting
- Use [Ruff](https://docs.astral.sh/ruff/) for linting
- Type hints are required for all public functions
- Run `ruff check .` and `black .` before committing

### TypeScript

- Use [Prettier](https://prettier.io/) for formatting
- Use [ESLint](https://eslint.org/) for linting
- Run `npm run lint` and `npm run format` before committing

## Testing

```bash
# Python tests
cd packages/core && pytest
cd apps/api && pytest

# TypeScript tests
cd apps/web && npm test
```

All new features should include tests. Aim for meaningful test coverage rather than 100% line coverage.

## Pull Request Process

1. **Create an issue first** for significant changes to discuss the approach
2. **Keep PRs focused** - one feature or fix per PR
3. **Write clear commit messages** following conventional commits:
   - `feat: add card export to TSV`
   - `fix: handle empty slides gracefully`
   - `docs: update API documentation`
   - `refactor: simplify evidence cropping logic`
4. **Update documentation** if you change behavior
5. **Add tests** for new functionality
6. **Ensure CI passes** before requesting review

## Reporting Issues

When reporting bugs, please include:

- A clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Your environment (OS, Python version, Node version)
- Relevant logs or screenshots

## Feature Requests

We welcome feature requests! Please:

- Check existing issues first to avoid duplicates
- Describe the use case and expected behavior
- Explain why this would be valuable to users

## Architecture Decisions

When proposing significant changes, consider:

- Does it maintain the separation between core pipeline and web framework?
- Does it work fully locally without external dependencies?
- Does it preserve the evidence-based, traceable nature of cards?
- Does it maintain the human-in-the-loop review capability?

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## Questions?

Open a GitHub Discussion or Issue if you have questions about contributing.

Thank you for helping make slide2anki better!

# Contributing to CodeIntel

First off, thanks for considering contributing! CodeIntel is better because of people like you.

## Quick Start

```bash
# Fork the repo, then clone
git clone https://github.com/YOUR_USERNAME/codeintel-mcp
cd codeintel-mcp

# Set up backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Add your API keys to .env

# Set up frontend
cd ../frontend
npm install

# Run tests
cd ../backend
pytest tests/ -v
```

## How to Contribute

### Reporting Bugs
- Use the Bug Report template
- Include error logs and steps to reproduce
- Check existing issues first

### Suggesting Features
- Use the Feature Request template
- Explain the problem you're solving
- Consider implementation complexity

### Pull Requests

**Before submitting:**
1. Create an issue first (discuss approach)
2. Fork the repo and create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass: `pytest tests/ -v`
5. Follow existing code style

**PR Guidelines:**
- Keep changes focused (one feature/fix per PR)
- Write clear commit messages
- Update documentation if needed
- Add tests for new code

## Code Style

**Python (Backend):**
- Follow PEP 8
- Use type hints
- Max line length: 120 characters
- Run: `flake8 services/ --max-line-length=120`

**TypeScript (Frontend):**
- Use TypeScript strict mode
- Prefer functional components
- Use Tailwind for styling
- Run: `npm run build` to check for errors

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=services --cov-report=term-missing

# Run specific test
pytest tests/test_validation.py -v
```

**Test Requirements:**
- All new features need tests
- Security-critical code needs comprehensive tests
- Aim for >70% coverage on new code

## Project Structure

```
backend/
├── services/          # Core business logic
├── tests/            # Test suite
├── migrations/       # Database schemas
└── main.py          # FastAPI app

frontend/
├── src/components/   # React components
├── src/lib/         # Utilities
└── src/types.ts     # TypeScript types

mcp-server/          # MCP protocol implementation
```

## Development Workflow

1. **Pick an issue** - Comment that you're working on it
2. **Create branch** - `git checkout -b feature/your-feature`
3. **Make changes** - Write code + tests
4. **Test locally** - Ensure tests pass
5. **Commit** - Use conventional commits: `feat:`, `fix:`, `docs:`
6. **Push** - `git push origin feature/your-feature`
7. **Open PR** - Reference the issue number

## Areas We Need Help With

**High Priority:**
- [ ] Support for more languages (Go, Rust, Java)
- [ ] Performance optimizations for large repos
- [ ] Better error messages and logging
- [ ] Integration tests with test database

**Good First Issues:**
- [ ] Add more unit tests
- [ ] Improve documentation
- [ ] UI/UX improvements
- [ ] Add examples for different use cases

## Questions?

- Open a discussion on GitHub
- Check existing issues and PRs
- Read the docs in `/docs` folder

## Code of Conduct

Be respectful, constructive, and collaborative. We're all here to build something useful.

---

**Thanks for contributing! 🚀**

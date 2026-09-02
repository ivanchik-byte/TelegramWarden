# Contributing to TelegramWarden

Thank you for your interest in contributing to TelegramWarden. We welcome contributions ranging from bug fixes and test coverage improvements to new moderation heuristics and documentation updates.

Please take a few minutes to read through this guide before you start working on code.

## Code of conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please report any unacceptable behavior to the project maintainer.

## Getting started

### Prerequisites

Make sure your development machine has the following tools installed:

* Python 3.12 or higher
* Docker and Docker Compose (Compose V2 recommended)
* Git
* Node.js 18 or higher (only needed if you modify the `webapp/` frontend)

### Local environment setup

1. Fork the repository on GitHub and clone your fork:

   ```bash
   git clone https://github.com/<your-username>/TelegramWarden.git
   cd TelegramWarden
   ```

2. Create and activate a Python virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install project dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Create your local environment configuration:

   ```bash
   cp .env.example .env
   ```

   Open `.env` and fill in the minimum required development values:
   * `BOT_TOKEN`: Test bot token from [@BotFather](https://t.me/BotFather)
   * `ADMIN_ID`: Your numeric Telegram user ID
   * `DATABASE_URL`: PostgreSQL connection string (defaults to local docker instance)
   * `REDIS_URL` and `REDIS_PASSWORD`: Redis credentials (matches `docker-compose.yml`)
   * `DEEPSEEK_API_KEY` or `GROQ_API_KEY`: API key for LLM moderation tests (optional for offline unit tests)

5. Start the background database and cache services using Docker Compose:

   ```bash
   docker compose up -d postgres redis
   ```

6. Apply database schema migrations:

   ```bash
   alembic upgrade head
   ```

7. Optional: Build the frontend (if you are working on the Telegram Mini App dashboard):

   ```bash
   cd webapp
   npm install
   npm run build
   cd ..
   ```

## Development workflow

### Branch naming conventions

Create a focused feature branch from `main` using standard prefixes:

* `feat/feature-name` for new features or moderation checks
* `fix/bug-description` for bug and regression fixes
* `docs/topic-name` for documentation improvements
* `refactor/scope` for structural code changes without behavior alterations
* `test/test-description` for adding or improving test coverage

Example:

```bash
git checkout -b feat/custom-rate-limiter
```

### Running tests

Always run the automated test suite before opening a pull request:

```bash
pytest
```

To run a specific test module or test function:

```bash
pytest tests/test_risk_scorer.py
pytest tests/test_risk_scorer.py -k test_high_risk_keyword_detection
```

All 87 existing tests should pass cleanly without regressions.

### Code quality and style

* Write Python code following PEP 8.
* Provide explicit type annotations on function parameters and return types.
* Keep functions focused and modular.
* Ensure asynchronous database sessions and Redis locks are released properly in `finally` blocks or context managers.
* Avoid committing hardcoded secrets, temporary debug prints, or `.env` files.
* Write docstrings and code comments in English.

### Commit message format

We use the Conventional Commits format:

```text
<type>(<scope>): <short description in imperative mood>
```

Common types:

* `feat`: A new feature or rule
* `fix`: A bug fix
* `refactor`: Code refactoring without behavior change
* `docs`: Documentation updates
* `test`: Adding or correcting tests
* `chore`: Build scripts, dependencies, or maintenance tasks

Examples:

* `feat(gatekeeper): add sliding window detection for rapid bot joins`
* `fix(ai): prevent double punitive sanctions on media captions`
* `docs(contributing): clarify local database migration steps`

## Submitting a pull request

1. Push your changes to your fork on GitHub:

   ```bash
   git push origin feat/your-feature-name
   ```

2. Open a pull request against the `main` branch of `ivanchik-byte/TelegramWarden`.
3. Complete the pull request template, summarizing the problem solved, your approach, and your test verification.
4. Verify that automated GitHub Actions checks pass on your PR.
5. Respond to review comments constructively.

## Getting help

If you have questions about architecture, local setup, or design decisions:

* Open an issue with the `question` label.
* Reach out to the maintainer on Telegram: [@ivanchikbyte](https://t.me/ivanchikbyte).
* Join the project channel: [ivanchik_byte](https://t.me/ivanchik_byte).

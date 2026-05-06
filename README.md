# Peoples Gas Library

Standalone web client for Peoples Gas (peopleseaccount.com) using web scraping.

⚠️ **Disclaimer**: This library is not affiliated with or endorsed by Peoples Gas. Use may violate Peoples' Terms of Service prohibiting unauthorized automated portal access. Web scraping is fragile and may break if the portal's HTML changes.

## Development

Enter a development shell with all dependencies:

```bash
nix develop
```

Run all tests:

```bash
pytest tests/ -v
```

## Testing

### Test Pattern

We follow a 4-step pattern for testing:

1. **Create integration test** - Write an integration test in `tests/integration/` that exercises the real code paths
1. **Record HTTP interactions** - Run with real credentials and `--record-mode=rewrite` to create VCR cassettes in `tests/fixtures/vcr/` (gitignored)
1. **Create unit tests from recordings** - Use the VCR recordings to create minimal fixtures in `tests/fixtures/` and write unit tests in `tests/unit/`
1. **Run unit tests** - Unit tests use mocked HTTP and minimal fixtures, no VCR needed

### Test Structure

- `tests/integration/` - Integration tests using pytest-recording for HTTP recording/replay
- `tests/unit/` - Unit tests using minimal fixtures derived from VCR recordings
- `tests/fixtures/` - Minimal HTML/JSON fixtures for unit tests (committed to repo)
- `tests/fixtures/vcr/` - VCR cassettes with full HTTP recordings (gitignored, local-only)

### Running Tests

```bash
# Run unit tests (no credentials needed)
python3 -m pytest tests/unit/ -v

# Run integration tests with recording (requires credentials)
export PEOPLES_GAS_USERNAME=your_username
export PEOPLES_GAS_PASSWORD=your_password
python3 -m pytest tests/integration/ -v --record-mode=rewrite
```

### Code Coverage

Run tests with coverage reporting:

```bash
pytest --cov
```

Coverage is configured to:

- Measure coverage for the `peoples_gas_lib` package
- Fail if coverage drops below 80%
- Show missing lines in terminal output

### Integration Testing with pytest-recording

The integration tests use [pytest-recording](https://github.com/kiwicom/pytest-recording) to record HTTP interactions on first run (with real credentials) and replay them on subsequent runs (without credentials).

**First run (records HTTP interactions):**

```bash
export PEOPLES_GAS_USERNAME=your_username
export PEOPLES_GAS_PASSWORD=your_password
pytest tests/integration/ -v --record-mode=rewrite
```

This creates cassettes in `tests/fixtures/vcr/` with recorded HTTP interactions. Sensitive data (usernames, passwords) is automatically sanitized.

**Subsequent runs (replays recorded interactions):**

```bash
pytest tests/integration/ -v
```

No credentials needed - pytest-recording replays the recorded HTTP responses.

## Mutation Testing

This project uses [fest](https://github.com/sakost/fest) for mutation testing — a Rust-powered tool that generates small changes (mutants) to the source code and checks whether the test suite catches them.

### Running Mutation Tests

```bash
# Install fest (if not already installed)
uv pip install fest-mutate

# Run mutation tests
fest run
```

### Configuration

Fest is configured via `fest.toml` in the project root:

- Sources: `peoples_gas_lib/**/*.py`
- Coverage-guided: only runs tests that cover the mutated line
- Parallel execution: uses all CPU cores
- Fail threshold: 80% mutation score

### Understanding Results

- **Killed**: mutants detected by tests (good)
- **Survived**: mutants not detected (review these tests)
- **Timeout**: mutant caused test to hang
- **Errors**: mutant caused test errors

Aim for a high mutation score — survived mutants reveal gaps that line coverage misses.

## ToS Warning

Peoples' Terms state: "Access or attempted access by unauthorized individuals may be subject to prosecution." Use at your own risk.

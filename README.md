# discotrade

A research instrument: an unattended daily loop that asks LLM workers for
price-based trading rules, tests them on data the workers never saw, charges
realistic costs, and reports only when a fixed alert rule fires. Every
trading decision is simulated; nothing here sends an order to a broker.

`SPEC.md` is the owner's specification, `DESIGN.md` the build specification.

## Use

    uv sync --extra dev
    uv run discotrade --help

Every subcommand takes `--state <dir>` (default `$DISCOTRADE_STATE`; a
directory inside this repository is refused), `--track <name>` (default
`hourly`), `--config <dir>` (default `config/`) and `--as-of <instant>`
(an ISO 8601 instant with a timezone; sets the clock). Exit status: 0
success, 1 failure, 2 usage error.

## Gates

    ./scripts/check          # the commit gate: ruff, tests (no gate, network or live), smoke
    ./scripts/gate M0        # a milestone gate; ./scripts/gate M0 G0.1 runs one item

Gate tests live in `tests/gates/test_g<m>_<n>_*.py` and carry the markers
`gate` and `gate_m<m>`. Under the gate a skipped test fails.

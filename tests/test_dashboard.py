"""The dashboard (DESIGN 15.5, 3, 16.1 step 7; SPEC 13, 14; owner decisions O-6,
O-14, O-16, O-18; decision 2026-10-17-m19 153; I-6, I-10, I-12, I-14).

The state is conftest's ``mixed_ran_template`` (two reference approaches admitted
2019-06-07, ``run-day`` over 2019-06-08..06-12 on ``test_mixed`` at the production
thresholds), copied under a pytest temporary directory. ``discotrade`` runs
in-process through ``discotrade.cli.main``; time comes only from ``--as-of``. A
changed threshold is written in a copied ``thresholds.toml`` under a temporary
directory, with a history entry for each change. The paper records of the
stage-3 money test are written by ``paper.write``, with every value written here.
No random draw is made beyond the synthetic sources' seeded ones (the fixture
records'). Every git this file runs is on local paths with
``GIT_ALLOW_PROTOCOL=file`` (decision 47).
"""

import contextlib
import io
import json
import math
import re
import shutil
from datetime import date

import pytest
from conftest import RAN_AS_OF, RAN_DAYS, copy_template

from discotrade import alerts, dashboard, journal, ledger, paper
from discotrade import state as state_mod
from discotrade.cli import REPO_ROOT, main
from discotrade.config import load_gates, load_thresholds

FIXTURE_CONFIG = REPO_ROOT / "tests" / "fixtures" / "config"
TRACK = "test_mixed"
D = RAN_DAYS[-1]
PAGE = f"dashboard/{TRACK}/index.html"
#: SPEC 13's panels in its order, by the headings decision 153 (b) names.
HEADINGS = ("Gates for the next stage", "Alert rules", "The combined paper portfolio",
            "Rank persistence", "The table", "The experiment ledger", "Health",
            "The history of threshold and configuration changes")
VIEWPORT = '<meta name="viewport" content="width=device-width, initial-scale=1">'
FORBIDDEN = ("<script", "<link", "http://", "https://", "@import", "url(", "src=", "href=")
MARK = re.compile(r'data-threshold="([^"]+)">([^<]*)<')


def git(repo, *args) -> str:
    """git on the local state directory through the state module's own runner
    (``GIT_ALLOW_PROTOCOL=file``, decision 47)."""
    return state_mod._git(repo, *args).stdout


def call(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            status = main(list(argv))
        except SystemExit as exc:
            status = exc.code
    return status, out.getvalue(), err.getvalue()


def files(root) -> dict[str, tuple[bytes, int]]:
    return {p.relative_to(root).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in sorted(root.rglob("*"))
            if p.is_file() and ".git" not in p.relative_to(root).parts}


def render(state, config, *extra, as_of=RAN_AS_OF):
    status, out, err = call("--state", str(state), "--config", str(config), "--track", TRACK,
                            "--as-of", as_of, "dashboard", *extra)
    assert status == 0, err
    return out


def marks(page) -> list[tuple[str, str]]:
    return MARK.findall(page)


@pytest.fixture(scope="module")
def config(tmp_path_factory):
    path = tmp_path_factory.mktemp("dbcfg") / "config"
    shutil.copytree(FIXTURE_CONFIG, path)
    shutil.copy(REPO_ROOT / "config" / "thresholds.toml", path / "thresholds.toml")
    return path


@pytest.fixture(scope="module")
def setup(config):
    return journal.Setup.load(config, TRACK)


@pytest.fixture(scope="module")
def ran(tmp_path_factory, mixed_ran_template):
    return copy_template(mixed_ran_template, tmp_path_factory.mktemp("dbran") / "state")


@pytest.fixture(scope="module")
def page(ran):
    return (ran / PAGE).read_text(encoding="utf-8")


# ------------------------------------------------------------------ the page (153 (a), (d))


def test_every_panel_is_present_by_its_heading_in_spec_13s_order(page):
    found = re.findall(r"<h2>([^<]*)</h2>", page)
    assert found == list(HEADINGS)


def test_no_forbidden_construct_appears(page):
    lowered = page.lower()
    assert [s for s in FORBIDDEN if s in lowered] == []
    assert "<style>" not in lowered          # inline styles only


def test_the_viewport_is_declared_and_the_page_names_d(page):
    assert page.count(VIEWPORT) == 1
    assert page.startswith("<!DOCTYPE html>\n")
    assert f"<title>discotrade {TRACK} {D.isoformat()}</title>" in page
    assert "<svg" in page                     # inline SVG charts


def test_two_renders_of_the_same_state_are_byte_identical(ran, config, page, tmp_path):
    a, b = tmp_path / "a.html", tmp_path / "b.html"
    assert render(ran, config, "--out", str(a)) == ""
    render(ran, config, "--out", str(b), as_of="2030-01-01T00:00:00+00:00")
    assert a.read_bytes() == b.read_bytes()
    assert a.read_text(encoding="utf-8") == page         # step 7's page of the same day
    assert render(ran, config) == page                   # to standard output


# ------------------------------------------------------------------ thresholds (153 (d))


def test_each_threshold_shown_equals_the_value_the_alert_code_reads(page, setup):
    shown = marks(page)
    assert shown
    for key, text in shown:
        kinds = [k for k, keys in alerts.THRESHOLD_KEYS.items() if key in keys]
        read = (alerts.in_force(setup, kinds[0])[key] if kinds else setup.thresholds[key])
        assert float(text) == float(read), key


def test_every_key_the_alert_code_reads_is_shown(page):
    shown = {key for key, _ in marks(page)}
    wanted = {key for keys in alerts.THRESHOLD_KEYS.values() for key in keys}
    assert wanted <= shown
    assert {"stage_gate.min_clean_days", "pool.fail_window", "budgets.worker_tokens_per_day",
            "budgets.coordinator_tokens_per_day"} <= shown


def changed_value(value):
    return value + 7 if isinstance(value, int) else value / 2


def rewrite(path, changes, when="2026-10-17"):
    """``path``'s thresholds with ``changes`` (``table.key`` -> value) written in their
    lines, and one ``[[history]]`` entry per change appended."""
    lines, table = [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        head = re.match(r"^\[([a-z_]+)\]\s*$", line)
        if head:
            table = head.group(1)
        pair = re.match(r"^([a-z_0-9]+) = ", line)
        if pair and f"{table}.{pair.group(1)}" in changes:
            line = f"{pair.group(1)} = {changes[f'{table}.{pair.group(1)}']!r}"
        lines.append(line)
    old = load_thresholds(path)
    for key, value in changes.items():
        lines += ["", "[[history]]", f'date = "{when}"', f'key = "{key}"',
                  f"old = {old[key]!r}", f"new = {value!r}",
                  f'reason = "test change of {key}"']
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_the_page_follows_a_changed_threshold(ran, config, page, tmp_path):
    copied = tmp_path / "config"
    shutil.copytree(config, copied)
    before = load_thresholds(copied / "thresholds.toml")
    keys = sorted({key for key, _ in marks(page)})
    changes = {key: changed_value(before[key]) for key in keys}
    rewrite(copied / "thresholds.toml", changes)
    after = load_thresholds(copied / "thresholds.toml")
    assert all(after[k] == v != before[k] for k, v in changes.items())
    followed = render(ran, copied)
    shown = marks(followed)
    assert {key for key, _ in shown} == set(keys)
    for key, text in shown:
        assert float(text) == float(after[key]) != float(before[key]), key
    for key in keys:
        assert f"test change of {key}" in followed          # the history panel


# ------------------------------------------------------------------ the gates panel (153 (b) 1)


def gate_value(page, name):
    m = re.search(rf'data-gate="{re.escape(name)}" data-exact="([^"]*)"', page)
    assert m, name
    return m.group(1)


def gate_verdict(page, name):
    m = re.search(rf'data-verdict="{re.escape(name)}">([^<]*)<', page)
    assert m, name
    return m.group(1)


def with_portfolios(state, track, clean_2x, plain_2x):
    """The stored paper records with every ``portfolio_clean`` row's ``net_2x`` set
    to ``clean_2x`` and every ``portfolio`` row's to ``plain_2x``."""
    records = paper.read(state, track).copy()
    records.loc[records["subject"] == paper.PORTFOLIO_CLEAN, "net_2x"] = clean_2x
    records.loc[records["subject"] == paper.PORTFOLIO, "net_2x"] = plain_2x
    paper.write(state, track, records)
    return records


@pytest.mark.parametrize("clean_2x, plain_2x, least, verdict", [
    (0.002, -0.003, 5, "pass"),
    (-0.002, 0.003, 5, "not yet"),
    (0.002, -0.003, 6, "not yet"),
])
def test_the_money_condition_reads_portfolio_clean_net_2x(ran, config, tmp_path, clean_2x,
                                                          plain_2x, least, verdict):
    state = copy_template(ran, tmp_path / "state")
    records = with_portfolios(state, TRACK, clean_2x, plain_2x)
    clean = records[records["subject"] == paper.PORTFOLIO_CLEAN]
    assert len(clean) == 5 and (records["subject"] == paper.PORTFOLIO).sum() == 5
    copied = tmp_path / "config"
    shutil.copytree(config, copied)
    rewrite(copied / "thresholds.toml", {"stage_gate.min_clean_days": least})
    got = render(state, copied)
    want = math.fsum(float(x) for x in clean["net_2x"])
    assert float(gate_value(got, "money")) == want
    assert gate_value(got, "money_days") == "5"
    assert gate_verdict(got, "money") == verdict
    assert dashboard.stage3_money(records) == {"sum": want, "days": 5}


def test_the_other_gate_conditions_come_from_the_alert_state_and_the_health_log(ran, page):
    held = json.loads((ran / "alerts" / TRACK / "state.json").read_text(encoding="utf-8"))
    group = held["alerts"][f"group_edge|{TRACK}"]
    assert gate_value(page, "group_edge") == ("-" if group["value"] is None
                                              else repr(group["value"]))
    assert gate_verdict(page, "group_edge") == ("pass" if group["active"] else "not yet")
    rank = held["alerts"][f"rank_persistence|{TRACK}"]
    assert gate_verdict(page, "rank_persistence") == ("pass" if rank["active"] else "not yet")
    log = (ran / "health" / f"{TRACK}.jsonl")
    events = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()] \
        if log.exists() else []
    count = sum(1 for e in events if e["kind"] == "journal_mismatch")
    assert gate_value(page, "journal_mismatch") == str(count)
    assert gate_verdict(page, "journal_mismatch") == ("pass" if count == 0 else "not yet")
    assert gate_verdict(page, "stage2_fills_match") == "not yet"
    assert gate_verdict(page, "tax_confirmed") == "not yet"


def test_the_owner_flags_are_read_from_gates_toml(tmp_path):
    held = load_gates(REPO_ROOT / "config")
    assert (held.stage2_fills_match, held.tax_confirmed) == (False, False)
    text = (REPO_ROOT / "config" / "gates.toml").read_text(encoding="utf-8")
    assert "SPEC" in text and "14" in text
    assert load_gates(tmp_path) == held                      # no file: neither is met
    (tmp_path / "gates.toml").write_text(
        "[stage3]\nstage2_fills_match = true\ntax_confirmed = false\n", encoding="utf-8")
    assert load_gates(tmp_path).stage2_fills_match is True
    (tmp_path / "gates.toml").write_text("[stage3]\nstage2_fills_match = 1\n",
                                         encoding="utf-8")
    with pytest.raises(ValueError):
        load_gates(tmp_path)


def test_an_owner_flag_set_true_shows_pass(ran, config, tmp_path):
    copied = tmp_path / "config"
    shutil.copytree(config, copied)
    (copied / "gates.toml").write_text(
        "[stage3]\nstage2_fills_match = false\ntax_confirmed = true\n", encoding="utf-8")
    got = render(ran, copied)
    assert gate_verdict(got, "tax_confirmed") == "pass"
    assert gate_verdict(got, "stage2_fills_match") == "not yet"


# ------------------------------------------------------------------ the other panels


def test_the_rank_panel_labels_the_net_and_gross_statistics_as_used_by_no_rule(page):
    section = page.split("<h2>Rank persistence</h2>", 1)[1].split("<h2>", 1)[0]
    assert "used by no rule or gate" in section
    assert "timing" in section and "net 1x" in section and "gross" in section


def test_the_table_panel_shows_table_json_rows_plain_and_adjusted_labelled(ran, page):
    held = json.loads((ran / "table" / TRACK / "table.json").read_text(encoding="utf-8"))
    section = page.split("<h2>The table</h2>", 1)[1].split("<h2>", 1)[0]
    assert section.count("<tr data-row=") == len(held["rows"])
    for row in held["rows"]:
        assert f'<tr data-row="{row["section"]}">' in section
    assert "adjusted_S (adjusted)" in section and "S (plain)" in section


def test_the_portfolio_panel_shows_the_static_exposure_as_plain_minus_adjusted(ran, setup):
    records = paper.read(ran, TRACK)
    part = dashboard.exposure_part(ran, setup, D, records)
    days = sorted(set(records[records["subject"] == paper.PORTFOLIO]["date"]))
    w = days[-int(setup.thresholds["alerts.group_days"]):]
    rows = records[(records["subject"] == paper.PORTFOLIO) & records["date"].isin(w)]
    assert part["plain"] == math.fsum(float(x) for x in rows["net_1x"])
    assert part["static"] == part["plain"] - part["adjusted"]
    assert part["days"] == len(w) == len(RAN_DAYS)
    assert sorted(part["position"]) == sorted(i.symbol for i in setup.instruments)


# ------------------------------------------------------------------ the day loop (153 (a))


def test_each_new_day_commits_its_page_naming_its_day(ran):
    log = git(ran, "log", "--format=%H %s").splitlines()
    shas = {line.split(" ", 1)[1]: line.split(" ", 1)[0] for line in log}
    for d in RAN_DAYS:
        sha = shas[f"run {TRACK} {d.isoformat()}"]
        assert PAGE in git(ran, "show", "--name-only", "--format=", sha).split()
        held = git(ran, "show", f"{sha}:{PAGE}")
        assert f"<title>discotrade {TRACK} {d.isoformat()}</title>" in held
    assert git(ran, "status", "--porcelain") == ""
    assert not (ran / "staging").exists()


def test_a_rerun_of_a_finished_day_writes_no_page(ran, config, tmp_path):
    state = copy_template(ran, tmp_path / "state")
    path = state / PAGE
    before, stat, head = files(state), path.stat(), git(state, "rev-parse", "HEAD")
    status, _, err = call("--state", str(state), "--config", str(config), "--track", TRACK,
                          "--as-of", RAN_AS_OF, "run-day", "--day", D.isoformat())
    assert status == 0, err
    after = path.stat()
    assert (after.st_ino, after.st_mtime_ns) == (stat.st_ino, stat.st_mtime_ns)
    assert files(state) == before and git(state, "rev-parse", "HEAD") == head


def test_the_command_writes_nothing_into_the_state_directory(ran, config, tmp_path):
    state = copy_template(ran, tmp_path / "state")
    before = files(state)
    render(state, config, "--out", str(tmp_path / "page.html"))
    assert files(state) == before
    status, _, err = call("--state", str(state), "--config", str(config), "--track", TRACK,
                          "dashboard", "--out", str(state / "page.html"))
    assert status == 2 and "state directory" in err
    assert files(state) == before


def test_a_state_with_no_journaled_day_has_no_page(tmp_path, config):
    state = tmp_path / "state"
    assert main(["init-state", "--state", str(state), "--as-of", RAN_AS_OF]) == 0
    status, out, err = call("--state", str(state), "--config", str(config), "--track", TRACK,
                            "dashboard")
    assert status == 1 and out == "" and "no journaled day" in err


def test_the_day_is_the_states_last_journaled_day(ran):
    assert dashboard.last_day(ran, TRACK) == D == date(2019, 6, 12)


# ------------------------------- the rank rule's p (decision 2026-10-18-m20 160)


T_CRIT_11 = 1.795884819               # the one-sided 5% critical value of t at 11 df


def own_t_sf(t, df, steps=4000):
    """The one-sided upper tail of Student's t at ``df`` degrees of freedom, by
    Simpson's rule on the density after ``x = sqrt(df) tan(theta)``."""
    c = math.gamma((df + 1) / 2) / (math.sqrt(df * math.pi) * math.gamma(df / 2))
    a, b = math.atan(t / math.sqrt(df)), math.pi / 2
    h = (b - a) / steps
    total = 0.0
    for k in range(steps + 1):
        w = 1 if k in (0, steps) else (4 if k % 2 else 2)
        total += w * math.cos(a + k * h) ** (df - 1)
    return c * math.sqrt(df) * total * h / 3


def with_rank_entry(state, entry):
    """The stored alert state with its ``rank_persistence`` entry replaced by ``entry``."""
    path = state / "alerts" / TRACK / "state.json"
    held = json.loads(path.read_text(encoding="utf-8"))
    held["alerts"][f"rank_persistence|{TRACK}"] = entry
    path.write_text(json.dumps(held, sort_keys=True, separators=(",", ":")) + "\n",
                    encoding="utf-8")


def gate_shown(page, name):
    m = re.search(rf'data-gate="{re.escape(name)}" data-exact="[^"]*">([^<]*)<', page)
    assert m, name
    return m.group(1)


def rank_alert_p(page):
    section = page.split("<h2>Alert rules</h2>", 1)[1].split("<h2>", 1)[0]
    section = section.split("<h3>rank_persistence</h3>", 1)[1].split("<h3>", 1)[0]
    m = re.search(r">p ([^<]*)<", section)
    assert m
    return m.group(1)


def test_the_page_shows_the_rank_rules_p_as_the_state_holds_it(ran, config, tmp_path):
    state = copy_template(ran, tmp_path / "state")
    mean, critical, held_p = 0.5, 0.25, 0.0123456789
    # The thresholds in force (12 blocks, level 0.05) would give another p from
    # the entry's value and threshold: t = t_crit * mean / critical.
    derived = own_t_sf(T_CRIT_11 * mean / critical, 11)
    assert abs(derived - held_p) > 0.005
    with_rank_entry(state, {"active": True, "since": D.isoformat(), "value": mean,
                            "threshold": critical, "p": held_p})
    got = render(state, config)
    assert gate_value(got, "rank_p") == repr(held_p)
    assert gate_shown(got, "rank_p") == f"{held_p:.6g}"
    assert rank_alert_p(got) == f"{held_p:.6g}"
    assert gate_value(got, "rank_persistence") == repr(mean)
    assert gate_verdict(got, "rank_persistence") == "pass"


def test_a_rank_entry_without_p_shows_a_dash_and_not_yet(ran, config, tmp_path):
    state = copy_template(ran, tmp_path / "state")
    with_rank_entry(state, {"active": True, "since": D.isoformat(), "value": 0.5,
                            "threshold": 0.25})
    got = render(state, config)
    assert gate_shown(got, "rank_p") == "—"
    assert rank_alert_p(got) == "—"
    assert gate_verdict(got, "rank_persistence") == "not yet"


def test_the_stored_rank_entry_holds_p_and_the_page_shows_it(ran, page):
    held = json.loads((ran / "alerts" / TRACK / "state.json").read_text(encoding="utf-8"))
    rank = held["alerts"][f"rank_persistence|{TRACK}"]
    assert "p" in rank
    assert gate_value(page, "rank_p") == ("-" if rank["p"] is None else repr(rank["p"]))


# ------------------------- the health panel's failures (decision 2026-10-18-m20 161)


FAIL_OUTCOMES = {"model-a": ["invalid:parse"] * 4 + ["trial", "provider_error", "duplicate",
                                                     "trial", "budget", "invalid:run", "trial",
                                                     "trial"],
                 "model-b": ["trial", "invalid:parse", "trial", "trial", "invalid:test",
                             "provider_error", "invalid:parse", "duplicate", "trial"]}


def failure_rows(page):
    section = page.split("<h2>Health</h2>", 1)[1].split("<h2>", 1)[0]
    cell = r'<td style="[^"]*">([^<]*)</td>'
    return {m.group(1): (int(m.group(2)), int(m.group(3)))
            for m in re.finditer(f"<tr>{cell}{cell}{cell}</tr>", section)
            if m.group(1) in FAIL_OUTCOMES}


def test_the_health_panel_counts_each_models_failures_over_pool_fail_window(
        ran, config, tmp_path):
    state = copy_template(ran, tmp_path / "state")
    rows, k = [], 0
    for model, outcomes in FAIL_OUTCOMES.items():
        for j, outcome in enumerate(outcomes):
            day = RAN_DAYS[min(j // 3, len(RAN_DAYS) - 1)]
            rows.append({"date": day.isoformat(), "call": f"c{k}", "attempt": 1,
                         "cell": "trend/short", "model": model, "outcome": outcome,
                         "response": None, "tokens_in": 0, "tokens_out": 0})
            k += 1
    rows.sort(key=lambda r: r["date"])
    ledger.append(state, TRACK, ledger.CALLS, rows)
    copied = tmp_path / "config"
    shutil.copytree(config, copied)
    window = 5
    assert load_thresholds(copied / "thresholds.toml")["pool.fail_window"] != window
    rewrite(copied / "thresholds.toml", {"pool.fail_window": window})
    got = failure_rows(render(state, copied))
    want = {}
    for model in FAIL_OUTCOMES:
        mine = [r["outcome"] for r in rows if r["model"] == model
                and (r["outcome"] in ("trial", "duplicate") or r["outcome"].startswith("invalid:"))]
        last = mine[-window:]
        want[model] = (len(last), sum(o.startswith("invalid:") for o in last))
    assert want == {"model-a": (5, 1), "model-b": (5, 2)}
    assert got == want

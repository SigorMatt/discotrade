"""The W profile, version ``p1`` (DESIGN 13.1, 4.1, 5.6, 6.2; decision 115 of
meta/decisions/decisions-2026-10-15-m14.md; I-1, I-3, I-9, I-12).

Every store here is synthetic, fetched from ``tests/fixtures/config/`` (the
synthetic sources' seeds are in their instrument records) at the instants
below, under a module-scoped temporary directory; the tests only read it.

- test_synth, day ``D`` 2019-07-15: W is 2019-06-11 to 2019-07-08 (it holds
  SYNA's roll of 2019-06-14 and the calendar's closure of 2019-07-03/04), T is
  2019-07-09 to 2019-07-15. The full store is ``conftest.synth_bars_template``
  (fetched at 2019-07-25T00:00Z); the W-only store is fetched at
  2019-07-08T21:00Z, the end of W's last trading day (17:00 New York).
- test_mixed, day ``D`` 2019-06-28: W is 2019-05-25 to 2019-06-21 (it holds
  SYNA's roll of 2019-06-14; SYNX is the proportional-fee, always-open
  instrument), T is 2019-06-22 to 2019-06-28. The full store is fetched at
  2019-07-10T00:00Z, the W-only store at 2019-06-22T00:00Z (SYNX is always
  open, so its trading day 2019-06-21 ends at midnight UTC).

The scaled store holds the full store's bars with the four prices multiplied by
``PRICE_SCALE`` and volume by ``VOLUME_SCALE``, and its roll records with the
gap multiplied by ``PRICE_SCALE``.

Every figure checked by value is computed here from the stored Parquet files
and roll records, with this file's own reading of W, of the trading date and of
the adjusted series, without calling ``discotrade.workers.profile``.
"""

from __future__ import annotations

import json
import math
import re
import tomllib
from datetime import date, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest
from conftest import FIXTURE_CONFIG, REPO_ROOT, SYNTH_DAY, copy_template
from error_texts import PATTERN, forbidden_words

from discotrade.bars.store import BarStore
from discotrade.cli import main
from discotrade.config import load_calendar, load_track_config
from discotrade.workers import profile as wp

SYNTH_W_ONLY_AS_OF = "2019-07-08T21:00:00+00:00"
MIXED_DAY = date(2019, 6, 28)
MIXED_FULL_AS_OF = "2019-07-10T00:00:00+00:00"
MIXED_W_ONLY_AS_OF = "2019-06-22T00:00:00+00:00"
PRICE_SCALE = 3.7
VOLUME_SCALE = 0.29
REL = 1e-9
TRACKS = ("test_synth", "test_mixed")
DAYS = {"test_synth": SYNTH_DAY, "test_mixed": MIXED_DAY}
#: The definitions of decision 115 checked by value, at the values it gives.
QUANTILES = {"q01": 0.01, "q05": 0.05, "q25": 0.25, "q50": 0.5, "q75": 0.75, "q95": 0.95,
             "q99": 0.99}


def _cli(*argv: str) -> None:
    assert main(list(argv)) == 0, argv


def _fetch(state: Path, config: Path, track: str, as_of: str) -> Path:
    _cli("--state", str(state), "--config", str(config), "--track", track, "--as-of", as_of,
         "bars", "fetch")
    return state


def _scaled(full: Path, dest: Path, track: str) -> Path:
    """A store holding ``full``'s bars of ``track`` with prices and volume scaled."""
    tc = load_track_config(FIXTURE_CONFIG, track)
    src = BarStore(full, track, tc.track.bar_seconds)
    out = BarStore(dest, track, tc.track.bar_seconds)
    far = pd.Timestamp("2100-01-01", tz="UTC")
    for symbol in tc.track.instruments:
        bars = src.read_range(symbol, pd.Timestamp("2000-01-01", tz="UTC"), far)
        for col in ("open", "high", "low", "close"):
            bars[col] = bars[col] * PRICE_SCALE
        bars["volume"] = bars["volume"] * VOLUME_SCALE
        out.append(symbol, bars, far)
        rolls = full / "rolls" / track / f"{symbol}.jsonl"
        if rolls.exists():
            lines = []
            for line in rolls.read_text(encoding="utf-8").splitlines():
                record = json.loads(line)
                record["gap"] = record["gap"] * PRICE_SCALE
                lines.append(json.dumps(record, sort_keys=True))
            target = dest / "rolls" / track / f"{symbol}.jsonl"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("".join(x + "\n" for x in lines), encoding="utf-8")
    return dest


@pytest.fixture(scope="module")
def config(tmp_path_factory):
    import shutil

    path = tmp_path_factory.mktemp("profile-cfg") / "config"
    shutil.copytree(FIXTURE_CONFIG, path)
    shutil.copy(REPO_ROOT / "config" / "thresholds.toml", path / "thresholds.toml")
    return path


@pytest.fixture(scope="module")
def stores(tmp_path_factory, config, synth_bars_template):
    """Per track: the full, the W-only and the scaled store."""
    root = tmp_path_factory.mktemp("profile-stores")
    synth_full = copy_template(synth_bars_template, root / "synth-full")
    mixed_full = _fetch(root / "mixed-full", config, "test_mixed", MIXED_FULL_AS_OF)
    return {
        "test_synth": {
            "full": synth_full,
            "w_only": _fetch(root / "synth-w", config, "test_synth", SYNTH_W_ONLY_AS_OF),
            "scaled": _scaled(synth_full, root / "synth-scaled", "test_synth"),
        },
        "test_mixed": {
            "full": mixed_full,
            "w_only": _fetch(root / "mixed-w", config, "test_mixed", MIXED_W_ONLY_AS_OF),
            "scaled": _scaled(mixed_full, root / "mixed-scaled", "test_mixed"),
        },
    }


def _setup(config: Path, track: str):
    tc = load_track_config(config, track)
    calendars = {i.calendar: load_calendar(config / "calendars" / f"{i.calendar}.toml")
                 for i in tc.instruments}
    return tc, calendars


def _profile(config: Path, state: Path, track: str, cell: tuple[str, str]) -> dict:
    tc, calendars = _setup(config, track)
    return wp.profile(state, tc.track, tc.instruments, calendars, DAYS[track], cell)


@pytest.fixture(scope="module")
def documents(config, stores):
    """Per track, per store kind, per cell: the profile document."""
    out: dict = {}
    for track in TRACKS:
        tc, _ = _setup(config, track)
        out[track] = {kind: {cell: _profile(config, state, track, cell)
                             for cell in tc.track.cells}
                      for kind, state in stores[track].items()}
    return out


# ------------------------------------------------------------------ by hand

def _record(path: Path) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8"))


class Hand:
    """W's bars of one instrument read by this file from the stored files."""

    def __init__(self, state: Path, track: str, symbol: str, day: date):
        rec = _record(FIXTURE_CONFIG / "tracks" / f"{track}.toml")
        inst = _record(FIXTURE_CONFIG / "instruments" / f"{symbol}.toml")
        cal = _record(FIXTURE_CONFIG / "calendars" / f"{inst['calendar']}.toml")
        t_first = day - timedelta(days=rec["t_days"] - 1)
        w_last = t_first - timedelta(days=1)
        w_first = w_last - timedelta(days=rec["w_days"] - 1)
        files = sorted((state / "bars" / track / symbol).glob("*.parquet"))
        bars = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
        bars = bars.sort_values("ts").reset_index(drop=True)
        ts = pd.to_datetime(bars["ts"], utc=True)
        if cal.get("always_open"):
            local = ts
            dates = [t.date() for t in ts]
        else:
            local = ts.dt.tz_convert(ZoneInfo(cal["tz"]))
            roll_h, roll_m = (int(x) for x in cal["day_rolls_at"].split(":"))
            dates = [t.date() + timedelta(days=1) if (t.hour, t.minute) >= (roll_h, roll_m)
                     else t.date() for t in local]
        trusted = pd.Timestamp(inst["trusted_from"], tz="UTC")
        keep = np.array([w_first <= d <= w_last for d in dates]) & (ts >= trusted).to_numpy()
        self.after_w = bool(np.array([d > w_last for d in dates]).any())
        self.before_w = bool(np.array([d < w_first for d in dates]).any())
        w = bars[keep].reset_index(drop=True)
        w_ts = ts[keep].reset_index(drop=True)
        self.contracts = w["contract"].to_numpy()
        offset = np.zeros(len(w))
        rolls = state / "rolls" / track / f"{symbol}.jsonl"
        self.rolls_inside = 0
        if rolls.exists():
            for line in rolls.read_text(encoding="utf-8").splitlines():
                r = json.loads(line)
                rts = pd.Timestamp(r["ts"])
                if rts <= w_ts.iloc[-1]:
                    offset[(w_ts < rts).to_numpy()] += r["gap"]
                    self.rolls_inside += int(rts > w_ts.iloc[0])
        self.close_raw = w["close"].to_numpy(dtype=float)
        self.close = self.close_raw + offset
        self.high = w["high"].to_numpy(dtype=float) + offset
        self.low = w["low"].to_numpy(dtype=float) + offset
        self.volume = w["volume"].to_numpy(dtype=float)
        self.hour = local[keep].dt.hour.to_numpy()
        self.weekday = local[keep].dt.weekday.to_numpy()
        self.r = (self.close[1:] - self.close[:-1]) / self.close_raw[:-1]
        self.r_hour = self.hour[1:]
        self.r_weekday = self.weekday[1:]


@pytest.fixture(scope="module")
def hands(stores):
    out = {}
    for track in TRACKS:
        rec = _record(FIXTURE_CONFIG / "tracks" / f"{track}.toml")
        for symbol in rec["instruments"]:
            out[track, symbol] = Hand(stores[track]["full"], track, symbol, DAYS[track])
    return out


def _corr(a: np.ndarray, b: np.ndarray) -> float:
    a, b = a - a.mean(), b - b.mean()
    return float((a * b).sum() / math.sqrt((a * a).sum() * (b * b).sum()))


def _rv(r: np.ndarray) -> np.ndarray:
    return np.array([np.std(r[i - 23:i + 1], ddof=1) for i in range(23, len(r))])


def _runs(flags) -> list[int]:
    runs, n = [], 0
    for f in list(flags) + [False]:
        if f:
            n += 1
        elif n:
            runs.append(n)
            n = 0
    return runs


def _close(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)


SYMBOLS = [("test_synth", "SYNA"), ("test_synth", "SYND"), ("test_mixed", "SYNA"),
           ("test_mixed", "SYNX")]


def _doc(documents, track, family):
    tc = load_track_config(FIXTURE_CONFIG, track)
    cell = next(c for c in tc.track.cells if c[0] == family)
    return documents[track]["full"][cell]


# ------------------------------------------------------------------ the gate of 115 (e)

def test_the_stores_are_what_the_tests_need(hands, stores, config):
    """W holds a roll of the rolling instrument, the full store holds bars before
    and after W, and the W-only store ends at W's last bar."""
    for track in TRACKS:
        assert hands[track, "SYNA"].rolls_inside == 1
        assert len(set(hands[track, "SYNA"].contracts)) == 2
        for symbol in _record(FIXTURE_CONFIG / "tracks" / f"{track}.toml")["instruments"]:
            full = hands[track, symbol]
            assert full.after_w and full.before_w
            w_only = Hand(stores[track]["w_only"], track, symbol, DAYS[track])
            assert not w_only.after_w
            assert np.array_equal(w_only.close, full.close)


@pytest.mark.parametrize("track", TRACKS)
def test_version_is_p1(documents, track):
    for doc in documents[track]["full"].values():
        assert doc["version"] == "p1" == wp.VERSION


@pytest.mark.parametrize("track", TRACKS)
def test_w_only_the_store_ending_at_w_gives_the_same_profile(documents, track):
    """I-3: T's and later bars in the store change nothing."""
    full, w_only = documents[track]["full"], documents[track]["w_only"]
    assert full.keys() == w_only.keys()
    for cell in full:
        assert json.dumps(full[cell], sort_keys=True) == json.dumps(w_only[cell], sort_keys=True)


def _same_to(a, b, path="") -> list[str]:
    if isinstance(a, dict):
        if not isinstance(b, dict) or a.keys() != b.keys():
            return [path]
        return [p for k in a for p in _same_to(a[k], b[k], f"{path}.{k}")]
    if isinstance(a, list):
        if not isinstance(b, list) or len(a) != len(b):
            return [path]
        return [p for i, (x, y) in enumerate(zip(a, b, strict=True))
                for p in _same_to(x, y, f"{path}[{i}]")]
    if isinstance(a, float) and isinstance(b, float):
        return [] if math.isclose(a, b, rel_tol=REL, abs_tol=0.0) else [path]
    return [] if a == b and type(a) is type(b) else [path]


@pytest.mark.parametrize("track", TRACKS)
def test_no_price_or_volume_unit(documents, track):
    """Prices times one constant and volumes times another: the same profile to
    a relative 1e-9."""
    full, scaled = documents[track]["full"], documents[track]["scaled"]
    for cell in full:
        assert _same_to(full[cell], scaled[cell]) == [], cell


@pytest.mark.parametrize("track", TRACKS)
def test_cells_of_one_family_agree_and_families_differ_only_in_the_cell_block(
        documents, track):
    docs = documents[track]["full"]
    tc = load_track_config(FIXTURE_CONFIG, track)
    families = tc.track.families
    assert len(tc.track.horizons) == 2
    for family in families:
        same = [docs[c] for c in tc.track.cells if c[0] == family]
        assert len(same) == 2 and same[0] == same[1]
    firsts = [docs[next(c for c in tc.track.cells if c[0] == f)] for f in families]
    for i, a in enumerate(firsts):
        for b in firsts[i + 1:]:
            assert {k: v for k, v in a.items() if k != "cell"} == \
                   {k: v for k, v in b.items() if k != "cell"}
            assert a["cell"] != b["cell"]
            assert a.keys() == b.keys()


def _strings(node, keys: list, values: list) -> None:
    if isinstance(node, dict):
        for k, v in node.items():
            keys.append(k)
            _strings(v, keys, values)
    elif isinstance(node, list):
        for v in node:
            _strings(v, keys, values)
    elif isinstance(node, str):
        values.append(node)


@pytest.mark.parametrize("track", TRACKS)
def test_no_date_timestamp_or_market_name(documents, stores, track):
    """No key or value holds a date, a timestamp, a venue or a contract; a
    symbol appears only where anonymization replaces it (item 116)."""
    symbols = load_track_config(FIXTURE_CONFIG, track).track.instruments
    words = forbidden_words(stores[track]["full"], track, symbols)
    for doc in documents[track]["full"].values():
        assert doc["instruments"] == list(symbols)
        assert list(doc["common"]) == list(symbols)
        assert list(doc["cell"]["instruments"]) == list(symbols)
        rest = {
            "version": doc["version"],
            "common": list(doc["common"].values()),
            "cell": {k: (list(v.values()) if k == "instruments" else v)
                     for k, v in doc["cell"].items()},
        }
        assert set(doc) == {"version", "instruments", "common", "cell"}
        keys: list = []
        values: list = []
        _strings(rest, keys, values)
        for text in keys + values:
            assert not PATTERN.search(text), text
            assert not [w for w in words if re.search(rf"(?<![A-Za-z0-9]){re.escape(w)}"
                                                      rf"(?![A-Za-z0-9])", text)], text
        assert values == [doc["version"], doc["cell"]["family"]]


# ------------------------------------------------------------------ figures by hand

@pytest.mark.parametrize("track,symbol", SYMBOLS)
def test_common_block_figures(documents, hands, track, symbol):
    h = hands[track, symbol]
    r = h.r
    c = _doc(documents, track, "trend")["common"][symbol]
    ret = c["returns"]
    assert ret["count"] == len(h.close) - 1 == len(r)
    assert _close(ret["mean_bp"], r.mean() * 1e4)
    assert _close(ret["std_bp"], np.std(r, ddof=1) * 1e4)
    for key, q in QUANTILES.items():
        assert _close(ret["quantiles_bp"][key], np.quantile(r, q) * 1e4)
    d = r - r.mean()
    m2, m3, m4 = (d ** 2).mean(), (d ** 3).mean(), (d ** 4).mean()
    assert _close(ret["skewness"], m3 / m2 ** 1.5)
    assert _close(ret["excess_kurtosis"], m4 / m2 ** 2 - 3)
    for hr in (0, 15, 23):
        sel = r[h.r_hour == hr]
        assert c["std_by_hour"]["count"][hr] == len(sel)
        assert _close(c["std_by_hour"]["std_bp"][hr], np.std(sel, ddof=1) * 1e4)
    for wd in range(7):
        sel = r[h.r_weekday == wd]
        assert c["std_by_weekday"]["count"][wd] == len(sel)
        if len(sel) >= 2:
            assert _close(c["std_by_weekday"]["std_bp"][wd], np.std(sel, ddof=1) * 1e4)
        else:
            assert c["std_by_weekday"]["std_bp"][wd] is None
    ac = c["autocorrelation"]
    assert len(ac["value"]) == len(ac["count"]) == 48
    for lag in (1, 2, 24, 48):
        assert ac["count"][lag - 1] == len(r) - lag
        assert _close(ac["value"][lag - 1], _corr(r[:-lag], r[lag:]))
    vs = c["volume_share_by_hour"]
    for hr in (3, 15):
        assert _close(vs["share"][hr], h.volume[h.hour == hr].sum() / h.volume.sum())
        assert vs["count"][hr] == int((h.hour == hr).sum())
    assert _close(sum(vs["share"]), 1.0)
    rv = _rv(r)
    hi, lo = rv > np.percentile(rv, 75), rv < np.percentile(rv, 25)
    reg = c["regimes"]
    assert reg["count"] == len(rv) == len(r) - 23
    for name, flags in (("high", hi), ("low", lo)):
        runs = _runs(flags)
        assert _close(reg[name]["share"], flags.mean())
        assert reg[name]["runs"] == len(runs)
        assert _close(reg[name]["mean_run"], float(np.mean(runs)))


@pytest.mark.parametrize("track,symbol", SYMBOLS)
def test_trend_block(documents, hands, track, symbol):
    r = hands[track, symbol].r
    block = _doc(documents, track, "trend")["cell"]["instruments"][symbol]
    for k in (6, 24, 48):
        sums = np.array([r[j * k:(j + 1) * k].sum() for j in range(len(r) // k)])
        a, b = sums[:-1], sums[1:]
        same = ((a > 0) & (b > 0)) | ((a < 0) & (b < 0))
        got = block[f"k{k}"]
        assert got["count"] == len(sums) - 1
        assert _close(got["same_sign_share"], same.mean())
        assert _close(got["autocorrelation"], _corr(a, b))


@pytest.mark.parametrize("track,symbol", SYMBOLS)
def test_mean_reversion_block(documents, hands, track, symbol):
    r = hands[track, symbol].r
    block = _doc(documents, track, "mean_reversion")["cell"]["instruments"][symbol]
    dev = np.std(r, ddof=1)
    events = [i for i in range(len(r)) if abs(r[i]) > 2 * dev]
    assert block["events"] == len(events) > 0
    for k in (1, 6, 24):
        kept = [i for i in events if i + k <= len(r) - 1]
        after = np.array([r[i + 1:i + 1 + k].sum() for i in kept])
        sign = np.sign(r[kept])
        got = block[f"k{k}"]
        assert got["count"] == len(kept)
        assert _close(got["opposite_share"], float(np.mean(after * sign < 0)))
        assert _close(got["mean_reversal_bp"], float(np.mean(-after * sign)) * 1e4)


@pytest.mark.parametrize("track,symbol", SYMBOLS)
def test_breakout_block(documents, hands, track, symbol):
    h = hands[track, symbol]
    c, r = h.close, h.r
    block = _doc(documents, track, "breakout")["cell"]["instruments"][symbol]
    for n in (24, 48):
        got = block[f"n{n}"]
        eligible = range(n, len(c))
        direction = {j: (1 if c[j] > c[j - n:j].max() else -1 if c[j] < c[j - n:j].min()
                         else 0) for j in eligible}
        outs = [j for j in eligible if direction[j]]
        assert got["eligible"] == len(eligible)
        assert _close(got["breakout_share"], len(outs) / len(eligible))
        for k in (1, 6, 24):
            kept = [j for j in outs if j + k <= len(c) - 1]
            follow = np.array([r[j:j + k].sum() * direction[j] for j in kept])
            assert got[f"k{k}"]["count"] == len(kept)
            assert _close(got[f"k{k}"]["follow_share"], float(np.mean(follow > 0)))
            assert _close(got[f"k{k}"]["mean_follow_bp"], float(np.mean(follow)) * 1e4)
        ranges = [(h.high[j - n + 1:j + 1].max() - h.low[j - n + 1:j + 1].min())
                  / h.close_raw[j] for j in range(n - 1, len(c))]
        assert got["range_count"] == len(ranges)
        assert _close(got["range_bp"], float(np.mean(ranges)) * 1e4)


@pytest.mark.parametrize("track,symbol", SYMBOLS)
def test_volatility_regime_block(documents, hands, track, symbol):
    r = hands[track, symbol].r
    block = _doc(documents, track, "volatility_regime")["cell"]["instruments"][symbol]
    rv = _rv(r)
    defined = r[23:]
    for name, flags in (("high", rv > np.percentile(rv, 75)),
                        ("low", rv < np.percentile(rv, 25))):
        sel = defined[flags]
        both = flags[:-1] & flags[1:]
        got = block[name]
        assert got["count"] == len(sel)
        assert _close(got["mean_bp"], sel.mean() * 1e4)
        assert _close(got["std_bp"], np.std(sel, ddof=1) * 1e4)
        assert got["pairs"] == int(both.sum())
        assert _close(got["autocorrelation"],
                      _corr(defined[:-1][both], defined[1:][both]))


@pytest.mark.parametrize("track,symbol", SYMBOLS)
def test_volume_block(documents, hands, track, symbol):
    h = hands[track, symbol]
    v, r = h.volume, h.r
    block = _doc(documents, track, "volume")["cell"]["instruments"][symbol]
    eligible = range(24, len(v))
    events = [j for j in eligible
              if v[j] > v[j - 24:j].mean() + 2 * np.std(v[j - 24:j], ddof=1)]
    assert block["eligible"] == len(eligible)
    assert block["events"] == len(events) > 0
    assert _close(block["event_share"], len(events) / len(eligible))
    nxt = [j for j in events if j <= len(v) - 2]
    assert block["ratio_count"] == len(nxt)
    assert _close(block["abs_return_ratio"],
                  float(np.mean(np.abs(r[nxt]))) / float(np.mean(np.abs(r))))
    for k in (1, 6):
        kept = [j for j in events if j + k <= len(v) - 1]
        follow = np.array([r[j:j + k].sum() * np.sign(r[j - 1]) for j in kept])
        got = block[f"k{k}"]
        assert got["count"] == len(kept)
        assert _close(got["follow_share"], float(np.mean(follow > 0)))
        assert _close(got["mean_follow_bp"], float(np.mean(follow)) * 1e4)


@pytest.mark.parametrize("track,symbol", SYMBOLS)
def test_time_of_day_block(documents, hands, track, symbol):
    h = hands[track, symbol]
    block = _doc(documents, track, "time_of_day")["cell"]["instruments"][symbol]
    for key, labels, n in (("by_hour", h.r_hour, 24), ("by_weekday", h.r_weekday, 7)):
        got = block[key]
        assert len(got["mean_bp"]) == len(got["positive_share"]) == len(got["count"]) == n
        for x in range(n):
            sel = h.r[labels == x]
            assert got["count"][x] == len(sel)
            if len(sel):
                assert _close(got["mean_bp"][x], sel.mean() * 1e4)
                assert _close(got["positive_share"][x], float(np.mean(sel > 0)))
            else:
                assert got["mean_bp"][x] is None and got["positive_share"][x] is None


def test_a_statistic_without_observations_is_null_beside_its_count(documents):
    """test_synth's W has no Saturday return: null beside a count of 0 (115 (d))."""
    c = _doc(documents, "test_synth", "trend")["common"]["SYNB"]
    assert c["std_by_weekday"]["count"][5] == 0
    assert c["std_by_weekday"]["std_bp"][5] is None


def test_the_document_is_json_ready(documents):
    for track in TRACKS:
        for doc in documents[track]["full"].values():
            text = json.dumps(doc, sort_keys=True, allow_nan=False)
            assert json.loads(text) == doc


def test_an_unknown_cell_is_refused(config, stores):
    with pytest.raises(wp.ProfileError):
        _profile(config, stores["test_synth"]["full"], "test_synth", ("trend", "long"))


@pytest.mark.parametrize("damage", ["file_removed", "record_names_another_contract"])
def test_a_contract_change_with_no_roll_record_is_refused(config, synth_bars_template,
                                                          tmp_path, damage):
    """REVIEW-14 note 4 (decision 119 (c)): a store built here from test_synth's bars
    fetched at ``SYNTH_AS_OF``, whose SYNA roll inside W (2019-06-14) has lost its
    record, is refused; the same store with the record intact is not."""
    state = copy_template(synth_bars_template, tmp_path / "state")
    cell = ("trend", "short")
    assert _profile(config, state, "test_synth", cell)["version"] == "p1"
    rolls = state / "rolls" / "test_synth" / "SYNA.jsonl"
    records = [json.loads(line) for line in rolls.read_text(encoding="utf-8").splitlines()]
    assert any(r["ts"].startswith("2019-06-14") for r in records), records
    if damage == "file_removed":
        rolls.unlink()
    else:
        for r in records:
            r["new"] = r["new"] + "Z"
        rolls.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in records),
                         encoding="utf-8")
    with pytest.raises(wp.ProfileError, match="no roll record"):
        _profile(config, state, "test_synth", cell)

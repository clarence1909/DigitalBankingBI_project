"""Applicants, the onboarding funnel and the mobile app event stream (source 1)."""

import numpy as np
import pandas as pd

from . import params as P
from .mess import CHANNEL_VARIANTS, DEVICE_OS_VARIANTS, pick_variants
from .timeutil import END_TS, MONTH_LABELS, N_MONTHS, SECOND, random_times_in_month, to_utc

FUNNEL_EVENTS = ["signup_started", "phone_verified", "id_scanned", "liveness_passed",
                 "ekyc_approved", "account_opened"]


def _app_version(rng, start_ts, os_):
    """App version in use, which moves on over time; 2.0 ships the guided eKYC flow."""
    month = start_ts.astype("datetime64[M]")
    version = np.where(month < np.datetime64("2025-02"), "1.0",
              np.where(month < np.datetime64("2025-08"), "1.1",
              np.where(month < np.datetime64("2026-02"), "1.4", "2.0")))
    patch = rng.integers(0, 4, size=len(start_ts)).astype(str)
    return np.char.add(np.char.add(version.astype(str), "."), patch)


def simulate_applicants(rng):
    """One row per applicant who started sign-up, with their journey through the funnel."""
    parts = []
    for m in range(N_MONTHS):
        t = m / (N_MONTHS - 1)
        label = MONTH_LABELS[m]
        for ch in P.CHANNELS:
            base = P.APPLICANTS_START[ch] + t * (P.APPLICANTS_END[ch] - P.APPLICANTS_START[ch])
            mult = P.SEASONALITY.get(label, 1.0) if ch != "organic" else P.ORGANIC_PROMO_LIFT.get(label, 1.0)
            n = rng.poisson(base * mult * rng.lognormal(0, 0.05))
            parts.append(pd.DataFrame({"channel": ch, "start_ts": random_times_in_month(rng, m, n)}))
    app = pd.concat(parts, ignore_index=True).sort_values("start_ts", kind="stable").reset_index(drop=True)
    n = len(app)
    app["applicant_id"] = [f"A{i:07d}" for i in range(1, n + 1)]
    start = app["start_ts"].to_numpy(dtype="datetime64[s]")
    start_d = start.astype("datetime64[D]")

    # eKYC flow: control until the A/B test, 50/50 during it, guided after rollout
    flow = np.full(n, "control", dtype=object)
    in_test = (start_d >= np.datetime64(P.AB_TEST_START)) & (start_d <= np.datetime64(P.AB_TEST_END))
    flow[in_test] = np.where(rng.random(in_test.sum()) < 0.5, "control", "guided")
    flow[start_d >= np.datetime64(P.GUIDED_ROLLOUT)] = "guided"
    app["ekyc_flow"] = flow
    app["in_ab_test"] = in_test
    app["device_os"] = np.where(rng.random(n) < 0.68, "android", "ios")
    app["app_version"] = _app_version(rng, start, app["device_os"].to_numpy())

    ch = app["channel"].to_numpy()
    p_phone = np.array([P.P_PHONE.get(c, P.P_PHONE["default"]) for c in ch])
    p_live = np.where(flow == "guided", P.P_LIVENESS["guided"], P.P_LIVENESS["control"])
    phone = rng.random(n) < p_phone
    idscan = phone & (rng.random(n) < P.P_ID_SCAN)
    live = idscan & (rng.random(n) < p_live)
    approved = live & (rng.random(n) < P.P_EKYC_APPROVED)
    rejected = live & ~approved
    opened = approved & (rng.random(n) < P.P_ACCOUNT_OPENED)

    # Timings between steps
    t_phone = start + (rng.exponential(90, n) + 15).astype(int) * SECOND
    resume = rng.random(n) < 0.10   # some applicants come back the next day for the ID scan
    t_id = t_phone + (rng.exponential(240, n) + 30).astype(int) * SECOND
    t_id[resume] += (rng.uniform(6, 30, resume.sum()) * 3600).astype(int) * SECOND
    guided = flow == "guided"
    fails = np.zeros(n, dtype=int)
    passers = live
    fails[passers] = rng.poisson(np.where(guided[passers], 0.35, 0.8))
    quitters = idscan & ~live
    fails[quitters] = 1 + rng.poisson(np.where(guided[quitters], 0.6, 1.0))
    gap = (rng.uniform(40, 150, n)).astype(int)
    t_live = t_id + (fails * gap + rng.uniform(30, 120, n).astype(int)) * SECOND
    manual = rng.random(n) < P.P_MANUAL_REVIEW
    review = np.where(manual, rng.uniform(2, 48, n) * 3600, rng.uniform(20, 120, n)).astype(int)
    t_decision = t_live + review * SECOND
    t_open = t_decision + rng.integers(5, 60, n) * SECOND

    app["phone_verified"] = phone
    app["id_scanned"] = idscan
    app["liveness_passed"] = live
    app["ekyc_approved"] = approved
    app["ekyc_rejected"] = rejected
    app["liveness_fails"] = fails
    app["t_phone"], app["t_id"], app["t_live"] = t_phone, t_id, t_live
    app["t_decision"], app["t_open"] = t_decision, t_open
    app["fail_gap_s"] = gap
    # An account only exists if it opened inside the data window
    app["account_opened"] = opened & (t_open <= END_TS)
    return app


def build_events(rng, app, customer_id_by_applicant):
    """The app event stream: one JSON object per funnel event, with real-world mess."""
    frames = []

    def add(mask, name, ts, props=None):
        idx = np.flatnonzero(mask)
        if len(idx) == 0:
            return
        df = pd.DataFrame({"i": idx, "event_name": name, "ts": np.asarray(ts)[idx]})
        if props is not None:
            for k, v in props.items():
                df[k] = np.asarray(v, dtype=object)[idx] if np.ndim(v) else v
        frames.append(df)

    n = len(app)
    everyone = np.ones(n, dtype=bool)
    add(everyone, "signup_started", app["start_ts"].to_numpy(dtype="datetime64[s]"))
    add(app["phone_verified"].to_numpy(), "phone_verified", app["t_phone"].to_numpy(dtype="datetime64[s]"))
    add(app["id_scanned"].to_numpy(), "id_scanned", app["t_id"].to_numpy(dtype="datetime64[s]"))

    # Failed liveness attempts, one event each
    fails = app["liveness_fails"].to_numpy()
    rep = np.repeat(np.arange(n), fails)
    attempt = np.concatenate([np.arange(1, k + 1) for k in fails[fails > 0]]) if fails.sum() else np.array([], int)
    t_id = app["t_id"].to_numpy(dtype="datetime64[s]")
    gap = app["fail_gap_s"].to_numpy()
    fail_ts = t_id[rep] + (attempt * gap[rep]) * SECOND
    reasons = rng.choice(["face_not_detected", "too_dark", "movement_not_detected", "glare_on_face"],
                         size=len(rep), p=[0.35, 0.25, 0.25, 0.15])
    frames.append(pd.DataFrame({"i": rep, "event_name": "liveness_failed", "ts": fail_ts,
                                "attempt": attempt.astype(object), "reason": reasons}))

    add(app["liveness_passed"].to_numpy(), "liveness_passed", app["t_live"].to_numpy(dtype="datetime64[s]"))
    add(app["ekyc_approved"].to_numpy(), "ekyc_approved", app["t_decision"].to_numpy(dtype="datetime64[s]"))
    rej_reason = rng.choice(["name_screening_hit", "id_mismatch", "document_expired"], size=n, p=[0.3, 0.5, 0.2])
    add(app["ekyc_rejected"].to_numpy(), "ekyc_rejected", app["t_decision"].to_numpy(dtype="datetime64[s]"),
        {"reason": rej_reason})
    cust = app["applicant_id"].map(customer_id_by_applicant).to_numpy(dtype=object)
    add(app["account_opened"].to_numpy(), "account_opened", app["t_open"].to_numpy(dtype="datetime64[s]"),
        {"customer_id": cust})

    ev = pd.concat(frames, ignore_index=True)
    ev = ev[ev["ts"] <= END_TS]
    ev = ev.sort_values(["ts", "i", "event_name"], kind="stable").reset_index(drop=True)
    m = len(ev)
    ev["event_id"] = [f"ev_{k:08d}" for k in range(1, m + 1)]

    i = ev["i"].to_numpy()
    ts = ev["ts"].to_numpy(dtype="datetime64[s]")
    delay = rng.exponential(3, m).astype(int)
    offline = rng.random(m) < 0.03
    delay[offline] = rng.integers(3600, 12 * 3600, offline.sum())
    received = ts + delay * SECOND

    # Mess 1: the older Android app logged local time with an offset instead of UTC
    os_ = app["device_os"].to_numpy()[i]
    ver = app["app_version"].to_numpy()[i]
    local_fmt = (os_ == "android") & np.char.startswith(ver.astype(str), "1.0")
    ts_utc = to_utc(ts)
    ts_str = np.where(local_fmt,
                      np.char.add(np.datetime_as_string(ts, unit="s"), "+08:00"),
                      np.char.add(np.datetime_as_string(ts_utc, unit="ms"), "Z"))
    received_str = np.char.add(np.datetime_as_string(to_utc(received), unit="ms"), "Z")

    # Mess 2: inconsistent channel and device labels from different SDK versions
    raw_channel = pick_variants(rng, app["channel"].to_numpy()[i], CHANNEL_VARIANTS)
    raw_os = pick_variants(rng, os_, DEVICE_OS_VARIANTS)

    # The experiment flag only exists once the A/B test started
    flow = app["ekyc_flow"].to_numpy()[i]
    has_flag = ts.astype("datetime64[D]") >= np.datetime64(P.AB_TEST_START)

    out = pd.DataFrame({
        "event_id": ev["event_id"],
        "event_name": ev["event_name"],
        "event_ts": ts_str,
        "received_at": received_str,
        "applicant_id": app["applicant_id"].to_numpy()[i],
        "channel": raw_channel,
        "device_os": raw_os,
        "app_version": ver,
        "ekyc_flow": np.where(has_flag, flow, None),
        "attempt": ev.get("attempt"),
        "reason": ev.get("reason"),
        "customer_id": ev.get("customer_id"),
        "_ts_myt": ts,
    })

    # Mess 3: about 1.5% of events are sent twice by the app's retry logic
    dup = rng.random(m) < 0.015
    dups = out[dup].copy()
    extra = rng.integers(1, 600, len(dups))
    dup_recv = to_utc(dups["_ts_myt"].to_numpy(dtype="datetime64[s]") + (delay[dup] + extra) * SECOND)
    dups["received_at"] = np.char.add(np.datetime_as_string(dup_recv, unit="ms"), "Z")
    out = pd.concat([out, dups], ignore_index=True)
    out = out.sort_values(["received_at", "event_id"], kind="stable").reset_index(drop=True)
    return out


def events_to_json_lines(events):
    """Serialise events as newline-delimited JSON with nested context and properties."""
    import json

    lines = []
    cols = ["event_id", "event_name", "event_ts", "received_at", "applicant_id", "channel",
            "device_os", "app_version", "ekyc_flow", "attempt", "reason", "customer_id"]
    arrays = [events[c].to_numpy(dtype=object) for c in cols]
    for (event_id, name, ts, recv, applicant, channel, os_, ver, flow, attempt, reason, cust) in zip(*arrays):
        props = {}
        if flow is not None and flow == flow:
            props["ekyc_flow"] = flow
        if attempt is not None and attempt == attempt:
            props["attempt"] = int(attempt)
        if reason is not None and reason == reason:
            props["reason"] = reason
        if cust is not None and cust == cust:
            props["customer_id"] = cust
        lines.append(json.dumps({
            "event_id": event_id, "event_name": name, "event_ts": ts, "received_at": recv,
            "applicant_id": applicant,
            "context": {"channel": channel, "device_os": os_, "app_version": ver},
            "properties": props,
        }, separators=(",", ":")))
    return lines

#!/usr/bin/env python3
"""AKF Telemetry Analyzer — Phase 2.3 Aggregation Scripts.

Three reports derived from telemetry/events.jsonl:

  A. retry-rate     — Signal A: first-attempt invalid rate + normalized retry
                      rate per enum value. Flags domains with >15% retry rate.
  B. candidates     — Rejected candidate distribution: absolute count +
                      unique document count per rejected value.
  C. convergence    — Convergence time per domain: mean attempts (converged
                      only) + non-convergence rate.
    D. ask-usage      — Tenant-level RAG usage: total asks, no-answer rate,
                                            retrieval-only/synthesis split, avg latency.

Usage:
    python scripts/analyze_telemetry.py                        # all reports
    python scripts/analyze_telemetry.py --report retry-rate
    python scripts/analyze_telemetry.py --report candidates
    python scripts/analyze_telemetry.py --report convergence
    python scripts/analyze_telemetry.py --report ask-usage
    python scripts/analyze_telemetry.py --input telemetry/events.jsonl
    python scripts/analyze_telemetry.py --flag-threshold 0.20  # custom threshold

ADR-001 v1.6 compliance:
    - Signal A and Signal B are kept separate (collapsing loses diagnostic resolution)
    - Normalized retry rate prevents popularity bias
    - Non-convergence rate never folded into mean attempts
    - Environmental control fields (model, temperature) included in output
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional


# ─── CONSTANTS ────────────────────────────────────────────────────────────────

DEFAULT_TELEMETRY_PATH = Path("telemetry/events.jsonl")
FLAG_THRESHOLD = 0.15  # domains with normalized retry rate > 15% flagged for review

GREEN  = "\033[0;32m"
YELLOW = "\033[1;33m"
RED    = "\033[0;31m"
BLUE   = "\033[0;34m"
BOLD   = "\033[1m"
NC     = "\033[0m"


# ─── LOADER ───────────────────────────────────────────────────────────────────

def load_events(path: Path) -> tuple[list[dict], list[dict], list[dict]]:
    """Load and split events into attempt and summary lists.

    Args:
        path: Path to JSONL telemetry file.

    Returns:
        Tuple of (attempt_events, summary_events, ask_events).

    Raises:
        SystemExit: If file not found or unreadable.
    """
    if not path.exists():
        print(f"{RED}❌ Telemetry file not found: {path}{NC}")
        print(f"   Run 'akf generate ...' first to produce telemetry data.")
        sys.exit(1)

    attempts, summaries, asks = [], [], []
    errors = 0

    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
            if event.get("event_type") == "generation_attempt":
                attempts.append(event)
            elif event.get("event_type") == "generation_summary":
                summaries.append(event)
            elif event.get("event_type") == "ask_query":
                asks.append(event)
        except json.JSONDecodeError:
            errors += 1
            print(f"{YELLOW}⚠  Line {i}: invalid JSON — skipped{NC}")

    if errors:
        print(f"{YELLOW}⚠  {errors} malformed line(s) skipped{NC}\n")

    return attempts, summaries, asks


# ─── REPORT A — Retry Rate ────────────────────────────────────────────────────

def report_retry_rate(
    attempts: list[dict],
    flag_threshold: float = FLAG_THRESHOLD,
) -> None:
    """Signal A: first-attempt invalid rate + normalized retry rate per enum value.

    Per ADR-001 v1.6:
      - Signal A = % of documents where attempt 1 violates enum constraints
      - Normalized rate = retry_count / usage_frequency (prevents popularity bias)
      - Domains with normalized rate > threshold flagged for boundary review
    """
    print(f"{BOLD}━━━ Report A — Retry Rate per Enum Value ━━━{NC}\n")

    if not attempts:
        print("  No attempt events found.\n")
        return

    # First-attempt events only (Signal A)
    first_attempts = [e for e in attempts if e.get("attempt") == 1]
    total_docs = len(first_attempts)

    if total_docs == 0:
        print("  No first-attempt events found.\n")
        return

    # Count per enum field/value: total uses and failed uses
    # usage[field][value] = total count
    # failures[field][value] = failed (converged=False) count
    usage: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    failures: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for evt in first_attempts:
        # Every first attempt is a "usage" of whatever value was tried
        # Extract field values from errors (received = attempted value)
        for error in evt.get("errors", []):
            field = error.get("field", "unknown")
            received = str(error.get("received", "unknown"))
            failures[field][received] += 1

    # For usage frequency: count total attempt-1 events per document
    # Use summary events for usage frequency (final committed domain)
    # Fallback: use attempt events where converged=True on attempt 1
    converged_first = [e for e in first_attempts if e.get("converged") is True]
    failed_first = [e for e in first_attempts if e.get("converged") is False]

    signal_a_rate = len(failed_first) / total_docs if total_docs else 0

    print(f"  Total documents (first attempts): {total_docs}")
    print(f"  Signal A — First-attempt invalid rate: "
          f"{_pct(signal_a_rate)}  "
          f"({len(failed_first)} failed / {total_docs} total)\n")

    # Per-field breakdown
    all_fields = sorted(set(failures.keys()))
    if not all_fields:
        print(f"  {GREEN}✅ No enum violations on first attempts.{NC}\n")
        return

    for field in all_fields:
        field_failures = failures[field]
        field_total = sum(field_failures.values())
        print(f"  {BOLD}Field: {field}{NC}  (total violations: {field_total})")

        # Sort by failure count descending
        for value, count in sorted(field_failures.items(), key=lambda x: -x[1]):
            # Normalized: failures for this value / total first-attempt events
            norm_rate = count / total_docs
            flag = (f"  {RED}⚑ REVIEW (>{int(flag_threshold*100)}%){NC}"
                    if norm_rate > flag_threshold else "")
            print(f"    {value:<30}  failures: {count:>4}  "
                  f"normalized rate: {_pct(norm_rate)}{flag}")
        print()


# ─── REPORT B — Rejected Candidates ──────────────────────────────────────────

def report_rejected_candidates(summaries: list[dict]) -> None:
    """Rejected candidate distribution from summary events.

    Per ADR-001 v1.6:
      - Threshold for governance action: high frequency across UNIQUE documents
      - Single-document outliers do not drive taxonomy decisions
      - Convergence outcome per rejected value shown
    """
    print(f"{BOLD}━━━ Report B — Rejected Candidate Distribution ━━━{NC}\n")

    if not summaries:
        print("  No summary events found.\n")
        return

    # candidate → {total_count, unique_doc_ids, converged_count, not_converged_count}
    stats: dict[str, dict] = defaultdict(lambda: {
        "total": 0,
        "docs": set(),
        "converged": 0,
        "not_converged": 0,
    })

    total_sessions = len(summaries)
    sessions_with_rejections = 0

    for evt in summaries:
        candidates = evt.get("rejected_candidates", [])
        if not candidates:
            continue
        sessions_with_rejections += 1
        doc_id = evt.get("document_id", "unknown")
        converged = evt.get("converged", False)

        for value in candidates:
            v = str(value)
            stats[v]["total"] += 1
            stats[v]["docs"].add(doc_id)
            if converged:
                stats[v]["converged"] += 1
            else:
                stats[v]["not_converged"] += 1

    print(f"  Total generation sessions: {total_sessions}")
    print(f"  Sessions with rejections:  {sessions_with_rejections}\n")

    if not stats:
        print(f"  {GREEN}✅ No rejected candidates found.{NC}\n")
        return

    # Sort by unique doc count descending (governance signal)
    sorted_candidates = sorted(
        stats.items(),
        key=lambda x: (-len(x[1]["docs"]), -x[1]["total"])
    )

    header = (f"  {'Value':<30}  {'Total':>6}  {'Unique docs':>11}  "
              f"{'Converged':>9}  {'Failed':>6}  Defect signal")
    print(header)
    print("  " + "─" * (len(header) - 2))

    for value, s in sorted_candidates:
        unique_docs = len(s["docs"])
        total = s["total"]
        conv = s["converged"]
        fail = s["not_converged"]

        # Defect signal heuristic (ADR-001 v1.6 diagnostic combinations)
        if unique_docs >= 3 and fail > conv:
            signal = f"{RED}missing category / boundary ambiguity{NC}"
        elif unique_docs >= 3 and conv >= fail:
            signal = f"{YELLOW}lexical misalignment{NC}"
        elif unique_docs == 1:
            signal = "outlier (1 doc)"
        else:
            signal = "monitor"

        print(f"  {value:<30}  {total:>6}  {unique_docs:>11}  "
              f"{conv:>9}  {fail:>6}  {signal}")

    print()


# ─── REPORT C — Convergence Time ─────────────────────────────────────────────

def report_convergence(summaries: list[dict]) -> None:
    """Convergence time per domain.

    Per ADR-001 v1.6:
      - Mean attempts computed on CONVERGED documents only
      - Non-convergence rate reported separately, never folded into mean
      - Pair (mean_attempts_converged + non_convergence_rate) is the signal
    """
    print(f"{BOLD}━━━ Report C — Convergence Time per Domain ━━━{NC}\n")

    if not summaries:
        print("  No summary events found.\n")
        return

    # domain → {attempts_list (converged only), non_converged_count, total}
    by_domain: dict[str, dict] = defaultdict(lambda: {
        "attempts": [],
        "non_converged": 0,
        "total": 0,
    })

    global_converged = []
    global_not_converged = 0

    for evt in summaries:
        domain = evt.get("final_domain") or "unknown"
        total_attempts = evt.get("total_attempts", 1)
        converged = evt.get("converged", False)

        by_domain[domain]["total"] += 1

        if converged:
            by_domain[domain]["attempts"].append(total_attempts)
            global_converged.append(total_attempts)
        else:
            by_domain[domain]["non_converged"] += 1
            global_not_converged += 1

    total_sessions = len(summaries)
    global_non_conv_rate = global_not_converged / total_sessions if total_sessions else 0
    global_mean = (sum(global_converged) / len(global_converged)
                   if global_converged else None)

    print(f"  Total sessions:         {total_sessions}")
    if global_mean is not None:
        print(f"  Global mean attempts:   {global_mean:.2f}  (converged only)")
    print(f"  Global non-convergence: {_pct(global_non_conv_rate)}  "
          f"({global_not_converged} failed)\n")

    if len(by_domain) <= 1:
        print("  Insufficient domain diversity for per-domain breakdown.\n")
        return

    # Sort by non-convergence rate descending
    sorted_domains = sorted(
        by_domain.items(),
        key=lambda x: (
            -(x[1]["non_converged"] / x[1]["total"] if x[1]["total"] else 0)
        )
    )

    header = (f"  {'Domain':<35}  {'Total':>6}  {'Mean attempts':>13}  "
              f"{'Non-conv rate':>13}  Status")
    print(header)
    print("  " + "─" * (len(header) - 2))

    for domain, s in sorted_domains:
        total = s["total"]
        attempts = s["attempts"]
        non_conv = s["non_converged"]
        non_conv_rate = non_conv / total if total else 0
        mean_att = sum(attempts) / len(attempts) if attempts else None
        mean_str = f"{mean_att:.2f}" if mean_att is not None else "n/a"

        if non_conv_rate > FLAG_THRESHOLD:
            status = f"{RED}⚑ HIGH FRICTION{NC}"
        elif non_conv_rate > 0:
            status = f"{YELLOW}monitor{NC}"
        else:
            status = f"{GREEN}ok{NC}"

        print(f"  {domain:<35}  {total:>6}  {mean_str:>13}  "
              f"{_pct(non_conv_rate):>13}  {status}")

    print()


# ─── REPORT D — Ask Usage (Tenant) ──────────────────────────────────────────

def report_ask_usage(asks: list[dict]) -> None:
    """Tenant-level usage report for RAG ask telemetry events."""
    print(f"{BOLD}━━━ Report D — Ask Usage by Tenant ━━━{NC}\n")

    if not asks:
        print("  No ask events found.\n")
        return

    # tenant -> counters
    by_tenant: dict[str, dict[str, float]] = defaultdict(lambda: {
        "total": 0,
        "insufficient": 0,
        "retrieval_only": 0,
        "synthesis": 0,
        "hits_sum": 0,
        "duration_sum": 0,
    })

    for evt in asks:
        tenant = str(evt.get("tenant_id", "default"))
        mode = str(evt.get("mode", "unknown"))
        insufficient = bool(evt.get("insufficient_context", False))
        hits_used = int(evt.get("hits_used", 0) or 0)
        duration_ms = int(evt.get("duration_ms", 0) or 0)

        by_tenant[tenant]["total"] += 1
        by_tenant[tenant]["hits_sum"] += hits_used
        by_tenant[tenant]["duration_sum"] += duration_ms
        if insufficient:
            by_tenant[tenant]["insufficient"] += 1
        if mode == "retrieval-only":
            by_tenant[tenant]["retrieval_only"] += 1
        elif mode == "synthesis":
            by_tenant[tenant]["synthesis"] += 1

    header = (
        f"  {'Tenant':<20}  {'Total':>5}  {'Insufficient':>12}  "
        f"{'No-LLM':>6}  {'Synthesis':>9}  {'Avg hits':>8}  {'Avg ms':>7}"
    )
    print(header)
    print("  " + "─" * (len(header) - 2))

    for tenant, s in sorted(by_tenant.items(), key=lambda x: -x[1]["total"]):
        total = int(s["total"])
        insuff = int(s["insufficient"])
        no_llm = int(s["retrieval_only"])
        synth = int(s["synthesis"])
        avg_hits = (s["hits_sum"] / total) if total else 0
        avg_ms = int((s["duration_sum"] / total) if total else 0)
        insuff_pct = insuff / total if total else 0

        status = f"{GREEN}ok{NC}"
        if insuff_pct > 0.30:
            status = f"{RED}high no-answer{NC}"
        elif insuff_pct > 0.15:
            status = f"{YELLOW}watch{NC}"

        print(
            f"  {tenant:<20}  {total:>5}  {insuff:>12}  "
            f"{no_llm:>6}  {synth:>9}  {avg_hits:>8.2f}  {avg_ms:>7}  {status}"
        )
    print()


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def _pct(rate: float) -> str:
    return f"{rate * 100:.1f}%"


def _print_header(path: Path, models: set[str], temps: set[float]) -> None:
    print(f"\n{BOLD}AKF Telemetry Report{NC}")
    print(f"  Source:      {path}")
    print(f"  Models:      {', '.join(sorted(models)) or 'unknown'}")
    print(f"  Temperature: {', '.join(str(t) for t in sorted(temps)) or 'unknown'}")
    print()


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="analyze_telemetry",
        description="AKF Phase 2.3 — Telemetry aggregation reports",
    )
    parser.add_argument(
        "--input", "-i",
        type=Path,
        default=DEFAULT_TELEMETRY_PATH,
        help=f"Path to JSONL telemetry file (default: {DEFAULT_TELEMETRY_PATH})",
    )
    parser.add_argument(
        "--report", "-r",
        choices=["retry-rate", "candidates", "convergence", "ask-usage", "all"],
        default="all",
        help="Which report to run (default: all)",
    )
    parser.add_argument(
        "--flag-threshold",
        type=float,
        default=FLAG_THRESHOLD,
        help=f"Normalized retry rate threshold for flagging (default: {FLAG_THRESHOLD})",
    )

    args = parser.parse_args()

    attempts, summaries, asks = load_events(args.input)

    # Extract environmental control fields for header
    models = {e.get("model", "unknown") for e in attempts + summaries + asks}
    temps  = {e.get("temperature", 0) for e in attempts + summaries + asks}

    _print_header(args.input, models, temps)

    run_all = args.report == "all"

    if run_all or args.report == "retry-rate":
        report_retry_rate(attempts, flag_threshold=args.flag_threshold)

    if run_all or args.report == "candidates":
        report_rejected_candidates(summaries)

    if run_all or args.report == "convergence":
        report_convergence(summaries)

    if run_all or args.report == "ask-usage":
        report_ask_usage(asks)


if __name__ == "__main__":
    main()
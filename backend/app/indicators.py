"""Durable canonical measurements and network-free projections for additional panels."""

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal, localcontext
from typing import Literal

from .batches import MeasurementBatch
from .gdp import timestamp
from .measurements import CATALOGUE, Measurement, Period, Reference, Unit, fiscal, month
from .models import Collection, Model


class GroupCollection(Collection):
    group_id: str
    provider_id: str
    next_request_not_before: str | None = None
    interval_seconds: int


class IndicatorSeries(Model):
    id: str
    label: str
    unit: Unit
    points: list[Measurement]


class IndicatorSummary(Model):
    current: Reference
    comparison: Reference | None
    kind: Literal["relative_percent", "percentage_points", "none"]
    value: str | None
    period_kind: Literal["month", "fiscal_year", "fiscal_year_to_date", "calendar_year"]


class IndicatorPanel(Model):
    schema_version: Literal["1"] = "1"
    id: Literal["expenditure", "gst", "trade", "inflation", "debt"]
    state: Literal["ready", "stale", "empty", "unavailable"]
    availability: Literal["implemented", "blocked", "unverified"] = "implemented"
    collection: list[GroupCollection]
    series: list[IndicatorSeries]
    summaries: list[IndicatorSummary]
    notes: list[str]
    coverage: list[str]
    policies: list["InflationPolicy"] = []
    freshness_assessment: Literal["unknown"] = "unknown"
    report_years: int = 5


class InflationPolicy(Model):
    validity: Period
    target: Reference
    lower: Reference
    upper: Reference
    active: bool


def null_gaps(points):
    result = list(points)
    for sid in {p.series_id for p in points if p.period.kind == "month"}:
        items = [p for p in points if p.series_id == sid and p.period.kind == "month"]
        first, last = min(p.period.start for p in items), max(p.period.start for p in items)
        lookup = {p.period.key for p in items}
        y, m = first.year, first.month
        while (y, m) <= (last.year, last.month):
            period = month(y, m)
            if period.key not in lookup:
                template = items[0]
                definition = template.definition.model_copy(
                    update={
                        "status": "unspecified",
                        "published_at": None,
                        "inputs": [],
                        "publication_note": "No stored observation for this reporting month.",
                    }
                )
                result.append(
                    template.model_copy(
                        update={
                            "period": period,
                            "definition": definition,
                            "value": None,
                            "source_url": None,
                            "retrieved_at": None,
                            "response_sha256": None,
                            "retained": False,
                            "footnote": "No stored observation; gap is not zero or interpolated.",
                        }
                    )
                )
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return result


def store_batch(database, state, run, rows: list[Measurement]):
    if (not rows and not isinstance(rows, MeasurementBatch)) or len(
        {(p.series_id, p.period.key) for p in rows}
    ) != len(rows):
        raise ValueError("Empty or duplicate measurement batch")
    if any(p.definition.group != state.group or p.definition.provider != state.provider for p in rows):
        raise ValueError("Collection identity mismatch")
    # Revalidate even programmatically created/copied models before crossing SQL boundary.
    expected = (
        rows.expected if isinstance(rows, MeasurementBatch) else {(p.series_id, p.period.key) for p in rows}
    )
    if any(CATALOGUE[sid][:2] != (state.group, state.provider) for sid, _ in expected):
        raise ValueError("Response scope identity mismatch")
    rows = [Measurement.model_validate(p.model_dump()) for p in rows]
    if any((p.series_id, p.period.key) not in expected for p in rows):
        raise ValueError("Observation outside expected response scope")
    with database.connect(write=True) as db:
        # Mark only advertised/requested keys before replacing accepted values. An
        # absent or null value keeps every byte of its original provenance.
        db.executemany(
            "UPDATE observations SET retained=1 WHERE group_id=? AND series_id=? AND period_key=?",
            [(state.group, sid, key) for sid, key in expected],
        )
        for point in rows:
            if point.value is None:
                db.execute(
                    "UPDATE observations SET retained=1 WHERE series_id=? AND period_key=?",
                    (point.series_id, point.period.key),
                )
                continue
            metadata = json.dumps(
                {
                    "period": point.period.model_dump(mode="json"),
                    "definition": point.definition.model_dump(mode="json"),
                },
                separators=(",", ":"),
            )
            db.execute(
                """INSERT INTO observations(series_id,period_key,value,provider_status,footnote,source_url,
                       dataset_updated_on,retrieved_at,response_sha256,group_id,measurement_json)
                       VALUES (?,?,?,?,?,?,NULL,?,?,?,?) ON CONFLICT(series_id,period_key) DO UPDATE SET
                       value=excluded.value,provider_status=excluded.provider_status,footnote=excluded.footnote,
                       source_url=excluded.source_url,dataset_updated_on=NULL,retrieved_at=excluded.retrieved_at,
                       response_sha256=excluded.response_sha256,group_id=excluded.group_id,
                       measurement_json=excluded.measurement_json,retained=0""",
                (
                    point.series_id,
                    point.period.key,
                    point.value,
                    point.definition.status,
                    point.footnote,
                    point.source_url,
                    point.retrieved_at,
                    point.response_sha256,
                    state.group,
                    metadata,
                ),
            )
        state.finish_in(db, run, timestamp(state.clock()))


def annual_gaps(points, years):
    if not points:
        return points
    result = list(points)
    last = max(p.period.end for p in points)
    fiscal_start = last.year - (last.month <= 3)
    completed = fiscal_start if last.month == 3 else fiscal_start - 1
    for sid in {p.series_id for p in points}:
        items = [p for p in points if p.series_id == sid]
        known = {p.period.key for p in items}
        for year in range(completed - years + 1, completed + 1):
            period = fiscal(year)
            if period.key not in known:
                template = items[0]
                definition = template.definition.model_copy(
                    update={
                        "status": "unspecified",
                        "published_at": None,
                        "inputs": [],
                        "publication_note": "No stored observation for this requested completed fiscal year.",
                    }
                )
                result.append(
                    template.model_copy(
                        update={
                            "period": period,
                            "definition": definition,
                            "value": None,
                            "source_url": None,
                            "retrieved_at": None,
                            "response_sha256": None,
                            "retained": False,
                            "footnote": definition.publication_note,
                        }
                    )
                )
    return result


def read_measurements(db, groups):
    result = []
    for group in groups:
        for row in db.execute("SELECT * FROM observations WHERE group_id=? ORDER BY period_key", (group,)):
            metadata = json.loads(row["measurement_json"])
            result.append(
                Measurement.model_validate(
                    dict(
                        series_id=row["series_id"],
                        value=row["value"],
                        source_url=row["source_url"],
                        retrieved_at=row["retrieved_at"],
                        response_sha256=row["response_sha256"],
                        footnote=row["footnote"],
                        retained=bool(row["retained"]),
                        **metadata,
                    )
                )
            )
    return result


def collection_status(db, group, provider, interval, now):
    latest = db.execute(
        "SELECT * FROM collection_runs WHERE group_id=? ORDER BY id DESC LIMIT 1", (group,)
    ).fetchone()
    finished = db.execute(
        "SELECT * FROM collection_runs WHERE group_id=? AND outcome!='running' ORDER BY id DESC LIMIT 1",
        (group,),
    ).fetchone()
    success = db.execute(
        "SELECT * FROM collection_runs WHERE group_id=? AND outcome='ok' ORDER BY id DESC LIMIT 1", (group,)
    ).fetchone()
    cooldown = db.execute(
        "SELECT not_before FROM provider_cooldowns WHERE provider_id=?", (provider,)
    ).fetchone()
    overdue = bool(
        success and now - datetime.fromisoformat(success["completed_at"]).timestamp() > interval * 2
    )
    return GroupCollection(
        group_id=group,
        provider_id=provider,
        interval_seconds=interval,
        last_attempt_at=latest["attempted_at"] if latest else None,
        last_success_at=success["completed_at"] if success else None,
        last_error_kind=finished["error_kind"]
        if finished and finished["outcome"] == "error"
        else "collection_overdue"
        if overdue
        else None,
        in_progress=bool(latest and latest["outcome"] == "running"),
        next_request_not_before=timestamp(cooldown[0]) if cooldown and cooldown[0] > now else None,
    )


def summaries(points):
    result = []
    for sid in sorted({p.series_id for p in points}):
        items = sorted(
            (p for p in points if p.series_id == sid), key=lambda p: (p.period.end, p.period.start)
        )
        if items[-1].period.kind == "policy_validity":
            continue
        # First summary is the most recent reporting grain; additional summaries
        # support FYTD cards and completed-FY tables without recomputing arithmetic.
        kinds = [items[-1].period.kind] + sorted({p.period.kind for p in items} - {items[-1].period.kind})
        for kind in kinds:
            result += _summaries_for_grain([p for p in items if p.period.kind == kind])
    return result


def _summaries_for_grain(points):
    result = []
    for series_id in sorted({p.series_id for p in points}):
        items = sorted(
            (p for p in points if p.series_id == series_id), key=lambda p: (p.period.end, p.period.start)
        )
        current = items[-1]
        if current.period.kind == "policy_validity":
            continue
        # Never use a previous fiscal total as the comparison for a partial FY.
        if current.period.kind == "month" and current.definition.group == "inflation":
            y, m = current.period.start.year, current.period.start.month
            wanted = (y - 1, 12) if m == 1 else (y, m - 1)
            matches = [
                p
                for p in items
                if (p.period.start.year, p.period.start.month) == wanted
                and p.definition.methodology == current.definition.methodology
            ]
            kind = "percentage_points"
        else:
            matches = [
                p
                for p in items
                if p.period.kind == current.period.kind
                and p.period.start.year == current.period.start.year - 1
                and p.period.start.month == current.period.start.month
                and p.period.end.month == current.period.end.month
                and p.definition.methodology == current.definition.methodology
            ]
            kind = "relative_percent"
        prior = matches[-1] if matches else None
        delta = None
        with localcontext() as context:
            context.prec = 80
            if prior and current.value is not None and prior.value is not None:
                c, p = Decimal(current.value), Decimal(prior.value)
                if kind == "percentage_points":
                    delta = format(c - p, "f")
                elif p != 0:
                    delta = format((c / p - 1) * 100, "f")
        result.append(
            IndicatorSummary(
                current=Reference(series_id=series_id, period_key=current.period.key),
                comparison=Reference(series_id=series_id, period_key=prior.period.key) if prior else None,
                kind=kind,
                value=delta,
                period_kind=current.period.kind,
            )
        )
    return result


def read_indicator(database, panel_id, jobs, now, report_years=5):
    groups = [job for job in jobs.values() if job.panel == panel_id]
    with database.connect() as db:
        db.execute("BEGIN")
        points = read_measurements(db, [job.group for job in groups])
        statuses = [collection_status(db, job.group, job.provider, job.interval, now) for job in groups]
    if panel_id == "gst":
        from .derived import gst_aggregates

        points += gst_aggregates(points, report_years)
    points = null_gaps(points)
    if panel_id in {"trade", "expenditure"}:
        points = annual_gaps(points, report_years)
    for status in statuses:
        if not status.last_error_kind and any(
            p.retained and p.definition.group == status.group_id for p in points
        ):
            status.last_error_kind = "provider_missing_retained"
    points.sort(key=lambda p: (p.period.end, p.period.start))
    series = [
        IndicatorSeries(id=key, label=spec[3], unit=spec[2], points=[p for p in points if p.series_id == key])
        for key, spec in CATALOGUE.items()
        if any(p.series_id == key for p in points)
    ]
    has_data = any(p.value is not None and p.definition.group != "inflation_policy" for p in points)
    failed = any(s.last_error_kind for s in statuses) or any(p.retained for p in points)
    policies = []
    # The statutory window is an Indian civil-date interval; retrieval timestamps
    # remain UTC. IST has a fixed +05:30 offset throughout these modern policies.
    today = datetime.fromtimestamp(now, timezone(timedelta(hours=5, minutes=30))).date()
    targets = [p for p in points if p.series_id == "inflation_target"]
    for p in targets:
        policies.append(
            InflationPolicy(
                validity=p.period,
                target=Reference(series_id=p.series_id, period_key=p.period.key),
                lower=Reference(series_id="inflation_target_lower", period_key=p.period.key),
                upper=Reference(series_id="inflation_target_upper", period_key=p.period.key),
                active=p.period.start <= today <= p.period.end,
            )
        )
    return IndicatorPanel(
        id=panel_id,
        state=("stale" if failed else "ready") if has_data else ("unavailable" if failed else "empty"),
        collection=statuses,
        series=series,
        summaries=summaries(points),
        notes=[note for job in groups for note in job.notes],
        coverage=[note for job in groups for note in job.coverage(points)],
        policies=policies,
        report_years=report_years,
    )

"""Compute canonical derived points once; cards/charts/tooltips/tables reference these same points."""

from decimal import Decimal, localcontext

from .measurements import Reference, fiscal


def gst_aggregates(points, years):
    base = [p for p in points if p.series_id == "gst_gross_ex_cess" and p.period.kind == "month"]
    if not base:
        return []
    latest = max(base, key=lambda p: p.period.end)
    current_fy = latest.period.start.year - (latest.period.start.month < 4)
    result = []

    def make(series_id, period, inputs, divisor, complete, method):
        template = max(inputs, key=lambda p: p.period.end) if inputs else latest
        value = None
        with localcontext() as ctx:
            ctx.prec = 80
            if complete and inputs and all(p.value is not None for p in inputs):
                value = format(sum(Decimal(p.value) for p in inputs) / divisor, "f")
        definition = template.definition.model_copy(
            update={
                "methodology": method,
                "inputs": [Reference(series_id=p.series_id, period_key=p.period.key) for p in inputs],
                "publication_note": f"Calculated from {len(inputs)} published months; no missing month is zero-filled.",
                "published_at": None,
            }
        )
        result = template.model_copy(
            update={
                "series_id": series_id,
                "period": period,
                "definition": definition,
                "value": value,
                "retained": any(p.retained for p in inputs),
                "footnote": definition.publication_note,
            }
        )
        if not inputs:
            result = result.model_copy(
                update={"source_url": None, "response_sha256": None, "retrieved_at": None}
            )
        return result

    last_completed = current_fy if latest.period.end.month == 3 else current_fy - 1
    for y in range(last_completed - years + 1, last_completed + 1):
        period = fiscal(y)
        inputs = [p for p in base if period.start <= p.period.start <= period.end]
        complete = len(inputs) == 12 and len({p.period.key for p in inputs}) == 12
        result.append(make("gst_fy_total", period, inputs, 1, complete, "gross_ex_cess_completed_fy_total"))
        result.append(
            make(
                "gst_fy_average",
                period,
                inputs,
                12,
                complete,
                "gross_ex_cess_completed_fy_total_divided_by_12",
            )
        )
    for y in (current_fy - 1, current_fy):
        period = fiscal(y, latest.period.end.month)
        inputs = [p for p in base if period.start <= p.period.start <= period.end]
        months = "_".join(f"{p.period.start.month:02}" for p in sorted(inputs, key=lambda p: p.period.start))
        result.append(
            make(
                "gst_fytd_average",
                period,
                inputs,
                max(1, len(inputs)),
                True,
                f"gross_ex_cess_average_published_months_{months}",
            )
        )
    return result

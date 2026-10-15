"""Explicit response coverage, independent of which values a parser returned."""

from .measurements import CATALOGUE, Measurement


class MeasurementBatch(list[Measurement]):
    def __init__(self, rows, expected):
        super().__init__(rows)
        self.expected = frozenset(expected)
        if not self.expected or any(sid not in CATALOGUE or not key for sid, key in self.expected):
            raise ValueError("Invalid expected response scope")
        if any((p.series_id, p.period.key) not in self.expected for p in self):
            raise ValueError("Observation outside expected response scope")


def scope(series, periods):
    return {(sid, p.key) for sid in series for p in periods}

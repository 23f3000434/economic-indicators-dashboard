from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EmptyBody(Model):
    pass


class ErrorDetail(Model):
    code: str
    message: str


class ErrorEnvelope(Model):
    error: ErrorDetail


class Point(Model):
    period_key: str
    period_label: str
    period_start: str
    period_end: str
    value: str | None
    estimate_status: Literal["unspecified"] = "unspecified"
    provider_status: str = ""
    footnote: str = ""
    retrieved_at: str | None
    dataset_updated_on: str | None
    retained: bool = False


class Source(Model):
    id: Literal["world_bank_wdi"] = "world_bank_wdi"
    url: str
    published_at: str | None = None
    dataset_updated_on: str | None
    retrieved_at: str | None


class Series(Model):
    id: Literal["gdp_india", "gdp_world"]
    label: str
    unit: Literal["percent"] = "percent"
    reporting_basis: Literal["fiscal_year_apr_mar", "calendar_year_aggregate"]
    points: list[Point]
    source: Source


class Change(Model):
    kind: Literal["percentage_points"] = "percentage_points"
    value: str | None


class Summary(Model):
    series_id: str
    current_period_key: str | None
    comparison_period_key: str | None
    change: Change


class Collection(Model):
    last_attempt_at: str | None
    last_success_at: str | None
    last_error_kind: str | None
    in_progress: bool


class Panel(Model):
    schema_version: Literal["1"] = "1"
    id: Literal["gdp"] = "gdp"
    state: Literal["ready", "stale", "empty", "unavailable"]
    collection: Collection
    series: list[Series]
    summaries: list[Summary]
    notes: list[str]


class Login(Model):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=1024)


class User(Model):
    id: str
    username: str


class SessionInfo(Model):
    session_expires_at: str
    csrf_token: str
    user: User


class Tokens(SessionInfo):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    access_expires_at: str


class Health(Model):
    status: Literal["ok", "unavailable"]
    database: Literal["ready", "unavailable"]
    collector: Literal["running", "standby", "stopped", "disabled"]

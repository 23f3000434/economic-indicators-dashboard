import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    database: Path
    jwt_secret: str
    csrf_secret: str
    rotation_secret: str
    environment: str = "development"
    api_origin: str = "http://localhost:8010"
    frontend_origin: str = "http://localhost:5173"
    site_domain: str = ""
    issuer: str = "economic-indicators-api"
    audience: str = "economic-indicators-dashboard"
    session_max_age: int = 604800
    settle_seconds: int = 30
    collector_enabled: bool = True
    collection_interval: int = 604800
    collection_years: int = 12
    start_year: int | None = None
    end_year: int | None = None
    report_years: int = 5
    upstream_timeout: float = 20
    upstream_attempts: int = 2
    cga_interval: int = 86400
    gst_interval: int = 86400
    trade_interval: int = 86400
    cpi_interval: int = 86400
    policy_interval: int = 604800
    debt_interval: int = 604800
    debt_appendix_url: str = "https://data.imf.org/-/media/iData/External-Storage/Documents/C4182C5C54794FC48892DE8F6C74FF82/en/October-2026-WEO-Database-Appendix.pdf"
    policy_url: str = "https://egazette.gov.in/WriteReadData/2026/271285.pdf"
    macro_groups: tuple[str, ...] | None = None
    collection_budget: int = 600
    macro_report_years: int = 5
    trade_history_urls: tuple[str, ...] = (
        "https://www.pib.gov.in/PressReleasePage.aspx?PRID=1916220&reg=48&lang=2",
        "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2017942&reg=48&lang=2",
    )

    def __post_init__(self):
        if self.environment not in {"development", "production", "test"}:
            raise ValueError("APP_ENV must be development, production, or test")
        secrets = [self.jwt_secret, self.csrf_secret, self.rotation_secret]
        if any(len(s) < 32 for s in secrets) or len(set(secrets)) != 3:
            raise ValueError("Three distinct server secrets of at least 32 characters are required")
        if not 1 <= self.session_max_age <= 604800 or not 25 <= self.settle_seconds <= 120:
            raise ValueError("Session maximum must be 1..604800 seconds; settling must be 25..120 seconds")
        if not 2 <= self.report_years <= 50 or not self.report_years + 1 <= self.collection_years <= 100:
            raise ValueError(
                "Collection window must include report window plus its comparison year (max 100)"
            )
        if self.collection_interval < 1 or not 1 <= self.upstream_attempts <= 3:
            raise ValueError("Invalid collector interval or attempt budget")
        if not 1 <= self.upstream_timeout <= 60:
            raise ValueError("Upstream timeout must be 1..60 seconds")
        if any(
            i < 1
            for i in (
                self.cga_interval,
                self.gst_interval,
                self.trade_interval,
                self.cpi_interval,
                self.policy_interval,
                self.debt_interval,
            )
        ):
            raise ValueError("Group intervals must be positive")
        if not 10 <= self.collection_budget <= 1800:
            raise ValueError("Collection job budget must be 10..1800 seconds")
        if not 2 <= self.macro_report_years <= 20:
            raise ValueError("Macro reporting window must be 2..20 completed years")
        if self.macro_groups is not None and not set(self.macro_groups) <= {
            "expenditure",
            "gst",
            "trade",
            "inflation",
            "inflation_policy",
            "debt",
        }:
            raise ValueError("Unknown collection group")
        policy = urlsplit(self.policy_url)
        if (
            policy.scheme != "https"
            or policy.hostname != "egazette.gov.in"
            or policy.username
            or policy.port
            or not policy.path.endswith(".pdf")
        ):
            raise ValueError("Policy must reference a reviewed official HTTPS Gazette PDF")
        appendix = urlsplit(self.debt_appendix_url)
        if (
            appendix.scheme != "https"
            or appendix.hostname != "data.imf.org"
            or appendix.username
            or appendix.port
            or not appendix.path.endswith(".pdf")
        ):
            raise ValueError("Debt appendix must be an official IMF HTTPS PDF")
        origins = [urlsplit(self.frontend_origin), urlsplit(self.api_origin)]
        if any(o.path or o.query or o.fragment or o.username or not o.hostname for o in origins):
            raise ValueError("Origins must contain only scheme, host and optional port")
        if self.environment == "production":
            domain = self.site_domain.lower()
            if (
                not domain
                or "." not in domain
                or any(o.scheme != "https" or not o.hostname.endswith("." + domain) for o in origins)
                or origins[0].hostname == origins[1].hostname
            ):
                raise ValueError("Production requires distinct HTTPS subdomains of COOKIE_SITE_DOMAIN")
        elif (
            any(o.scheme != "http" or o.hostname not in {"localhost", "127.0.0.1", "::1"} for o in origins)
            or origins[0].hostname != origins[1].hostname
        ):
            raise ValueError(
                "Local HTTP requires matching loopback hosts; do not mix localhost and 127.0.0.1"
            )

    @property
    def cookie_name(self) -> str:
        return "__Host-refresh" if self.environment == "production" else "dev_refresh"

    def window(self, year: int) -> tuple[int, int]:
        end = self.end_year if self.end_year is not None else year - 1
        start = self.start_year if self.start_year is not None else end - self.collection_years + 1
        if not 1960 <= start <= end < 2200 or end - start + 1 < self.report_years + 1 or end - start >= 100:
            raise ValueError("GDP window must be 1960..2199, at most 100 years, with a comparison year")
        return start, end

    @classmethod
    def load(cls):
        load_dotenv(ROOT / ".env", override=False)

        def integer(name, default):
            return int(os.getenv(name, default))

        def optional(name):
            return int(os.environ[name]) if os.getenv(name) else None

        enabled = os.getenv("COLLECTOR_ENABLED", "true").lower()
        if enabled not in {"true", "false"}:
            raise ValueError("COLLECTOR_ENABLED must be true or false")

        return cls(
            database=Path(os.getenv("SQLITE_PATH", str(ROOT / "data/dashboard.sqlite3"))).resolve(),
            jwt_secret=os.getenv("JWT_SECRET", ""),
            csrf_secret=os.getenv("CSRF_SECRET", ""),
            rotation_secret=os.getenv("ROTATION_SECRET", ""),
            environment=os.getenv("APP_ENV", "production"),
            api_origin=os.getenv("API_ORIGIN", ""),
            frontend_origin=os.getenv("FRONTEND_ORIGIN", ""),
            site_domain=os.getenv("COOKIE_SITE_DOMAIN", ""),
            issuer=os.getenv("JWT_ISSUER", "economic-indicators-api"),
            audience=os.getenv("JWT_AUDIENCE", "economic-indicators-dashboard"),
            session_max_age=integer("SESSION_MAX_AGE_SECONDS", 604800),
            settle_seconds=integer("REFRESH_SETTLE_SECONDS", 30),
            collector_enabled=enabled == "true",
            collection_interval=integer("GDP_COLLECTION_INTERVAL_SECONDS", 604800),
            collection_years=integer("GDP_COLLECTION_YEARS", 12),
            start_year=optional("GDP_START_YEAR"),
            end_year=optional("GDP_END_YEAR"),
            report_years=integer("GDP_REPORT_YEARS", 5),
            upstream_timeout=float(os.getenv("UPSTREAM_TIMEOUT_SECONDS", 20)),
            upstream_attempts=integer("UPSTREAM_ATTEMPTS", 2),
            cga_interval=integer("CGA_COLLECTION_INTERVAL_SECONDS", 86400),
            gst_interval=integer("GST_COLLECTION_INTERVAL_SECONDS", 86400),
            trade_interval=integer("TRADE_COLLECTION_INTERVAL_SECONDS", 86400),
            cpi_interval=integer("CPI_COLLECTION_INTERVAL_SECONDS", 86400),
            policy_interval=integer("POLICY_COLLECTION_INTERVAL_SECONDS", 604800),
            debt_interval=integer("DEBT_COLLECTION_INTERVAL_SECONDS", 604800),
            debt_appendix_url=os.getenv(
                "DEBT_APPENDIX_URL", cls.__dataclass_fields__["debt_appendix_url"].default
            ),
            policy_url=os.getenv(
                "INFLATION_POLICY_URL", "https://egazette.gov.in/WriteReadData/2026/271285.pdf"
            ),
            macro_groups=tuple(g.strip() for g in os.environ["COLLECTION_GROUPS"].split(",") if g.strip())
            if "COLLECTION_GROUPS" in os.environ
            else None,
            collection_budget=integer("COLLECTION_JOB_BUDGET_SECONDS", 600),
            macro_report_years=integer("MACRO_REPORT_YEARS", 5),
            trade_history_urls=tuple(os.environ["TRADE_HISTORY_URLS"].split("|"))
            if os.getenv("TRADE_HISTORY_URLS")
            else cls.__dataclass_fields__["trade_history_urls"].default,
        )

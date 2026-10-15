# Reviewed official debt fixtures

Captured on 15 October 2026 UTC (16 October IST). These compressed original responses are test-only, never production inputs.

Data360 redistributes IMF WEO GGXWDG_NGDP. The CSV includes historical and projected years; application collection excludes future source years. The official October 2026 WEO appendix supplies the actual-year cutoffs (India FY2024–25; US CY2025), government coverage/accounting and exceptional fiscal reporting.

| Response | SHA-256 of original bytes |
| --- | --- |
| data360_debt | 79c1e31bf2524edaf765dda2477119cc2d84097abd1b03512a964353fd1a47d5 |
| data360_debt_metadata | 188becca8e104481bb7044adc550c71d5e56b8773a35ee91d0149e6be9ef1c44 |
| weo_oct2026_appendix | cd4e2829d7e621d43134728bfc128547f776e909e08ef1d38b837e2d39e5ae2a |

Reviewed latest values: India FY2025–26 84.260729% (estimate), US CY2025 124.376732% (actual). India FY2024–25 84.805205%; US CY2024 122.334277%. Changes −0.544476 pp and +2.042455 pp. Source A means Normal value; classification uses the matching appendix, not the A flag alone.

Stable Data360 data/metadata URLs are in app/providers/debt.py; the reviewed official appendix URL is configured by DEBT_APPENDIX_URL. A mismatched later vintage fails validation and retains valid data until its matching appendix is reviewed.

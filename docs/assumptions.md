# Assumptions and known limitations

Current at final delivery from 596e4a7. Implementation evidence and production acceptance are separate in [delivery status](delivery-status.md).

| Decision / assumption | Consequence and verification boundary |
| --- | --- |
| User accepted installed Segoe UI with self-hosted Roboto fallback on 16 Oct2026 | No proprietary webfont is distributed. Cards/axes/SENSEX differ on machines without Segoe. This is accepted, not an exact Figma-font claim. Roboto/Manrope use included OFL licences. |
| Visual1248×2193 reference width-fits1214×2159 | Figma's rotated frame is mapped uniformly at 1214/1248; geometry was measured individually. Real values, chart ranges, correct units and FY/CY labels necessarily differ from illustrative figures. Details stay outside the fixed panel footprint. No mobile reference frame was supplied. |
| GST primary series excludes compensation cess (D17) | Published older totals are normalised with reconciled cess/components; original definitions remain recorded. Gross means before refunds. FYTD averages divide by published month count; complete annual values require12 months. |
| Comparable headline debt is general-government gross debt/GDP | IMF WEO India/US share the headline concept but differ in institutional coverage, cash/accrual and FY/CY. Vintage-matched appendix determines actual/estimate cutoffs. No claim of perfect national-account comparability or daily observations. |
| GDP uses WDI annual real growth | India is FY, World CY; no independent alignment/rebasing. Blank WDI status is unspecified. Individual release date is unknown when absent. |
| Trade is merchandise only | Match month/FYTD/FY comparisons; signed balance uses exports minus imports. Canonical arithmetic can differ from separately rounded headlines. Older bootstrap references need maintenance as the configured window advances. |
| CPI bases are incompatible | Separate2012/2024 series with null pandemic gaps; no interpolated bridge or cross-base badge. Unknown new methodology fails closed for review. |
| Inflation target is dated statutory policy | Reviewed Gazette reference, separately scheduled; automatic successor discovery is not implemented. Expiry never extends policy. A successor notification needs review/configuration. |
| CGA figures are unaudited actuals/provisional accounts | BE/RE are excluded; revenue + capital must reconcile. Publication date stays null when absent. |
| Missing release calendars are not inferred | Recently collecting an older release does not establish economic freshness. Collection lateness/failure/retention are labelled separately; exact overdue-release assessment remains unknown where not established. |
| Public quotes are snapshots | NSE has no verified latency SLA. Live applies only to recent Upstox quotes during a verified normal session. Exchange timestamps, status/schedule and failure thresholds determine all labels; no synthetic price changes. |
| One process owns SQLite and in-process scheduling | One worker/replica and mounted private disk. Multi-replica/high-availability operation is not supported by this arrangement. Render disk deploys incur downtime; no zero-downtime promise. |
| Recovery revokes restored sessions | Online snapshots contain private user/hash/session state; restore writes a new path and removes sessions/tokens. Users sign in again. Account/password state and off-host backup security require operator review. |
| Bounded refresh settling window | Normal concurrent/lost responses are tested. Extremely delayed obsolete responses beyond the documented settling window may require sign-in; unlimited replay is intentionally unsupported. |
| Operator-managed evaluation accounts | No self-registration, account-management UI, email reset, MFA or password-reset workflow is included. No default credentials. Account access and secrets are shared privately. |

Production-unverified items: actual domain/DNS/TLS, Pages headers/build origin, Render ingress proxy trust and egress/native TLS, filesystem/mount ownership, restart/redeploy persistence, real-site cookie/CORS/CSRF behaviour, provider display permission, rotated market credentials and off-host backup operation. These are concrete acceptance items, not locally completed deliverables. See [deployment](deployment.md) and [production smoke](production-smoke.md).

Artwork is deterministically resized from the assignment's supplied SVG; original cropping/transparency/provenance is retained. Supplied assignment artwork does not establish a general redistribution licence. The private repository preserves source provenance; do not publish proprietary fonts or secrets with it. No project-wide third-party ownership or licence grant is inferred.

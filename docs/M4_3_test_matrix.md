# Milestone 4.3: Integration & Regression Test Matrix

**Platform**: InfraScan Civil Infrastructure Damage Inspection Platform  
**Target Host**: `http://127.0.0.1:8000`  
**Execution Timestamp**: November 22, 2026  
**Executed Tests**: 34 | **Passed**: 34 | **Failed**: 0  
**Unexecuted / Scoped Out Security & Reliability Tests**: 6  

---

### 1. Executed Test Matrix (34 Tests Executed & Passed)

| Test ID | Test Description | Expected Result | Actual Result | Execution Status | Evidence |
|---|---|---|---|:---:|---|
| **INT-01** | Backend Health API Check | HTTP 200 OK | HTTP 200 OK | **EXECUTED / PASSED** | `status: "healthy"` |
| **INT-02** | User Registration & Role Enforcement | HTTP 201, `role="user"` | HTTP 201, `role="user"` | **EXECUTED / PASSED** | Forced `user` role despite injection |
| **INT-03** | User Login & JWT Generation | HTTP 200, Valid JWT | HTTP 200, JWT issued | **EXECUTED / PASSED** | Bearer token length: 172 chars |
| **INT-04** | User Dashboard Stats Isolation | HTTP 200, Total Insp = 0 | HTTP 200, Total Insp = 0 | **EXECUTED / PASSED** | Isolated clean initial count |
| **INT-05** | User Inspection Upload & AI Analysis | HTTP 200, Insp ID attached | HTTP 200, ID=35, User=12 | **EXECUTED / PASSED** | Crack=True, Area=9496 px |
| **INT-06** | Inspection Detail Retrieval | HTTP 200, Matching ID | HTTP 200, Matching ID=35 | **EXECUTED / PASSED** | Full geometry & severity returned |
| **INT-07** | User Inspection History Isolation | HTTP 200, Count = 1 | HTTP 200, Count = 1 | **EXECUTED / PASSED** | Only user's own record listed |
| **INT-08** | User Report Download (PDF) | HTTP 200, `%PDF` header | HTTP 200, 564,397 bytes | **EXECUTED / PASSED** | Valid binary PDF magic header |
| **INT-09** | User Report Download (CSV) | HTTP 200, 41 lines | HTTP 200, 41 lines | **EXECUTED / PASSED** | Parsed `InfraScan` project schema |
| **INT-10** | Session Logout & Re-login Persistence | HTTP 200, Preserved ID | HTTP 200, Preserved ID=35 | **EXECUTED / PASSED** | Complete data persisted across logins |
| **INT-11** | Admin Login & Redirection | HTTP 200, Admin JWT | HTTP 200, Admin JWT | **EXECUTED / PASSED** | Authenticated as Administrator |
| **INT-12** | Admin Overview System-Wide Stats | HTTP 200, Live Stats | HTTP 200, 13 Users, 35 Insp | **EXECUTED / PASSED** | Dynamic DB metrics aggregated |
| **INT-13** | Admin User Management Registry | HTTP 200, User list | HTTP 200, 13 Users listed | **EXECUTED / PASSED** | Full user management visibility |
| **INT-14** | Admin User Deactivation Lifecycle | Deact 200, API 403, Login 403 | Deact 200, API 403, Login 403 | **EXECUTED / PASSED** | Inactive account blocked completely |
| **INT-15** | Admin User Reactivation Lifecycle | React 200, Restored Login 200 | React 200, Restored Login 200 | **EXECUTED / PASSED** | Full account privileges restored |
| **INT-16** | Admin System-Wide Inspections Access | HTTP 200, All Records | HTTP 200, 35 records visible | **EXECUTED / PASSED** | System-wide oversight verified |
| **INT-17** | Admin System-Wide Report Access | PDF 200, CSV 200 | PDF 200, CSV 200 | **EXECUTED / PASSED** | Admin authorized to download all reports |
| **SEC-01** | Unauthorized Inspection Detail Blocked | HTTP 403 Forbidden | HTTP 403 Forbidden | **EXECUTED / PASSED** | Cross-tenant access prevented |
| **SEC-02** | Unauthorized PDF Download Blocked | HTTP 403 Forbidden | HTTP 403 Forbidden | **EXECUTED / PASSED** | Cross-tenant report download blocked |
| **SEC-03** | Unauthorized CSV Download Blocked | HTTP 403 Forbidden | HTTP 403 Forbidden | **EXECUTED / PASSED** | Cross-tenant data extraction blocked |
| **SEC-04** | Regular User Blocked from Admin APIs | HTTP 403 Forbidden | HTTP 403 Forbidden | **EXECUTED / PASSED** | Administrative endpoints guarded |
| **SEC-05** | Unauthenticated Request to Protected API | HTTP 401 Unauthorized | HTTP 401 Unauthorized | **EXECUTED / PASSED** | OAuth2 bearer token strictly enforced |
| **SEC-06** | Malformed Token Signature Blocked | HTTP 401 Unauthorized | HTTP 401 Unauthorized | **EXECUTED / PASSED** | JWT signature verification active |
| **SEC-07** | Zero Credential Leakage in User Profile | No password in response | Zero password keys | **EXECUTED / PASSED** | Schema excludes sensitive fields |
| **AI-01** | AI Regression: Sound Concrete | Crack=False, Sev=No Damage | Crack=False, Sev=No Damage | **EXECUTED / PASSED** | Score: 0.0/100, Routine Monitoring |
| **AI-02** | AI Regression: Longitudinal Crack | Crack=True, Sev=Severe Damage| Crack=True, Sev=Severe Damage| **EXECUTED / PASSED** | Score: 80.0/100, Urgent Review |
| **AI-03** | AI Regression: Severe Alligator Crack | Crack=True, Sev=Severe Damage| Crack=True, Sev=Severe Damage| **EXECUTED / PASSED** | Score: 80.0/100, Progression detected |
| **AI-04** | AI Regression: Hairline Defect | Crack=True, Sev=Severe Damage| Crack=True, Sev=Severe Damage| **EXECUTED / PASSED** | Score: 80.0/100, Topology score: +15 |
| **AI-05** | AI Regression: Follow-Up Inspection | Crack=True, Sev=Critical | Crack=True, Sev=Critical | **EXECUTED / PASSED** | Score: 95.0/100, Density > 5% |
| **ERR-01** | Unsupported Extension (.exe) | HTTP 415 Unsupported Media | HTTP 415 Unsupported Media | **EXECUTED / PASSED** | Clean client rejection |
| **ERR-02** | Corrupted Image Content (.png) | HTTP 400 Bad Request | HTTP 400 Bad Request | **EXECUTED / PASSED** | OpenCV decoding guard |
| **ERR-03** | Empty Image Payload | HTTP 400 Bad Request | HTTP 400 Bad Request | **EXECUTED / PASSED** | Minimum payload size guard |
| **ERR-04** | Missing Inspection ID for Report | HTTP 404 Not Found | HTTP 404 Not Found | **EXECUTED / PASSED** | Missing record cleanly handled |
| **ERR-05** | Invalid Report Format Query Parameter | HTTP 422 Unprocessable Entity| HTTP 422 Unprocessable Entity| **EXECUTED / PASSED** | Query regex validation `^(csv\|pdf)$` |

---

### 2. Specific Security & Reliability Tests (Verification & Audit Status)

The following advanced reliability and security edge cases were reviewed during the final audit:

| Test ID | Test Target | Description / Vectors | Status in Test Suite | Technical Rationale & Current Protection |
|---|---|---|:---:|---|
| **ADV-01** | JWT Expiry Simulation | Issuing expired token or testing past 24-hr TTL | **NOT RUN** | `SEC-06` tested malformed signatures. PyJWT natively validates `exp` claims with `jwt.ExpiredSignatureError`, but expired token generation was not simulated in automated runner. |
| **ADV-02** | SQL Injection (SQLi) | Injecting `' OR '1'='1` in auth or query params | **NOT RUN** | All database queries are constructed via SQLAlchemy ORM parameterized statements (`db.query(User).filter(User.username == ...)`), preventing SQL injection by design; not tested with active fuzzing payloads. |
| **ADV-03** | Path Traversal | Injecting `../../etc/passwd` in filename / format | **NOT RUN** | Filenames are sanitized via UUID generation and format parameter is strictly validated via regex `^(csv\|pdf)$` (`ERR-05`); filesystem path traversal attacks were not explicitly fuzzed. |
| **ADV-04** | Oversized Uploads | Submitting >50 MB payloads to `/api/inspections/analyze` | **NOT RUN** | `ERR-01` tested invalid types and `ERR-03` tested empty files; payloads exceeding web server buffer limits were not tested in the automated runner. |
| **ADV-05** | Database Unavailability | Simulating SQLite connection drop / disk lock | **NOT RUN** | Live automated teardown of SQLite DB was scoped out to avoid risking operational database integrity. |
| **ADV-06** | Model-Loading Failure | Simulating missing or corrupted `.pt` checkpoint | **NOT RUN** | Handled in code via fallback handling (`backend/services/detector.py`), but runtime corruption of the active model file was not triggered during automated suite. |

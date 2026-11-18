# InfraScan API endpoint inventory

Checked against the FastAPI routers on branch `feature/milestone-1-2-demo`.
Base URL for the local demo: `http://127.0.0.1:8000`.

Authentication is a bearer JWT from `POST /auth/login` (OAuth2 password form). The access token expires after `ACCESS_TOKEN_EXPIRE_MINUTES` (60 by default). Logout is done in the browser by deleting the token. The API does not keep a server session.

Roles used below:

| Short name | Database role |
|---|---|
| Admin | Administrator |
| Manager | Infrastructure Manager |
| Inspector | Infrastructure Inspector |
| Civil | Civil Engineer |
| Maintenance | Maintenance Engineer |

Self-service registration may choose Civil, Inspector, or Maintenance. Admin and Manager accounts are created by seed data or by an administrator.

| Method | Path | Purpose | Auth | Role | Body / parameters | Success | Failure |
|---|---|---|---|---|---|---|---|
| GET | `/health` | Liveness | No | Public | None | 200 |  |
| GET | `/auth/roles` | Role list | Optional | Public sees self-service roles. Admin sees all. | None | 200 |  |
| POST | `/auth/register` | Create a user | No | Public, self-service roles only | JSON: email, full_name, password, optional role_id | 201 | 400 duplicate or bad role, 403 privileged role |
| POST | `/auth/login` | Issue a JWT | No | Any active user | Form: username (email), password | 200 | 401 bad credentials, 403 inactive |
| GET | `/auth/me` | Current profile | Bearer | Any active user | None | 200 | 401 missing, invalid, or expired token, 403 inactive |
| PUT | `/auth/me` | Update own name or email | Bearer | Any active user | JSON: full_name, email | 200 | 400 email taken, 401 |
| POST | `/auth/change-password` | Change own password | Bearer | Any active user | JSON: old_password, new_password | 200 | 400 wrong old password, 401 |
| GET | `/auth/oauth/google` | Google sign-in stub | No | Public | None |  | 501 not implemented |
| GET | `/users/` | List users | Bearer | Admin | Query: skip, limit | 200 | 401, 403 |
| GET | `/users/inspectors` | List active inspectors | Bearer | Any active user | None | 200 | 401 |
| PUT | `/users/{user_id}` | Change role or active flag | Bearer | Admin | JSON: role_id, optional is_active | 200 | 400 bad role, 401, 403, 404 |
| GET | `/assets/` | List assets | Bearer | Any active user | Query: page, size, search, asset_type | 200 | 401 |
| GET | `/assets/{asset_id}` | Read one asset | Bearer | Any active user | Path: asset_id | 200 | 401, 404 |
| POST | `/assets/` | Create an asset | Bearer | Admin, Manager | JSON asset fields, including asset_code, name, type | 201 | 400 duplicate code, 401, 403 |
| PUT | `/assets/{asset_id}` | Update an asset | Bearer | Admin, Manager | JSON partial asset fields | 200 | 400 duplicate code, 401, 403, 404 |
| DELETE | `/assets/{asset_id}` | Delete an asset with no inspections | Bearer | Admin, Manager | Path: asset_id | 204 | 401, 403, 404, 409 if inspections exist |
| GET | `/inspections/` | Inspection history | Bearer | Any active user | Query: asset_id, status | 200 | 401 |
| GET | `/inspections/{inspection_id}` | Read one inspection | Bearer | Any active user | Path: inspection_id | 200 | 401, 404 |
| POST | `/inspections/` | Create an inspection | Bearer | Admin, Manager, Inspector | JSON: asset_id, inspector_id, inspection_date, optional notes and status | 201 | 400 bad asset or inspector, 401, 403 if an inspector assigns someone else |
| PUT | `/inspections/{inspection_id}` | Update an inspection | Bearer | Admin and Manager: any field. Civil: notes and status. Inspector: own inspection only. Maintenance: denied. | JSON partial inspection fields | 200 | 401, 403, 404 |
| POST | `/inspections/{inspection_id}/images` | Upload images | Bearer | Admin, Manager, or the assigned Inspector | Multipart field `files` | 201 | 400 type, size, duplicate, or unreadable image, 401, 403, 404 |
| GET | `/inspections/{inspection_id}/images` | List images | Bearer | Any active user | Path: inspection_id | 200 | 401 |
| GET | `/images/{image_id}/preview` | Original or enhanced preview | No | Public if the id is known | Query: mode=original or enhanced | 200 image | 404, 500 if enhance fails |
| GET | `/models/status` | Weight files on disk | Bearer | Any active user | None | 200 | 401 |
| GET | `/inspections/{inspection_id}/analyses` | Saved analyses | Bearer | Any active user | Path: inspection_id | 200 | 401 |
| GET | `/images/{image_id}/analysis` | One saved analysis | Bearer | Any active user | Path: image_id | 200 | 401, 404 |
| POST | `/images/{image_id}/analyze` | Run quality, classification, detection, segmentation, and geometry | Bearer | Admin, Manager, Civil, Inspector. Maintenance is denied. | Path: image_id | 200 | 400 corrupt image, 401, 403, 404 |
| GET | `/images/{image_id}/analysis/overlay` | Overlay JPEG | Bearer | Any active user | Path: image_id | 200 image/jpeg | 401, 404 |
| GET | `/images/{image_id}/analysis/mask` | Mask PNG | Bearer | Any active user | Path: image_id | 200 image/png | 401, 404 |
| GET | `/stats` | Dashboard counts | Bearer | Any active user | None | 200 | 401 |
| GET | `/uploads/{filename}` | Stored file | No | Public if the filename is known | Path: randomized filename | 200 | 404 |

`POST /images/{image_id}/analyze` returns `classification`, `detection`, `segmentation`, and `geometry` objects. A completed detection with `reliable: false` and an empty `detections` list is the expected YOLO outcome for the current weights. Do not treat missing boxes as a failed test.

Import `postman/InfraScan_API_Tests.postman_collection.json` and `postman/InfraScan_Local.postman_environment.json`. Fill `demo_password` and `sample_image` in Postman. Do not save those values back into git.

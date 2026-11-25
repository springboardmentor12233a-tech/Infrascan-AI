"""Background Job Worker for InfraScan.

Consumes jobs from the `jobs` table using `SKIP LOCKED` concurrency control on PostgreSQL,
supporting async analysis runs, report generation, and batch imports with retries,
progress updates, and graceful termination.
"""

from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import signal
import sys
import time
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine
from app.models.job import Job
from app.models.user import User

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [Worker] %(message)s",
)
logger = logging.getLogger("worker")

HEARTBEAT_FILE = Path(__file__).resolve().parent.parent / "storage" / "worker_heartbeat.json"


def write_heartbeat() -> None:
    """Record worker heartbeat timestamp."""
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        HEARTBEAT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(HEARTBEAT_FILE, "w", encoding="utf-8") as f:
            json.dump({"timestamp": now_iso, "pid": os.getpid(), "status": "online"}, f)
    except Exception as e:
        logger.warning(f"Failed to write worker heartbeat: {e}")


def is_worker_online(max_age_seconds: float = 30.0) -> bool:
    """Check if worker heartbeat is recent."""
    if not HEARTBEAT_FILE.exists():
        return False
    try:
        with open(HEARTBEAT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        ts_str = data.get("timestamp")
        if not ts_str:
            return False
        ts = datetime.fromisoformat(ts_str)
        now = datetime.now(timezone.utc)
        return (now - ts).total_seconds() <= max_age_seconds
    except Exception:
        return False

_RUNNING = True


def _signal_handler(signum, frame):
    global _RUNNING
    logger.info(f"Received termination signal ({signum}). Shutting down worker gracefully...")
    _RUNNING = False


def _register_signals():
    try:
        import threading
        if threading.current_thread() is threading.main_thread():
            signal.signal(signal.SIGINT, _signal_handler)
            signal.signal(signal.SIGTERM, _signal_handler)
    except (ValueError, AttributeError):
        pass


_register_signals()


def fetch_next_job(db: Session) -> Optional[Job]:
    """Fetch the next pending job safely, using SKIP LOCKED when supported."""
    query = db.query(Job).filter(Job.status == "pending").order_by(Job.created_at.asc())
    # Use with_for_update(skip_locked=True) for PostgreSQL to avoid lock contention
    if engine.dialect.name == "postgresql":
        query = query.with_for_update(skip_locked=True)
    return query.first()


def execute_job(job_id: int, db: Session) -> bool:
    """Execute a single job by id with progress tracking and retry logic."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job or job.status != "pending":
        return False

    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    job.progress = 10
    db.commit()

    logger.info(f"Processing Job #{job.id} (type: {job.job_type}, attempt: {job.retries + 1}/{job.max_retries})")

    try:
        payload = json.loads(job.payload_json) if job.payload_json else {}

        if job.job_type == "analysis_run":
            from app.services.analysis_service import execute_image_analysis
            run_id = payload.get("run_id")
            image_id = payload.get("image_id")
            mm_per_pixel = payload.get("mm_per_pixel")

            job.progress = 30
            db.commit()

            run = execute_image_analysis(
                run_id=run_id,
                image_id=image_id,
                db=db,
                mm_per_pixel=mm_per_pixel,
            )

            job.progress = 100
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            job.result_json = json.dumps({
                "run_id": run.run_id,
                "status": run.status,
                "detections_count": len(run.detections) if run.detections else 0,
                "measurements_count": len(run.crack_measurements) if run.crack_measurements else 0,
            })
            db.commit()
            logger.info(f"Job #{job.id} (analysis_run) completed successfully.")
            return True

        elif job.job_type == "report_generation":
            from app.services.report_service import create_inspection_report
            inspection_id = payload.get("inspection_id")
            notes = payload.get("notes")

            # Look up initiating user
            user = db.query(User).filter(User.user_id == job.user_id).first() if job.user_id else None
            if not user:
                user = db.query(User).filter(User.role == "admin").first()

            job.progress = 40
            db.commit()

            report = create_inspection_report(
                db=db,
                inspection_id=inspection_id,
                user=user,
                notes=notes,
            )

            job.progress = 100
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            job.result_json = json.dumps({
                "report_id": report.report_id,
                "version_number": report.version_number,
                "status": report.status,
            })
            db.commit()
            logger.info(f"Job #{job.id} (report_generation) completed successfully.")
            return True

        elif job.job_type == "batch_import":
            items = payload.get("items", [])
            total = max(len(items), 1)
            for idx, item in enumerate(items):
                time.sleep(0.01)  # Simulate chunk processing
                job.progress = int(((idx + 1) / total) * 100)
                db.commit()

            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            job.result_json = json.dumps({"imported_count": len(items)})
            db.commit()
            logger.info(f"Job #{job.id} (batch_import) completed successfully.")
            return True

        else:
            raise ValueError(f"Unknown job_type '{job.job_type}'")

    except Exception as e:
        logger.error(f"Error executing Job #{job.id}: {e}", exc_info=True)
        job.retries += 1
        if job.retries < job.max_retries:
            job.status = "pending"
            job.error_message = f"Attempt {job.retries} failed: {str(e)}. Retrying..."
        else:
            job.status = "failed"
            job.completed_at = datetime.now(timezone.utc)
            job.error_message = f"Job failed after {job.max_retries} attempts: {str(e)}"
        db.commit()
        return False


def run_worker_loop(poll_interval: float = 2.0, max_iterations: Optional[int] = None) -> None:
    """Main worker loop with model warmup."""
    logger.info("InfraScan Background Worker started. Warming up models...")
    try:
        from app.services.analysis_service import warmup_models
        warmup_models()
    except Exception as e:
        logger.warning(f"Model warmup encountered issue: {e}")

    logger.info("Waiting for jobs...")
    iterations = 0
    while _RUNNING:
        write_heartbeat()
        if max_iterations is not None and iterations >= max_iterations:
            break
        iterations += 1

        db = SessionLocal()
        try:
            job = fetch_next_job(db)
            if job:
                execute_job(job.id, db)
            else:
                time.sleep(poll_interval)
        except Exception as e:
            logger.error(f"Worker iteration error: {e}", exc_info=True)
            time.sleep(poll_interval)
        finally:
            db.close()

    logger.info("InfraScan Background Worker shut down.")


if __name__ == "__main__":
    run_worker_loop()

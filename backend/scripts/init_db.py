"""Initializes a fresh database by creating all tables and running all idempotent migrations.
Safe to run on a new empty database or an existing database.
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.database import Base, engine
import app.models  # Ensure all SQLAlchemy models are registered


def init_database():
    print("=" * 80)
    print("INITIALIZING DATABASE TABLES AND MIGRATIONS")
    print("=" * 80)

    # 1. Create Base tables
    print("Creating all tables via Base.metadata.create_all...")
    Base.metadata.create_all(bind=engine)
    print("Base metadata tables created successfully.")

    # 2. Run migrations idempotently
    try:
        from scripts.migrate_preprocess import run_migration as m_prep
        m_prep()
    except Exception as e:
        print(f"Notice (preprocess migration): {e}")

    try:
        from scripts.migrate_severity import run_migration as m_sev
        m_sev()
    except Exception as e:
        print(f"Notice (severity migration): {e}")

    try:
        from scripts.migrate_explanations import run_migration as m_exp
        m_exp()
    except Exception as e:
        print(f"Notice (explanations migration): {e}")

    try:
        from scripts.migrate_m3_part2 import run_migration as m_m3
        m_m3()
    except Exception as e:
        print(f"Notice (m3_part2 migration): {e}")

    try:
        from scripts.migrate_phase1 import run_migration as m_p1
        m_p1()
    except Exception as e:
        print(f"Notice (phase1 migration): {e}")

    try:
        from scripts.migrate_phase2 import run_migration as m_p2
        m_p2()
    except Exception as e:
        print(f"Notice (phase2 migration): {e}")

    try:
        from scripts.migrate_phase3 import run_migration as m_p3
        m_p3()
    except Exception as e:
        print(f"Notice (phase3 migration): {e}")

    try:
        from scripts.migrate_phase4 import run_migration as m_p4
        m_p4()
    except Exception as e:
        print(f"Notice (phase4 migration): {e}")

    try:
        from scripts.migrate_phase5 import run_migration as m_p5
        m_p5()
    except Exception as e:
        print(f"Notice (phase5 migration): {e}")

    try:
        from scripts.migrate_phase2_events import run_migration as m_events
        m_events()
    except Exception as e:
        print(f"Notice (phase2 events migration): {e}")

    print("=" * 80)
    print("DATABASE INITIALIZATION COMPLETED.")
    print("=" * 80)


if __name__ == "__main__":
    init_database()

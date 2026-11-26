import sys, os
sys.path.insert(0, r'E:\infosys\Internship\InfraScan\backend')
from create_admin import create_admin_user, migrate_database
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bootstrap or create an InfraScan Administrator account.")
    parser.add_argument("--username", required=True, help="Admin username")
    parser.add_argument("--email", required=True, help="Admin email")
    parser.add_argument("--password", required=True, help="Admin password")
    parser.add_argument("--fullname", default="System Administrator", help="Admin full name")

    args = parser.parse_args()
    create_admin_user(args.username, args.email, args.password, args.fullname)

#!/usr/bin/env python3
"""Add a teacher credential to the server-managed teachers file.

Usage: sudo python3 scripts/add_teacher.py add <teacher_id>
This will prompt for a password and store a hashed password in TEACHERS_FILE.
Default TEACHERS_FILE is /etc/asproject/teachers.json; override with TEACHERS_FILE env var.
"""
import sys
import os
import json
import getpass
from werkzeug.security import generate_password_hash


def main():
    if len(sys.argv) < 3 or sys.argv[1] != "add":
        print("Usage: add_teacher.py add <teacher_id>")
        sys.exit(2)

    teacher_id = sys.argv[2]
    teachers_file = os.getenv("TEACHERS_FILE", "/etc/asproject/teachers.json")

    pwd = getpass.getpass("Password for %s: " % teacher_id)
    pwd2 = getpass.getpass("Confirm password: ")
    if pwd != pwd2:
        print("Passwords do not match")
        sys.exit(1)

    hashed = generate_password_hash(pwd)

    os.makedirs(os.path.dirname(teachers_file), exist_ok=True)

    try:
        if os.path.exists(teachers_file):
            with open(teachers_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {}

        data[teacher_id] = hashed

        with open(teachers_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        print(f"Added teacher {teacher_id} to {teachers_file}")
    except Exception as e:
        print("Error writing teachers file:", e)
        sys.exit(1)


if __name__ == "__main__":
    main()

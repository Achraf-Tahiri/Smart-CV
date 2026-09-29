"""Reject common private data artifacts and credential patterns in tracked files.

This is a guardrail, not proof that arbitrary free text is free of personal data.
Review new fixtures and screenshot content before publishing them.
"""

import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
FORBIDDEN_SUFFIXES = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".db", ".sqlite", ".sqlite3", ".dump", ".pem", ".key"}
TOKEN_PATTERNS = [
    rb"gsk_[A-Za-z0-9]{25,}",
    rb"gh[pousr]_[A-Za-z0-9]{30,}",
    rb"github_pat_[A-Za-z0-9_]{30,}",
    rb"AIza[A-Za-z0-9_-]{30,}",
    rb"hf_[A-Za-z0-9]{25,}",
    rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
]
paths = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
errors = []
for name in filter(None, paths):
    path = pathlib.Path(name)
    if path.suffix.lower() in FORBIDDEN_SUFFIXES:
        errors.append(f"Private-data file type: {name}")
    if path.name.startswith(".env") and not path.name.endswith(".example"):
        errors.append(f"Environment file: {name}")
    if path.name in {"credentials.json", "service-account.json"}:
        errors.append(f"Credential file: {name}")
    disk_path = ROOT / path
    if disk_path.is_file():
        data = disk_path.read_bytes()
        if any(re.search(pattern, data) for pattern in TOKEN_PATTERNS):
            errors.append(f"Potential credential: {name}")
for message in errors:
    print(message, file=sys.stderr)
if errors:
    sys.exit(1)
print("Public-file guard passed: no prohibited documents, databases, environment files, or known credential patterns.")

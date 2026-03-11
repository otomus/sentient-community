#!/usr/bin/env python3
"""Secret scanner — checks files for leaked credentials, keys, and absolute paths."""

import os
import re
import sys

# Filenames that should never be committed
FORBIDDEN_FILES = {".env", "credentials.json"}
FORBIDDEN_EXTENSIONS = {".pem", ".key"}

# Content patterns that indicate leaked secrets
SECRET_PATTERNS = [
    (r"sk-[A-Za-z0-9]{20,}", "OpenAI/Stripe secret key"),
    (r"ghp_[A-Za-z0-9]{36,}", "GitHub personal access token"),
    (r"AKIA[A-Z0-9]{16}", "AWS access key ID"),
    (r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", "Bearer token"),
    (r"-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----", "Private key"),
    (r"(?:mongodb|postgres|mysql)://[^\s\"']+:[^\s\"']+@", "Database connection string"),
    (r"(?:api_key|apikey|api-key)\s*[=:]\s*[\"']?[A-Za-z0-9\-._]{16,}", "API key assignment"),
    (r"(?:secret|password|passwd)\s*[=:]\s*[\"']?[^\s\"']{8,}", "Secret/password assignment"),
]

# Absolute path patterns
ABS_PATH_PATTERNS = [
    (r"/Users/[^\s\"']+", "macOS absolute path"),
    (r"/home/[^\s\"']+", "Linux absolute path"),
    (r"C:\\Users\\[^\s\"']+", "Windows absolute path"),
]


def check_file(filepath: str) -> list[str]:
    """Check a single file for secrets. Returns list of violation messages."""
    violations = []
    basename = os.path.basename(filepath)
    _, ext = os.path.splitext(basename)

    # Check forbidden filenames
    if basename in FORBIDDEN_FILES or ext in FORBIDDEN_EXTENSIONS:
        violations.append(f"  FORBIDDEN FILE: {filepath}")
        return violations

    # Skip binary files
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except (OSError, UnicodeDecodeError):
        return violations

    for pattern, desc in SECRET_PATTERNS:
        matches = re.findall(pattern, content)
        for match in matches:
            violations.append(f"  {desc}: {filepath} ({match[:40]}...)")

    for pattern, desc in ABS_PATH_PATTERNS:
        matches = re.findall(pattern, content)
        for match in matches:
            violations.append(f"  {desc}: {filepath} ({match[:60]})")

    return violations


def scan_directory(path: str) -> list[str]:
    """Scan a directory tree for secrets. Returns list of violations."""
    violations = []
    for root, dirs, files in os.walk(path):
        # Skip hidden directories and node_modules
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "node_modules"]
        for fname in files:
            filepath = os.path.join(root, fname)
            violations.extend(check_file(filepath))
    return violations


def main():
    paths = sys.argv[1:] if len(sys.argv) > 1 else ["."]
    all_violations = []

    for path in paths:
        if os.path.isfile(path):
            all_violations.extend(check_file(path))
        elif os.path.isdir(path):
            all_violations.extend(scan_directory(path))

    if all_violations:
        print("SECRET SCAN FAILED — violations found:")
        for v in all_violations:
            print(v)
        sys.exit(1)
    else:
        print("Secret scan passed — no violations found.")
        sys.exit(0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Standardize all nerves to the required structure.

For incomplete nerves (missing size dirs): generates large/, medium/, small/,
tinylm/ directories with context.json + meta.json, and test_cases.json.

For ALL nerves: classifies and adds platform tags (desktop, iot, server)
to bundle.json.
"""

import json
from pathlib import Path

NERVES_DIR = Path(__file__).parent

# ── Platform classification (explicit per-nerve mapping) ─────────────────
# Each nerve is manually classified into one or more platforms:
#   desktop — runs on user workstations/laptops (GUI, productivity, local dev)
#   iot     — runs on IoT/smart-home/embedded devices
#   server  — runs on servers/infrastructure (CI, deploy, monitoring, infra)

NERVE_PLATFORMS: dict[str, list[str]] = {
    # ── IoT-only ─────────────────────────────────────────────────────────
    "actuator_nerve":           ["iot"],
    "camera_snapshot_nerve":    ["iot"],
    "device_nerve":             ["iot"],
    "light_nerve":              ["iot"],
    "lock_nerve":               ["iot"],
    "sensor_nerve":             ["iot"],
    "speaker_nerve":            ["iot"],
    "thermostat_nerve":         ["iot"],

    # ── IoT + desktop ────────────────────────────────────────────────────
    "barcode_nerve":            ["desktop", "iot"],
    "health_summary_nerve":     ["desktop", "iot"],
    "music_identify_nerve":     ["desktop", "iot"],
    "qr_nerve":                 ["desktop", "iot"],
    "reminder_nerve":           ["desktop", "iot"],
    "sleep_data_nerve":         ["iot"],
    "weather_nerve":            ["desktop", "iot"],

    # ── Desktop-only (GUI interaction) ───────────────────────────────────
    "click_nerve":              ["desktop"],
    "clipboard_nerve":          ["desktop"],
    "form_fill_nerve":          ["desktop"],
    "hotkey_nerve":             ["desktop"],
    "image_capture_nerve":      ["desktop"],
    "screen_read_nerve":        ["desktop"],
    "scroll_nerve":             ["desktop"],
    "type_nerve":               ["desktop"],
    "ui_review_nerve":          ["desktop"],
    "window_nerve":             ["desktop"],

    # ── Desktop-only (productivity / personal) ───────────────────────────
    "budget_nerve":             ["desktop"],
    "contract_review_nerve":    ["desktop"],
    "docx_nerve":               ["desktop"],
    "expense_track_nerve":      ["desktop"],
    "fitness_plan_nerve":       ["desktop"],
    "gif_nerve":                ["desktop"],
    "goal_track_nerve":         ["desktop"],
    "habit_track_nerve":        ["desktop"],
    "lesson_plan_nerve":        ["desktop"],
    "note_nerve":               ["desktop"],
    "nutrition_nerve":          ["desktop"],
    "pptx_nerve":               ["desktop"],
    "quiz_nerve":               ["desktop"],
    "reflect_nerve":            ["desktop"],
    "wireframe_nerve":          ["desktop"],
    "xlsx_nerve":               ["desktop"],

    # ── Server-only (infra / ops / CI) ───────────────────────────────────
    "backup_nerve":             ["server"],
    "cert_check_nerve":         ["server"],
    "ci_check_nerve":           ["server"],
    "db_nerve":                 ["server"],
    "deploy_nerve":             ["server"],
    "dns_check_nerve":          ["server"],
    "docker_nerve":             ["server"],
    "embedding_nerve":          ["server"],
    "escalation_nerve":         ["server"],
    "etl_nerve":                ["server"],
    "incident_nerve":           ["server"],
    "infra_audit_nerve":        ["server"],
    "pkg_nerve":                ["server"],
    "port_scan_nerve":          ["server"],
    "vuln_scan_nerve":          ["server"],
    "webhook_nerve":            ["server"],

    # ── Desktop + server (dev tools, git, code) ──────────────────────────
    "code_review_nerve":        ["desktop", "server"],
    "coverage_nerve":           ["desktop", "server"],
    "deps_nerve":               ["desktop", "server"],
    "file_backup_nerve":        ["desktop", "server"],
    "file_diff_nerve":          ["desktop", "server"],
    "file_find_nerve":          ["desktop", "server"],
    "file_nerve":               ["desktop", "server"],
    "file_organize_nerve":      ["desktop", "server"],
    "file_watch_nerve":         ["desktop", "server"],
    "format_nerve":             ["desktop", "server"],
    "git_branch_nerve":         ["desktop", "server"],
    "git_cleanup_nerve":        ["desktop", "server"],
    "git_clone_nerve":          ["desktop", "server"],
    "git_commit_nerve":         ["desktop", "server"],
    "git_conflict_nerve":       ["desktop", "server"],
    "git_history_nerve":        ["desktop", "server"],
    "git_merge_nerve":          ["desktop", "server"],
    "git_pull_nerve":           ["desktop", "server"],
    "git_push_nerve":           ["desktop", "server"],
    "git_rebase_nerve":         ["desktop", "server"],
    "git_stash_nerve":          ["desktop", "server"],
    "git_tag_nerve":            ["desktop", "server"],
    "image_ocr_nerve":          ["desktop", "server"],
    "license_check_nerve":      ["desktop", "server"],
    "lint_nerve":               ["desktop", "server"],
    "privacy_audit_nerve":      ["desktop", "server"],
    "process_nerve":            ["desktop", "server"],
    "regex_nerve":              ["desktop", "server"],
    "schedule_nerve":           ["desktop", "server"],
    "system_design_nerve":      ["desktop", "server"],
    "technical_write_nerve":    ["desktop", "server"],
    "test_nerve":               ["desktop", "server"],

    # ── Desktop + server (content / research / AI) ───────────────────────
    "academic_research_nerve":  ["desktop", "server"],
    "ad_create_nerve":          ["desktop", "server"],
    "browse_nerve":             ["desktop", "server"],
    "campaign_plan_nerve":      ["desktop", "server"],
    "compliance_check_nerve":   ["desktop", "server"],
    "copywrite_nerve":          ["desktop", "server"],
    "crypto_analyze_nerve":     ["desktop", "server"],
    "crypto_price_nerve":       ["desktop", "server"],
    "csv_nerve":                ["desktop", "server"],
    "data_clean_nerve":         ["desktop", "server"],
    "data_explore_nerve":       ["desktop", "server"],
    "deep_research_nerve":      ["desktop", "server"],
    "doc_convert_nerve":        ["desktop", "server"],
    "domain_info_nerve":        ["desktop", "server"],
    "draft_blog_nerve":         ["desktop", "server"],
    "draft_email_nerve":        ["desktop", "server"],
    "email_nerve":              ["desktop", "server"],
    "explain_nerve":            ["desktop", "server"],
    "fact_check_nerve":         ["desktop", "server"],
    "faq_answer_nerve":         ["desktop", "server"],
    "grade_nerve":              ["desktop", "server"],
    "image_edit_nerve":         ["desktop"],
    "image_generate_nerve":     ["desktop", "server"],
    "json_extract_nerve":       ["desktop", "server"],
    "knowledge_capture_nerve":  ["desktop", "server"],
    "lead_research_nerve":      ["desktop", "server"],
    "llm_ask_nerve":            ["desktop", "server"],
    "market_research_nerve":    ["desktop", "server"],
    "page_screenshot_nerve":    ["desktop", "server"],
    "password_nerve":           ["desktop", "server"],
    "pdf_nerve":                ["desktop", "server"],
    "pitch_draft_nerve":        ["desktop", "server"],
    "portfolio_review_nerve":   ["desktop", "server"],
    "proofread_nerve":          ["desktop", "server"],
    "report_nerve":             ["desktop", "server"],
    "risk_assess_nerve":        ["desktop", "server"],
    "rss_monitor_nerve":        ["desktop", "server"],
    "seo_analyze_nerve":        ["desktop", "server"],
    "social_nerve":             ["desktop", "server"],
    "social_schedule_nerve":    ["desktop", "server"],
    "sprint_plan_nerve":        ["desktop", "server"],
    "standup_nerve":            ["desktop", "server"],
    "status_report_nerve":      ["desktop", "server"],
    "stock_analyze_nerve":      ["desktop", "server"],
    "stock_nerve":              ["desktop", "server"],
    "summarize_nerve":          ["desktop", "server"],
    "ticket_triage_nerve":      ["desktop", "server"],
    "video_download_nerve":     ["desktop", "server"],
    "video_extract_frames_nerve": ["desktop", "server"],
    "video_info_nerve":         ["desktop", "server"],
    "video_transcribe_nerve":   ["desktop", "server"],
    "video_trim_nerve":         ["desktop", "server"],
    "web_fetch_nerve":          ["desktop", "server"],
    "web_scrape_nerve":         ["desktop", "server"],
    "web_search_nerve":         ["desktop", "server"],
    "youtube_info_nerve":       ["desktop", "server"],
    "youtube_search_nerve":     ["desktop", "server"],
    "youtube_transcript_nerve": ["desktop", "server"],

    # ── Multi-platform (desktop + server + iot) ──────────────────────────
    "crypt_nerve":              ["desktop", "server", "iot"],
    "currency_nerve":           ["desktop", "server", "iot"],
    "encode_nerve":             ["desktop", "server", "iot"],
    "hash_nerve":               ["desktop", "server", "iot"],
    "json_extract_nerve":       ["desktop", "server", "iot"],
    "news_nerve":               ["desktop", "server", "iot"],
    "notification_nerve":       ["desktop", "server", "iot"],
    "sms_send_nerve":           ["desktop", "server", "iot"],
    "timestamp_nerve":          ["desktop", "server", "iot"],
    "translate_nerve":          ["desktop", "server", "iot"],
    "web_fetch_nerve":          ["desktop", "server", "iot"],

    # ── Desktop + server (comms) ─────────────────────────────────────────
    "audio_convert_nerve":      ["desktop", "server"],
    "audio_record_nerve":       ["desktop"],
    "audio_synthesize_nerve":   ["desktop", "server"],
    "audio_transcribe_nerve":   ["desktop", "server"],
    "calendar_nerve":           ["desktop", "server"],

    # ── Remaining ────────────────────────────────────────────────────────
    "file_nerve":               ["desktop", "server"],
}

# ── Tool argument templates ──────────────────────────────────────────────

TOOL_ARG_TEMPLATES: dict[str, dict] = {
    "web_search": {"query": "example search query"},
    "web_scrape": {"url": "https://example.com"},
    "web_fetch": {"url": "https://example.com/api"},
    "browser_open": {"url": "https://example.com"},
    "browser_text": {"selector": "body"},
    "browser_close": {},
    "docker_run": {"image": "nginx:latest", "ports": {"80": "8080"}},
    "docker_stop": {"container": "my-container"},
    "docker_ps": {},
    "docker_logs": {"container": "my-container"},
    "docker_build": {"path": ".", "tag": "my-image:latest"},
    "docker_pull": {"image": "nginx:latest"},
    "docker_exec": {"container": "my-container", "command": "ls -la"},
    "deploy": {"target": "production", "version": "1.0.0"},
    "ci_check": {"pipeline": "main"},
    "cert_check": {"domain": "example.com"},
    "dns_check": {"domain": "example.com", "record_type": "A"},
    "port_scan": {"host": "192.168.1.1", "ports": "1-1024"},
    "vuln_scan": {"target": "https://example.com"},
    "infra_audit": {"scope": "all"},
    "incident": {"action": "list"},
    "backup": {"source": "/data", "destination": "/backup"},
    "db_query": {"query": "SELECT * FROM users LIMIT 10"},
    "process": {"action": "list"},
    "pkg": {"action": "list"},
    "webhook": {"url": "https://example.com/hook", "payload": {}},
    "coverage": {"path": "."},
    "deps": {"action": "check"},
    "lint": {"path": "src/"},
    "test": {"path": "tests/"},
    "mouse_click": {"x": 500, "y": 300},
    "scroll": {"direction": "down", "amount": 3},
    "clipboard_read": {},
    "clipboard_write": {"text": "example text"},
    "hotkey": {"keys": ["ctrl", "c"]},
    "type_text": {"text": "hello world"},
    "screen_read": {"region": {"x": 0, "y": 0, "w": 1920, "h": 1080}},
    "form_fill": {"selector": "#email", "value": "user@example.com"},
    "page_screenshot": {"url": "https://example.com"},
    "ui_review": {"screenshot": "screen.png"},
    "image_capture": {"source": "screen"},
    "image_edit": {"path": "image.png", "action": "resize", "width": 800},
    "sensor": {"device_id": "sensor-01", "action": "read"},
    "thermostat": {"action": "get_temperature"},
    "actuator": {"device_id": "actuator-01", "action": "activate"},
    "light": {"device_id": "light-01", "action": "on"},
    "lock": {"device_id": "lock-01", "action": "status"},
    "device": {"device_id": "device-01", "action": "status"},
    "camera_snapshot": {"device_id": "cam-01"},
    "speaker": {"device_id": "speaker-01", "action": "play", "url": "alert.mp3"},
    "sleep_data": {"user_id": "user-01", "date": "2026-03-19"},
    "barcode": {"image": "barcode.png"},
    "pdf_read": {"path": "document.pdf"},
    "json_format": {"data": {}, "indent": 2},
    "file_read": {"path": "example.txt"},
    "file_write": {"path": "output.txt", "content": "data"},
    "file_list": {"path": "."},
    "file_delete": {"path": "temp.txt"},
    "file_move": {"source": "old.txt", "destination": "new.txt"},
    "file_copy": {"source": "orig.txt", "destination": "copy.txt"},
    "csv_read": {"path": "data.csv"},
    "csv_write": {"path": "output.csv", "rows": []},
    "xlsx_read": {"path": "data.xlsx"},
    "xlsx_write": {"path": "output.xlsx", "rows": []},
    "docx_read": {"path": "document.docx"},
    "docx_write": {"path": "output.docx", "content": "text"},
    "pptx_read": {"path": "slides.pptx"},
    "pptx_write": {"path": "output.pptx", "slides": []},
    "pdf_write": {"path": "output.pdf", "content": "text"},
    "qr_generate": {"data": "https://example.com"},
    "qr_read": {"image": "qr.png"},
    "gif_create": {"frames": [], "output": "animation.gif"},
    "translate": {"text": "hello", "target_lang": "es"},
    "summarize": {"text": "long text here..."},
    "sentiment": {"text": "I love this product"},
    "email_send": {"to": "user@example.com", "subject": "Hello", "body": "Hi"},
    "email_read": {"folder": "inbox", "limit": 10},
    "sms_send": {"to": "+1234567890", "body": "Hello"},
    "calendar_read": {"date": "2026-03-19"},
    "calendar_create": {"title": "Meeting", "date": "2026-03-19", "time": "10:00"},
    "reminder_set": {"text": "Check email", "time": "2026-03-19T10:00:00"},
    "note_create": {"title": "Meeting Notes", "content": "Discussion points..."},
    "note_search": {"query": "meeting"},
    "weather": {"location": "New York"},
    "stock_price": {"symbol": "AAPL"},
    "currency_convert": {"amount": 100, "from": "USD", "to": "EUR"},
    "news_search": {"query": "technology", "limit": 5},
    "rss_read": {"url": "https://example.com/feed.xml"},
    "notification_send": {"title": "Alert", "body": "Something happened"},
    "password_generate": {"length": 16},
    "hash_compute": {"algorithm": "sha256", "data": "hello"},
    "encode": {"data": "hello", "format": "base64"},
    "regex_match": {"pattern": "\\d+", "text": "abc123"},
    "timestamp": {"action": "now"},
    "crypt_encrypt": {"data": "secret", "key": "mykey"},
    "crypt_decrypt": {"data": "encrypted", "key": "mykey"},
    "git_clone": {"url": "https://github.com/user/repo.git"},
    "git_commit": {"message": "fix: resolve issue"},
    "git_push": {"remote": "origin", "branch": "main"},
    "git_pull": {"remote": "origin", "branch": "main"},
    "git_branch": {"action": "list"},
    "git_merge": {"branch": "feature"},
    "git_stash": {"action": "save"},
    "git_tag": {"name": "v1.0.0"},
    "git_log": {"limit": 10},
    "git_diff": {"path": "."},
    "git_status": {},
    "git_rebase": {"branch": "main"},
    "git_cleanup": {"action": "prune"},
    "git_conflict": {"action": "list"},
    "git_history": {"path": ".", "limit": 10},
    "llm_ask": {"prompt": "Explain this concept", "model": "default"},
    "embedding": {"text": "sample text"},
    "image_generate": {"prompt": "a sunset over mountains"},
    "image_ocr": {"path": "document.png"},
    "audio_transcribe": {"path": "recording.wav"},
    "audio_record": {"duration": 5, "output": "recording.wav"},
    "audio_synthesize": {"text": "Hello world", "output": "speech.mp3"},
    "audio_convert": {"input": "audio.wav", "output": "audio.mp3"},
    "video_download": {"url": "https://example.com/video.mp4"},
    "video_trim": {"input": "video.mp4", "start": "00:00:10", "end": "00:00:30"},
    "video_info": {"path": "video.mp4"},
    "video_extract_frames": {"path": "video.mp4", "interval": 1},
    "video_transcribe": {"path": "video.mp4"},
    "music_identify": {"path": "clip.mp3"},
    "youtube_info": {"url": "https://youtube.com/watch?v=example"},
    "youtube_search": {"query": "python tutorial"},
    "youtube_transcript": {"url": "https://youtube.com/watch?v=example"},
    "domain_info": {"domain": "example.com"},
    "crypto_price": {"symbol": "BTC"},
    # Canonical parent tool names (matching mcp_tools/ directories)
    "json_tool": {"input": "{}", "operation": "parse"},
    "csv": {"path": "data.csv", "operation": "read"},
    "regex": {"pattern": "\\d+", "text": "abc123", "operation": "match"},
    "base64": {"input": "hello world", "operation": "encode"},
    "stock": {"symbol": "AAPL", "operation": "quote"},
    "pdf": {"path": "document.pdf", "operation": "read"},
    "docx": {"path": "document.docx", "operation": "read"},
    "xlsx": {"path": "data.xlsx", "operation": "read"},
    "pptx": {"path": "slides.pptx", "operation": "read"},
    "note": {"title": "My Note", "content": "Note content"},
    "social": {"action": "post", "content": "Hello world"},
    "email": {"to": "user@example.com", "subject": "Hello", "body": "Hi"},
    "markdown_convert": {"content": "# Hello", "format": "html"},
    "screen_capture": {"region": "full"},
    "camera_capture": {"device_id": "cam-01"},
    "sleep_tracker_read": {"user_id": "user-01", "date": "2026-03-19"},
    "http_get": {"url": "https://api.example.com/status"},
    "http_post": {"url": "https://api.example.com/data", "body": {}},
    "log": {"path": "/var/log/app.log", "lines": 100},
    "llm_call": {"prompt": "Explain this concept", "model": "default"},
    "code_lint": {"path": "src/", "language": "python"},
    "code_analyze": {"path": "src/main.py"},
    "code_deps": {"path": "."},
    "code_format": {"path": "src/main.py"},
    "chart_create": {"type": "bar", "data": [], "title": "Chart"},
    "math_eval": {"expression": "2 + 2 * 3"},
    "diagram_create": {"type": "flowchart", "spec": "A -> B -> C"},
    "diff_compute": {"file_a": "old.txt", "file_b": "new.txt"},
    "file_grep": {"pattern": "TODO", "path": "src/"},
    "file_search": {"pattern": "*.py", "path": "src/"},
    "rss_fetch": {"url": "https://example.com/feed.xml"},
    "alert_send": {"message": "Deployment complete", "channel": "ops"},
    "db_execute": {"query": "INSERT INTO logs VALUES (...)"},
    "get_current_time": {"timezone": "UTC"},
    "convert_timezone": {"time": "2026-03-19T10:00:00Z", "to": "America/New_York"},
    "test_run": {"path": "tests/"},
    "coverage_report": {"path": "."},
    "process_list": {},
    "process_run": {"command": "ls -la"},
    "process_kill": {"pid": 1234},
}


# ── Meta.json templates per size tier ────────────────────────────────────

SIZE_META: dict[str, dict] = {
    "large": {
        "model": "large",
        "size_class": "large",
        "contributor": {"github": "arqitect-community"},
        "capabilities": {
            "json_mode": True,
            "tool_calling": True,
            "max_context": 16384,
            "max_messages": 100,
            "include_summary": False,
        },
        "tuning": {
            "min_training_examples": 500,
            "test_cases_per_batch": 20,
            "few_shot_limit": 8,
            "lora_rank": 32,
            "lora_epochs": 2,
            "lora_lr": 2e-05,
            "lora_dropout": 0.05,
            "lora_target_modules": ["q_proj", "k_proj", "v_proj"],
            "training_max_length": 4096,
            "warmup_steps": 100,
            "eval_split": 0.1,
            "scheduler": "cosine",
            "quantization": "4bit",
            "batch_size": 1,
            "gradient_accumulation_steps": 8,
        },
        "qualification": {
            "low_quality_threshold": 0.5,
            "minimum_threshold": 0.75,
            "golden_threshold": 0.95,
            "min_iterations": 3,
            "golden_iterations": 7,
        },
    },
    "medium": {
        "model": "medium",
        "size_class": "medium",
        "contributor": {"github": "arqitect-community"},
        "capabilities": {
            "json_mode": True,
            "tool_calling": True,
            "max_context": 8192,
            "max_messages": 20,
            "include_summary": False,
        },
        "tuning": {
            "min_training_examples": 200,
            "test_cases_per_batch": 15,
            "few_shot_limit": 5,
            "lora_rank": 32,
            "lora_epochs": 3,
            "lora_lr": 5e-05,
            "lora_dropout": 0.05,
            "lora_target_modules": [
                "q_proj", "k_proj", "v_proj", "o_proj",
                "gate_proj", "up_proj", "down_proj",
            ],
            "training_max_length": 2048,
            "warmup_steps": 50,
            "eval_split": 0.1,
            "scheduler": "cosine",
            "quantization": "4bit",
            "batch_size": 2,
            "gradient_accumulation_steps": 4,
        },
        "qualification": {
            "low_quality_threshold": 0.5,
            "minimum_threshold": 0.7,
            "golden_threshold": 0.9,
            "min_iterations": 3,
            "golden_iterations": 7,
        },
    },
    "small": {
        "model": "small",
        "size_class": "small",
        "contributor": {"github": "arqitect-community"},
        "capabilities": {
            "json_mode": True,
            "tool_calling": True,
            "max_context": 4096,
            "max_messages": 5,
            "include_summary": True,
        },
        "tuning": {
            "min_training_examples": 100,
            "test_cases_per_batch": 10,
            "few_shot_limit": 3,
            "lora_rank": 12,
            "lora_epochs": 3,
            "lora_lr": 1e-04,
            "lora_dropout": 0.05,
            "lora_target_modules": ["q_proj", "k_proj", "v_proj"],
            "training_max_length": 1024,
            "warmup_steps": 20,
            "eval_split": 0.1,
            "scheduler": "linear",
            "quantization": "fp16",
            "batch_size": 4,
            "gradient_accumulation_steps": 2,
        },
        "qualification": {
            "low_quality_threshold": 0.5,
            "minimum_threshold": 0.65,
            "golden_threshold": 0.85,
            "min_iterations": 3,
            "golden_iterations": 5,
        },
    },
    "tinylm": {
        "model": "tinylm",
        "size_class": "tinylm",
        "contributor": {"github": "arqitect-community"},
        "capabilities": {
            "json_mode": True,
            "tool_calling": True,
            "max_context": 2048,
            "max_messages": 1,
            "include_summary": True,
        },
        "tuning": {
            "min_training_examples": 50,
            "test_cases_per_batch": 5,
            "few_shot_limit": 2,
            "lora_rank": 8,
            "lora_epochs": 3,
            "lora_lr": 2e-04,
            "lora_dropout": 0.05,
            "lora_target_modules": ["q_proj", "v_proj"],
            "training_max_length": 512,
            "warmup_steps": 10,
            "eval_split": 0.1,
            "scheduler": "constant",
            "quantization": "fp16",
            "batch_size": 4,
            "gradient_accumulation_steps": 1,
        },
        "qualification": {
            "low_quality_threshold": 0.5,
            "minimum_threshold": 0.6,
            "golden_threshold": 0.8,
            "min_iterations": 3,
            "golden_iterations": 5,
        },
    },
}

FEW_SHOT_COUNTS = {"large": 5, "medium": 5, "small": 3, "tinylm": 2}

CONTEXT_SUFFIX = (
    "\n\nCONTEXT: You may receive context with: userDetails (name, language), "
    "location (city/region), timezone (IANA), and messages (conversation history). "
    "Use these to personalize your responses — address the user by name, respect "
    "their language preference, and consider their location/timezone when relevant."
)

CONTEXT_SUFFIX_MEDIUM = (
    "\n\nCONTEXT: You may receive: userDetails (name, language), location, timezone, "
    "and messages. Use these to personalize responses when relevant."
)

CONTEXT_SUFFIX_SMALL = (
    "\n\nCONTEXT: You may receive userDetails (name, language), location, timezone, "
    "messages. Use them to personalize responses."
)

CONTEXT_SUFFIX_TINYLM = (
    "\n\nCONTEXT: Use userDetails, location, timezone, messages from context "
    "when available."
)

SIZE_CONTEXT_SUFFIXES = {
    "large": CONTEXT_SUFFIX,
    "medium": CONTEXT_SUFFIX_MEDIUM,
    "small": CONTEXT_SUFFIX_SMALL,
    "tinylm": CONTEXT_SUFFIX_TINYLM,
}


def classify_platforms(bundle: dict) -> list[str]:
    """Look up platform tags from the explicit NERVE_PLATFORMS mapping."""
    nerve_name = bundle.get("name", "")
    return NERVE_PLATFORMS.get(nerve_name, [])


def get_tool_args(tool_name: str) -> dict:
    """Look up realistic args for a tool, falling back to a generic shape."""
    if tool_name in TOOL_ARG_TEMPLATES:
        return TOOL_ARG_TEMPLATES[tool_name]
    # Fuzzy match: check if any template key is a substring of tool_name
    for pattern, args in TOOL_ARG_TEMPLATES.items():
        if pattern in tool_name or tool_name in pattern:
            return args
    return {"input": "example"}


def build_tool_call_output(tool_name: str, args: dict) -> str:
    """Build a JSON tool-call output string."""
    call = {"action": "call", "tool": tool_name, "args": args}
    return json.dumps(call)


def generate_system_prompt(
    description: str, tools: list[dict], size: str
) -> str:
    """Generate a system prompt scaled by size tier."""
    tool_names = [t["name"] for t in tools]
    tool_list = ", ".join(tool_names)

    if size == "large":
        prompt = (
            f"{description}. "
            f"Available tools: {tool_list}. "
            f"Use the appropriate tool for each request. "
            f"Return tool calls as JSON with action, tool, and args fields. "
            f"Handle edge cases and invalid inputs gracefully."
        )
    elif size == "medium":
        prompt = (
            f"{description}. "
            f"Tools: {tool_list}. "
            f"Return tool calls as JSON with action, tool, and args fields."
        )
    elif size == "small":
        prompt = (
            f"{description}. "
            f"Tools: {tool_list}. "
            f"Respond with JSON tool calls."
        )
    else:  # tinylm
        prompt = f"{description}. Tools: {tool_list}."

    return prompt + SIZE_CONTEXT_SUFFIXES[size]


def generate_few_shot_examples(
    description: str, tools: list[dict], count: int
) -> list[dict]:
    """Generate few-shot examples using tool-call JSON format."""
    if not tools:
        return []

    examples = []
    primary_tool = tools[0]["name"]
    primary_args = get_tool_args(primary_tool)

    # Core example using primary tool
    examples.append({
        "input": f"{description.rstrip('.')}",
        "output": build_tool_call_output(primary_tool, primary_args),
    })

    # One example per additional tool (up to count - 1)
    for tool in tools[1:]:
        if len(examples) >= count:
            break
        tool_name = tool["name"]
        args = get_tool_args(tool_name)
        verb = tool_name.replace("_", " ")
        examples.append({
            "input": f"Use {verb}",
            "output": build_tool_call_output(tool_name, args),
        })

    # Pad with variations of primary tool if needed
    if len(examples) < count:
        examples.append({
            "input": f"Run {primary_tool.replace('_', ' ')} with default settings",
            "output": build_tool_call_output(primary_tool, primary_args),
        })

    if len(examples) < count:
        examples.append({
            "input": "What tools are available?",
            "output": json.dumps({
                "action": "call",
                "tool": primary_tool,
                "args": primary_args,
            }),
        })

    if len(examples) < count:
        examples.append({
            "input": f"Help me {description.lower().rstrip('.')}",
            "output": build_tool_call_output(primary_tool, primary_args),
        })

    return examples[:count]


def generate_test_cases(description: str, tools: list[dict]) -> list[dict]:
    """Generate 5 test cases covering core, edge, boundary, and negative."""
    if not tools:
        return []

    primary_tool = tools[0]["name"]
    primary_args = get_tool_args(primary_tool)

    cases = [
        {
            "input": f"{description.rstrip('.')}",
            "context": {},
            "output": build_tool_call_output(primary_tool, primary_args),
            "category": "core",
        },
        {
            "input": f"Run {primary_tool.replace('_', ' ')} with specific parameters",
            "context": {},
            "output": build_tool_call_output(primary_tool, primary_args),
            "category": "core",
        },
        {
            "input": f"Use {primary_tool.replace('_', ' ')} with empty input",
            "context": {},
            "output": json.dumps({
                "action": "call",
                "tool": primary_tool,
                "args": {},
            }),
            "category": "edge",
        },
        {
            "input": f"Run {primary_tool.replace('_', ' ')} with maximum values",
            "context": {},
            "output": build_tool_call_output(primary_tool, primary_args),
            "category": "boundary",
        },
        {
            "input": "Do something completely unrelated to this nerve",
            "context": {},
            "output": json.dumps({
                "action": "error",
                "tool": primary_tool,
                "args": {},
                "error": "Request does not match available tools",
            }),
            "category": "negative",
        },
    ]

    # Replace second test with a secondary tool test if available
    if len(tools) > 1:
        secondary = tools[1]["name"]
        secondary_args = get_tool_args(secondary)
        cases[1] = {
            "input": f"Use {secondary.replace('_', ' ')}",
            "context": {},
            "output": build_tool_call_output(secondary, secondary_args),
            "category": "core",
        }

    return cases


def write_json(path: Path, data: object) -> None:
    """Write data as formatted JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def is_nerve_complete(nerve_dir: Path) -> bool:
    """Check if a nerve has all required size directories."""
    for size in ("large", "medium", "small", "tinylm"):
        size_dir = nerve_dir / size
        if not (size_dir / "context.json").exists():
            return False
        if not (size_dir / "meta.json").exists():
            return False
    if not (nerve_dir / "test_cases.json").exists():
        return False
    return True


def standardize_nerve(nerve_dir: Path) -> dict:
    """
    Standardize a single nerve directory.

    Returns a dict summarizing what was done.
    """
    bundle_path = nerve_dir / "bundle.json"
    if not bundle_path.exists():
        return {"name": nerve_dir.name, "skipped": True, "reason": "no bundle.json"}

    bundle = json.loads(bundle_path.read_text())
    result = {"name": bundle.get("name", nerve_dir.name), "generated": [], "tags_added": []}

    # ── Step 1: Generate missing structure ────────────────────────────
    if not is_nerve_complete(nerve_dir):
        description = bundle.get("description", nerve_dir.name.replace("_", " "))
        tools = bundle.get("tools", [])

        for size in ("large", "medium", "small", "tinylm"):
            size_dir = nerve_dir / size
            count = FEW_SHOT_COUNTS[size]

            # context.json
            context_path = size_dir / "context.json"
            if not context_path.exists():
                context = {
                    "system_prompt": generate_system_prompt(description, tools, size),
                    "few_shot_examples": generate_few_shot_examples(
                        description, tools, count
                    ),
                    "max_tokens": 256,
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "qualification_score": 0,
                }
                write_json(context_path, context)
                result["generated"].append(f"{size}/context.json")

            # meta.json
            meta_path = size_dir / "meta.json"
            if not meta_path.exists():
                meta = dict(SIZE_META[size])
                meta["description"] = description
                write_json(meta_path, meta)
                result["generated"].append(f"{size}/meta.json")

        # test_cases.json
        test_path = nerve_dir / "test_cases.json"
        if not test_path.exists():
            tools = bundle.get("tools", [])
            description = bundle.get("description", nerve_dir.name.replace("_", " "))
            test_cases = generate_test_cases(description, tools)
            write_json(test_path, test_cases)
            result["generated"].append("test_cases.json")

    # ── Step 2: Set platform tags ─────────────────────────────────────
    # Remove any old platform tags first, then add the correct ones
    platform_set = {"desktop", "iot", "server"}
    platforms = classify_platforms(bundle)
    existing_tags = bundle.get("tags", [])
    non_platform_tags = [t for t in existing_tags if t not in platform_set]
    desired_tags = non_platform_tags + platforms

    if set(desired_tags) != set(existing_tags) or desired_tags != existing_tags:
        bundle["tags"] = desired_tags
        write_json(bundle_path, bundle)
        result["tags_added"] = platforms

    return result


def main() -> None:
    """Iterate all nerve directories and standardize them."""
    nerve_dirs = sorted(
        d for d in NERVES_DIR.iterdir()
        if d.is_dir() and (d / "bundle.json").exists()
    )

    print(f"Found {len(nerve_dirs)} nerve directories\n")

    generated_count = 0
    tagged_count = 0
    skipped_count = 0

    for nerve_dir in nerve_dirs:
        result = standardize_nerve(nerve_dir)

        if result.get("skipped"):
            skipped_count += 1
            continue

        if result["generated"]:
            generated_count += 1
            print(f"  Generated {len(result['generated'])} files for {result['name']}")

        if result["tags_added"]:
            tagged_count += 1
            print(f"  Added tags {result['tags_added']} to {result['name']}")

    print(f"\nDone!")
    print(f"  Nerves with new files generated: {generated_count}")
    print(f"  Nerves with new tags added: {tagged_count}")
    print(f"  Skipped: {skipped_count}")


if __name__ == "__main__":
    main()

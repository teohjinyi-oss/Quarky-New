"""
Quarky_Ai v2 — Global Configuration

All system thresholds, memory limits, worker counts, file paths,
and safety settings live here. Every system reads from this.
"""

import os
from pathlib import Path

# ─── Base Paths ─────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# ─── Version ────────────────────────────────────────────────
VERSION = "2.0.0"
CHANNEL = "beta"  # "stable" | "beta"
MEMORY_DIR = DATA_DIR / "memory"
ACTIONS_DIR = DATA_DIR / "actions"
MODELS_DIR = BASE_DIR / "models"
DB_PATH = DATA_DIR / "quarky.db"
VECTOR_DIR = DATA_DIR / "vector_db"
GRAPH_DIR = DATA_DIR / "graph"
LEARNING_DIR = DATA_DIR / "learning"
HABITS_DIR = DATA_DIR / "habits"
MONITOR_DIR = DATA_DIR / "monitor"
INTEGRATIONS_DIR = DATA_DIR / "integrations"
ENCRYPTION_KEY_FILE = DATA_DIR / ".quarky_key"

# ─── Ensure directories exist ───────────────────────────────
for _dir in (DATA_DIR, MEMORY_DIR, ACTIONS_DIR, MODELS_DIR,
             VECTOR_DIR, GRAPH_DIR, LEARNING_DIR, HABITS_DIR,
             MONITOR_DIR, INTEGRATIONS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# ─── Performance Modes ──────────────────────────────────────
FAST_MODE_THRESHOLD = 0.8      # confidence above this → fast path (single brain)
DEEP_MODE_THRESHOLD = 0.5      # confidence below this → deep path (both brains)
MAX_INPUT_LENGTH_FAST = 100    # inputs shorter than this chars → fast mode candidate

# ─── Multi-Agent Reasoning System ───────────────────────────
# Contextual, multi-agent reasoning add-on. Keeps three independent signals:
# correctness (truth), coherence (consistency), contextual value (task fit).
REASONING = {
    "enabled": True,                 # master switch for the reasoning stack
    "agent_timeout": 5.0,            # seconds to wait for each agent
    "belief_learning_rate": 0.3,     # gradual confidence revision step (0–1)
    "coherence_overlap_threshold": 0.5,  # word overlap to treat claims as same topic
    "context_selection_threshold": 0.5,  # min contextual value to select a path
}

# ─── Infrastructure: Transport ───────────────────────────────
TRANSPORT = {
    "max_chunk_size": 4096,          # bytes per chunk for packer
    "direct_call_max_payload": 2048, # payloads up to this → direct call eligible
    "async_queue_size": 256,         # max items per system queue
    "event_bus_max_subscribers": 64, # max subscribers per event type
}

# ─── Infrastructure: Worker Pool ─────────────────────────────
WORKER_POOL = {
    "default_min_workers": 1,
    "default_max_workers": 4,
    "scale_up_threshold": 0.75,    # queue fill ratio to trigger scale-up
    "scale_down_threshold": 0.25,  # queue fill ratio to trigger scale-down
    "worker_idle_timeout": 30.0,   # seconds before idle worker is removed
}

# Per-department overrides (system.department → max_workers)
DEPARTMENT_WORKERS = {
    "core.analytical.calculator": 4,
    "core.analytical.pattern_matcher": 4,
    "core.creative.concept_expander": 3,
    "infrastructure.packer": 4,
    "infrastructure.unpacker": 4,
    "memory.flexible.summarizer": 3,
    "memory.flexible.fuzzy_retriever": 2,
    "memory.permanent.retriever": 2,
    "action.app_launcher": 3,
    "action.file_manager": 3,
    "action.code_runner": 2,
}

# ─── Infrastructure: Permissions ─────────────────────────────
# Format: (source_system, target_system) → allowed
# If a pair is not listed, it's DENIED by default
PERMISSION_MATRIX = {
    ("core", "infrastructure"): True,
    ("infrastructure", "core"): True,
    ("infrastructure", "memory"): True,
    ("infrastructure", "decision"): True,
    ("infrastructure", "action"): True,
    ("infrastructure", "start"): True,
    ("memory", "infrastructure"): True,
    ("decision", "infrastructure"): True,
    ("decision", "action"): True,
    ("decision", "memory"): True,
    ("action", "infrastructure"): True,
    ("action", "decision"): True,
    ("start", "infrastructure"): True,
    ("nlp", "infrastructure"): True,
    ("infrastructure", "nlp"): True,
    # BLOCKED: action cannot directly touch permanent memory
    ("action", "memory"): False,
}

# ─── Memory System ───────────────────────────────────────────
MEMORY = {
    # Temporary (Layer 1)
    "temporary_default_ttl_hours": 24,
    "temporary_max_entries": 200,
    "temporary_file": MEMORY_DIR / "temporary.json",

    # Flexible (Layer 2)
    "flexible_max_entries": 500,
    "flexible_summary_ratio": 0.3,       # compress to 30% of original
    "flexible_file": MEMORY_DIR / "flexible.json",

    # Priority (Layer 3)
    "priority_max_entries": 300,
    "priority_initial_importance": 0.5,
    "priority_access_boost": 0.1,        # +0.1 per access
    "priority_user_boost": 0.2,          # +0.2 if user marks important
    "priority_importance_cap": 1.0,
    "priority_decay_per_day": 0.05,      # -0.05 per day
    "priority_prune_threshold": 0.1,     # auto-delete below this
    "priority_promote_threshold": 0.9,   # auto-promote to permanent above this
    "priority_promote_days": 7,          # must stay above threshold for N days
    "priority_file": MEMORY_DIR / "priority.json",

    # Permanent (Layer 4)
    "permanent_db": DB_PATH,

    # Decay engine
    "decay_interval_seconds": 300,       # run decay every 5 minutes
}

# ─── NLP Engine ──────────────────────────────────────────────
NLP = {
    "min_confidence": 0.3,       # below this → fallback to TASK intent
    "fallback_intent": "TASK",
}

# ─── Action System ───────────────────────────────────────────
ACTION = {
    "code_runner_timeout": 10,           # seconds max per execution
    "code_runner_blocked_imports": [
        "os", "subprocess", "shutil", "sys", "pathlib",
        "socket", "ctypes", "importlib",
    ],
    "log_file": ACTIONS_DIR / "action_log.json",

    # Risk levels: LOW=auto, MEDIUM=log, HIGH=confirm, CRITICAL=confirm+cooldown
    "risk_levels": {
        "open_url": "HIGH",       # always confirm before opening browser/URLs
        "open_app": "LOW",
        "open_file": "MEDIUM",
        "create_file": "MEDIUM",
        "move_file": "MEDIUM",
        "copy_file": "MEDIUM",
        "delete_file": "HIGH",
        "volume": "LOW",
        "brightness": "LOW",
        "window_manage": "LOW",
        "shutdown": "CRITICAL",
        "restart": "CRITICAL",
        "run_code": "HIGH",
        "clipboard_write": "LOW",
        "clipboard_read": "LOW",
    },
}

# ─── Start System (Voice) ───────────────────────────────────
START = {
    "wake_word": "quarky",
    "vosk_model_path": MODELS_DIR / "vosk-model-small-en-us-0.15",
    "silence_timeout": 3.0,     # seconds of silence to stop recording
    "sample_rate": 16000,
}

# ─── Backup ──────────────────────────────────────────────────
BACKUP = {
    "auto_backup_interval": 3600,       # seconds (1 hour)
    "max_hourly_backups": 24,
    "max_daily_backups": 7,
    "backup_dir": DATA_DIR / "backups",
}

# ─── Learning Engine ─────────────────────────────────────────
LEARNING = {
    "positive_boost": 0.05,
    "negative_penalty": 0.02,
    "max_boost": 1.0,
    "min_boost": -0.5,
    "data_file": DATA_DIR / "learning.json",
}

# ─── API ─────────────────────────────────────────────────────
API = {
    "host": "127.0.0.1",
    "port": 8000,
    "cors_origins": ["http://localhost:*", "http://127.0.0.1:*"],
    "sse_chunk_size": 20,               # characters per SSE chunk
    "sse_chunk_delay": 0.03,            # seconds between SSE chunks
}

# ─── Logging ─────────────────────────────────────────────────
LOG = {
    "transport_log_max_entries": 10000,
    "log_to_console": True,
    "log_level": "INFO",        # DEBUG, INFO, WARNING, ERROR
}

# ═══════════════════════════════════════════════════════════════
#  V2 ADDITIONS
# ═══════════════════════════════════════════════════════════════

# ─── Intelligence: Token Value System ────────────────────────
INTELLIGENCE = {
    # Scoring weights (should sum to ~1.0)
    "weight_specificity": 0.25,
    "weight_confirmation": 0.20,
    "weight_importance": 0.20,
    "weight_frequency": 0.10,
    "weight_recency": 0.15,
    "weight_context_relevance": 0.10,

    # Decay
    "recency_halflife_hours": 24.0,
    "frequency_scale": 5.0,
    "decay_amount": 0.02,
    "decay_interval_seconds": 300.0,

    # Tracker
    "max_active_tokens": 5000,
    "eviction_threshold": 0.10,

    # Embeddings
    "embedding_model": "all-MiniLM-L6-v2",
    "embedding_cache_size": 10000,
}

# ─── NLP v2 ──────────────────────────────────────────────────
NLP_V2 = {
    "min_confidence": 0.3,
    "fallback_intent": "TASK",

    # Spell check
    "symspell_max_distance": 2,
    "symspell_prefix_length": 7,
    "symspell_dict_path": MODELS_DIR / "frequency_dictionary_en_82_765.txt",
    "custom_dict_path": DATA_DIR / "custom_dictionary.txt",

    # Context window
    "context_window_size": 10,       # max turns to keep
    "topic_change_threshold": 0.4,   # cosine similarity below this = new topic

    # Classifier
    "tfidf_retrain_interval": 100,   # retrain after N new samples
    "tfidf_model_path": MODELS_DIR / "intent_tfidf.pkl",
}

# ─── Memory v2 (3-tier) ─────────────────────────────────────
MEMORY_V2 = {
    # Hot cache (Layer 1 — JSON in-memory)
    "hot_cache_max_entries": 500,
    "hot_cache_file": MEMORY_DIR / "hot_cache.json",

    # Vector store (Layer 2 — ChromaDB)
    "vector_db_path": str(VECTOR_DIR),
    "vector_collection": "quarky_memory",
    "vector_max_entries": 50000,
    "vector_search_top_k": 20,

    # Graph store (Layer 3 — NetworkX)
    "graph_file": GRAPH_DIR / "knowledge_graph.gml",
    "graph_max_nodes": 100000,

    # Eviction
    "eviction_check_interval": 600,  # seconds
    "eviction_batch_size": 50,

    # Encryption
    "encrypt_at_rest": True,

    # Decay
    "decay_interval_seconds": 300,
}

# ─── Web Search ──────────────────────────────────────────────
WEB = {
    "enabled": True,
    "auto_search_confidence_threshold": 0.3,  # below this, auto web search
    "max_results_per_query": 5,
    "scrape_timeout": 10,            # seconds
    "max_content_length": 5000,      # chars per page
    "learn_from_results": True,      # auto-absorb into knowledge
    "engines": ["duckduckgo"],       # available: duckduckgo, bing, google
}

# ─── System Monitoring ───────────────────────────────────────
MONITOR = {
    "enabled": True,
    "poll_interval": 5.0,            # seconds between readings
    "history_db": MONITOR_DIR / "system_stats.db",
    "max_history_days": 30,
    "alerts": {
        "cpu_threshold": 90.0,       # percent
        "memory_threshold": 85.0,    # percent
        "disk_threshold": 90.0,      # percent
        "cooldown_seconds": 300,     # min time between repeated alerts
    },
}

# ─── Habit Intelligence ──────────────────────────────────────
HABITS = {
    "enabled": True,
    "tracking_file": HABITS_DIR / "habit_log.json",
    "patterns_file": HABITS_DIR / "patterns.json",
    "min_occurrences": 3,            # minimum times before a habit is detected
    "time_cluster_minutes": 30,      # window for time-based clustering
    "confidence_for_proactive": 0.8, # must be this confident to suggest
    "max_tracked_actions": 10000,
}

# ─── Integrations (Email / Calendar) ─────────────────────────
INTEGRATIONS = {
    "google_credentials_file": INTEGRATIONS_DIR / "google_creds.json",
    "google_token_file": INTEGRATIONS_DIR / "google_token.json",
    "microsoft_client_id": "",       # set by user in setup wizard
    "microsoft_token_file": INTEGRATIONS_DIR / "ms_token.json",
    "calendar_sync_interval": 300,   # seconds
    "email_check_interval": 120,     # seconds
}

# ─── Task Automation ─────────────────────────────────────────
AUTOMATION = {
    "macros_file": DATA_DIR / "macros.json",
    "max_chain_steps": 20,
    "step_timeout": 30,              # seconds per action step
    "rollback_on_failure": True,
}

# ─── Notifications ───────────────────────────────────────────
NOTIFICATIONS = {
    "enabled": True,
    "toast_timeout": 5,              # seconds
    "sound_enabled": True,
    "priority_levels": {
        "urgent": "toast",           # Windows native toast
        "info": "in_app",            # In-app glass popup
        "low": "silent",             # Log only
    },
}

# ─── GUI Protocol (Java ↔ Python TCP) ────────────────────────
GUI = {
    "protocol_host": "127.0.0.1",
    "protocol_port": 9400,
    "max_message_size": 1_048_576,   # 1 MB
    "heartbeat_interval": 5.0,       # seconds
    "reconnect_delay": 2.0,         # seconds
    "message_types": [
        "CHAT", "ACTION", "STATUS", "STREAM",
        "MEMORY_QUERY", "NOTIFICATION", "HEARTBEAT",
        "VOICE_STATE", "SETTINGS",
    ],
}

# ─── Learning Engine v2 ──────────────────────────────────────
LEARNING_V2 = {
    "positive_boost": 0.05,
    "negative_penalty": 0.02,
    "max_boost": 1.0,
    "min_boost": -0.5,
    "data_dir": LEARNING_DIR,
    "feedback_file": LEARNING_DIR / "feedback.json",
    "corrections_file": LEARNING_DIR / "corrections.json",
    "patterns_file": LEARNING_DIR / "extracted_patterns.json",
    "retrain_interval": 100,         # samples between retraining
}

# ─── Feature Flags ───────────────────────────────────────────
FEATURES = {
    "web_search": True,              # enable web fallback for unknown questions
    "integrations": True,            # enable email/calendar integrations
    "deep_research": True,           # enable adaptive-depth web research
    "voice": True,                   # enable voice pipeline
    "habits": True,                  # enable habit tracking & proactive suggestions
    "continuous_learning": True,     # learn from every interaction
    "software_manager": True,        # winget-based install/update
}

# ═══════════════════════════════════════════════════════════════
#  Unified CONFIG accessor — all section dicts in a single dict
# ═══════════════════════════════════════════════════════════════

CONFIG = {
    "VERSION": VERSION,
    "CHANNEL": CHANNEL,
    "TRANSPORT": TRANSPORT,
    "WORKER_POOL": WORKER_POOL,
    "DEPARTMENT_WORKERS": DEPARTMENT_WORKERS,
    "PERMISSION_MATRIX": PERMISSION_MATRIX,
    "MEMORY": MEMORY,
    "NLP": NLP,
    "ACTION": ACTION,
    "START": START,
    "BACKUP": BACKUP,
    "LEARNING": LEARNING,
    "API": API,
    "LOG": LOG,
    "INTELLIGENCE": INTELLIGENCE,
    "NLP_V2": NLP_V2,
    "MEMORY_V2": MEMORY_V2,
    "WEB": WEB,
    "MONITOR": MONITOR,
    "HABITS": HABITS,
    "INTEGRATIONS": INTEGRATIONS,
    "AUTOMATION": AUTOMATION,
    "NOTIFICATIONS": NOTIFICATIONS,
    "GUI": GUI,
    "LEARNING_V2": LEARNING_V2,
    "FEATURES": FEATURES,
}

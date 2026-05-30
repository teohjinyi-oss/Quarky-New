# Quarky AI

A fully local, zero-LLM personal AI assistant with a glassmorphism desktop GUI.  
Custom token-value intelligence engine, 3-tier memory, always-on voice, and .exe packaging.

> **No cloud APIs. No telemetry. Everything runs on your machine.**

---

## Features

- **Glassmorphism Desktop UI** — PySide6/Qt frameless window with blur glass panels, animated chat bubbles, collapsible sidebar
- **Always-On Voice** — System tray with Vosk wake-word detection ("Quarky"), full-screen voice overlay with animated orb
- **Custom Intelligence Engine** — Token-value specificity system (SS/GS/SG/GG tiers) drives all routing and confidence scoring
- **3-Tier Memory** — Hot cache + ChromaDB vector store + NetworkX knowledge graph with encrypted storage
- **Learning System** — Feedback processing, correction engine, pattern extraction, web learning
- **10+ Capabilities** — Web search, email/calendar (Gmail + Outlook), system monitoring, habit tracking, task automation, notifications
- **260 Tests Passing** — Full pytest coverage across all subsystems
- **.exe Packaging** — PyInstaller spec for single-directory distribution, no Python install required

---

## Architecture

| System | Module | Role |
|--------|--------|------|
| **Intelligence Core** | `intelligence/` | Token scoring, specificity classification, tracking |
| **NLP Pipeline** | `nlp/` | Embeddings, intent classification, spell-check, entity extraction, context resolution |
| **Memory** | `memory/` | Hot cache → vector search → graph store, with decay and eviction |
| **Brain** | `core/` | Analytical (pattern matching, reasoning) + Creative (concept blending) |
| **Multi-Agent Reasoning** | `core/reasoning/` | Parallel agents + coherence + belief state + contextual value selection |
| **Decision Engine** | `decision/` | Evaluation, merging, output gating |
| **Learning** | `learning/` | Feedback, corrections, pattern extraction, training, web learning |
| **Voice** | `voice/` | Microphone, wake detection, STT, TTS, pipeline |
| **Desktop GUI** | `gui/` | PySide6 glassmorphism app, sidebar, voice overlay, toasts, system tray |
| **Infrastructure** | `infrastructure/` | JSON-over-TCP protocol, transport layer |
| **Capabilities** | `web/`, `monitor/`, `habits/`, `integrations/`, `automation/`, `notifications/` | Extended features |

## Project Structure

```text
quarky_ai/
├── config.py               # All paths, thresholds, and settings
├── orchestrator.py          # Central wiring — boot + process pipeline
├── session_v2.py            # Session management (wraps v1)
│
├── intelligence/            # Token-value scoring system
│   ├── token.py             # Token dataclass, SpecificityTier
│   ├── scorer.py            # TokenScorer with weights
│   ├── classifier.py        # SpecificityClassifier (SS/GS/SG/GG)
│   └── tracker.py           # Register, search, evict tokens
│
├── nlp/                     # Natural language pipeline
│   ├── embeddings.py        # MiniLM sentence embeddings + fallback
│   ├── classifier.py        # Intent classification
│   ├── spell_check.py       # SymSpell correction
│   ├── entity_extractor.py  # Named entity extraction
│   └── context_manager.py   # Pronoun resolution, turn tracking
│
├── memory/                  # 3-tier memory system
│   ├── hot_cache.py         # Fast in-memory LRU
│   ├── vector_store.py      # ChromaDB semantic search
│   ├── graph_store.py       # NetworkX knowledge graph
│   ├── memory_scorer.py     # Relevance scoring
│   ├── evictor.py           # Memory eviction policies
│   ├── encryptor.py         # Fernet encryption at rest
│   ├── decay.py             # Time-based decay
│   └── manager_v2.py        # Unified store/search/recall/relate
│
├── core/                    # Brain processing
│   ├── analytical/          # Pattern matching, reasoning, response gen
│   ├── creative/            # Concept blending + expanding
│   └── spinal_cord/         # Intent routing, forwarding
│
├── decision/                # Output control
│   ├── evaluator.py         # Score candidates
│   ├── merger.py            # Merge brain outputs
│   ├── output_gate.py       # Quality gating
│   └── collector.py         # DecisionContext dataclass
│
├── learning/                # Continuous improvement
│   ├── feedback.py          # Detect + apply user feedback
│   ├── correction.py        # Track wrong→right corrections
│   ├── pattern_extractor.py # Learn patterns from interactions
│   ├── trainer.py           # Retrain with accumulated examples
│   └── web_learner.py       # Learn from web search results
│
├── gui/                     # PySide6 Desktop Application
│   ├── app.py               # Entry point (high-DPI, theming)
│   ├── main_window.py       # Frameless window, backend thread
│   ├── theme.py             # Glassmorphism palette + QSS
│   ├── title_bar.py         # Custom drag/min/max/close
│   ├── chat_panel.py        # Bubbles, input bar, typing indicator
│   ├── sidebar.py           # 4-tab collapsible (history/memory/settings/monitor)
│   ├── voice_overlay.py     # Full-screen orb + live transcription
│   ├── toast.py             # Glass notification stack
│   └── tray.py              # System tray icon + menu
│
├── voice/                   # Voice pipeline
│   ├── microphone.py        # Audio capture
│   ├── wake_detector.py     # "Quarky" wake word (Vosk)
│   ├── stt.py               # Speech-to-text
│   ├── tts.py               # Text-to-speech (pyttsx3)
│   └── pipeline.py          # End-to-end voice flow
│
├── web/                     # Web search + scraping
├── monitor/                 # CPU/RAM/disk monitoring
├── habits/                  # Habit tracking + prediction
├── integrations/            # Email + calendar (Google/Microsoft)
├── automation/              # Task chains + macros
├── notifications/           # Toast + scheduled alerts
├── infrastructure/          # TCP protocol + transport
├── action/                  # Desktop automation (v1)
├── api/                     # REST API (FastAPI, v1)
└── start/                   # Wake word service (v1)

data/                        # Runtime data (created automatically)
models/                      # Vosk speech model
tests/                       # 260 pytest tests
```

## Quick Start

### Desktop GUI (recommended)

```bash
# Install dependencies
pip install -r requirements.txt

# Launch the desktop app
python -m quarky_ai.gui.app

# Or use the batch file (Windows)
QuarkyGUI.bat
```

### CLI Mode

```bash
python -m quarky_ai --mode cli
```

### Build .exe Installer

```bash
# Full build (runs tests first)
python build.py

# Skip tests
python build.py --skip-tests

# Output: dist/QuarkyAI/QuarkyAI.exe
```

### Voice Setup

1. The Vosk model should already be at `models/vosk-model-small-en-us-0.15/`
2. Launch the GUI — click the 🎤 button or say **"Quarky"**
3. Quarky listens, transcribes, processes, and speaks back

## CLI Commands

| Command | Description |
|---------|-------------|
| `/help` | List all commands |
| `/status` | System health & stats |
| `/debug` | Toggle debug output |
| `/memory` | Memory layer stats |
| `/recall <keyword>` | Search all memory layers |
| `/remember <text>` | Force-store to permanent memory |
| `/forget <layer> <id>` | Delete a memory entry |
| `/history` | Conversation history |
| `/replay` | Replay recent conversation |
| `/actions` | Recent action log |
| `/undo` | Undo last reversible action |
| `/app add <name> <path>` | Register custom app |
| `/export` | Export all data to zip |
| `/config` | Show config values |
| `/about` | Version & system info |
| `/clear` | Clear screen |
| `/quit` | Exit with stats |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/chat` | Process text → response + metadata |
| POST | `/chat/stream` | SSE streaming response |
| POST | `/chat/confirm` | Execute confirmed action |
| GET | `/health` | Health check |
| GET | `/memory/stats` | Memory layer counts |
| GET | `/memory/search?q=` | Cross-layer search |
| DELETE | `/memory/{layer}/{id}` | Forget entry |
| POST | `/memory/permanent` | Force-store |
| GET | `/actions/recent` | Action log |
| POST | `/actions/undo` | Undo last action |
| GET | `/system/status` | Full dashboard |

## Token-Value System

Quarky's intelligence is driven by a **specificity scoring** system — no LLMs, no neural nets for decision-making.

| Tier | Score | Meaning | Example |
|------|-------|---------|---------|
| **SS** | ≥ 0.65 | Specific query, specific answer | "What's the capital of France?" |
| **GS** | ≥ 0.55 | General query, specific answer | "Tell me about France" |
| **SG** | ≥ 0.40 | Specific query, general answer | "What's the meaning of life?" |
| **GG** | < 0.40 | General query, general answer | "Hey" |

## Multi-Agent Reasoning System

An add-on reasoning stack (`core/reasoning/`) layered on top of the dual-brain
pipeline. Specialised agents generate **parallel reasoning paths**, which are
then judged by **three independent signals** rather than a single unified score:

| Signal | Meaning | Produced by |
|--------|---------|-------------|
| **Correctness** | Truth validation | Logic + Evidence agent confidence |
| **Coherence** | Consistency between paths | Coherence Layer |
| **Contextual value** | Task-dependent usefulness | Contextual Evaluation Layer |

### Layers

1. **Agent Layer** (`agents.py`) — four independent agents each emit a structured
   `AgentOutput` (claims, assumptions, evidence, confidence, reasoning trace):
   - **Logic** — formal reasoning, correctness checking
   - **Creativity** — hypothesis generation, exploration
   - **Evidence** — supports claims with known data (memory-backed)
   - **Memory** — retrieves past context and recurring patterns
2. **Coherence Layer** (`coherence.py`) — flags contradictions and conflicting
   assumptions between agents but **preserves** every valid perspective instead
   of discarding disagreement.
3. **Belief State Layer** (`belief_state.py`) — maintains a structured belief
   representation across turns, revising confidence **gradually** (not binary)
   as new evidence arrives.
4. **Contextual Evaluation Layer** (`contextual_evaluation.py`) — classifies the
   task type and applies a **value-based policy profile** to prioritise paths:

   | Task type | Profile | Prioritised agents |
   |-----------|---------|--------------------|
   | Verification | `logic+evidence` | Logic + Evidence |
   | Exploration | `creativity+exploration` | Creativity (+ Memory) |
   | Explanation | `balanced` | All, weighted |
   | Mixed | `preserve-multi-path` | Multiple paths kept |

The `MultiAgentReasoningEngine` (`engine.py`) orchestrates the full flow and
returns a `ReasoningOutcome` exposing all three signals separately, so reliable
reasoning (accuracy, consistency) and exploratory reasoning (novelty) are never
collapsed into one optimisation objective.

```python
from core.reasoning import MultiAgentReasoningEngine

outcome = MultiAgentReasoningEngine().reason("Is the sky blue?")
print(outcome.task_type, outcome.signals)
```

## Tests

```bash
# Run all 260 tests
python -m pytest tests/ -q --tb=short

# Run specific module tests
python -m pytest tests/test_v2_gui.py -q         # GUI (19 tests)
python -m pytest tests/test_v2_intelligence.py -q # Intelligence (13 tests)
python -m pytest tests/test_v2_orchestrator.py -q # End-to-end (5 tests)
python -m pytest tests/test_v2_reasoning.py -q    # Multi-agent reasoning (27 tests)
```

## Dependencies

All dependencies install via pip (see `requirements.txt`):

- **GUI:** PySide6
- **Intelligence:** sentence-transformers, symspellpy, scikit-learn, numpy
- **Memory:** chromadb, networkx, cryptography
- **Voice:** vosk, pyttsx3, sounddevice
- **Web:** duckduckgo-search, beautifulsoup4, lxml
- **Integrations:** google-api-python-client, google-auth-oauthlib, msal
- **System:** psutil, plyer, pyautogui
- **Packaging:** pyinstaller

## Status

### v1 (Complete)
- [x] Infrastructure + NLP foundation
- [x] Core Brain (analytical + creative)
- [x] Memory system (4 layers)
- [x] Decision Engine
- [x] Action System (desktop automation)
- [x] CLI + REST API
- [x] Voice (Vosk STT + pyttsx3 TTS)
- [x] Integration testing — 130 tests passing

### v2 (Complete)
- [x] Token-value intelligence engine (A1-A2)
- [x] 3-tier memory with encryption (A3)
- [x] Brain v2 — analytical, creative, routing (A4)
- [x] Learning system — feedback, corrections, patterns (A5)
- [x] Infrastructure protocol (A6)
- [x] Decision engine v2 (A7)
- [x] Web search, monitoring, habits (C1-C3)
- [x] Email + calendar integrations (C4)
- [x] Task automation + notifications (C5-C6)
- [x] Voice pipeline rebuild (C7)
- [x] PySide6 desktop GUI — glassmorphism (B1-B7)
- [x] PyInstaller .exe packaging (D2)
- [x] 260 tests passing, 0 failures

---

*Zero LLM. Pure Brain. Your personal AI — running entirely on your machine.*
# Quarky-New

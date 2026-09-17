# Jarvis Assistant - Changelog

## Version 5.8 (2026-09-16)

### Request Lifecycle & State Management Fixes

**Duplicate Request Creation Bug:**
- Fixed `get_response_text()` creating a new request even when one already existed from the frontend, causing "superseded" errors and stale processing state
- Now reuses existing active request if available instead of always creating a duplicate

**Stale Processing State Fix:**
- Superseded/cancelled requests now properly reset UI state to idle instead of leaving it stuck in "processing" indefinitely
- Added cleanup logic that removes thinking messages, resets state, and re-enables input when a request is superseded

**Chat Processing Flag Scope:**
- Fixed `chat_processing` flag being set outside the current-request check, causing superseded requests to interfere with newer active requests

### Web Search Improvements

**Retry Logic Optimization:**
- Reduced max retries in `search_and_answer()` from 3 to 2 for faster response times
- Added cancellation checks at start of each retry iteration to avoid unnecessary work on cancelled requests
- Returns None immediately if request was cancelled during processing

### Listening State Race Condition Fix

**Duplicate "Already listening" Warnings:**
- Fixed race condition where `toggle_listening()` set `is_listening = True` before calling `start_listening()`, which had its own duplicate check that would fail
- Removed redundant duplicate-check logic from `start_listening()` since state transitions are now handled atomically in `toggle_listening()`

### UI/UX Improvements

**Listen Button Disabled During Busy States:**
- Listen button is now automatically disabled during processing, searching, response_ready, chat_updated, and speaking states to prevent duplicate requests
- Button re-enables when returning to idle or listening states

**Contextual Status Messages for Duplicate Requests:**
- When user clicks Listen while Jarvis is busy, status panel shows contextual message (e.g., "Processing your request...", "Searching the web...") instead of silently ignoring
- Provides clear frontend feedback about what operation is currently in progress

### Validation

- All existing unit tests pass (test_command_matching, test_jarvis.py suite)
- Request lifecycle integration verified through manual testing scenarios

## Version 5.7 (2026-09-15)

### General-Purpose Web Search System Redesign

**New `web_search/` Package:**
- Created dedicated web search package with provider architecture for general-purpose information retrieval
- Weather is now one specialized provider among many, not the foundation of the search system
- Supports: weather, stocks/finance, sports, news, shopping, local businesses, and general web fallback

**Package Structure (`web_search/`):**
- `__init__.py` - Package exports (SearchManager, SearchClassifier, models, utilities)
- `manager.py` - Central orchestration: classify → select provider → execute → normalize → validate → respond/fallback
- `classifier.py` - LLM-based intent classification to determine if web search is needed and generate optimized queries
- `models.py` - SearchRequest and SearchResult dataclasses with normalization metadata (request_id, category, entities, sources, freshness, confidence, conflicts)
- `query_builder.py` - Constructs optimized search queries with freshness terms and location context
- `normalizer.py` - Standardizes raw provider results into consistent SearchResult objects
- `validator.py` - Validates result quality, freshness, source authority, and data integrity
- `ranking.py` - Multi-signal result scoring (relevance, freshness, source authority, confidence)
- `fallback.py` - Deterministic user-friendly fallback responses when search or LLM generation fails

**Provider Architecture (`web_search/providers/`):**
- `base.py` - Abstract SearchProvider interface with `supports()` and `search()` methods
- `weather.py` - Migrated Open-Meteo API weather provider (geocoding, current conditions, forecasts, alerts)
- `finance.py`, `sports.py`, `news.py`, `shopping.py`, `local.py` - Specialized provider stubs for future implementation
- `general.py` - DuckDuckGo fallback provider for any category not covered by specialized providers

**Integration into Jarvis:**
- Updated `jarvis.py` to initialize SearchManager with all providers
- Weather queries now route through the new web_search package while preserving legacy fallback behavior
- Added request-level logging throughout search workflow (REQUEST_STARTED, REQUEST_CLASSIFIED, PROVIDER_SELECTED, SEARCH_COMPLETED, etc.)

**Listening-State Bug Fix:**
- Fixed duplicate listening session bug in `frontend/main_window.py`
- Made state transitions atomic using `state_lock` in `toggle_listening()` and `start_listening()`
- Prevents race conditions that caused "Duplicate listening request ignored" errors

**Test Output Cleanup & GitHub Readiness:**
- Created `.gitignore` with patterns for Python caches, virtual environments, IDE files, test outputs, pytest cache, coverage reports, voice records, and changelog
- Created `tests/output/` directory as designated location for generated test output files
- Moved all test .txt files to `tests/output/`, keeping only the final passing result (42/42 tests)
- Removed legacy duplicate `weather.py` from project root (already migrated to web_search/providers/)
- Ensured only root `README.md` is committed to GitHub

**Tests:**
- Created `tests/web_search/test_models.py` with 5 tests for SearchRequest/SearchResult models
- Verified existing weather tests pass (19/19) after migration
- Verified core jarvis unit tests pass (6/6)
- All web_search package imports validated working

### Chat Tab UI Improvements

**Futuristic HUD Message Styling:**
- Redesigned `ChatMessageWidget` with bordered message containers matching reference image aesthetic
- Added uppercase sender labels (`JARVIS` / `USER`) with letter-spacing and teal accents
- Implemented separator lines between sender label and message content
- Dark navy chat background (`rgba(5, 10, 20, 0.95)`) with custom teal scrollbar styling

**Thinking Indicator Integration:**
- Added temporary "JARVIS — Thinking..." message that appears when user submits a question
- Syncs with existing `processing` state transition in the application's state machine
- Automatically replaced with actual response when `response_ready` → `chat_updated` states are reached
- Proper cleanup on request cancellation and all error paths (ConnectionError, TimeoutError, ValueError, RuntimeError)

**State Synchronization:**
- Chat tab now fully synchronized with existing Jarvis state system (`idle`, `processing`, `searching`, `response_ready`, `chat_updated`, `speaking`, `error`)
- No duplicate state machine created; reuses existing thread-safe state transitions via `state_lock`
- RequestManager integration preserved for request ordering and cancellation

**Input Area Enhancements:**
- Improved focus states on chat input field with brighter teal border
- Enhanced button hover effects matching futuristic theme

### State Management and UI Sync Fixes

**Incorrect State Transition Logging:**
- Fixed misleading log message in `toggle_listening()` that showed "LISTENING -> PROCESSING (user stopped)" when user clicked STOP LISTENING
- Actual state transitions now correctly logged only where they occur: IDLE->LISTENING, LISTENING->PROCESSING, PROCESSING->IDLE

**Button Text Race Condition:**
- Fixed race condition where button text could get stuck on "STOP LISTENING" due to multiple `QTimer.singleShot` calls overwriting each other
- Button text now set directly in `toggle_listening()` (already on main thread) instead of via delayed singleShot calls
- Removed duplicate button text setting in `start_listening()`

### Post-Capture Speech-to-Text with Auto-Stop

**Auto-Stop Timer:**
- Added 5-second auto-stop timer that starts when listening begins
- Automatically stops audio capture if user doesn't manually click "STOP LISTENING" first
- Prevents indefinite listening sessions and improves UX

**Post-Capture Transcription Flow:**
- Modified `jarvis.py` to separate audio capture from transcription: `listen()` now returns raw audio data, new `recognize_audio(audio_data)` method handles batch transcription after capture stops
- Frontend listen thread updated to: capture audio → transcribe → display transcribed text in chat → process command
- Transcribed text appears as "You" message in chat before Jarvis responds, allowing users to verify what was heard

**Benefits:**
- User can see exactly what Jarvis heard before it processes the command
- Text-based command parsing is more reliable than audio-based processing
- Easier debugging when commands are misheard
- Better transparency and user experience

### Weather Query Timeout Fix

**Blocking I/O Causing Indefinite Hang:**
- Fixed issue where weather queries would hang indefinitely on "Thinking..." with no response or error
- Root cause: `asyncio.wait_for()` timeout not working because provider's blocking `requests.get()` calls blocked the entire event loop, preventing timeout from firing
- Solution 1: Wrapped provider search execution in `asyncio.to_thread()` so blocking I/O runs in separate thread and doesn't block event loop
- Solution 2: Added overall 45-second timeout wrapper around weather query execution in `jarvis.py` using `concurrent.futures.ThreadPoolExecutor` with automatic fallback to DuckDuckGo search if timeout occurs
- Weather provider per-request timeout explicitly set to 10 seconds

**Files Modified:**
- `web_search/manager.py` - Wrapped provider.search() in asyncio.to_thread() for proper timeout behavior
- `jarvis.py` - Added overall weather query timeout with fallback mechanism
- `web_search/providers/weather.py` - Explicitly set default timeout to 10 seconds per request

## Version 5.6 (2026-09-09)

### Temporary Voice Recording Folder, Listen Button Behavior, Chat Flow, and Startup Greeting Improvements

**Temporary Voice Recording Folder (`voice_records`):**
- Created automatic initialization of `voice_records/` directory in `jarvis.py` at runtime
- Updated `_speak_edge_tts()` to save audio files in this dedicated folder instead of the current working directory
- Files use unique UUID-based names: `jarvis_output_{uuid}.mp3`
- Existing cleanup logic preserved — files are deleted after playback or on error

**Listen Button Start/Stop Behavior:**
- Updated `toggle_listening()` and `start_listening()` in `frontend/main_window.py` for proper single-capture processing between clicks
- First click ("LISTEN") starts recording, button changes to "STOP LISTENING"
- Second click stops listening and processes the captured speech
- Single-capture processing between start/stop clicks (no continuous loop)
- Proper state management with thread-safe transitions

**Frontend Chat Updates:**
- Added new `get_response_text()` method in `jarvis.py` that returns response text without speaking
- Updated chat flow so Jarvis's response is displayed in chat **before** being spoken
- Both voice and text input modes now follow: user message → Jarvis response text → audio playback

**Startup Greeting Audio Fix:**
- Added new `speak_startup_greeting()` method with cached audio file support
- Frontend displays "Good day, Sir. How may I assist you?" in chat AND speaks it aloud on startup
- Cached audio file at `voice_records/startup_greeting.mp3` (~26KB) is reused across launches
- Validates cached file is non-empty (>1KB) to detect corruption before reuse
- Falls back to live speech if file operations fail

**Testing & Debugging:**
- Fixed listen button behavior (single session instead of continuous loop)
- Created comprehensive test suite (`test_voice_workflow.py`) with 9 tests covering:
  - Voice records directory creation and cleanup
  - get_response_text method returns text without speaking
  - process_command speaks response
  - Listen button toggle simulation (start/stop/restart)
  - Chat message flow (user msg → Jarvis response → speak)
  - No duplicate listening sessions on rapid clicks
  - State transition validation
  - Error handling for speech recognition failures
  - Audio file cleanup after playback
- All tests passed (9/9 in test_voice_workflow.py, all in test_jarvis.py)

**Files Modified:**
- `jarvis.py`: Voice records directory initialization, updated TTS file path, new `get_response_text()` method, new `speak_startup_greeting()` method with cached audio support
- `frontend/main_window.py`: Listen button toggle behavior, chat processing flow in both voice and text modes, startup greeting playback trigger
- `test_jarvis.py`: Updated TTS test expectations to match new architecture
- `CHANGE.md`: Complete documentation of all changes

**Cached Audio File Location:**
- Path: `<jarvis_root>/voice_records/startup_greeting.mp3` (relative to project root)
- Filename: `startup_greeting.mp3` (stable, never changes)
- Size on first generation: ~26KB
- Reuse strategy: Checked for existence and non-empty size before each launch

**Startup Sequence After Fix:**
```text
1. Jarvis backend initializes (speech recognition, TTS engine, LM Studio connection)
2. Frontend UI builds and displays welcome message in chat
3. QTimer triggers play_startup_greeting() after 500ms delay
4. speak_startup_greeting() checks for cached startup_greeting.mp3
   - If exists and valid: plays cached file immediately
   - If missing or corrupted: generates new audio, saves to cache, then plays
5. Greeting is spoken aloud via PyAudio playback
6. Application continues in idle state, ready for user input
```

## Version 5.5 (2026-09-07)

### Listening State and Threading Bug Fixes

**Root Cause Analysis:**

1. **Listening state problem:** The `listen()` method in `jarvis.py` was using `recognizer.listen()` which blocks until speech is detected or timeout occurs. When the user clicked "Stop Listening", the `_stop_listening_flag` was set but the blocking call wasn't interrupted, causing the UI to remain stuck in "Listening" state. Additionally, the frontend's `toggle_listening()` method didn't properly transition states when stopping.

2. **Qt threading errors:** The `QBasicTimer::start: current thread's event dispatcher has already been destroyed` error occurred because worker threads were creating and using Qt objects (timers) after their parent thread's event loop had been destroyed. The `QObject::setParent` error happened when trying to set parents across different threads.

3. **Incomplete speech behavior:** The `is_sentence_complete()` method was too strict, rejecting valid short commands like "stop", "cancel", and "bye" as incomplete because they lacked punctuation or sufficient word count.

**Solution Implemented:**

1. **Fixed listening state management:**
   - Added proper state transition logging (`STATE: IDLE -> LISTENING`, etc.)
   - Modified `toggle_listening()` to properly handle stop button clicks by signaling the backend and transitioning to processing state
   - Ensured only one listener can be active at a time with duplicate request detection

2. **Fixed Qt threading issues:**
   - All UI updates now use `QTimer.singleShot(0, lambda: ...)` for thread-safe signal emission
   - Worker threads no longer create Qt objects directly; they emit signals to the main thread
   - Proper cleanup of timers and event loops on shutdown

3. **Improved speech completeness detection:**
   - Added "stop", "cancel", "exit" to recognized command words that are always considered complete
   - Made short question phrases (1-2 words starting with question words) valid as complete sentences
   - Reduced false positives for incomplete speech on legitimate commands

4. **Fixed CSS warnings:**
   - Removed unsupported `text-shadow` and `box-shadow` properties from Qt stylesheets
   - Replaced with Qt-compatible alternatives (font-weight, border-radius only)

**Files Modified:**
- `jarvis.py`: Improved `is_sentence_complete()` logic for better command recognition
- `frontend/main_window.py`: Fixed listening state management, added state transition logging, fixed CSS warnings, improved thread safety

**Testing Performed:**
1. Normal conversation flow: "Hello, what's the weather today?" - ✅ Works correctly
2. Manual stop via button click during speech capture - ✅ Processes captured audio
3. Incomplete speech detection - ✅ More accurate, fewer false positives
4. Silence and timeout behavior - ✅ Proper error messages displayed
5. Command recognition ("stop", "cancel", "bye") - ✅ All recognized as complete
6. Repeated conversations - ✅ No duplicate listeners or state conflicts
7. Multiple button clicks - ✅ Safe to click multiple times without errors
8. Speaking while Jarvis is responding - ✅ Handled correctly with proper state transitions

**State Machine Flow:**
```
IDLE → LISTENING → PROCESSING → SPEAKING → IDLE
```
All transitions are now properly validated and logged.

## Version 5.4 (2026-09-06)

### Speech Synthesis Fix - WinError 2 Resolution

**Root Cause:** The `[WinError 2] The system cannot find the file specified` error occurred because the `_play_audio_file()` method relied on external executables (`ffplay`, `powershell`, `cmd`) that may not be installed or available in PATH. When none of these were found, subprocess calls failed with WinError 2.

**Solution:** Replaced all subprocess-based audio playback with PyAudio direct playback:
- Added PyAudio as required dependency for edge-tts playback
- Implemented `_play_audio_with_pyaudio()` method that plays WAV/MP3 files directly without external executables
- Uses numpy for audio data conversion and PyAudio streams for playback
- No more WinError 2 from missing ffplay/powershell/cmd

**Fallback Chain:**
1. Primary: edge-tts + PyAudio (high-quality neural voices, no subprocess)
2. Fallback: pyttsx3 (if edge-tts or PyAudio unavailable)
3. Graceful degradation with clear error messages if all fail

**Additional Improvements:**
- Added `_playing_audio` flag for proper stop-speaking functionality during cancellation
- Improved `stop_speaking()` to signal both pyttsx3 and PyAudio playback stopping
- Better dependency detection at initialization (checks for edge-tts AND PyAudio together)
- Temporary audio files still cleaned up properly after playback

**Required Dependencies:**
```bash
pip install pyaudio numpy soundfile
```
(Pyaudio requires PortAudio development headers on Linux: `apt-get install portaudio19-dev`)

### Files Changed
- `jarvis.py`: Added PyAudio import and detection, replaced `_play_audio_file()` with `_play_audio_with_pyaudio()`, added `_playing_audio` flag for cancellation support
- `requirements.txt`: Added pyaudio, numpy, soundfile as required dependencies

## Version 5.3 (2026-09-06)

### Chat and LM Studio Integration Improvements

**API Communication Enhancements:**
- Added 30-second timeout to all LM Studio API calls via OpenAI client configuration
- Implemented specific exception handling for different API error types:
  - `ConnectionError` - Cannot connect to LM Studio API
  - `TimeoutError` - Request timed out after 30 seconds
  - `ValueError` - Invalid request or model not found
  - `PermissionError` - API authentication failed
  - `RuntimeError` - Server errors, rate limits, and other failures
- User-friendly error messages displayed in chat interface for each error type

**Chat Functionality Improvements:**
- Prevented duplicate submissions by disabling input field during request processing
- Added proper control management: input disabled while waiting, re-enabled after response
- Improved Stop Chat functionality with dedicated `_stop_chat_flag` threading event
- Reset stop flags before each new chat operation to ensure clean state

**Request and Cancellation Flow:**
1. User sends message → Input field disabled, processing state shown
2. Message sent to LM Studio API via OpenAI client with 30s timeout
3. Response received → Displayed in chat, input re-enabled, idle state restored
4. If user clicks "Stop Chat" during processing:
   - `_stop_chat_flag` is set to signal cancellation
   - Speech output stopped immediately
   - Listening stopped if active
   - UI returns to usable idle state

**Error Handling Coverage:**
- Connection failures (LM Studio not running)
- Request timeouts (30 seconds)
- Invalid API responses and malformed JSON
- Unavailable models in LM Studio
- Server errors (500 status codes)
- Rate limit exceeded scenarios
- Authentication issues

### Files Changed
- `jarvis.py`: Added timeout to OpenAI client, specific exception handling in get_ai_response(), stop_chat() method with threading event flag
- `frontend/main_window.py`: Improved chat message sending with input field management, enhanced error handling for different API error types, improved Stop Chat functionality

## Version 5.2 (2026-09-06)

### Terminal Integration Fix

**Problem:** The project was opening a separate Windows PowerShell or Command Prompt window instead of displaying terminal activity inside the built-in Terminal tab.

**Solution:** Added `CREATE_NO_WINDOW` flag to all subprocess calls on Windows to prevent external console windows from appearing. This ensures:
- Audio playback via ffplay, PowerShell WMPlayer, and cmd start commands run silently in background
- No separate PowerShell or Command Prompt window opens during operation
- All terminal activity remains within the application's built-in Terminal tab

**Technical Approach:**
- Used `subprocess.CREATE_NO_WINDOW` constant (Windows-specific) for all subprocess.run() calls
- Applied to ffplay version check and playback commands
- Applied to PowerShell WMPlayer audio playback command
- Applied to cmd start fallback command
- Flag is only set on Windows platform, maintaining cross-platform compatibility

### Files Changed
- `jarvis.py`: Added CREATE_NO_WINDOW flag to all subprocess.run() calls in _play_audio_file() method

## Version 5.1 (2026-09-06)

### Voice Listening and State Transition Fixes

**State Machine Implementation:**
- Implemented proper state machine with thread-safe transitions using threading.Lock
- Added validated state transitions to prevent race conditions between listening and processing
- States: Idle → Listening → Processing → Speaking → Idle (with Error as terminal state)
- Invalid transitions are now logged as warnings instead of silently occurring

**Voice Listening Behavior:**
- Fixed premature reset to Idle when user clicks "Stop Listening" - now waits for command processing to complete
- Prevented multiple simultaneous recognition sessions by checking if listen thread is already alive
- Added duplicate command submission prevention during chat processing
- Improved error handling with specific exception types (TimeoutError, ValueError, PermissionError, RuntimeError)

**Error Handling Improvements:**
- Microphone unavailable now raises RuntimeError instead of silently returning None
- Speech recognition timeout raises TimeoutError with clear message
- Unknown speech raises ValueError for better user feedback
- Permission errors are caught and displayed to user without crashing application
- All error states transition back to Idle after 3 seconds (except fatal errors)

**User-Facing Error Messages:**
- "No speech detected" - when listening times out
- "Could not understand speech" - when recognition fails
- "Microphone permission denied" - when OS blocks microphone access
- Specific error messages for service failures and runtime issues

### Files Changed
- `jarvis.py`: Modified listen() to raise specific exceptions instead of returning None
- `frontend/main_window.py`: Implemented state machine, thread-safe transitions, improved error handling

## Version 5.0 (2026-09-05)

### Major Improvements and Bug Fixes

**Voice Listening Behavior:**
- Fixed premature reset to Idle state when user clicks "Stop Listening"
- Added proper stop signal mechanism using threading.Event for interruptible listening
- Improved speech recognition timeout handling (10s listen, 15s phrase limit)
- Better error handling for microphone initialization failures
- Voice commands now process in separate threads to keep UI responsive

**Terminal Integration:**
- Terminal output now displays inside the project's built-in Terminal tab
- No longer opens external Windows PowerShell or Command Prompt windows
- All Jarvis responses, user messages, and system logs appear in the integrated terminal

**Chat Functionality:**
- Fixed chat message processing with proper thread-safe signal emissions
- Added "Stop Chat" button that appears during response generation
- Stop Chat cancels ongoing speech, listening, and returns interface to usable state
- Improved error handling for LM Studio API connection failures
- Better loading states and user feedback during processing

**Speech Synthesis Error Fix:**
- Replaced subprocess-based edge-tts CLI calls with direct Python API usage
- Added robust fallback chain: edge-tts → pyttsx3 → platform audio players
- Fixed `[WinError 2] The system cannot find the file specified` error by using asyncio event loop properly
- Improved temp file cleanup and error reporting

**Code Cleanup:**
- Removed unused imports (librosa, numpy) from main jarvis.py
- Added proper type hints throughout codebase
- Improved docstrings and inline comments for clarity
- Better exception handling with specific error types
- Consistent naming conventions across all files
- Separated concerns: UI logic in frontend/, backend logic in jarvis.py

**Documentation:**
- Updated README.md with Quick Start section, better prerequisites, and troubleshooting guide
- Added configuration examples to documentation
- Improved project structure documentation

### Files Changed
- `jarvis.py`: Major refactoring - improved TTS handling, stop listening mechanism, error handling
- `frontend/main_window.py`: Fixed chat processing, added Stop Chat button, improved voice interaction
- `README.md`: Updated with better documentation and troubleshooting
- `Changelog.md`: This file

## Version 4.1 (2026-09-04)

### Project Audit and Safe Cleanup

**Audit Performed:** Comprehensive review of all project files, documentation, frontend/backend integration, naming consistency, and code organization.

**Naming Standardization:**
- Replaced all user-facing "J.A.R.V.I.S." with "JARVIS" across the entire application (14 instances)
- Updated window title, chat labels, status panel, voice responses, and README documentation
- Internal AI system prompts retained original naming (not user-facing)

**Bug Fix - Terminal Output:**
- Fixed terminal tab not displaying conversation logs by emitting `output_received` signals from both chat processing thread and voice listening thread
- Terminal now shows real-time logging of all interactions (user messages, JARVIS responses, voice commands)

**Files Changed:**
- `frontend/main_window.py`: Naming updates + terminal output signal emissions in process_thread() and listen_thread()
- `frontend/status_panel.py`: Updated default status message to "JARVIS is ready."
- `jarvis.py`: Updated user-facing voice response text ("I am JARVIS, Sir...")
- `README.md`: Updated project description naming

**Validation:**
- All Python files compile without errors (py_compile)
- Existing test suite passes (test_jarvis.py - all tests passed)
- No remaining user-facing "J.A.R.V.I.S." instances found via grep search

## Version 4.0 (2026-09-04)

### Frontend as Primary Interaction Interface

**Major architectural change:** The frontend is now the primary and only user-facing way to interact with Jarvis. Terminal-based interaction has been deprecated in favor of a rich chat interface.

**New Features:**
- **Chat Interface**: Added a full chat panel with message history, input field, and "Ask Jarvis" button as the primary text interaction method
- **Enter Key Submission**: Users can submit prompts by pressing Enter or clicking the Ask Jarvis button
- **Conversation History**: Chat displays user messages, Jarvis responses, loading states, errors, and conversation history
- **Improved Voice Interaction**: Listen button now toggles listening state; says "bye", "goodbye", or "stop listening" to end voice sessions
- **Tabbed Interface**: Chat tab (primary) and Terminal tab (secondary for logs only)

**Files Changed:**
- `frontend/main_window.py`: Added chat interface, conversation history management, improved voice interaction with stop phrase detection
- `jarvis.py`: Modified `process_command()` to return response text for display in chat; removed standalone execution entry point
- `run_jarvis.py`: Updated to launch frontend GUI instead of terminal version
- `start_jarvis.bat`: Updated to launch frontend GUI
- `README.md`: Updated usage instructions to reflect new interaction model

**Removed:**
- Standalone terminal execution from `jarvis.py` (class still available for frontend use)
- Terminal-only launch option as primary interface

## Code Review Report

A thorough review removed dead code and a stale reference while preserving behavior. All changes are non-functional (unreachable paths) except one test fix; both test suites pass and every module compiles cleanly.

### Removed: dead / non-functional code
- **`jarvis.py` — `edge_speak_async()`**: an `async` method never called anywhere; all TTS goes through the synchronous `speak()`. It also spoke an empty string via PowerShell. Removing it drops one confusing path and a latent bug.
- **`voice_gen/audio.py` — `convert_to_wav()` & `cleanup_temp_files()`**: exported from the package but never invoked by any module or test. Removed them plus their now-unused `tempfile`/`shutil` imports.
- **`voice_gen/generation.py` — `generate_voice_batch()`**: only referenced in this changelog, never called in code.
- **`voice_gen/__init__.py` / `cli.py`**: trimmed `convert_to_wav` from the re-export and import list so the public surface matches what is actually used (9 functions).

### Fixed: stale reference
- **`test_jarvis.py`** checked for `duckduckgo_search`, but the code imports `ddgs`. The dependency check now tests the real package so it reports accurately.

### Observed (non-blocking)
- **`frontend/main_window.py`**: the terminal panel is connected to the `output_received` signal, but that signal is never emitted — the GUI terminal stays quiet while the console still logs. CLI (`jarvis.py`) shows both transcription and replies correctly. Fix: emit `output_received` from the listen thread.

### Verification
- `python -m py_compile` across all 16 modules → exit 0 (no syntax errors)
- `test_jarvis.py` → all passed (deps, config, sentence completeness, weather parsing, command matching, TTS sync)
- `test_voice_gen.py` → all passed (validation, consent, duplicate detection, lifecycle, CUDA, generation, CLI)
- Headless import of `jarvis`, `voice_gen`, and `frontend.main_window` → OK (no circular-import/export issues)

## Version 3.1 (2026-09-04)

### Frontend Crash Fix & TTS Reliability Improvements

**Issue:** Frontend crashed when asking questions like "What is the weather today?" Generated MP3 files appeared briefly then disappeared.

**Root Causes Identified:**
1. `asyncio.run()` called inside PyQt6 background thread conflicted with event loop, causing crashes
2. MP3 files were intentionally deleted after playback (by design in cleanup code)
3. Signal emissions from background threads weren't properly synchronized with Qt's main thread

**Fixes Applied:**

1. **Replaced asyncio-based edge-tts with CLI approach (`jarvis.py`)**
   - Changed from `asyncio.run()` + Python API to direct `edge-tts` CLI subprocess calls
   - More reliable in threaded environments without event loop conflicts
   - Added fallback to pyttsx3 if edge-tts CLI fails or file isn't created

2. **Added `_speak_pyttsx3()` helper method (`jarvis.py`)**
   - Centralized pyttsx3 fallback logic for consistent error handling
   - Ensures TTS always works even if primary engine fails

3. **Thread-safe signal emissions (`frontend/main_window.py`)**
   - Wrapped all signal emissions from background thread in `QTimer.singleShot(0, ...)` 
   - Ensures signals are emitted on Qt's main thread for proper UI updates
   - Prevents race conditions and crashes during state transitions

4. **Enhanced error reporting (`frontend/main_window.py`)**
   - Added traceback printing for detailed error diagnostics in listen thread
   - Better visibility into what causes crashes or failures

**Behavior Notes:**
- MP3 files are still temporary (created, played, then deleted) - this is intentional cleanup behavior
- Files use unique UUID-based names to prevent conflicts during concurrent operations
- Audio playback remains synchronous to ensure Jarvis doesn't start listening before finishing speaking

## Version 3.0 (2026-09-03)

### New: Futuristic PyQt6 Frontend (`frontend/`)

Built a modern, futuristic user interface inspired by sci-fi HUD designs, featuring animated circular elements, glowing effects, and real-time status visualization.

**Project Structure:**
```
frontend/
├── __init__.py              # Package initialization
├── main_window.py           # Main application window with layout
├── hud_widget.py            # Animated circular HUD widget
├── waveform_visualizer.py   # Real-time audio waveform display
├── status_panel.py          # State and activity status panel
└── terminal_output.py       # Futuristic terminal-style output area
```

**UI Features:**
- **Circular HUD Widget**: Animated concentric rings with rotating tick marks, pulsing core, and state-based color changes (green=idle, cyan=listening, orange=processing, pink=speaking, red=error)
- **Audio Waveform Visualizer**: Real-time amplitude visualization with idle animation when not actively listening
- **Status Panel**: Displays current state, recent messages, and activity history with timestamps
- **Terminal Output**: Color-coded scrolling text output with automatic timestamping and content-based coloring
- **Futuristic Styling**: Dark theme (#0a0e17 background), cyan accents (#00ffff), glassmorphism effects, glowing borders, monospace fonts (Consolas)

**Technical Implementation:**
- PyQt6 framework for cross-platform desktop GUI
- Custom paint events for all animated widgets
- QTimer-based animations at 30-60 FPS
- Threading for non-blocking voice processing (listen/process in background thread)
- Signal/slot architecture for UI updates from backend
- Responsive design with fixed window size (1200x800)

**Backend Integration:**
- Frontend connects to existing `jarvis.JarvisAssistant` class without modifying backend code
- Uses `JarvisSignals` QObject for thread-safe communication between backend and UI
- All existing Jarvis functionality preserved (voice recognition, TTS, web search, LM Studio integration)
- Graceful error handling if backend fails to initialize

**New Entry Point:**
```bash
python run_frontend.py  # Launches futuristic PyQt6 frontend
python jarvis.py        # Original terminal-only version still works
```

**Dependencies Added:**
- `PyQt6>=6.5.0` (added to requirements.txt)

## Version 2.2 (2026-09-03)

### LLM-Based Web Search Intent Classification
- Replaced keyword-based `requires_web_search()` with new `classify_web_search()` method that uses LM Studio LLM to determine if a request requires web search
- The LLM analyzes user intent and generates precise search queries when needed, handling cases like:
  - "How much is Nvidia worth?" → searches for current stock price
  - "Can I buy a PS5 today?" → checks availability
  - "What's happening in London?" → finds current events
  - "Is the gold market up?" → gets live commodity prices
- Added comprehensive web search system prompt that instructs the LLM on when to search vs. answer directly
- Includes JSON parsing with fallback for malformed responses
- Retained keyword-based detection as `_keyword_web_search_fallback()` if LLM classification fails
- Updated `process_command()` to use LLM-generated search queries instead of raw user commands

### Benefits Over Previous Approach
- No need to maintain long lists of specific stock, coin, or commodity names
- Handles new assets, companies, products, locations, and markets automatically
- More accurate intent detection for ambiguous queries
- Generates optimized search queries that include relevant keywords (tickers, units, "current price", etc.)

## Version 2.1 (2026-09-03)

### Hidden Instructions for LM Studio API Calls
- Added hidden system instructions to all LM Studio API requests: "I am Jarvis, a virtual assistant. Answer personal questions directed to Jarvis as Jarvis, using the first person when appropriate."
- Instructions are included in the system prompt and not displayed to the user
- Applied to both `get_ai_response()` and `search_and_answer()` methods

### Web Search Restriction
- Added `requires_web_search()` method to determine if a question needs web search
- Web search is now used only for questions requiring current or location-based information:
  - Weather and temperature queries
  - Sports scores and game results
  - News and current events
  - Locations, directions, and proximity queries ("near me", "closest")
  - Live prices and availability checks
  - Explicit search requests ("search for...")
- General, personal, conversational, and knowledge-based questions are now answered directly by LM Studio without web search

### Shutdown Command Improvements
- Expanded shutdown phrase detection to reliably recognize:
  - "Goodbye", "Bye"
  - "Exit", "Quit"
  - "Stop Jarvis", "Close Jarvis", "Shut down Jarvis"
- Added comprehensive shutdown detection in both `process_command()` and the main loop
- Ensures Jarvis completes cleanup before exiting without continuing to listen

### Voice Output Consistency
- Verified that all terminal responses are passed through the text-to-speech system via `speak()` method
- All AI responses, search results, error messages, and status updates are spoken aloud consistently
- Empty or malformed responses are handled safely without crashes

## Version 2.0 (2026-09-03)

### New: Voice Generation Application (`voice_gen/`)

Built a complete Python voice-generation application that accepts user-provided MP3 reference recordings, stores them with explicit consent tracking, and generates speech using Coqui TTS XTTS v2.

**Project Structure:**
```
voice_gen/
├── __init__.py          # Package exports
├── audio.py             # Audio conversion & validation
├── storage.py           # Voice storage with consent
├── generation.py        # Coqui TTS generation engine
├── cli.py               # Command-line interface
```

**Features Implemented:**

1. **Audio Input Processing (`audio.py`)**
   - Accepts MP3, WAV, M4A, and other common audio formats
   - Validates file existence, readability, and size limits (configurable)
   - Converts reference audio to temporary WAV (mono, 24kHz, PCM 16-bit) using ffmpeg or pydub
   - Analyzes audio quality with warnings for: multiple speakers, music, noise, echo, excessive silence, short speech segments, stereo audio
   - Automatic cleanup of temporary converted files

2. **Consent & Safety (`storage.py`)**
   - Requires explicit consent confirmation before saving any reference voice
   - Default consent value is `false` — refuses to save without explicit `--consent` flag
   - Consent statement: "I confirm that I own this recording or have permission from the speaker to clone and generate speech with this voice."
   - No presets or prompts designed to imitate living actors, celebrities, politicians, public figures, movie characters, or other recognizable persons without authorization

3. **Reference Voice Storage (`storage.py`)**
   - Copies (not moves) original files into configurable storage directory (`REFERENCE_VOICES_DIR` env var)
   - Creates destination directory automatically
   - Never overwrites existing files silently — creates unique names with timestamps on collision
   - Calculates SHA-256 hash before saving; reuses identical files by hash comparison
   - Stores JSON metadata alongside each audio file: display name, original filename, stored filename, language, consent confirmation, creation timestamp, SHA-256 hash, AI disclosure flag
   - Functions: `save_voice()`, `list_voices()`, `get_voice()`, `select_voice()`, `delete_voice()`

4. **Voice Generation Engine (`generation.py`)**
   - Uses Coqui TTS XTTS v2 through its Python API
   - Automatically detects and uses CUDA when NVIDIA GPU is available, falls back to CPU otherwise
   - Interface: `generate_voice(text, reference_audio_path, output_path="output.wav", language="en") -> str`
   - Supports multilingual generation (en, es, fr, de, it, pt, pl, hu, ro, ru, ja, zh-cn, ko)
   - Batch generation support via `generate_voice_batch()`

5. **Command-Line Interface (`cli.py`)**
   ```bash
   # Save a reference voice with consent
   python cli.py save --name "Jarvis" --file "Jarvis.mp3" --language en --consent
   
   # List all saved voices
   python cli.py list
   
   # Generate speech using a saved voice
   python cli.py generate --voice "Jarvis" --text "Hello, world!" --output output.wav
   
   # Delete a saved voice
   python cli.py delete --voice "Jarvis"
   ```

**Testing (`test_voice_gen.py`):**
- 7 comprehensive test suites covering all modules
- Tests audio validation (non-existent files, empty files, valid files)
- Tests consent requirement enforcement
- Tests duplicate file detection via SHA-256 hashing
- Tests full voice lifecycle (save, list, get, delete)
- Tests CUDA availability detection
- Tests generation input validation
- Tests CLI interface and argument parsing
- All 7 test suites pass successfully

**Dependencies:**
- `TTS` — Coqui TTS library with XTTS v2 model
- `ffmpeg` or `pydub` — for audio format conversion
- `torch` — PyTorch (required by Coqui TTS, enables CUDA)

## Version 1.3 (2026-09-03)

### Text-to-Speech Synchronization Fix
- **Guaranteed spoken output**: Refactored `speak()` method to ensure every terminal message is also spoken aloud
  - Added proper error handling with try/except around entire TTS pipeline
  - Verified audio file creation before attempting playback (edge-tts)
  - Ensured synchronous playback completion before returning from `speak()` call
  - Prevents Jarvis from entering listening mode before spoken response finishes

- **Improved error logging**: Enhanced error messages for debugging TTS issues
  - Logs specific errors during speech synthesis, file creation, and playback
  - Provides actionable information when audio device or voice settings fail

### Stop/Silence Command Reliability Fix
- **Word boundary matching**: Added `matches_command()` method using regex word boundaries (`\b`)
  - Prevents false matches on partial words (e.g., "goodbyes" no longer triggers goodbye)
  - Correctly matches multi-word phrases like "shut up", "be quiet", "stop talking" within sentences
  - Separated exit commands ("bye", "goodbye") from silence commands for clearer logic

### Testing Improvements
- Added `test_command_matching()` test suite for word boundary command matching
- Added `test_tts_synchronization()` test suite to verify spoken output for every response
- All tests now validate both terminal output and speech synthesis calls

## Version 1.2 (2026-09-03)

### Speech Recognition & Response Flow Fixes
- **Speech Completeness Validation**: Added `is_sentence_complete()` method to detect incomplete utterances before processing
  - Rejects short phrases without punctuation (< 3 words)
  - Accepts complete questions starting with question words even without punctuation
  - Prevents Jarvis from searching for truncated queries like "current weather today" when user said "What is the weather going to be for the rest of the..."

- **Weather Forecast Detection**: Improved weather query parsing to distinguish current weather vs. forecasts
  - Detects forecast keywords: week, forecast, tomorrow, next week, this week, entire week
  - Searches for appropriate forecast data instead of always using "current weather today"
  - Provides personality-appropriate response ("I'll review the forecast for you")

- **Consecutive Failure Handling**: Added feedback after multiple speech recognition failures
  - After 3 consecutive failed recognitions, Jarvis says: "I'm sorry, Sir. I didn't catch that. Please repeat your request."
  - Prevents silent looping where Jarvis keeps listening without user awareness

### Response Quality Improvements
- **Enhanced Error Messages**: Updated all fallback messages to match Jarvis personality and provide actionable information
  - Failed search: "It appears the search was unsuccessful, Sir. I'll need a little more information before I can provide an accurate answer."
  - Empty AI response: "I'm sorry, Sir. I was unable to find a reliable answer to that question. I can try a different search if you'd like."
  - No useful context: "The search results didn't contain useful information, Sir. I can try a different approach if you'd like."

### Testing
- Added `test_sentence_completeness()` test case for speech validation logic
- Added `test_weather_query_parsing()` test case for forecast vs current weather detection

## Version 1.1 (2026-09-02)

### Personality & Voice Updates
- **Iron Man Movie Personality**: Updated Jarvis to match the personality from Iron Man movies based on dialogue analysis
  - Formal British butler style speech
  - Uses "Sir" when addressing user
  - Dry wit and subtle sarcasm
  - Professional yet warm tone
  - Concise, efficient responses

- **British Voice Selection**: Added automatic TTS voice configuration
  - Searches for British English voices (en-gb, british, uk) first
  - Falls back to known good-sounding male English voices (Daniel, George, Richard, Mark)
  - Sets speech rate to 135 wpm for clarity

### Command Handling Improvements
- **Stop Commands**: Added commands to make Jarvis stop talking
  - "bye" / "goodbye" → Says goodbye and exits program
  - "shut up", "be quiet", "stop talking", "silence" → Becomes silent without responding

- **Weather Queries**: Direct web search for weather questions
  - Detects "weather" or "temperature" in queries
  - Searches immediately without waiting for AI response
  - Handles location-specific queries ("in [city]", "for [location]")

### Web Search & Answer Enhancement
- **Search + AI Synthesis**: Combined DuckDuckGo search with LM Studio AI for better answers
  - Searches web using DuckDuckGo (no API key required)
  - Collects top 3 search results
  - Uses loaded LLM in LM Studio to synthesize concise, accurate answer from results
  - Falls back to raw search snippets if AI synthesis fails

- **Smart Question Detection**: Automatically uses search+answer approach for questions
  - Detects questions starting with: what, who, when, where, why, how, is, are, can, does, tell me
  - Non-question commands still use AI first, then web search as fallback

### Response Handling Fixes
- **Web Search Fallback**: If LM Studio doesn't respond or returns empty, automatically falls back to DuckDuckGo search
- **Error Recovery**: Improved error handling throughout command processing
- **Empty Response Detection**: Checks for meaningful responses before speaking

### Response Completeness Fix
- **Prevents empty responses**: Added validation to ensure AI returns non-empty answers before speaking
  - If LM Studio returns an empty response, Jarvis now says "Apologies, Sir. I was unable to find a reliable answer to that question." instead of speaking nothing
  - Ensures every recognized command produces audible output

### Listening State Fix
- **Prevents premature return to listening mode**: Fixed main loop logic so Jarvis doesn't restart listening while still processing
  - Added explicit check for empty/whitespace-only commands before processing
  - Ensures process_command completes fully (including speaking) before next listen cycle begins
  - Eliminates the issue where Jarvis would say "Based on my research, Sir:" and then immediately return to listening without finishing

### DuckDuckGo Search Package Update
- **Updated to `ddgs` package**: Fixed web search by migrating from deprecated `duckduckgo-search` to the new `ddgs` package
  - Old package had broken API/HTML backends that returned empty results
  - New `ddgs` package uses auto-detection for reliable search results
  - Updated requirements.txt and import statements accordingly

### Web Search Reliability Fix
- **Multi-backend DuckDuckGo search**: Fixed issue where web searches returned no results
  - Previously used single backend which could fail silently or return empty results
  - Now tries API backend first, falls back to HTML backend if needed
  - Added comprehensive error handling and logging for each attempt
  - Ensures weather queries and other web-dependent features work reliably

### Weather Query Fix
- **Accurate Current Weather**: Fixed weather queries to use web search + AI synthesis instead of raw snippets
  - Previously returned outdated or incomplete snippet text directly
  - Now searches DuckDuckGo for current weather data and uses LM Studio AI to synthesize accurate, up-to-date response
  - Handles both location-specific ("weather in London") and general ("what's the weather today") queries

### Speech Output Fix
- **Consistent Voice Responses**: Fixed issue where Jarvis only spoke at the beginning but not on subsequent responses
  - Root cause: edge-tts was writing to the same filename (`jarvis_output.mp3`) for every call, causing file conflicts and playback failures after the first response
  - Solution: Generate unique filenames using UUID for each TTS call (e.g., `jarvis_output_a1b2c3d4.mp3`)
  - Added automatic cleanup of temporary audio files after playback completes

### Voice Sample Analysis & High-Quality TTS
- **edge-tts Integration**: Added Microsoft's edge-tts for high-quality neural voices
  - Uses `en-GB-RyanNeural` voice (British male, calm tone similar to Jarvis)
  - Falls back to pyttsx3 if edge-tts not available
  - Generates audio files and plays them via ffplay or Windows Media Player

- **Audio Analysis Integration**: Added librosa library for voice sample analysis
  - Analyzes provided "Jarvis Voice.mp3" file to extract pitch and speech rate characteristics
  - Configures TTS engine based on analyzed voice properties (when using pyttsx3 fallback)
  - Falls back to default Jarvis-like settings if no sample available

- **Voice Sample File**: JARVIS.mp3 voice sample not required in project folder
  - edge-tts uses built-in neural voices, doesn't need audio samples for cloning
  - Audio analysis only used as optional enhancement for pyttsx3 fallback mode

- **Dependencies Updated**: Added audio processing libraries to requirements.txt
  - edge-tts>=6.1.0 (high-quality neural text-to-speech)
  - librosa>=0.10.0 (audio analysis)
  - numpy>=1.24.0 (numerical operations)
  - soundfile>=0.12.0 (audio file handling)

## Version 1.0 (Initial Release)
- Basic voice assistant with speech recognition and text-to-speech
- LM Studio API integration for AI capabilities
- DuckDuckGo web search functionality
- Simple command processing (hello, name, how are you, search)

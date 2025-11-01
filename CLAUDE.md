# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Application

**Start the web server:**
```bash
python3 chat_analyzer_web.py
```
The app runs on port 5000 by default (configurable via `PORT` environment variable).

**Install dependencies:**
```bash
pip install -r requirements.txt
```

**Environment variables required:**
- `OPENROUTER_API_KEY` - OpenRouter API key (required)
- `OPENROUTER_MODEL` - Model to use (optional, defaults to 'anthropic/claude-3.5-haiku')
- `SECRET_KEY` - Flask session secret (optional, defaults to dev key)
- `PORT` - Server port (optional, defaults to 5000)

## Architecture Overview

This is a Flask web app that analyzes WhatsApp chat exports using Claude Haiku 3.5 via OpenRouter. The analysis pipeline follows a two-stage approach:

### Analysis Pipeline

```
WhatsApp .txt file
    ↓
ChatParser (chat_analyzer.py) → Parses message format
    ↓
Date filtering → Filters to last N days from most recent message
    ↓
CandidateExtractor (chat_analyzer.py) → Pattern matching to find candidates
    ↓
AIAnalyzer (chat_analyzer_ai.py) → Claude API refines results
    ↓
AIMarkdownFormatter (ai_formatter.py) → Outputs markdown/HTML
    ↓
Download file
```

### Key Components

**chat_analyzer_web.py** - Flask entry point
- Handles file uploads at `/analyze` endpoint
- Routes queries to appropriate extractors
- Manages temporary file storage
- Serves markdown files for most query types, HTML for check-ins

**chat_analyzer.py** - Pattern matching layer
- `ChatParser`: Parses WhatsApp export format `[DD/MM/YYYY, HH:MM:SS] Sender: Message`
- `CandidateExtractor`: Pattern matches messages to find potential items
- Supports 8 query types: actions, urls, decisions, meetings, questions, deadlines, assignments, checkins

**chat_analyzer_ai.py** - AI refinement layer
- `AIAnalyzer`: Uses Claude Haiku 3.5 (via OpenRouter) to refine pattern-matched candidates
- Supports any OpenRouter-compatible model via `OPENROUTER_MODEL` environment variable
- Processes in chunks (max_tokens=8192) to avoid truncation
- Returns structured JSON with extracted information

**ai_formatter.py** - Output formatting
- `AIMarkdownFormatter`: Formats results with emojis, priorities, status indicators
- `format_checkins_html()`: Generates interactive SVG graphs for mood trends
- Groups results by date, person, priority

## Important Implementation Details

### Date Filtering Logic
Date filtering is relative to the **most recent message in the file**, not today's date. This ensures old exports still return useful data:

```python
most_recent_date = max(datetime.strptime(m['date'], '%d/%m/%Y') for m in messages)
cutoff_date = most_recent_date - timedelta(days=days)
messages = [m for m in messages if datetime.strptime(m['date'], '%d/%m/%Y') >= cutoff_date]
```

### AI Token Limits
- Claude Haiku 3.5 (via OpenRouter): max_tokens=8192
- Candidates are chunked (50 per chunk by default) to avoid JSON truncation
- Previously had bug where max_tokens=4096 caused truncated responses

### Check-ins Feature
The check-ins query type is special:
- Returns HTML (not markdown) with interactive SVG graph
- Pattern matches multiple mood score formats: `X/10`, `- X`, `mood: X`
- AI extracts: person, date, time, score (0-10), comments
- Graph shows trends over time with hover tooltips

### WhatsApp Export Format
Expects exact format: `[DD/MM/YYYY, HH:MM:SS] Sender: Message`
- Multi-line messages are concatenated
- System messages have sender='SYSTEM'

## Query Types

Each query type has specific pattern matching logic in `CandidateExtractor`:

- **actions** - Tasks, deliverables (outputs: priority 🔴🟡🟢, status ✅📋🔄💬)
- **urls** - Links with context
- **decisions** - Key decisions and agreements
- **meetings** - Schedules, Zoom links, agendas
- **questions** - Questions asked
- **deadlines** - Time-sensitive items
- **assignments** - Direct task assignments
- **checkins** - Daily mood scores (special: outputs HTML graph)

## Deployment Notes

This app is designed for Replit:
- `.replit` file sets PORT=5000 and run command
- Dependencies auto-install from `requirements.txt`
- No persistent storage - all processing is in-memory with temp files
- No authentication/multi-user support
- Single-threaded (one analysis at a time)

## Cost Considerations

- Uses Claude Haiku 3.5 via OpenRouter (affordable and fast)
- Typical cost: $0.01-0.05 per chat export
- Chunking ensures large files don't exceed token limits
- Can use other models by setting `OPENROUTER_MODEL` environment variable

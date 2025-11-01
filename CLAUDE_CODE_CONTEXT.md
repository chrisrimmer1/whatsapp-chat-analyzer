# WhatsApp Chat Analyzer - Claude Code Context

This is a clean deployment package for the WhatsApp Chat Analyzer application, ready for Replit deployment.

## Project Overview

**What it does:**
AI-powered WhatsApp chat analyzer that extracts structured information (actions, URLs, decisions, meetings, questions, deadlines, assignments, and check-ins with mood scores) from WhatsApp chat exports using Claude Haiku 3.5 via OpenRouter.

**Technology Stack:**
- Flask web server (Python)
- Claude Haiku 3.5 API (via OpenRouter)
- Vanilla JavaScript + SVG for interactive graphs
- No external dependencies beyond Python packages

## Architecture

### Core Files

1. **chat_analyzer_web.py** (Main entry point)
   - Flask web server running on port 5000
   - Handles file uploads, date filtering, query routing
   - Returns markdown files for most query types, HTML for check-ins
   - Uses temporary file storage (tempfile.gettempdir())

2. **chat_analyzer.py** (Pattern matching & parsing)
   - `ChatParser`: Parses WhatsApp export format `[DD/MM/YYYY, HH:MM:SS] Sender: Message`
   - `CandidateExtractor`: Pattern matches messages to find potential items (actions, URLs, etc.)
   - `OutputFormatter`: Legacy formatter (mostly replaced by AI formatter)

3. **chat_analyzer_ai.py** (AI analysis)
   - `AIAnalyzer`: Uses Claude Haiku 3.5 (via OpenRouter) to refine pattern-matched candidates
   - Chunks large datasets to stay within token limits (max_tokens=8192)
   - Returns structured JSON with extracted information
   - Supports any OpenRouter-compatible model via `OPENROUTER_MODEL` environment variable

4. **ai_formatter.py** (Output formatting)
   - `AIMarkdownFormatter`: Beautiful markdown output with emojis, priorities, status indicators
   - `format_checkins_html()`: Interactive HTML graph for mood trends over time
   - Groups by date, person, priority, etc.

5. **templates/index.html** (Web UI)
   - Modern gradient design with card-based layout
   - File upload with query type selection
   - Date range filter (last X days)
   - Progress indicators with 15-second timeout for downloads

### Key Features

**Query Types:**
- **actions**: Task assignments, deliverables (outputs: priority 🔴🟡🟢, status ✅📋🔄💬)
- **urls**: Links shared with context and importance
- **decisions**: Key decisions and agreements
- **meetings**: Meeting schedules, Zoom links, agendas
- **questions**: Questions asked in conversations
- **deadlines**: Time-sensitive items and due dates
- **assignments**: Direct task assignments to people
- **checkins**: Daily mood scores with interactive graph visualization

**Smart Date Filtering:**
- User enters "last X days" (default: 7)
- Calculates from **most recent message in file**, not today's date
- This ensures old exports still return useful data
- Filters messages BEFORE pattern matching and AI analysis for efficiency

**Interactive Check-ins Graph:**
- SVG-based line graph showing mood trends over time
- Different colors per person (blue for Chris Rimmer, purple for Olly Slater)
- Hover tooltips showing: person, date, time, score, full comments
- Responsive design with gradient background

## Flow Diagram

```
User uploads .txt file
    ↓
ChatParser.parse() → List[Dict] (all messages)
    ↓
Date filter (keep last X days from most recent message)
    ↓
CandidateExtractor.extract(query_type) → Pattern match candidates
    ↓
AIAnalyzer.analyze_chunk() → Claude API refines results
    ↓
AIMarkdownFormatter.format_*() → Beautiful output
    ↓
Download .md file (or .html for check-ins)
```

## Important Implementation Details

### Date Filtering Logic
```python
# Find most recent message date in file
most_recent_date = max(datetime.strptime(m['date'], '%d/%m/%Y') for m in messages)
cutoff_date = most_recent_date - timedelta(days=days)
# Filter messages
messages = [m for m in messages if datetime.strptime(m['date'], '%d/%m/%Y') >= cutoff_date]
```

### Check-ins Pattern Matching
Matches multiple mood score formats:
- `X/10` (e.g., "9/10", "10/10")
- `- X` or `• X` (e.g., "- 9", "• 10")
- `mood: X` or `mood\nX` (e.g., "mood: 9")

Keywords: "check in", "check-in", "checkin", "mood"

### Token Limits
- Claude Haiku 3.5 (via OpenRouter): max_tokens=8192
- Chunking: Process candidates in batches to avoid truncation
- Previously had bug where max_tokens=4096 caused JSON truncation (fixed by doubling)

### Port Configuration
- Code reads PORT environment variable
- Defaults to 5000 (consistent with Replit)
- .replit file sets PORT=5000

### UI Spinner Fix
- Downloads trigger via Flask `send_file()`
- JavaScript can't detect completion event
- Solution: 15-second setTimeout to stop spinner and show alert

## Recent Changes

### Check-ins Feature (Latest)
- Added new query type for daily mood score tracking
- Pattern matching enhanced to capture various score formats
- AI prompt extracts: person, date, time, score, comments
- HTML formatter with interactive SVG graph (not markdown)
- Tooltips show full message details on hover

### Date Filter Enhancement
- Changed from "cut-off date" to "last X days" UX
- Default: 7 days
- Calculates from most recent message in file (not today)
- Help text: "Analyze messages from the last X days (default: 7)"

### Bug Fixes
- JSON truncation: Increased max_tokens from 4096 to 8192
- UI spinner: Added 15-second timeout with completion alert
- Date parsing: Support both DD/MM/YYYY and DD/MM/YY formats

## Environment Variables

**Required:**
- `OPENROUTER_API_KEY`: OpenRouter API key from https://openrouter.ai/keys

**Optional:**
- `OPENROUTER_MODEL`: Model to use (defaults to 'anthropic/claude-3.5-haiku')
- `SECRET_KEY`: Flask session secret (has default: 'dev-secret-key-change-in-production')
- `PORT`: Server port (defaults to 5000)

## Deployment on Replit

1. Upload all files to Replit
2. Set `OPENROUTER_API_KEY` in Secrets tab
3. (Optional) Set `OPENROUTER_MODEL` if you want to use a different model
4. Click "Run" - Replit auto-installs dependencies from requirements.txt
5. Access web UI at provided URL

## Testing Checklist

- [ ] File upload works
- [ ] All 8 query types extract correctly
- [ ] Date filter reduces message count
- [ ] Check-ins generate interactive HTML graph
- [ ] Other query types generate markdown files
- [ ] Downloads complete and spinner stops
- [ ] API key error shows helpful message
- [ ] Large files process without timeout

## Known Limitations

- No authentication/user accounts
- No persistent storage (files processed in memory)
- Single-threaded (one analysis at a time)
- Requires Claude API credits
- WhatsApp export format must be exact

## Cost Estimate

- Claude Haiku 3.5 via OpenRouter: ~$0.01-0.05 per typical chat export
- OpenRouter supports multiple models at different price points
- Replit: Free tier supports this (or ~$7/month for always-on)

## Future Enhancement Ideas

- Add authentication for multi-user deployments
- Persistent storage for analysis history
- Batch processing multiple files
- Export to CSV/JSON formats
- Summary statistics dashboard
- Custom query types via prompts

---

This clean package contains only production-ready code with no test files, sample chats, or experimental features from the development folder.

# WhatsApp Chat Analyzer

AI-powered WhatsApp chat analyzer that extracts structured information from chat exports using Claude AI.

## Quick Start on Replit

### 1. Set Up Your API Key

1. Click the "Secrets" tab in Replit (lock icon in left sidebar)
2. Add a new secret:
   - Key: `OPENROUTER_API_KEY`
   - Value: Your OpenRouter API key from https://openrouter.ai/keys
3. (Optional) Add another secret to customize the model:
   - Key: `OPENROUTER_MODEL`
   - Value: Model name (default: `anthropic/claude-3.5-haiku`)

### 2. Run the App

1. Click the "Run" button at the top
2. Wait for the server to start (you'll see "Running on http://0.0.0.0:5000")
3. Click the preview URL to open the web interface

### 3. Analyze Your Chats

1. Export your WhatsApp chat as a .txt file:
   - **iPhone**: Open chat → Profile → Export Chat → Without Media
   - **Android**: Open chat → ⋮ → More → Export chat → Without media

2. Upload the .txt file to the web interface
3. Choose what to extract:
   - **Actions**: Tasks, assignments, deliverables
   - **URLs**: Links shared with context
   - **Decisions**: Key decisions made
   - **Meetings**: Meeting schedules and Zoom links
   - **Questions**: Questions asked in the conversation
   - **Deadlines**: Due dates and time-sensitive items
   - **Assignments**: Direct task assignments to people
   - **Check-ins**: Daily mood scores with interactive graph

4. Set time range (optional):
   - Default: Last 7 days from most recent message
   - Change to any number of days you want to analyze

5. Click "Analyze with AI"
6. Download your results (markdown for most types, interactive HTML for check-ins)

## Features

### Query Types

- **Action Items** - Extract tasks with priority, status, assignee, and deadlines
- **URLs & Links** - Capture all shared links with context and importance
- **Decisions** - Track key decisions and agreements
- **Meetings** - Find meeting times, Zoom links, and agendas
- **Questions** - Collect all questions asked
- **Deadlines** - Extract time-sensitive items
- **Assignments** - Track who's responsible for what
- **Check-ins** - Visualize daily mood trends with interactive graphs

### Smart Date Filtering

- Analyzes messages from the last X days (relative to most recent message in file)
- Default: 7 days
- Ensures you get relevant recent data even from older exports

### Beautiful Output

- **Markdown files**: Priority emojis, status indicators, organized by date
- **Interactive HTML graphs**: For check-ins with mood trends over time (hover to see details)

## Troubleshooting

### "No results found"

- Make sure your chat export is in the correct format: `[DD/MM/YYYY, HH:MM:SS] Sender: Message`
- Try increasing the time range (e.g., 30 days instead of 7)
- Check that your query type matches the content (e.g., "check-in" requires messages with mood scores)

### "API Error"

- Verify your `OPENROUTER_API_KEY` is set correctly in Replit Secrets
- Check you have API credits remaining at https://openrouter.ai/credits

### Server won't start

- Check the Console tab for error messages
- Make sure all dependencies are installed (Replit should do this automatically)
- Try clicking "Stop" then "Run" again

## Technical Details

**Built with:**
- Flask (Python web framework)
- Claude Haiku 3.5 (AI analysis via OpenRouter API)
- Vanilla JavaScript (interactive graphs)
- SVG (data visualization)

**Cost:**
- Uses Claude Haiku 3.5 via OpenRouter (affordable and fast)
- Typical analysis: $0.01-0.05 per chat export
- Check your usage at https://openrouter.ai/credits
- You can also use other models by setting `OPENROUTER_MODEL` environment variable

**Privacy:**
- Chat files processed in memory only
- Temporary files deleted after analysis
- Messages sent to OpenRouter API for analysis (see OpenRouter's privacy policy)

## Support

Need help? Open an issue or check the documentation at the main repository.

---

Made with Claude Code 🤖

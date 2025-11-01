# Google API Setup

The URL analyzer can fetch content from Google Docs, Google Drive, and Google Sheets.

## Local Development

1. You need two files in the project root:
   - `credentials.json` - OAuth client credentials from Google Cloud Console
   - `token.json` - Generated after first authentication

2. These files are already in `.gitignore` and won't be committed to git.

## Production (Railway)

For Railway deployment, you need to set these as environment variables:

1. **GOOGLE_CREDENTIALS** - Contents of `credentials.json` as a JSON string
2. **GOOGLE_TOKEN** - Contents of `token.json` as a JSON string

To set them:
```bash
# Get the JSON content (one line)
cat credentials.json | tr -d '\n'
cat token.json | tr -d '\n'

# Add to Railway:
# Settings > Variables > Add Variable
# Name: GOOGLE_CREDENTIALS
# Value: <paste the one-line JSON>
```

## How to Get Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google Drive API and Google Docs API
4. Create OAuth 2.0 credentials (Desktop app type)
5. Download as `credentials.json`
6. Run the app locally once to generate `token.json`

## Without Google Credentials

The app will still work without Google credentials! It will:
- Skip Google Docs/Drive/Sheets content analysis
- Still analyze regular web pages, ChatGPT shares, LinkedIn, etc.
- Show a warning: "Google services not available"

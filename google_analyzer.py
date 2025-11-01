#!/usr/bin/env python3
"""
Google Drive & Docs Analyzer
Analyzes files in Google Drive and extracts content from Google Docs.
"""

import os
import os.path
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configuration
SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/documents.readonly'
]

def get_credentials():
    """Handles OAuth flow and returns valid credentials.

    Supports both file-based credentials (local dev) and environment variables (Railway).
    """
    creds = None

    # First, try to load from environment variables (Railway deployment)
    google_token = os.environ.get('GOOGLE_TOKEN')
    print(f"DEBUG: GOOGLE_TOKEN env var exists: {bool(google_token)}, length: {len(google_token) if google_token else 0}")
    if google_token:
        try:
            print(f"DEBUG: Attempting to parse GOOGLE_TOKEN JSON...")
            # Remove any newlines/whitespace that Railway might have added
            google_token_cleaned = google_token.replace('\n', '').replace('\r', '').strip()
            print(f"DEBUG: First 200 chars: {google_token_cleaned[:200]}")
            print(f"DEBUG: Cleaned length: {len(google_token_cleaned)}")
            token_data = json.loads(google_token_cleaned)
            print(f"DEBUG: JSON parsed successfully, keys: {list(token_data.keys())}")
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
            print(f"✓ Loaded credentials from GOOGLE_TOKEN environment variable")
            print(f"DEBUG: Credentials valid: {creds.valid}, expired: {creds.expired if hasattr(creds, 'expired') else 'N/A'}")
        except json.JSONDecodeError as e:
            import traceback
            print(f"❌ JSON decode error in GOOGLE_TOKEN: {e}")
            print(f"DEBUG: Error at position {e.pos}: '{google_token[max(0, e.pos-20):e.pos+20]}'")
            print(f"DEBUG: Full traceback: {traceback.format_exc()}")
        except Exception as e:
            import traceback
            print(f"❌ Could not load credentials from GOOGLE_TOKEN env var: {e}")
            print(f"DEBUG: Traceback: {traceback.format_exc()}")

    # Fall back to file-based credentials (local development)
    if not creds and os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        print(f"✓ Loaded credentials from token.json file")

    # If no valid credentials, try to refresh or do OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print(f"⟳ Refreshing expired credentials...")
                creds.refresh(Request())
                # Save refreshed credentials back to file if possible
                if os.path.exists('token.json'):
                    with open('token.json', 'w') as token:
                        token.write(creds.to_json())
                print(f"✓ Credentials refreshed successfully")
            except Exception as e:
                print(f"❌ Could not refresh credentials: {e}")
                creds = None
        elif os.path.exists('credentials.json'):
            # Local development - do OAuth flow
            print(f"Starting OAuth flow...")
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            # Save credentials for next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
            print(f"✓ OAuth flow completed, credentials saved")
        else:
            raise Exception("No Google credentials available. Need either GOOGLE_TOKEN env var or token.json file. See GOOGLE_SETUP.md")

    return creds

def get_drive_service():
    """Returns authenticated Google Drive service."""
    creds = get_credentials()
    return build('drive', 'v3', credentials=creds)

def get_docs_service():
    """Returns authenticated Google Docs service."""
    creds = get_credentials()
    return build('docs', 'v1', credentials=creds)

def list_drive_files(service, page_size=10):
    """Lists files in Google Drive."""
    try:
        results = service.files().list(
            pageSize=page_size,
            fields="nextPageToken, files(id, name, mimeType, createdTime, modifiedTime)"
        ).execute()

        items = results.get('files', [])

        if not items:
            print('No files found.')
            return []

        print(f'Found {len(items)} files:')
        for item in items:
            print(f"  {item['name']} ({item['mimeType']})")

        return items

    except HttpError as error:
        print(f'An error occurred: {error}')
        return []

def get_doc_content(service, document_id):
    """Retrieves content from a Google Doc."""
    try:
        doc = service.documents().get(documentId=document_id).execute()

        title = doc.get('title')
        content = doc.get('body').get('content')

        # Extract text from document structure
        text_content = []
        for element in content:
            if 'paragraph' in element:
                paragraph = element.get('paragraph')
                for text_run in paragraph.get('elements', []):
                    if 'textRun' in text_run:
                        text_content.append(text_run.get('textRun').get('content'))

        return {
            'title': title,
            'content': ''.join(text_content)
        }

    except HttpError as error:
        print(f'An error occurred: {error}')
        return None

def main():
    """Main execution function."""
    print("Google Drive & Docs Analyzer")
    print("-" * 40)

    # Get services
    drive_service = get_drive_service()
    docs_service = get_docs_service()

    # Example: List files in Drive
    print("\nListing files in Google Drive:")
    files = list_drive_files(drive_service, page_size=10)

    # Example: Get content from first Google Doc found
    google_docs = [f for f in files if f['mimeType'] == 'application/vnd.google-apps.document']
    if google_docs:
        print(f"\nRetrieving content from: {google_docs[0]['name']}")
        doc_content = get_doc_content(docs_service, google_docs[0]['id'])
        if doc_content:
            print(f"Title: {doc_content['title']}")
            print(f"Content preview: {doc_content['content'][:200]}...")

if __name__ == '__main__':
    main()

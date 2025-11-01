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
    if google_token:
        try:
            token_data = json.loads(google_token)
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        except Exception as e:
            print(f"Warning: Could not load credentials from GOOGLE_TOKEN env var: {e}")

    # Fall back to file-based credentials (local development)
    if not creds and os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # If no valid credentials, try to refresh or do OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Save refreshed credentials back to file if possible
                if os.path.exists('token.json'):
                    with open('token.json', 'w') as token:
                        token.write(creds.to_json())
            except Exception as e:
                print(f"Warning: Could not refresh credentials: {e}")
                creds = None
        elif os.path.exists('credentials.json'):
            # Local development - do OAuth flow
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            # Save credentials for next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        else:
            raise Exception("No Google credentials available. See GOOGLE_SETUP.md")

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

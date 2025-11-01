#!/usr/bin/env python3
"""
URL Summarizer
Reads URLs from a text file, analyzes their content, and generates a markdown summary.
"""

import sys
import re
from urllib.parse import urlparse
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Import Google API functions from google_analyzer
from google_analyzer import get_credentials, get_drive_service, get_docs_service, get_doc_content


def read_urls_from_file(filepath):
    """
    Reads URLs from a text file (one URL per line).
    Returns a list of URLs, ignoring empty lines and comments.
    """
    urls = []
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith('#'):
                    urls.append(line)
        return urls
    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)


def is_google_doc_url(url):
    """Check if URL is a Google Doc."""
    return 'docs.google.com/document' in url


def is_google_drive_url(url):
    """Check if URL is a Google Drive file."""
    return 'drive.google.com' in url


def is_chatgpt_share_url(url):
    """Check if URL is a ChatGPT shared conversation."""
    return 'chatgpt.com/share/' in url


def is_linkedin_url(url):
    """Check if URL is a LinkedIn profile or post."""
    return 'linkedin.com/' in url


def is_gptshowcase_url(url):
    """Check if URL is a GPT Showcase app."""
    return 'gptshowcase.onrender.com' in url


def extract_google_doc_id(url):
    """Extract document ID from Google Docs URL."""
    match = re.search(r'/document/d/([a-zA-Z0-9-_]+)', url)
    return match.group(1) if match else None


def extract_google_drive_id(url):
    """Extract file ID from Google Drive URL."""
    # Handle various Drive URL formats
    patterns = [
        r'/file/d/([a-zA-Z0-9-_]+)',
        r'id=([a-zA-Z0-9-_]+)',
        r'/d/([a-zA-Z0-9-_]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def fetch_google_doc_summary(url, docs_service):
    """Fetch summary from a Google Doc."""
    doc_id = extract_google_doc_id(url)
    if not doc_id:
        return {'title': 'Unknown Google Doc', 'summary': 'Could not extract document ID from URL.'}

    try:
        doc_content = get_doc_content(docs_service, doc_id)
        if doc_content:
            title = doc_content['title']
            content = doc_content['content'].strip()

            # Create brief summary (first 500 chars or first paragraph)
            summary = content[:500].replace('\n', ' ').strip()
            if len(content) > 500:
                summary += '...'

            return {'title': title, 'summary': summary if summary else 'Empty document.'}
        else:
            return {'title': 'Google Doc', 'summary': 'Could not access document content.'}
    except Exception as e:
        return {'title': 'Google Doc', 'summary': f'Error accessing document: {str(e)}'}


def fetch_google_drive_summary(url, drive_service):
    """Fetch summary from a Google Drive file."""
    file_id = extract_google_drive_id(url)
    if not file_id:
        return {'title': 'Unknown Drive File', 'summary': 'Could not extract file ID from URL.'}

    try:
        file_metadata = drive_service.files().get(
            fileId=file_id,
            fields='id,name,mimeType,description,createdTime,modifiedTime'
        ).execute()

        title = file_metadata.get('name', 'Untitled')
        mime_type = file_metadata.get('mimeType', 'Unknown type')
        description = file_metadata.get('description', '')

        # Create summary based on file type
        type_name = mime_type.split('.')[-1].replace('google-apps.', '').title()
        summary = f"{type_name} file"
        if description:
            summary += f": {description}"

        return {'title': title, 'summary': summary}
    except Exception as e:
        return {'title': 'Google Drive File', 'summary': f'Error accessing file: {str(e)}'}


def fetch_chatgpt_summary(url):
    """Fetch summary from a ChatGPT shared conversation using browser automation."""
    try:
        with sync_playwright() as p:
            # Launch headless browser
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Navigate to the URL
            page.goto(url, timeout=30000)

            # Wait for the conversation to load
            # ChatGPT uses specific classes for conversation content
            try:
                page.wait_for_selector('div[class*="conversation"]', timeout=10000)
            except PlaywrightTimeoutError:
                # Try alternative selector if first one fails
                pass

            # Extract title
            title = page.title()

            # Extract conversation text
            # ChatGPT shared conversations use specific HTML structure
            conversation_text = []

            # Try to get all message content
            messages = page.query_selector_all('div[data-message-author-role]')

            if messages:
                for msg in messages[:4]:  # Get first 4 messages for summary
                    text = msg.inner_text().strip()
                    if text:
                        conversation_text.append(text)

            browser.close()

            if conversation_text:
                # Join messages and limit to 500 chars
                summary = ' | '.join(conversation_text)
                if len(summary) > 500:
                    summary = summary[:500] + '...'
            else:
                summary = 'ChatGPT shared conversation (content could not be extracted)'

            return {'title': title, 'summary': summary}

    except PlaywrightTimeoutError:
        return {'title': 'ChatGPT Conversation', 'summary': 'Timeout while loading conversation'}
    except Exception as e:
        return {'title': 'ChatGPT Conversation', 'summary': f'Error fetching conversation: {str(e)}'}


def fetch_linkedin_summary(url):
    """Fetch summary from a LinkedIn profile or post using browser automation."""
    # Extract username from URL as fallback
    username_match = re.search(r'linkedin\.com/in/([^/\?]+)', url)
    username = username_match.group(1) if username_match else 'Unknown'

    try:
        with sync_playwright() as p:
            # Launch headless browser
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Navigate to the URL
            page.goto(url, timeout=30000)

            # Wait a moment for content to load
            page.wait_for_timeout(2000)

            # Extract title
            title = page.title()

            # Try to extract profile information
            summary_parts = []

            # Try to get name from profile
            try:
                # LinkedIn uses various selectors, try multiple
                name_selectors = [
                    'h1.text-heading-xlarge',
                    'h1[class*="inline"]',
                    '.pv-text-details__left-panel h1',
                    'h1'
                ]
                for selector in name_selectors:
                    name_elem = page.query_selector(selector)
                    if name_elem:
                        name = name_elem.inner_text().strip()
                        # Filter out LinkedIn signup/login text
                        if name and len(name) < 100 and 'join' not in name.lower() and 'sign' not in name.lower():
                            summary_parts.append(f"Name: {name}")
                            break
            except:
                pass

            # Try to get headline/description
            try:
                headline_selectors = [
                    '.text-body-medium',
                    '.pv-text-details__left-panel .text-body-medium',
                    'div[class*="headline"]'
                ]
                for selector in headline_selectors:
                    headline_elem = page.query_selector(selector)
                    if headline_elem:
                        headline = headline_elem.inner_text().strip()
                        if headline and len(headline) > 10 and len(headline) < 300:
                            summary_parts.append(headline)
                            break
            except:
                pass

            # Try to get about section
            try:
                about_selectors = [
                    '#about ~ * p',
                    'section[data-section="about"] p',
                    '.pv-about-section p'
                ]
                for selector in about_selectors:
                    about_elem = page.query_selector(selector)
                    if about_elem:
                        about = about_elem.inner_text().strip()
                        if about and len(about) > 20:
                            summary_parts.append(about[:300])
                            break
            except:
                pass

            browser.close()

            if summary_parts:
                summary = ' | '.join(summary_parts)
                if len(summary) > 500:
                    summary = summary[:500] + '...'
            else:
                # If we couldn't extract content, show username from URL
                summary = f'LinkedIn profile: @{username} (requires login to view full details)'

            return {'title': title, 'summary': summary}

    except PlaywrightTimeoutError:
        return {'title': 'LinkedIn Profile', 'summary': 'Timeout while loading profile'}
    except Exception as e:
        return {'title': 'LinkedIn Profile', 'summary': f'Error fetching profile: {str(e)}'}


def fetch_gptshowcase_summary(url):
    """Fetch summary from a GPT Showcase app using browser automation."""
    try:
        with sync_playwright() as p:
            # Launch headless browser
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Navigate to the URL
            page.goto(url, timeout=30000)

            # Wait for content to render (JavaScript apps need time)
            page.wait_for_timeout(3000)

            # Extract title
            title = page.title()

            # Try to extract app content
            summary_parts = []

            # Look for common content areas
            try:
                # Try to get main heading
                h1_elements = page.query_selector_all('h1, h2, h3')
                for h in h1_elements[:2]:
                    text = h.inner_text().strip()
                    if text and len(text) < 200:
                        summary_parts.append(text)
            except:
                pass

            # Try to get paragraphs or description text
            try:
                paragraphs = page.query_selector_all('p, div[class*="description"], div[class*="content"]')
                for p in paragraphs[:5]:
                    text = p.inner_text().strip()
                    if text and len(text) > 20 and len(text) < 500:
                        summary_parts.append(text)
                        if len(' '.join(summary_parts)) > 300:
                            break
            except:
                pass

            # Try to get any visible text from main content area
            if not summary_parts:
                try:
                    main_selectors = ['main', '#app', '#root', 'body']
                    for selector in main_selectors:
                        main = page.query_selector(selector)
                        if main:
                            text = main.inner_text().strip()
                            if text:
                                # Get first 500 chars of visible text
                                summary_parts.append(text[:500])
                                break
                except:
                    pass

            browser.close()

            if summary_parts:
                summary = ' | '.join(summary_parts)
                if len(summary) > 500:
                    summary = summary[:500] + '...'
            else:
                summary = 'GPT Showcase app (content could not be extracted)'

            return {'title': title, 'summary': summary}

    except PlaywrightTimeoutError:
        return {'title': 'GPT Showcase App', 'summary': 'Timeout while loading app'}
    except Exception as e:
        return {'title': 'GPT Showcase App', 'summary': f'Error fetching app: {str(e)}'}


def fetch_web_page_summary(url):
    """Fetch summary from a regular web page."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Try to extract title
        title = 'Untitled Page'
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        elif soup.find('h1'):
            title = soup.find('h1').get_text().strip()

        # Try to extract description/summary
        summary = ''

        # Try meta description first
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if not meta_desc:
            meta_desc = soup.find('meta', attrs={'property': 'og:description'})

        if meta_desc and meta_desc.get('content'):
            summary = meta_desc['content'].strip()
        else:
            # Fall back to first paragraph
            paragraphs = soup.find_all('p')
            for p in paragraphs:
                text = p.get_text().strip()
                if len(text) > 50:  # Skip very short paragraphs
                    summary = text[:500]
                    if len(text) > 500:
                        summary += '...'
                    break

        if not summary:
            summary = 'No description available.'

        return {'title': title, 'summary': summary}

    except requests.exceptions.Timeout:
        return {'title': url, 'summary': 'Request timed out.'}
    except requests.exceptions.RequestException as e:
        return {'title': url, 'summary': f'Error fetching page: {str(e)}'}
    except Exception as e:
        return {'title': url, 'summary': f'Error parsing page: {str(e)}'}


def analyze_url(url, drive_service=None, docs_service=None):
    """
    Analyze a URL and return title and summary.
    Returns a dict with 'title' and 'summary' keys.
    """
    url = url.strip()

    # Determine URL type and fetch accordingly
    if is_google_doc_url(url):
        if not docs_service:
            return {'title': 'Google Doc', 'summary': 'Google Docs service not initialized.'}
        return fetch_google_doc_summary(url, docs_service)

    elif is_google_drive_url(url):
        if not drive_service:
            return {'title': 'Google Drive File', 'summary': 'Google Drive service not initialized.'}
        return fetch_google_drive_summary(url, drive_service)

    elif is_chatgpt_share_url(url):
        # ChatGPT shared conversation - use browser automation
        return fetch_chatgpt_summary(url)

    elif is_linkedin_url(url):
        # LinkedIn profile or post - use browser automation
        return fetch_linkedin_summary(url)

    elif is_gptshowcase_url(url):
        # GPT Showcase app - use browser automation
        return fetch_gptshowcase_summary(url)

    else:
        # Regular web page
        return fetch_web_page_summary(url)


def generate_markdown_report(url_summaries, output_file):
    """
    Generate a markdown report with URLs and summaries.
    url_summaries: list of tuples (url, result_dict)
    """
    try:
        with open(output_file, 'w') as f:
            f.write("# URL Summary Report\n\n")
            f.write(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
            f.write(f"**Total URLs analyzed:** {len(url_summaries)}\n\n")
            f.write("---\n\n")

            for i, (url, result) in enumerate(url_summaries, 1):
                title = result['title']
                summary = result['summary']

                f.write(f"## {i}. {title}\n\n")
                f.write(f"**URL:** {url}\n\n")
                f.write(f"**Summary:** {summary}\n\n")
                f.write("---\n\n")

        print(f"Report generated successfully: {output_file}")

    except Exception as e:
        print(f"Error writing output file: {e}")
        sys.exit(1)


def main():
    """Main execution function."""
    if len(sys.argv) != 3:
        print("Usage: python url_summarizer.py <input_file> <output_file>")
        print("\nExample:")
        print("  python url_summarizer.py urls.txt summary.md")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    print("URL Summarizer")
    print("-" * 40)

    # Read URLs from input file
    print(f"Reading URLs from: {input_file}")
    urls = read_urls_from_file(input_file)
    print(f"Found {len(urls)} URLs to analyze\n")

    if not urls:
        print("No URLs found in input file.")
        sys.exit(1)

    # Initialize Google API services (only if needed)
    drive_service = None
    docs_service = None

    # Check if any Google URLs exist
    has_google_urls = any(is_google_doc_url(url) or is_google_drive_url(url) for url in urls)

    if has_google_urls:
        print("Initializing Google API services...")
        try:
            creds = get_credentials()
            drive_service = get_drive_service()
            docs_service = get_docs_service()
            print("Google services initialized successfully\n")
        except Exception as e:
            print(f"Warning: Could not initialize Google services: {e}")
            print("Google Docs/Drive URLs will not be accessible.\n")

    # Analyze each URL
    print("Analyzing URLs...")
    url_summaries = []

    for i, url in enumerate(urls, 1):
        print(f"  [{i}/{len(urls)}] {url}")
        result = analyze_url(url, drive_service, docs_service)
        url_summaries.append((url, result))

    print()

    # Generate markdown report
    print(f"Generating report: {output_file}")
    generate_markdown_report(url_summaries, output_file)
    print("\nDone!")


if __name__ == '__main__':
    main()

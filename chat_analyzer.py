#!/usr/bin/env python3
"""
Chat Analyzer - Extract structured information from WhatsApp chat exports
Supports multiple query types: actions, URLs, decisions, questions, etc.
"""

import re
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path


class ChatParser:
    """Parse WhatsApp chat export files"""

    # WhatsApp timestamp pattern: [DD/MM/YYYY, HH:MM:SS]
    TIMESTAMP_PATTERN = r'\[(\d{2}/\d{2}/\d{4}, \d{2}:\d{2}(?::\d{2})?)\]'

    # Sender pattern: Name after timestamp
    SENDER_PATTERN = r'\[.*?\]\s*([^:]+?):\s*(.+)'

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.messages = []

    def parse(self) -> List[Dict[str, Any]]:
        """Parse chat file into structured messages"""

        with open(self.file_path, 'r', encoding='utf-8') as f:
            current_message = None

            for line in f:
                # Try to match timestamp at start of line
                timestamp_match = re.match(self.TIMESTAMP_PATTERN, line)

                if timestamp_match:
                    # Save previous message if exists
                    if current_message:
                        self.messages.append(current_message)

                    # Parse new message
                    timestamp_str = timestamp_match.group(1)
                    remainder = line[timestamp_match.end():].strip()

                    # Try to extract sender and content
                    sender_match = re.match(r'^([^:]+?):\s*(.+)', remainder)

                    if sender_match:
                        sender = sender_match.group(1).strip()
                        content = sender_match.group(2).strip()

                        current_message = {
                            'timestamp': timestamp_str,
                            'sender': sender,
                            'content': content,
                            'date': self._extract_date(timestamp_str),
                            'time': self._extract_time(timestamp_str)
                        }
                    else:
                        # System message (no sender)
                        current_message = {
                            'timestamp': timestamp_str,
                            'sender': 'SYSTEM',
                            'content': remainder,
                            'date': self._extract_date(timestamp_str),
                            'time': self._extract_time(timestamp_str)
                        }
                else:
                    # Continuation of previous message
                    if current_message:
                        current_message['content'] += '\n' + line.rstrip()

            # Don't forget last message
            if current_message:
                self.messages.append(current_message)

        return self.messages

    def _extract_date(self, timestamp: str) -> str:
        """Extract date from timestamp"""
        return timestamp.split(',')[0].strip()

    def _extract_time(self, timestamp: str) -> str:
        """Extract time from timestamp"""
        return timestamp.split(',')[1].strip()


class CandidateExtractor:
    """Extract candidate entries based on patterns"""

    def __init__(self, messages: List[Dict[str, Any]]):
        self.messages = messages
        self.extractors = {
            'actions': self._extract_actions,
            'urls': self._extract_urls,
            'decisions': self._extract_decisions,
            'questions': self._extract_questions,
            'meetings': self._extract_meetings,
            'deadlines': self._extract_deadlines,
            'assignments': self._extract_assignments,
            'checkins': self._extract_checkins,
        }

    def extract(self, query_type: str) -> List[Dict[str, Any]]:
        """Extract candidates for a specific query type"""

        if query_type not in self.extractors:
            raise ValueError(f"Unknown query type: {query_type}. Options: {list(self.extractors.keys())}")

        return self.extractors[query_type]()

    def _extract_actions(self) -> List[Dict[str, Any]]:
        """Extract potential action items"""

        action_patterns = [
            r'@\w+',  # Mentions
            r'\b(can you|could you|please|need to|have to|should|must)\b',
            r'\b(task|action|todo|assignment|deliverable)\b',
            r'\b(by \w+day|by EOD|before|deadline|due)\b',
            r'^\s*[\d\-\*•]\s+',  # List items
            r'\b(will|going to|planning to|need to)\b',
            r'\b(create|make|build|develop|design|write|research|investigate|review)\b',
        ]

        candidates = []
        for msg in self.messages:
            content = msg['content'].lower()

            # Skip system messages
            if msg['sender'] == 'SYSTEM':
                continue

            # Check for action patterns
            for pattern in action_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    candidates.append({
                        **msg,
                        'matched_pattern': pattern,
                        'type': 'action'
                    })
                    break

        return candidates

    def _extract_urls(self) -> List[Dict[str, Any]]:
        """Extract messages containing URLs"""

        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'

        candidates = []
        for i, msg in enumerate(self.messages):
            urls = re.findall(url_pattern, msg['content'])

            if urls:
                # Get context: previous and next messages
                context_before = []
                context_after = []

                # Get up to 2 messages before
                for j in range(max(0, i-2), i):
                    if self.messages[j]['sender'] != 'SYSTEM':
                        context_before.append({
                            'sender': self.messages[j]['sender'],
                            'content': self.messages[j]['content'][:200],  # Truncate long messages
                            'time': self.messages[j]['time']
                        })

                # Get up to 2 messages after
                for j in range(i+1, min(len(self.messages), i+3)):
                    if self.messages[j]['sender'] != 'SYSTEM':
                        context_after.append({
                            'sender': self.messages[j]['sender'],
                            'content': self.messages[j]['content'][:200],
                            'time': self.messages[j]['time']
                        })

                # Get description from the line containing URL
                content_lines = msg['content'].split('\n')
                description = ""
                for line in content_lines:
                    if urls[0] in line:
                        # Remove URL from line to get description
                        description = line.replace(urls[0], '').strip()
                        break

                for url in urls:
                    candidates.append({
                        'timestamp': msg['timestamp'],
                        'date': msg['date'],
                        'time': msg['time'],
                        'sender': msg['sender'],
                        'url': url,
                        'description': description,
                        'full_message': msg['content'],
                        'context_before': context_before,
                        'context_after': context_after,
                        'type': 'url'
                    })

        return candidates

    def _extract_decisions(self) -> List[Dict[str, Any]]:
        """Extract decision-making moments"""

        decision_patterns = [
            r'\b(decided|decision|agreed|settled on|chose|selected|going with)\b',
            r'\b(let\'s|we should|we will|we\'re going to)\b',
            r'\b(approved|confirmed|finalized|locked in)\b',
        ]

        candidates = []
        for msg in self.messages:
            content = msg['content'].lower()

            for pattern in decision_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    candidates.append({
                        **msg,
                        'matched_pattern': pattern,
                        'type': 'decision'
                    })
                    break

        return candidates

    def _extract_questions(self) -> List[Dict[str, Any]]:
        """Extract questions asked"""

        candidates = []
        for msg in self.messages:
            # Look for question marks or question words
            if '?' in msg['content'] or re.search(r'\b(what|why|how|when|where|who|which)\b',
                                                   msg['content'], re.IGNORECASE):
                candidates.append({
                    **msg,
                    'type': 'question'
                })

        return candidates

    def _extract_meetings(self) -> List[Dict[str, Any]]:
        """Extract meeting references"""

        meeting_patterns = [
            r'\b(meeting|call|zoom|session)\b',
            r'\b(agenda|minutes)\b',
            r'zoom\.us',
        ]

        candidates = []
        for msg in self.messages:
            content = msg['content'].lower()

            for pattern in meeting_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    candidates.append({
                        **msg,
                        'matched_pattern': pattern,
                        'type': 'meeting'
                    })
                    break

        return candidates

    def _extract_deadlines(self) -> List[Dict[str, Any]]:
        """Extract deadline mentions"""

        deadline_patterns = [
            r'\b(by \w+day|by EOD|by end of|before \w+day)\b',
            r'\b(deadline|due date|due by)\b',
            r'\b(today|tomorrow|next week|this week)\b',
        ]

        candidates = []
        for msg in self.messages:
            content = msg['content'].lower()

            for pattern in deadline_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    candidates.append({
                        **msg,
                        'matched_pattern': pattern,
                        'type': 'deadline'
                    })
                    break

        return candidates

    def _extract_assignments(self) -> List[Dict[str, Any]]:
        """Extract task assignments to specific people"""

        candidates = []
        for msg in self.messages:
            content = msg['content']

            # Look for @mentions or direct assignments
            mentions = re.findall(r'@(\w+)', content)
            assignments = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:to|will|can you|please)', content)

            if mentions or assignments:
                candidates.append({
                    **msg,
                    'mentions': mentions,
                    'assigned_to': assignments,
                    'type': 'assignment'
                })

        return candidates

    def _extract_checkins(self) -> List[Dict[str, Any]]:
        """Extract daily check-in messages with mood scores"""

        candidates = []
        for msg in self.messages:
            content = msg['content'].lower()

            # Look for check-in keywords and mood score patterns
            has_checkin_keyword = any(keyword in content for keyword in [
                'check in', 'checkin', 'check-in', 'mood'
            ])

            # Look for score patterns:
            # - "10/10", "8/10" format
            # - "- 9" or "- 10" (dash followed by number)
            # - "mood\n9" or "mood: 9" (mood keyword followed by number)
            score_pattern = re.search(r'(?:(\d+)/10|[-•]\s*(\d+)(?:\s*\(|$)|mood[\s:]+(\d+))', content)

            if has_checkin_keyword and score_pattern:
                # Extract the actual score from whichever group matched
                score = score_pattern.group(1) or score_pattern.group(2) or score_pattern.group(3)
                candidates.append({
                    **msg,
                    'score': score,
                    'type': 'checkin'
                })

        return candidates


class OutputFormatter:
    """Format extracted data for output"""

    @staticmethod
    def to_markdown(candidates: List[Dict[str, Any]], query_type: str, output_file: Optional[str] = None) -> str:
        """Format candidates as markdown"""

        if query_type == 'urls':
            content = OutputFormatter._format_urls_markdown(candidates)
        elif query_type == 'actions':
            content = OutputFormatter._format_actions_markdown(candidates)
        elif query_type == 'decisions':
            content = OutputFormatter._format_decisions_markdown(candidates)
        elif query_type == 'meetings':
            content = OutputFormatter._format_meetings_markdown(candidates)
        else:
            content = OutputFormatter._format_generic_markdown(candidates, query_type)

        if output_file:
            Path(output_file).write_text(content, encoding='utf-8')

        return content

    @staticmethod
    def _format_urls_markdown(candidates: List[Dict[str, Any]]) -> str:
        """Format URL candidates with full context"""

        lines = [
            "# URLs from Chat",
            "",
            f"*Total URLs found: {len(candidates)}*",
            "",
            "---",
            ""
        ]

        # Group by date
        by_date = {}
        for candidate in candidates:
            date = candidate['date']
            if date not in by_date:
                by_date[date] = []
            by_date[date].append(candidate)

        for date in sorted(by_date.keys()):
            lines.append(f"## {date}")
            lines.append("")

            for item in by_date[date]:
                lines.append(f"### {item['time']} - {item['sender']}")
                lines.append(f"**URL:** [{item['url']}]({item['url']})")
                lines.append("")

                # Show context before (if any)
                if item.get('context_before'):
                    lines.append("**Context (messages before):**")
                    for ctx in item['context_before']:
                        lines.append(f"- *{ctx['time']} - {ctx['sender']}:* {ctx['content']}")
                    lines.append("")

                # Show the actual message
                lines.append("**Message:**")
                full_msg = item['full_message']
                # Truncate if very long
                if len(full_msg) > 500:
                    full_msg = full_msg[:500] + "..."
                lines.append(f"> {full_msg}")
                lines.append("")

                # Show context after (if any)
                if item.get('context_after'):
                    lines.append("**Context (messages after):**")
                    for ctx in item['context_after']:
                        lines.append(f"- *{ctx['time']} - {ctx['sender']}:* {ctx['content']}")
                    lines.append("")

                lines.append("---")
                lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _format_actions_markdown(candidates: List[Dict[str, Any]]) -> str:
        """Format action candidates"""

        lines = [
            "# Action Items from Chat",
            "",
            f"*Total potential actions found: {len(candidates)}*",
            "",
            "---",
            ""
        ]

        # Group by date
        by_date = {}
        for candidate in candidates:
            date = candidate['date']
            if date not in by_date:
                by_date[date] = []
            by_date[date].append(candidate)

        for date in sorted(by_date.keys()):
            lines.append(f"## {date}")
            lines.append("")

            for item in by_date[date]:
                lines.append(f"- **{item['time']}** - {item['sender']}: {item['content'][:200]}{'...' if len(item['content']) > 200 else ''}")

            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _format_decisions_markdown(candidates: List[Dict[str, Any]]) -> str:
        """Format decision candidates"""

        lines = [
            "# Decisions from Chat",
            "",
            f"*Total decisions found: {len(candidates)}*",
            "",
            "---",
            ""
        ]

        # Group by date
        by_date = {}
        for candidate in candidates:
            date = candidate['date']
            if date not in by_date:
                by_date[date] = []
            by_date[date].append(candidate)

        for date in sorted(by_date.keys()):
            lines.append(f"## {date}")
            lines.append("")

            for item in by_date[date]:
                lines.append(f"### {item['time']} - {item['sender']}")
                lines.append(f"{item['content']}")
                lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _format_meetings_markdown(candidates: List[Dict[str, Any]]) -> str:
        """Format meeting references"""

        lines = [
            "# Meetings from Chat",
            "",
            f"*Total meeting references found: {len(candidates)}*",
            "",
            "---",
            ""
        ]

        # Group by date
        by_date = {}
        for candidate in candidates:
            date = candidate['date']
            if date not in by_date:
                by_date[date] = []
            by_date[date].append(candidate)

        for date in sorted(by_date.keys()):
            lines.append(f"## {date}")
            lines.append("")

            for item in by_date[date]:
                lines.append(f"- **{item['time']}** - {item['sender']}: {item['content'][:200]}{'...' if len(item['content']) > 200 else ''}")

            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _format_generic_markdown(candidates: List[Dict[str, Any]], query_type: str) -> str:
        """Generic formatter for other types"""

        lines = [
            f"# {query_type.title()} from Chat",
            "",
            f"*Total items found: {len(candidates)}*",
            "",
            "---",
            ""
        ]

        # Group by date
        by_date = {}
        for candidate in candidates:
            date = candidate['date']
            if date not in by_date:
                by_date[date] = []
            by_date[date].append(candidate)

        for date in sorted(by_date.keys()):
            lines.append(f"## {date}")
            lines.append("")

            for item in by_date[date]:
                lines.append(f"- **{item['time']}** - {item['sender']}: {item['content'][:200]}{'...' if len(item['content']) > 200 else ''}")

            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def to_json(candidates: List[Dict[str, Any]], output_file: Optional[str] = None) -> str:
        """Format candidates as JSON"""

        content = json.dumps(candidates, indent=2, ensure_ascii=False)

        if output_file:
            Path(output_file).write_text(content, encoding='utf-8')

        return content


def main():
    """Main entry point for CLI usage"""

    import argparse

    parser = argparse.ArgumentParser(
        description='Analyze WhatsApp chat exports and extract structured information',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract all URLs with descriptions
  python chat_analyzer.py chat.txt --query urls --output urls.md

  # Extract action items
  python chat_analyzer.py chat.txt --query actions --output actions.md

  # Extract decisions made
  python chat_analyzer.py chat.txt --query decisions

  # Get JSON output
  python chat_analyzer.py chat.txt --query urls --format json --output urls.json

Query types:
  actions     - Task assignments, action items, deliverables
  urls        - All URLs shared with descriptions and who posted them
  decisions   - Decision-making moments and agreements
  questions   - Questions asked in the chat
  meetings    - Meeting references, agendas, Zoom links
  deadlines   - Deadline mentions and due dates
  assignments - Direct task assignments to people
        """
    )

    parser.add_argument('file', help='Path to WhatsApp chat export file')
    parser.add_argument(
        '--query', '-q',
        required=True,
        choices=['actions', 'urls', 'decisions', 'questions', 'meetings', 'deadlines', 'assignments'],
        help='Type of information to extract'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output file path (default: print to stdout)'
    )
    parser.add_argument(
        '--format', '-f',
        choices=['markdown', 'json'],
        default='markdown',
        help='Output format (default: markdown)'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show statistics only'
    )

    args = parser.parse_args()

    # Parse chat file
    print(f"Parsing chat file: {args.file}")
    parser = ChatParser(args.file)
    messages = parser.parse()
    print(f"Found {len(messages)} messages")

    # Extract candidates
    print(f"Extracting {args.query}...")
    extractor = CandidateExtractor(messages)
    candidates = extractor.extract(args.query)
    print(f"Found {len(candidates)} potential {args.query}")

    if args.stats:
        print("\nStatistics:")
        print(f"  Total messages: {len(messages)}")
        print(f"  Matches found: {len(candidates)}")
        print(f"  Match rate: {len(candidates)/len(messages)*100:.1f}%")
        return

    # Format output
    if args.format == 'markdown':
        content = OutputFormatter.to_markdown(candidates, args.query, args.output)
    else:
        content = OutputFormatter.to_json(candidates, args.output)

    if not args.output:
        print("\n" + "="*80 + "\n")
        print(content)
    else:
        print(f"\nOutput written to: {args.output}")


if __name__ == '__main__':
    main()

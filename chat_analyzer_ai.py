#!/usr/bin/env python3
"""
AI-Enhanced Chat Analyzer
Uses Claude AI via OpenRouter to process and refine extracted candidates from chat analysis
"""

import os
import json
import re
from typing import List, Dict, Any, Optional
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from chat_analyzer import ChatParser, CandidateExtractor
from ai_formatter import AIMarkdownFormatter


class AIAnalyzer:
    """AI-powered analysis of chat candidates"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize with OpenRouter API key"""
        self.api_key = api_key or os.environ.get('OPENROUTER_API_KEY')
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")

        # Default to Claude Haiku 4.5 via OpenRouter
        self.model = model or os.environ.get('OPENROUTER_MODEL', 'anthropic/claude-3.5-haiku')

        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key
        )

    def analyze_chunk(self, candidates: List[Dict[str, Any]], query_type: str, chunk_size: int = 50) -> List[Dict[str, Any]]:
        """
        Process candidates in chunks using AI for refined analysis

        Args:
            candidates: List of candidate items extracted by pattern matching
            query_type: Type of query (actions, urls, decisions, etc.)
            chunk_size: Number of items to process at once

        Returns:
            List of AI-analyzed and enriched items
        """

        results = []

        # Process in chunks
        for i in range(0, len(candidates), chunk_size):
            chunk = candidates[i:i + chunk_size]
            print(f"Processing chunk {i//chunk_size + 1}/{(len(candidates)-1)//chunk_size + 1}...")

            # Get analysis for this chunk
            analyzed = self._analyze_single_chunk(chunk, query_type)
            results.extend(analyzed)

        return results

    def _analyze_single_chunk(self, chunk: List[Dict[str, Any]], query_type: str) -> List[Dict[str, Any]]:
        """Analyze a single chunk of candidates"""

        # Create prompt based on query type
        prompt = self._create_prompt(chunk, query_type)

        # Call OpenRouter API
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                max_tokens=8192,  # Increased to handle larger responses
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Parse response
            original_response = completion.choices[0].message.content
            response_text = original_response.strip()

            # Extract JSON using simple string operations (most reliable)
            if '```json' in response_text:
                start_marker = response_text.find('```json')
                start = start_marker + 7  # Length of '```json'
                end = response_text.find('```', start)

                if end > start:
                    response_text = response_text[start:end].strip()
                elif end == -1:
                    # No closing ``` found - response was truncated!
                    print(f"  ⚠️ WARNING: Response truncated (max_tokens limit hit)")
                    print(f"  ⚠️ Try reducing chunk size with --chunk-size")
                    # Extract from start to end of response
                    response_text = response_text[start:].strip()

            elif '```' in response_text:
                # Fallback: any code block
                start_marker = response_text.find('```')
                start = start_marker + 3
                end = response_text.find('```', start)

                if end > start:
                    response_text = response_text[start:end].strip()
                elif end == -1:
                    print(f"  ⚠️ WARNING: Response truncated")
                    response_text = response_text[start:].strip()

            analyzed_items = json.loads(response_text)
            return analyzed_items

        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {e}")
            print(f"   Try reducing --chunk-size to process fewer items at once")
            # Return original items with error flag
            return [{'error': str(e), **item} for item in chunk]
        except Exception as e:
            print(f"❌ Error analyzing chunk: {e}")
            # Return original items with error flag
            return [{'error': str(e), **item} for item in chunk]

    def _create_prompt(self, chunk: List[Dict[str, Any]], query_type: str) -> str:
        """Create appropriate prompt based on query type"""

        prompts = {
            'actions': self._prompt_actions,
            'urls': self._prompt_urls,
            'decisions': self._prompt_decisions,
            'meetings': self._prompt_meetings,
            'questions': self._prompt_questions,
            'deadlines': self._prompt_deadlines,
            'assignments': self._prompt_assignments,
            'checkins': self._prompt_checkins,
        }

        if query_type in prompts:
            return prompts[query_type](chunk)
        else:
            return self._prompt_generic(chunk, query_type)

    def _prompt_actions(self, chunk: List[Dict[str, Any]]) -> str:
        """Prompt for action item analysis"""

        return f"""Analyze these potential action items from a WhatsApp chat conversation.
For each item, determine:

1. Is it actually an action item? (true/false)
2. Who is responsible? (extract person's name or "team" or "unspecified")
3. What is the specific action? (brief, clear description)
4. When is the deadline? (extract if mentioned, or null)
5. What is the status? ("assigned", "in-progress", "completed", or "mentioned")
6. What is the priority? ("high", "medium", "low" based on language used)

Return ONLY a JSON array with this structure:
[
  {{
    "is_action": true/false,
    "responsible": "name or team",
    "action": "clear description",
    "deadline": "when or null",
    "status": "assigned/in-progress/completed/mentioned",
    "priority": "high/medium/low",
    "original_date": "from message",
    "original_time": "from message",
    "original_sender": "from message",
    "original_content": "original message"
  }}
]

Only include items where is_action is true in your output.

Messages to analyze:
{json.dumps(chunk, indent=2)}
"""

    def _prompt_urls(self, chunk: List[Dict[str, Any]]) -> str:
        """Prompt for URL analysis"""

        return f"""Analyze these URLs shared in a WhatsApp chat conversation.
For each URL, determine:

1. What type of content is it? (e.g., "meeting notes", "video", "document", "article", "tool", etc.)
2. Generate a better description if the original is unclear or empty
3. Summarize the surrounding context from messages before/after (1-2 sentences explaining why it was shared)
4. Is it important? (true/false based on context)

Return ONLY a JSON array with this structure:
[
  {{
    "url": "the URL",
    "type": "content type",
    "context": "summary of why this was shared based on surrounding messages",
    "description": "clear description",
    "important": true/false,
    "shared_by": "person name",
    "date": "date from the message (DD/MM/YYYY format)",
    "time": "time from the message"
  }}
]

Messages to analyze (each includes context_before and context_after showing surrounding conversation):
{json.dumps(chunk, indent=2)}
"""

    def _prompt_decisions(self, chunk: List[Dict[str, Any]]) -> str:
        """Prompt for decision analysis"""

        return f"""Analyze these potential decisions from a WhatsApp chat conversation.
For each item, determine:

1. Is it actually a decision? (true/false)
2. What was decided?
3. Who made the decision? (individual or team)
4. What was the decision about? (category: naming, branding, process, technical, etc.)
5. Was it final or tentative?

Return ONLY a JSON array with this structure:
[
  {{
    "is_decision": true/false,
    "decision": "what was decided",
    "decided_by": "who decided",
    "category": "what it's about",
    "finality": "final/tentative",
    "date": "from message",
    "context": "brief context"
  }}
]

Only include items where is_decision is true.

Messages to analyze:
{json.dumps(chunk, indent=2)}
"""

    def _prompt_meetings(self, chunk: List[Dict[str, Any]]) -> str:
        """Prompt for meeting analysis"""

        return f"""Analyze these meeting-related messages from a WhatsApp chat.
For each item, determine:

1. What type is it? (scheduled meeting, meeting notes, agenda, or just a mention)
2. When is/was the meeting? (extract date/time if mentioned)
3. What is the topic/purpose?
4. Who is involved?
5. Extract any Zoom/meeting links

Return ONLY a JSON array with this structure:
[
  {{
    "type": "scheduled/notes/agenda/mention",
    "meeting_time": "when or null",
    "topic": "what it's about",
    "participants": ["list", "of", "people"],
    "link": "meeting link or null",
    "date_mentioned": "from message"
  }}
]

Messages to analyze:
{json.dumps(chunk, indent=2)}
"""

    def _prompt_questions(self, chunk: List[Dict[str, Any]]) -> str:
        """Prompt for question analysis"""

        return f"""Analyze these questions from a WhatsApp chat.
For each question, determine:

1. What is the core question being asked?
2. Who asked it?
3. What category? (technical, process, decision-seeking, clarification, etc.)
4. Was it answered? (look for responses in the content)
5. If answered, what was the answer?

Return ONLY a JSON array with this structure:
[
  {{
    "question": "the core question",
    "asked_by": "person name",
    "category": "type of question",
    "answered": true/false,
    "answer": "the answer or null",
    "date": "from message"
  }}
]

Messages to analyze:
{json.dumps(chunk, indent=2)}
"""

    def _prompt_deadlines(self, chunk: List[Dict[str, Any]]) -> str:
        """Prompt for deadline analysis"""

        return f"""Analyze these deadline mentions from a WhatsApp chat.
For each item, determine:

1. What is the deadline for?
2. When is the deadline? (specific date or relative like "by Friday")
3. Who is responsible?
4. How urgent is it? (high/medium/low)

Return ONLY a JSON array with this structure:
[
  {{
    "task": "what needs to be done",
    "deadline": "when",
    "responsible": "who or unspecified",
    "urgency": "high/medium/low",
    "date_mentioned": "from message"
  }}
]

Messages to analyze:
{json.dumps(chunk, indent=2)}
"""

    def _prompt_assignments(self, chunk: List[Dict[str, Any]]) -> str:
        """Prompt for assignment analysis"""

        return f"""Analyze these task assignments from a WhatsApp chat.
For each assignment, determine:

1. What is the task?
2. Who assigned it?
3. Who is it assigned to?
4. When should it be completed?
5. What is the context/project?

Return ONLY a JSON array with this structure:
[
  {{
    "task": "clear task description",
    "assigned_by": "who assigned it",
    "assigned_to": "who should do it",
    "deadline": "when or null",
    "project_context": "what it's for",
    "date_assigned": "from message"
  }}
]

Messages to analyze:
{json.dumps(chunk, indent=2)}
"""

    def _prompt_checkins(self, chunk: List[Dict[str, Any]]) -> str:
        """Prompt for check-in analysis"""

        return f"""Analyze these daily check-in messages from a WhatsApp chat.
For each check-in, extract:

1. Who sent the check-in? (person's name)
2. What is their mood score? (can be "X/10" or just "X" - normalize to "X/10" format)
3. What comments did they include about their mood? (text immediately after the score)
4. When was it sent? (date and time from message)

Return ONLY a JSON array with this structure:
[
  {{
    "person": "sender name",
    "date": "DD/MM/YYYY",
    "time": "HH:MM:SS",
    "score": "X/10",
    "comments": "mood comments from message"
  }}
]

Important:
- The comments should capture the text immediately following the mood score, typically describing how they feel and their priorities for the day.
- Mood scores can appear in various formats: "9/10", "- 9", "mood: 9", etc. Always normalize to "X/10" format in the output.
- Include the explanation in parentheses if provided (e.g., "9 (for a good nights sleep)")

Messages to analyze:
{json.dumps(chunk, indent=2)}
"""

    def _prompt_generic(self, chunk: List[Dict[str, Any]], query_type: str) -> str:
        """Generic prompt for unknown query types"""

        return f"""Analyze these items of type "{query_type}" from a WhatsApp chat.
Extract relevant information and structure it in a clear JSON format.

Messages to analyze:
{json.dumps(chunk, indent=2)}
"""


def main():
    """Main entry point for AI-enhanced CLI"""

    import argparse
    import re
    from typing import Optional

    parser = argparse.ArgumentParser(
        description='AI-Enhanced WhatsApp Chat Analyzer using Claude via OpenRouter',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract and AI-analyze URLs
  python chat_analyzer_ai.py chat.txt --query urls --output urls_analyzed.json

  # Extract action items with AI enhancement
  python chat_analyzer_ai.py chat.txt --query actions --output actions_analyzed.json

  # Extract decisions with AI context
  python chat_analyzer_ai.py chat.txt --query decisions

Environment:
  Set OPENROUTER_API_KEY environment variable with your OpenRouter API key
  Optionally set OPENROUTER_MODEL to specify a different model (default: anthropic/claude-3.5-haiku)

Query types: actions, urls, decisions, questions, meetings, deadlines, assignments
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
        help='Output file path (JSON format)'
    )
    parser.add_argument(
        '--chunk-size',
        type=int,
        default=30,
        help='Number of items to process per AI call (default: 30)'
    )
    parser.add_argument(
        '--no-ai',
        action='store_true',
        help='Skip AI analysis, just use pattern matching'
    )

    args = parser.parse_args()

    # Parse chat file
    print(f"📖 Parsing chat file: {args.file}")
    parser = ChatParser(args.file)
    messages = parser.parse()
    print(f"✓ Found {len(messages)} messages\n")

    # Extract candidates
    print(f"🔍 Extracting {args.query} using pattern matching...")
    extractor = CandidateExtractor(messages)
    candidates = extractor.extract(args.query)
    print(f"✓ Found {len(candidates)} potential {args.query}\n")

    # AI analysis
    if not args.no_ai and candidates:
        print(f"🤖 Analyzing with Claude AI...")
        try:
            ai_analyzer = AIAnalyzer()
            analyzed = ai_analyzer.analyze_chunk(candidates, args.query, args.chunk_size)
            print(f"✓ AI analysis complete: {len(analyzed)} refined results\n")
        except ValueError as e:
            print(f"⚠️  Warning: {e}")
            print("Falling back to pattern-matching only (use --no-ai to suppress this message)\n")
            analyzed = candidates
    else:
        analyzed = candidates

    # Format output as markdown
    if args.query == 'actions':
        markdown_content = AIMarkdownFormatter.format_actions(analyzed)
    elif args.query == 'urls':
        markdown_content = AIMarkdownFormatter.format_urls(analyzed)
    elif args.query == 'decisions':
        markdown_content = AIMarkdownFormatter.format_decisions(analyzed)
    else:
        markdown_content = AIMarkdownFormatter.format_generic(analyzed, args.query)

    # Output results
    if args.output:
        Path(args.output).write_text(markdown_content, encoding='utf-8')
        print(f"📄 Output written to: {args.output}")
    else:
        print(markdown_content)


if __name__ == '__main__':
    main()

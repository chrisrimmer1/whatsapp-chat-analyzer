#!/usr/bin/env python3
"""
Markdown formatter for AI-analyzed chat results
"""

from typing import List, Dict, Any
from datetime import datetime


class AIMarkdownFormatter:
    """Format AI-analyzed results as readable markdown"""

    @staticmethod
    def format_actions(items: List[Dict[str, Any]]) -> str:
        """Format action items as markdown"""

        # Filter to only include actual actions (where is_action is True)
        # Also skip items with errors (from failed AI chunks)
        real_actions = [
            item for item in items
            if item.get('is_action', False) == True
            and 'error' not in item
        ]

        md = "# Action Items (AI-Analyzed)\n\n"
        md += f"*Total actions found: {len(real_actions)}*\n\n"
        md += "---\n\n"

        if not real_actions:
            md += "_No action items found in this chat._\n"
            return md

        # Group by date
        by_date = {}
        for item in real_actions:
            date = item.get('original_date', 'Unknown Date')
            if date not in by_date:
                by_date[date] = []
            by_date[date].append(item)

        # Sort dates
        sorted_dates = sorted(by_date.keys(), key=lambda d: AIMarkdownFormatter._parse_date(d))

        for date in sorted_dates:
            md += f"## {date}\n\n"

            for item in by_date[date]:
                # Skip if no action description
                action = item.get('action', '').strip()
                if not action or action == 'No action described':
                    continue

                responsible = item.get('responsible', 'unspecified')
                deadline = item.get('deadline')
                status = item.get('status', 'mentioned')
                priority = item.get('priority', 'medium')
                sender = item.get('original_sender', 'Unknown')
                time = item.get('original_time', '')
                content = item.get('original_content', '')

                # Priority emoji
                priority_emoji = {
                    'high': '🔴',
                    'medium': '🟡',
                    'low': '🟢'
                }.get(priority.lower(), '⚪')

                # Status emoji
                status_emoji = {
                    'completed': '✅',
                    'in-progress': '🔄',
                    'assigned': '📋',
                    'mentioned': '💬'
                }.get(status.lower(), '❓')

                md += f"### {priority_emoji} {status_emoji} {action}\n\n"
                md += f"- **Who**: {responsible}\n"
                if deadline:
                    md += f"- **Deadline**: {deadline}\n"
                md += f"- **Status**: {status}\n"
                md += f"- **Priority**: {priority}\n"
                md += f"- **Mentioned by**: {sender} at {time}\n"
                md += f"- **Original**: _{content[:200]}..._\n\n"

        return md

    @staticmethod
    def format_urls(items: List[Dict[str, Any]]) -> str:
        """Format URLs as markdown"""

        md = "# URLs & Links (AI-Analyzed)\n\n"
        md += f"*Total links found: {len(items)}*\n\n"
        md += "---\n\n"

        # Group by date
        by_date = {}
        for item in items:
            date = item.get('date', 'Unknown Date')
            if date not in by_date:
                by_date[date] = []
            by_date[date].append(item)

        sorted_dates = sorted(by_date.keys(), key=lambda d: AIMarkdownFormatter._parse_date(d))

        for date in sorted_dates:
            md += f"## {date}\n\n"

            for item in by_date[date]:
                url = item.get('url', '')
                description = item.get('description', 'No description')
                shared_by = item.get('shared_by', 'Unknown')
                context = item.get('context', 'No context available')
                time = item.get('time', '')

                md += f"### 🔗 {description}\n\n"
                md += f"- **URL**: {url}\n"
                md += f"- **Shared by**: {shared_by} at {time}\n"
                md += f"- **Context**: {context}\n\n"

        return md

    @staticmethod
    def format_decisions(items: List[Dict[str, Any]]) -> str:
        """Format decisions as markdown"""

        md = "# Decisions Made (AI-Analyzed)\n\n"
        md += f"*Total decisions found: {len(items)}*\n\n"
        md += "---\n\n"

        for i, item in enumerate(items, 1):
            decision = item.get('decision', 'No decision described')
            confidence = item.get('confidence', 'medium')
            participants = item.get('participants', [])
            date = item.get('date', 'Unknown')
            time = item.get('time', '')

            conf_emoji = {
                'high': '🟢',
                'medium': '🟡',
                'low': '🔴'
            }.get(confidence.lower(), '⚪')

            md += f"## {i}. {conf_emoji} {decision}\n\n"
            md += f"- **Confidence**: {confidence}\n"
            md += f"- **Participants**: {', '.join(participants)}\n"
            md += f"- **Date**: {date} at {time}\n\n"

        return md

    @staticmethod
    def _parse_date(date_str: str) -> datetime:
        """Parse date string for sorting"""
        try:
            # Try DD/MM/YYYY format
            return datetime.strptime(date_str, '%d/%m/%Y')
        except:
            try:
                # Try other formats
                return datetime.strptime(date_str, '%Y-%m-%d')
            except:
                # Return far future for unparseable dates
                return datetime(2099, 12, 31)

    @staticmethod
    def format_checkins(items: List[Dict[str, Any]]) -> str:
        """Format check-ins as markdown"""

        md = "# Daily Check-ins (AI-Analyzed)\n\n"
        md += f"*Total check-ins found: {len(items)}*\n\n"
        md += "---\n\n"

        if not items:
            md += "_No check-ins found in this chat._\n"
            return md

        # Group by date
        by_date = {}
        for item in items:
            date = item.get('date', 'Unknown Date')
            if date not in by_date:
                by_date[date] = []
            by_date[date].append(item)

        # Sort dates
        sorted_dates = sorted(by_date.keys(), key=lambda d: AIMarkdownFormatter._parse_date(d))

        for date in sorted_dates:
            md += f"## {date}\n\n"

            for item in by_date[date]:
                person = item.get('person', 'Unknown')
                score = item.get('score', 'N/A')
                comments = item.get('comments', 'No comments')
                time = item.get('time', '')

                # Score emoji based on value
                try:
                    score_value = int(score.split('/')[0])
                    if score_value >= 8:
                        score_emoji = '😊'
                    elif score_value >= 5:
                        score_emoji = '😐'
                    else:
                        score_emoji = '😔'
                except:
                    score_emoji = '📊'

                md += f"### {score_emoji} {person} - {score}\n\n"
                md += f"- **Time**: {time}\n"
                md += f"- **Mood**: {score}\n"
                md += f"- **Comments**: {comments}\n\n"

        return md

    @staticmethod
    def format_checkins_html(items: List[Dict[str, Any]]) -> str:
        """Format check-ins as interactive HTML with graph"""

        # Group by person and date
        by_person = {}
        for item in items:
            person = item.get('person', 'Unknown')
            if person not in by_person:
                by_person[person] = []
            by_person[person].append(item)

        # Sort each person's check-ins by date
        for person in by_person:
            by_person[person].sort(key=lambda x: AIMarkdownFormatter._parse_date(x.get('date', '01/01/2000')))

        # Build chart data
        import json
        chart_data = {}
        all_dates = set()

        for person, checkins in by_person.items():
            chart_data[person] = []
            for checkin in checkins:
                date = checkin.get('date', '')
                score = checkin.get('score', '0/10')
                # Extract numeric score
                try:
                    if '/' in score:
                        numeric_score = int(score.split('/')[0])
                    else:
                        numeric_score = int(score)
                except:
                    numeric_score = 0

                # Format date for display (DD/MM)
                date_parts = date.split('/')
                if len(date_parts) >= 2:
                    display_date = f"{date_parts[0]}/{date_parts[1]}"
                else:
                    display_date = date

                all_dates.add(display_date)
                chart_data[person].append({
                    'date': display_date,
                    'full_date': date,
                    'score': numeric_score,
                    'time': checkin.get('time', ''),
                    'comments': checkin.get('comments', 'No comments'),
                    'raw_score': score
                })

        # Get sorted dates
        sorted_dates = sorted(list(all_dates), key=lambda d: AIMarkdownFormatter._parse_date(d + '/2025'))

        # Generate colors for each person
        colors = ['#5B8FF9', '#9966CC', '#FF6B6B', '#4ECDC4', '#FFD93D']
        person_colors = {}
        for i, person in enumerate(by_person.keys()):
            person_colors[person] = colors[i % len(colors)]

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mood Trends Over Time</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }}

        h1 {{
            font-size: 32px;
            color: #333;
            margin-bottom: 30px;
            display: flex;
            align-items: center;
            gap: 15px;
        }}

        .chart-container {{
            position: relative;
            height: 500px;
            margin-bottom: 40px;
        }}

        svg {{
            width: 100%;
            height: 100%;
        }}

        .legend {{
            display: flex;
            gap: 30px;
            justify-content: center;
            margin-top: 20px;
            flex-wrap: wrap;
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 16px;
        }}

        .legend-color {{
            width: 30px;
            height: 4px;
            border-radius: 2px;
        }}

        .tooltip {{
            position: absolute;
            background: rgba(0, 0, 0, 0.9);
            color: white;
            padding: 15px;
            border-radius: 8px;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.2s;
            max-width: 400px;
            z-index: 1000;
            font-size: 14px;
            line-height: 1.6;
        }}

        .tooltip.show {{
            opacity: 1;
        }}

        .tooltip-header {{
            font-weight: bold;
            margin-bottom: 8px;
            font-size: 16px;
        }}

        .tooltip-score {{
            font-size: 24px;
            margin: 5px 0;
        }}

        .tooltip-comments {{
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid rgba(255, 255, 255, 0.3);
        }}

        .data-point {{
            cursor: pointer;
            transition: all 0.2s;
        }}

        .data-point:hover {{
            r: 8;
            filter: brightness(1.2);
        }}

        .grid-line {{
            stroke: #e0e0e0;
            stroke-width: 1;
        }}

        .axis-label {{
            fill: #666;
            font-size: 12px;
        }}

        .axis-line {{
            stroke: #333;
            stroke-width: 2;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Mood Trends Over Time</h1>

        <div class="chart-container">
            <svg id="chart"></svg>
            <div class="tooltip" id="tooltip"></div>
        </div>

        <div class="legend" id="legend"></div>
    </div>

    <script>
        const data = {json.dumps(chart_data)};
        const dates = {json.dumps(sorted_dates)};
        const colors = {json.dumps(person_colors)};

        const svg = document.getElementById('chart');
        const tooltip = document.getElementById('tooltip');
        const legend = document.getElementById('legend');

        // Chart dimensions
        const padding = {{ top: 40, right: 40, bottom: 60, left: 60 }};
        const width = svg.clientWidth;
        const height = svg.clientHeight;
        const chartWidth = width - padding.left - padding.right;
        const chartHeight = height - padding.top - padding.bottom;

        // Scales
        const xScale = (index) => padding.left + (index / (dates.length - 1)) * chartWidth;
        const yScale = (score) => padding.top + chartHeight - (score / 10) * chartHeight;

        // Draw grid lines
        for (let i = 0; i <= 10; i++) {{
            const y = yScale(i);
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', padding.left);
            line.setAttribute('y1', y);
            line.setAttribute('x2', width - padding.right);
            line.setAttribute('y2', y);
            line.setAttribute('class', 'grid-line');
            svg.appendChild(line);

            // Y-axis labels
            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('x', padding.left - 15);
            text.setAttribute('y', y + 4);
            text.setAttribute('class', 'axis-label');
            text.setAttribute('text-anchor', 'end');
            text.textContent = i;
            svg.appendChild(text);
        }}

        // Draw X-axis labels
        dates.forEach((date, i) => {{
            const x = xScale(i);
            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('x', x);
            text.setAttribute('y', height - padding.bottom + 25);
            text.setAttribute('class', 'axis-label');
            text.setAttribute('text-anchor', 'middle');
            text.textContent = date;
            svg.appendChild(text);
        }});

        // Draw axes
        const xAxis = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        xAxis.setAttribute('x1', padding.left);
        xAxis.setAttribute('y1', height - padding.bottom);
        xAxis.setAttribute('x2', width - padding.right);
        xAxis.setAttribute('y2', height - padding.bottom);
        xAxis.setAttribute('class', 'axis-line');
        svg.appendChild(xAxis);

        const yAxis = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        yAxis.setAttribute('x1', padding.left);
        yAxis.setAttribute('y1', padding.top);
        yAxis.setAttribute('x2', padding.left);
        yAxis.setAttribute('y2', height - padding.bottom);
        yAxis.setAttribute('class', 'axis-line');
        svg.appendChild(yAxis);

        // Draw lines and points for each person
        Object.keys(data).forEach(person => {{
            const checkins = data[person];
            const color = colors[person];

            // Draw line
            const points = checkins.map(checkin => {{
                const dateIndex = dates.indexOf(checkin.date);
                return `${{xScale(dateIndex)}},${{yScale(checkin.score)}}`;
            }}).join(' ');

            const polyline = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
            polyline.setAttribute('points', points);
            polyline.setAttribute('fill', 'none');
            polyline.setAttribute('stroke', color);
            polyline.setAttribute('stroke-width', '3');
            polyline.setAttribute('stroke-linejoin', 'round');
            svg.appendChild(polyline);

            // Draw points
            checkins.forEach(checkin => {{
                const dateIndex = dates.indexOf(checkin.date);
                const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                circle.setAttribute('cx', xScale(dateIndex));
                circle.setAttribute('cy', yScale(checkin.score));
                circle.setAttribute('r', '6');
                circle.setAttribute('fill', color);
                circle.setAttribute('stroke', 'white');
                circle.setAttribute('stroke-width', '2');
                circle.setAttribute('class', 'data-point');

                // Add hover events
                circle.addEventListener('mouseenter', (e) => {{
                    tooltip.innerHTML = `
                        <div class="tooltip-header">${{person}}</div>
                        <div class="tooltip-score">${{checkin.raw_score}}</div>
                        <div><strong>Date:</strong> ${{checkin.full_date}}</div>
                        <div><strong>Time:</strong> ${{checkin.time}}</div>
                        <div class="tooltip-comments"><strong>Comments:</strong> ${{checkin.comments}}</div>
                    `;
                    tooltip.classList.add('show');
                }});

                circle.addEventListener('mousemove', (e) => {{
                    tooltip.style.left = (e.pageX + 15) + 'px';
                    tooltip.style.top = (e.pageY + 15) + 'px';
                }});

                circle.addEventListener('mouseleave', () => {{
                    tooltip.classList.remove('show');
                }});

                svg.appendChild(circle);
            }});

            // Add to legend
            const legendItem = document.createElement('div');
            legendItem.className = 'legend-item';
            legendItem.innerHTML = `
                <div class="legend-color" style="background: ${{color}}"></div>
                <span>${{person}}</span>
            `;
            legend.appendChild(legendItem);
        }});
    </script>
</body>
</html>"""

        return html

    @staticmethod
    def format_questions(items: List[Dict[str, Any]]) -> str:
        """Format questions as markdown"""

        md = "# Questions (AI-Analyzed)\n\n"
        md += f"*Total questions found: {len(items)}*\n\n"
        md += "---\n\n"

        if not items:
            md += "_No questions found in this chat._\n"
            return md

        # Group by date
        by_date = {}
        for item in items:
            date = item.get('date', 'Unknown Date')
            if date not in by_date:
                by_date[date] = []
            by_date[date].append(item)

        # Sort dates
        sorted_dates = sorted(by_date.keys(), key=lambda d: AIMarkdownFormatter._parse_date(d))

        for date in sorted_dates:
            md += f"## {date}\n\n"

            for item in by_date[date]:
                question = item.get('question', '').strip()
                if not question:
                    continue

                asked_by = item.get('asked_by', 'Unknown')
                category = item.get('category', 'general')
                answered = item.get('answered', False)
                answer = item.get('answer', '')

                # Status emoji
                status_emoji = '✅' if answered else '❓'

                md += f"### {status_emoji} {question}\n\n"
                md += f"- **Asked by**: {asked_by}\n"
                md += f"- **Category**: {category}\n"
                md += f"- **Status**: {'Answered' if answered else 'Unanswered'}\n"

                if answered and answer:
                    md += f"- **Answer**: {answer}\n"

                md += "\n"

        return md

    @staticmethod
    def format_generic(items: List[Dict[str, Any]], query_type: str) -> str:
        """Generic formatter for other query types"""

        md = f"# {query_type.title()} (AI-Analyzed)\n\n"
        md += f"*Total items found: {len(items)}*\n\n"
        md += "---\n\n"

        import json
        for i, item in enumerate(items, 1):
            md += f"## Item {i}\n\n"
            md += "```json\n"
            md += json.dumps(item, indent=2)
            md += "\n```\n\n"

        return md

    @staticmethod
    def format_actions_html(items: List[Dict[str, Any]]) -> str:
        """Format action items as interactive HTML"""
        import json

        # Filter to only include actual actions
        real_actions = [
            item for item in items
            if item.get('is_action', False) == True
            and 'error' not in item
        ]

        # Group by date
        by_date = {}
        for item in real_actions:
            date = item.get('original_date', 'Unknown Date')
            if date not in by_date:
                by_date[date] = []
            by_date[date].append(item)

        # Sort dates
        sorted_dates = sorted(by_date.keys(), key=lambda d: AIMarkdownFormatter._parse_date(d))

        html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Action Items - AI Analysis</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }
        h1 {
            font-size: 32px;
            color: #333;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 15px;
        }
        .subtitle {
            color: #666;
            margin-bottom: 30px;
            font-size: 16px;
        }
        .date-section {
            margin-bottom: 40px;
        }
        .date-header {
            font-size: 24px;
            color: #667eea;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e0e0e0;
        }
        .action-card {
            background: #f8f9ff;
            border-left: 4px solid #667eea;
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 8px;
            transition: all 0.3s;
        }
        .action-card:hover {
            transform: translateX(5px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
        }
        .action-card.priority-high {
            border-left-color: #f44336;
            background: #fff5f5;
        }
        .action-card.priority-medium {
            border-left-color: #ff9800;
            background: #fff9f5;
        }
        .action-card.priority-low {
            border-left-color: #4caf50;
            background: #f5fff5;
        }
        .action-title {
            font-size: 18px;
            font-weight: 600;
            color: #333;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .action-meta {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            margin-top: 12px;
        }
        .meta-item {
            font-size: 14px;
            color: #666;
        }
        .meta-label {
            font-weight: 600;
            color: #333;
        }
        .original-message {
            margin-top: 12px;
            padding: 10px;
            background: white;
            border-radius: 6px;
            font-size: 13px;
            color: #666;
            font-style: italic;
        }
        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }
        .badge.status-completed {
            background: #e8f5e9;
            color: #2e7d32;
        }
        .badge.status-in-progress {
            background: #fff3e0;
            color: #e65100;
        }
        .badge.status-assigned {
            background: #e3f2fd;
            color: #1565c0;
        }
        .badge.status-mentioned {
            background: #f3e5f5;
            color: #6a1b9a;
        }
        .no-actions {
            text-align: center;
            color: #666;
            padding: 40px;
            font-size: 18px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>✅ Action Items</h1>
        <p class="subtitle">AI-Analyzed from WhatsApp Chat • Total: """ + str(len(real_actions)) + """ actions</p>
"""

        if not real_actions:
            html += '<div class="no-actions">No action items found in this chat.</div>'
        else:
            for date in sorted_dates:
                html += f'<div class="date-section"><h2 class="date-header">{date}</h2>'

                for item in by_date[date]:
                    action = item.get('action', '').strip()
                    if not action or action == 'No action described':
                        continue

                    responsible = item.get('responsible', 'unspecified')
                    deadline = item.get('deadline', 'No deadline')
                    status = item.get('status', 'mentioned')
                    priority = item.get('priority', 'medium')
                    sender = item.get('original_sender', 'Unknown')
                    time = item.get('original_time', '')
                    content = item.get('original_content', '')

                    priority_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(priority.lower(), '⚪')
                    status_emoji = {'completed': '✅', 'in-progress': '🔄', 'assigned': '📋', 'mentioned': '💬'}.get(status.lower(), '❓')

                    html += f'''
        <div class="action-card priority-{priority.lower()}">
            <div class="action-title">{priority_emoji} {status_emoji} {action}</div>
            <div class="action-meta">
                <div class="meta-item"><span class="meta-label">Responsible:</span> {responsible}</div>
                <div class="meta-item"><span class="meta-label">Deadline:</span> {deadline}</div>
                <div class="meta-item"><span class="meta-label">Priority:</span> <span class="badge">{priority}</span></div>
                <div class="meta-item"><span class="meta-label">Status:</span> <span class="badge status-{status.lower()}">{status}</span></div>
            </div>
            <div class="meta-item" style="margin-top: 10px;"><span class="meta-label">Mentioned by:</span> {sender} at {time}</div>
            <div class="original-message">"{content[:200]}..."</div>
        </div>'''

                html += '</div>'

        html += """
    </div>
</body>
</html>"""

        return html

    @staticmethod
    def format_urls_html(items: List[Dict[str, Any]]) -> str:
        """Format URLs as interactive HTML with clickable links"""
        import json

        # Group by date
        by_date = {}
        for item in items:
            date = item.get('date', 'Unknown Date')
            if date not in by_date:
                by_date[date] = []
            by_date[date].append(item)

        sorted_dates = sorted(by_date.keys(), key=lambda d: AIMarkdownFormatter._parse_date(d))

        html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>URLs & Links - AI Analysis</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }
        h1 {
            font-size: 32px;
            color: #333;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 15px;
        }
        .subtitle {
            color: #666;
            margin-bottom: 30px;
            font-size: 16px;
        }
        .date-section {
            margin-bottom: 40px;
        }
        .date-header {
            font-size: 24px;
            color: #667eea;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e0e0e0;
        }
        .link-card {
            background: #f8f9ff;
            border-left: 4px solid #667eea;
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 8px;
            transition: all 0.3s;
        }
        .link-card:hover {
            transform: translateX(5px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
        }
        .link-title {
            font-size: 18px;
            font-weight: 600;
            color: #333;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .link-url {
            display: block;
            color: #667eea;
            text-decoration: none;
            font-size: 14px;
            margin-bottom: 10px;
            word-break: break-all;
            padding: 8px 12px;
            background: white;
            border-radius: 6px;
            transition: all 0.2s;
        }
        .link-url:hover {
            background: #667eea;
            color: white;
        }
        .link-meta {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 10px;
            margin-top: 12px;
        }
        .meta-item {
            font-size: 14px;
            color: #666;
        }
        .meta-label {
            font-weight: 600;
            color: #333;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔗 URLs & Links</h1>
        <p class="subtitle">AI-Analyzed from WhatsApp Chat • Total: """ + str(len(items)) + """ links</p>
"""

        if not items:
            html += '<div style="text-align: center; color: #666; padding: 40px; font-size: 18px;">No links found in this chat.</div>'
        else:
            for date in sorted_dates:
                html += f'<div class="date-section"><h2 class="date-header">{date}</h2>'

                for item in by_date[date]:
                    url = item.get('url', '')
                    description = item.get('description', 'No description')
                    shared_by = item.get('shared_by', 'Unknown')
                    time = item.get('time', '')
                    # Use the original message content like action items do
                    original_content = item.get('full_message', item.get('context', 'No context available'))

                    # Get URL content info if available
                    url_title = item.get('url_title', '')
                    url_summary = item.get('url_summary', '')

                    html += f'''
        <div class="link-card">
            <div class="link-title">🔗 {description}</div>
            <a href="{url}" target="_blank" class="link-url">{url}</a>
            <div class="link-meta">
                <div class="meta-item"><span class="meta-label">Shared by:</span> {shared_by} at {time}</div>
            </div>'''

                    # Show URL content summary if available
                    if url_title or url_summary:
                        html += f'''
            <div style="margin-top: 10px; padding: 12px; background: #e8f5e9; border-radius: 6px; border-left: 3px solid #4caf50;">
                <div style="font-weight: 600; color: #2e7d32; margin-bottom: 4px; font-size: 14px;">📄 Content: {url_title or 'Unknown'}</div>
                <div style="font-size: 13px; color: #555;">{url_summary or 'No summary available'}</div>
            </div>'''

                    # Show original message
                    html += f'''
            <div style="margin-top: 10px; padding: 10px; background: white; border-radius: 6px; font-size: 13px; color: #666; font-style: italic;">
                "{original_content[:200]}..."
            </div>
        </div>'''

                html += '</div>'

        html += """
    </div>
</body>
</html>"""

        return html

    @staticmethod
    def format_questions_html(items: List[Dict[str, Any]]) -> str:
        """Format questions as interactive HTML"""
        import json

        # Group by date
        by_date = {}
        for item in items:
            date = item.get('date', 'Unknown Date')
            if date not in by_date:
                by_date[date] = []
            by_date[date].append(item)

        sorted_dates = sorted(by_date.keys(), key=lambda d: AIMarkdownFormatter._parse_date(d))

        html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Questions - AI Analysis</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }
        h1 {
            font-size: 32px;
            color: #333;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 15px;
        }
        .subtitle {
            color: #666;
            margin-bottom: 30px;
            font-size: 16px;
        }
        .date-section {
            margin-bottom: 40px;
        }
        .date-header {
            font-size: 24px;
            color: #667eea;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e0e0e0;
        }
        .question-card {
            background: #f8f9ff;
            border-left: 4px solid #667eea;
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 8px;
            transition: all 0.3s;
        }
        .question-card:hover {
            transform: translateX(5px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
        }
        .question-card.answered {
            border-left-color: #4caf50;
            background: #f5fff5;
        }
        .question-card.unanswered {
            border-left-color: #ff9800;
            background: #fff9f5;
        }
        .question-title {
            font-size: 18px;
            font-weight: 600;
            color: #333;
            margin-bottom: 12px;
            display: flex;
            align-items: flex-start;
            gap: 8px;
        }
        .question-meta {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            margin-top: 12px;
        }
        .meta-item {
            font-size: 14px;
            color: #666;
        }
        .meta-label {
            font-weight: 600;
            color: #333;
        }
        .answer-box {
            margin-top: 12px;
            padding: 12px;
            background: white;
            border-radius: 6px;
            border-left: 3px solid #4caf50;
        }
        .answer-label {
            font-weight: 600;
            color: #4caf50;
            margin-bottom: 5px;
        }
        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            background: #e3f2fd;
            color: #1565c0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>❓ Questions</h1>
        <p class="subtitle">AI-Analyzed from WhatsApp Chat • Total: """ + str(len(items)) + """ questions</p>
"""

        if not items:
            html += '<div style="text-align: center; color: #666; padding: 40px; font-size: 18px;">No questions found in this chat.</div>'
        else:
            for date in sorted_dates:
                html += f'<div class="date-section"><h2 class="date-header">{date}</h2>'

                for item in by_date[date]:
                    question = item.get('question', '').strip()
                    if not question:
                        continue

                    asked_by = item.get('asked_by', 'Unknown')
                    category = item.get('category', 'general')
                    answered = item.get('answered', False)
                    answer = item.get('answer', '')

                    status_emoji = '✅' if answered else '❓'
                    card_class = 'answered' if answered else 'unanswered'

                    html += f'''
        <div class="question-card {card_class}">
            <div class="question-title">{status_emoji} {question}</div>
            <div class="question-meta">
                <div class="meta-item"><span class="meta-label">Asked by:</span> {asked_by}</div>
                <div class="meta-item"><span class="meta-label">Category:</span> <span class="badge">{category}</span></div>
                <div class="meta-item"><span class="meta-label">Status:</span> {'Answered' if answered else 'Unanswered'}</div>
            </div>'''

                    if answered and answer:
                        html += f'''
            <div class="answer-box">
                <div class="answer-label">✅ Answer:</div>
                <div>{answer}</div>
            </div>'''

                    html += '</div>'

                html += '</div>'

        html += """
    </div>
</body>
</html>"""

        return html

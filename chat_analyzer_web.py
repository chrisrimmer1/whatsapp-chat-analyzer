#!/usr/bin/env python3
"""
Web Interface for Chat Analyzer
Simple Flask app for non-technical users
"""

from flask import Flask, render_template, request, send_file, jsonify, flash, redirect, url_for
from werkzeug.utils import secure_filename
import os
import json
from pathlib import Path
import tempfile
import zipfile
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from chat_analyzer import ChatParser, CandidateExtractor, OutputFormatter
from chat_analyzer_ai import AIAnalyzer
from ai_formatter import AIMarkdownFormatter
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

ALLOWED_EXTENSIONS = {'txt', 'zip'}
QUERY_TYPES = {
    'actions': {
        'name': 'Action Items',
        'description': 'Task assignments, deliverables, and things to do',
        'icon': '✅'
    },
    'urls': {
        'name': 'URLs & Links',
        'description': 'All links shared with who posted them and why',
        'icon': '🔗'
    },
    'checkins': {
        'name': 'Check-ins',
        'description': 'Daily mood scores and check-in messages',
        'icon': '📊'
    }
}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """Home page"""
    return render_template('index.html', query_types=QUERY_TYPES)


@app.route('/debug/env')
def debug_env():
    """Debug endpoint to check environment variables"""
    env_check = {
        'GOOGLE_TOKEN': 'SET' if os.environ.get('GOOGLE_TOKEN') else 'NOT SET',
        'GOOGLE_TOKEN_LENGTH': len(os.environ.get('GOOGLE_TOKEN', '')) if os.environ.get('GOOGLE_TOKEN') else 0,
        'OPENROUTER_API_KEY': 'SET' if os.environ.get('OPENROUTER_API_KEY') else 'NOT SET',
    }
    return jsonify(env_check)


@app.route('/analyze', methods=['POST'])
def analyze():
    """Process uploaded file and extract information"""

    # Check if file was uploaded
    if 'file' not in request.files:
        flash('No file uploaded', 'error')
        return redirect(url_for('index'))

    file = request.files['file']

    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('index'))

    if not allowed_file(file.filename):
        flash('Only .txt files are allowed', 'error')
        return redirect(url_for('index'))

    # Get query type and date filter
    query_type = request.form.get('query_type', 'actions')
    output_format = request.form.get('output_format', 'markdown')
    days_back = request.form.get('days_back', '7')  # Default: 7 days

    try:
        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Handle ZIP files - extract the .txt file
        original_filepath = filepath
        if filename.endswith('.zip'):
            print(f"📦 Extracting ZIP file: {filename}...")
            try:
                with zipfile.ZipFile(filepath, 'r') as zip_ref:
                    # Find .txt file in the ZIP
                    txt_files = [f for f in zip_ref.namelist() if f.endswith('.txt') and not f.startswith('__MACOSX')]

                    if not txt_files:
                        flash('No .txt file found in the ZIP archive', 'error')
                        return redirect(url_for('index'))

                    # Extract the first .txt file
                    txt_filename = txt_files[0]

                    # Read the file content and write it to a flat location
                    # This avoids subdirectory issues
                    txt_content = zip_ref.read(txt_filename)
                    flat_filename = os.path.basename(txt_filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], flat_filename)

                    with open(filepath, 'wb') as f:
                        f.write(txt_content)

                    filename = flat_filename
                    print(f"✓ Extracted: {filename}")
            except zipfile.BadZipFile:
                flash('Invalid ZIP file', 'error')
                return redirect(url_for('index'))

        # Parse and analyze
        print(f"📖 Parsing {filename}...")
        parser = ChatParser(filepath)
        messages = parser.parse()
        print(f"✓ Parsed {len(messages)} messages")

        # Filter by days back if provided
        if days_back:
            try:
                days = int(days_back)
                from datetime import timedelta

                # Find the most recent message date in the file
                if messages:
                    most_recent_date = max(datetime.strptime(m['date'], '%d/%m/%Y') for m in messages)
                    cutoff_date = most_recent_date - timedelta(days=days)

                    original_count = len(messages)
                    messages = [m for m in messages if datetime.strptime(m['date'], '%d/%m/%Y') >= cutoff_date]
                    print(f"✓ Filtered to {len(messages)} messages from last {days} days (removed {original_count - len(messages)})")
                    print(f"  Most recent message: {most_recent_date.strftime('%d/%m/%Y')}, cutoff: {cutoff_date.strftime('%d/%m/%Y')}")
            except Exception as date_error:
                print(f"⚠️ Date filter error: {date_error}, processing all messages")

        # Extract candidates
        print(f"🔍 Extracting {query_type}...")
        extractor = CandidateExtractor(messages)
        candidates = extractor.extract(query_type)
        print(f"✓ Found {len(candidates)} candidates")

        # Use AI to enhance results
        print(f"🤖 Analyzing with AI (OpenRouter)...")
        ai_analyzer = AIAnalyzer()
        ai_results = ai_analyzer.analyze_chunk(candidates, query_type)
        print(f"✅ AI analysis complete: {len(ai_results)} refined results")

        # Generate output using AI formatter - always use HTML now
        output_extension = 'html'
        # Use just the filename (not full path) to avoid subdirectory issues
        base_filename = os.path.basename(filepath).replace('.txt', '')
        output_filename = f'{base_filename}_{query_type}_AI.html'
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)

        if query_type == 'actions':
            html_content = AIMarkdownFormatter.format_actions_html(ai_results)
        elif query_type == 'urls':
            html_content = AIMarkdownFormatter.format_urls_html(ai_results)
        elif query_type == 'checkins':
            html_content = AIMarkdownFormatter.format_checkins_html(ai_results)
        else:
            # Fallback to markdown for unknown types, then wrap in basic HTML
            markdown_content = AIMarkdownFormatter.format_generic(ai_results, query_type)
            html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{query_type.title()} - AI Analysis</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }}
        pre {{
            background: #f5f5f5;
            padding: 20px;
            border-radius: 8px;
            overflow-x: auto;
        }}
    </style>
</head>
<body>
    <div class="container">
        <pre>{markdown_content}</pre>
    </div>
</body>
</html>"""

        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        # Return JSON with download info
        file_id = output_filename  # Use the filename we created earlier
        print(f"📝 Created file: {output_path}")
        print(f"📤 Returning file_id: {file_id}")

        return jsonify({
            'success': True,
            'file_id': file_id,
            'filename': file_id,  # Just use file_id as the download name
            'download_url': url_for('download_file', file_id=file_id)
        })

    except Exception as e:
        flash(f'Error processing file: {str(e)}', 'error')
        return redirect(url_for('index'))

    finally:
        # Clean up temporary INPUT files only (not the output file - it will be cleaned up after download)
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
            # Also clean up original ZIP if it was different
            if 'original_filepath' in locals() and original_filepath != filepath and os.path.exists(original_filepath):
                os.remove(original_filepath)
        except:
            pass


@app.route('/download/<path:file_id>')
def download_file(file_id):
    """Serve the generated file for viewing/download"""
    try:
        # Don't use secure_filename since we control the filename and it strips underscores
        # Just validate that it doesn't contain path traversal characters
        if '..' in file_id or '/' in file_id or '\\' in file_id:
            return jsonify({'error': 'Invalid file_id'}), 400

        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_id)

        print(f"📥 Download request for file_id: {file_id}")
        print(f"📂 Looking for file at: {file_path}")
        print(f"❓ File exists: {os.path.exists(file_path)}")

        if not os.path.exists(file_path):
            # List files in temp folder for debugging
            temp_files = os.listdir(app.config['UPLOAD_FOLDER'])
            print(f"📁 Files in temp folder: {temp_files}")
            return jsonify({'error': 'File not found'}), 404

        # Serve HTML files inline (for viewing in browser), others as attachment
        is_html = file_id.endswith('.html')

        response = send_file(
            file_path,
            as_attachment=not is_html,  # HTML opens in browser, others download
            download_name=file_id,
            mimetype='text/html' if is_html else None
        )

        # Clean up the file after a delay (using a background task would be better, but this works)
        # Actually, we can't delete here because the file is being streamed
        # We'll rely on temp folder cleanup or implement a cleanup job later

        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/preview', methods=['POST'])
def preview():
    """Preview results without downloading"""

    # Check if file was uploaded
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Only .txt files allowed'}), 400

    query_type = request.form.get('query_type', 'actions')

    try:
        # Save temporarily
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Parse and analyze
        parser = ChatParser(filepath)
        messages = parser.parse()

        extractor = CandidateExtractor(messages)
        candidates = extractor.extract(query_type)

        # Use AI to enhance results (limit to first 20 for preview)
        ai_analyzer = AIAnalyzer()
        candidates_preview = candidates[:20]
        candidates_preview = ai_analyzer.analyze_chunk(candidates_preview, query_type)

        # Return preview
        preview_items = candidates_preview[:10]  # First 10 items

        return jsonify({
            'total_messages': len(messages),
            'total_found': len(candidates),
            'preview': preview_items,
            'query_type': query_type
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        # Clean up
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except:
            pass


if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)

    # Create basic HTML template if it doesn't exist
    template_path = Path('templates/index.html')
    if not template_path.exists():
        template_path.write_text("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WhatsApp Chat Analyzer</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 2em;
        }
        .subtitle {
            color: #666;
            margin-bottom: 30px;
            font-size: 1.1em;
        }
        .upload-area {
            border: 3px dashed #667eea;
            border-radius: 8px;
            padding: 40px;
            text-align: center;
            margin-bottom: 30px;
            background: #f8f9ff;
            cursor: pointer;
            transition: all 0.3s;
        }
        .upload-area:hover {
            background: #f0f2ff;
            border-color: #764ba2;
        }
        .upload-area.dragover {
            background: #e8ebff;
            border-color: #764ba2;
        }
        .file-input-label {
            font-size: 1.2em;
            color: #667eea;
            cursor: pointer;
            display: block;
        }
        input[type="file"] {
            display: none;
        }
        .query-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        .query-option {
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            padding: 20px;
            cursor: pointer;
            transition: all 0.3s;
            text-align: center;
        }
        .query-option:hover {
            border-color: #667eea;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
        }
        .query-option.selected {
            border-color: #667eea;
            background: #f8f9ff;
        }
        .query-icon {
            font-size: 2em;
            margin-bottom: 10px;
        }
        .query-name {
            font-weight: 600;
            color: #333;
            margin-bottom: 5px;
        }
        .query-desc {
            font-size: 0.85em;
            color: #666;
        }
        .format-options {
            margin-bottom: 30px;
        }
        .format-label {
            font-weight: 600;
            color: #333;
            margin-bottom: 10px;
            display: block;
        }
        .radio-group {
            display: flex;
            gap: 20px;
        }
        .radio-option {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        button {
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 1.1em;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
        }
        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .flash {
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .flash.error {
            background: #fee;
            color: #c33;
            border: 1px solid #fcc;
        }
        .flash.success {
            background: #efe;
            color: #3c3;
            border: 1px solid #cfc;
        }
        .preview {
            margin-top: 20px;
            padding: 20px;
            background: #f8f9ff;
            border-radius: 8px;
            border: 1px solid #e0e0e0;
        }
        .preview-title {
            font-weight: 600;
            color: #333;
            margin-bottom: 10px;
        }
        .stats {
            display: flex;
            gap: 20px;
            margin-bottom: 15px;
        }
        .stat {
            flex: 1;
            padding: 10px;
            background: white;
            border-radius: 6px;
            text-align: center;
        }
        .stat-value {
            font-size: 1.5em;
            font-weight: 700;
            color: #667eea;
        }
        .stat-label {
            font-size: 0.85em;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📱 WhatsApp Chat Analyzer</h1>
        <p class="subtitle">Extract structured information from your chat exports</p>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <form method="POST" action="/analyze" enctype="multipart/form-data" id="analyzeForm">
            <div class="upload-area" id="uploadArea">
                <label for="fileInput" class="file-input-label">
                    📁 Click or drag to upload chat file (.txt)
                </label>
                <input type="file" name="file" id="fileInput" accept=".txt" required>
                <p style="margin-top: 10px; color: #999; font-size: 0.9em;" id="fileName"></p>
            </div>

            <div class="query-grid">
                {% for key, info in query_types.items() %}
                <div class="query-option" data-query="{{ key }}">
                    <div class="query-icon">{{ info.icon }}</div>
                    <div class="query-name">{{ info.name }}</div>
                    <div class="query-desc">{{ info.description }}</div>
                </div>
                {% endfor %}
            </div>
            <input type="hidden" name="query_type" id="queryType" value="actions">

            <div class="format-options">
                <label class="format-label">Output Format:</label>
                <div class="radio-group">
                    <label class="radio-option">
                        <input type="radio" name="output_format" value="markdown" checked>
                        <span>Markdown (.md)</span>
                    </label>
                    <label class="radio-option">
                        <input type="radio" name="output_format" value="json">
                        <span>JSON (.json)</span>
                    </label>
                </div>
            </div>

            <button type="submit" id="submitBtn">Analyze Chat</button>
        </form>

        <div id="preview" class="preview" style="display: none;">
            <div class="preview-title">Preview Results</div>
            <div class="stats">
                <div class="stat">
                    <div class="stat-value" id="totalMessages">-</div>
                    <div class="stat-label">Total Messages</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="totalFound">-</div>
                    <div class="stat-label">Items Found</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // File upload handling
        const fileInput = document.getElementById('fileInput');
        const uploadArea = document.getElementById('uploadArea');
        const fileName = document.getElementById('fileName');

        fileInput.addEventListener('change', function() {
            if (this.files.length > 0) {
                fileName.textContent = '✓ ' + this.files[0].name;
            }
        });

        // Drag and drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            if (e.dataTransfer.files.length > 0) {
                fileInput.files = e.dataTransfer.files;
                fileName.textContent = '✓ ' + e.dataTransfer.files[0].name;
            }
        });

        // Query type selection
        const queryOptions = document.querySelectorAll('.query-option');
        const queryTypeInput = document.getElementById('queryType');

        // Set first option as selected by default
        queryOptions[0].classList.add('selected');

        queryOptions.forEach(option => {
            option.addEventListener('click', function() {
                queryOptions.forEach(opt => opt.classList.remove('selected'));
                this.classList.add('selected');
                queryTypeInput.value = this.dataset.query;
            });
        });
    </script>
</body>
</html>
        """)

    port = int(os.environ.get('PORT', 8080))
    print("🌐 Starting web interface...")
    print(f"📍 Open http://localhost:{port} in your browser")
    app.run(debug=True, port=port, host='0.0.0.0')

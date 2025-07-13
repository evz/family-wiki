#!/usr/bin/env python3
"""
Flask web interface for Family Wiki tools

This provides a simple web interface to access all the genealogy processing tools
through a browser instead of the command line.
"""

import sys
from pathlib import Path
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import subprocess
import json
import os

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from shared_genealogy.logging_config import get_project_logger

app = Flask(__name__)
app.secret_key = 'family-wiki-secret-key-change-in-production'

logger = get_project_logger(__name__)

@app.route('/')
def index():
    """Main dashboard showing available tools"""
    return render_template('index.html')

@app.route('/api/status')
def status():
    """API endpoint to check system status"""
    return jsonify({
        'status': 'running',
        'tools': {
            'ocr': 'Available',
            'benchmark': 'Available', 
            'extract': 'Available',
            'gedcom': 'Available',
            'research': 'Available'
        }
    })

@app.route('/api/run/<tool>')
def run_tool(tool):
    """API endpoint to run a specific tool"""
    valid_tools = ['ocr', 'benchmark', 'extract', 'gedcom', 'research', 'pipeline']
    
    if tool not in valid_tools:
        return jsonify({'error': f'Invalid tool: {tool}'}), 400
    
    try:
        # Run the CLI tool
        cmd = [sys.executable, 'family_wiki_cli.py', tool]
        if request.args.get('verbose'):
            cmd.insert(-1, '--verbose')
            
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )
        
        return jsonify({
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'return_code': result.returncode
        })
        
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Tool execution timed out'}), 408
    except Exception as e:
        logger.error(f"Error running tool {tool}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/tools/<tool>')
def tool_page(tool):
    """Individual tool pages"""
    valid_tools = {
        'ocr': 'OCR Processing',
        'benchmark': 'Model Benchmarking',
        'extract': 'LLM Extraction', 
        'gedcom': 'GEDCOM Generation',
        'research': 'Research Questions',
        'pipeline': 'Full Pipeline'
    }
    
    if tool not in valid_tools:
        flash(f'Unknown tool: {tool}', 'error')
        return redirect(url_for('index'))
    
    return render_template('tool.html', tool=tool, tool_name=valid_tools[tool])

@app.route('/logs')
def logs():
    """View recent log files"""
    logs_dir = PROJECT_ROOT / 'logs'
    log_files = []
    
    if logs_dir.exists():
        for log_file in sorted(logs_dir.glob('*.log'), reverse=True)[:10]:
            log_files.append({
                'name': log_file.name,
                'size': log_file.stat().st_size,
                'modified': log_file.stat().st_mtime
            })
    
    return render_template('logs.html', log_files=log_files)

@app.route('/api/logs/<filename>')
def get_log(filename):
    """API endpoint to get log file contents"""
    logs_dir = PROJECT_ROOT / 'logs'
    log_file = logs_dir / filename
    
    if not log_file.exists() or not log_file.name.endswith('.log'):
        return jsonify({'error': 'Log file not found'}), 404
    
    try:
        # Get last 1000 lines of log file
        with open(log_file, 'r') as f:
            lines = f.readlines()
            recent_lines = lines[-1000:] if len(lines) > 1000 else lines
            
        return jsonify({
            'content': ''.join(recent_lines),
            'total_lines': len(lines),
            'showing_lines': len(recent_lines)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def create_templates():
    """Create basic HTML templates"""
    templates_dir = PROJECT_ROOT / 'templates'
    
    # Base template
    base_template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Family Wiki Tools</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 2rem; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .header { border-bottom: 2px solid #333; margin-bottom: 2rem; padding-bottom: 1rem; }
        .tool-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem; margin: 2rem 0; }
        .tool-card { border: 1px solid #ddd; padding: 1.5rem; border-radius: 6px; background: #f9f9f9; }
        .tool-card h3 { margin-top: 0; color: #333; }
        .btn { background: #007bff; color: white; padding: 0.5rem 1rem; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; }
        .btn:hover { background: #0056b3; }
        .btn-secondary { background: #6c757d; }
        .btn-secondary:hover { background: #545b62; }
        .status { padding: 1rem; margin: 1rem 0; border-radius: 4px; }
        .status.success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .status.error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .log-output { background: #1e1e1e; color: #ffffff; padding: 1rem; border-radius: 4px; font-family: monospace; white-space: pre-wrap; max-height: 400px; overflow-y: auto; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Family Wiki - Genealogy Tools</h1>
            <nav>
                <a href="/" class="btn btn-secondary">Dashboard</a>
                <a href="/logs" class="btn btn-secondary">Logs</a>
            </nav>
        </div>
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="status {{ 'error' if category == 'error' else 'success' }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        {% block content %}{% endblock %}
    </div>
    <script>
        function runTool(tool, verbose = false) {
            const btn = event.target;
            btn.disabled = true;
            btn.textContent = 'Running...';
            
            const url = `/api/run/${tool}${verbose ? '?verbose=1' : ''}`;
            fetch(url)
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert('Tool completed successfully!');
                    } else {
                        alert(`Tool failed: ${data.stderr || data.error}`);
                    }
                })
                .catch(error => {
                    alert(`Error: ${error}`);
                })
                .finally(() => {
                    btn.disabled = false;
                    btn.textContent = btn.dataset.originalText;
                });
        }
    </script>
</body>
</html>'''
    
    # Index template
    index_template = '''{% extends "base.html" %}
{% block content %}
<h2>Available Tools</h2>
<div class="tool-grid">
    <div class="tool-card">
        <h3>OCR Processing</h3>
        <p>Extract text from PDF files using OCR with rotation detection.</p>
        <button class="btn" onclick="runTool('ocr')" data-original-text="Run OCR">Run OCR</button>
        <a href="/tools/ocr" class="btn btn-secondary">Details</a>
    </div>
    
    <div class="tool-card">
        <h3>Model Benchmarking</h3>
        <p>Test multiple LLM models to find the best one for genealogy extraction.</p>
        <button class="btn" onclick="runTool('benchmark')" data-original-text="Run Benchmark">Run Benchmark</button>
        <a href="/tools/benchmark" class="btn btn-secondary">Details</a>
    </div>
    
    <div class="tool-card">
        <h3>LLM Extraction</h3>
        <p>Extract genealogical data from text using AI language models.</p>
        <button class="btn" onclick="runTool('extract')" data-original-text="Run Extraction">Run Extraction</button>
        <a href="/tools/extract" class="btn btn-secondary">Details</a>
    </div>
    
    <div class="tool-card">
        <h3>GEDCOM Generation</h3>
        <p>Generate standard GEDCOM files from extracted genealogy data.</p>
        <button class="btn" onclick="runTool('gedcom')" data-original-text="Generate GEDCOM">Generate GEDCOM</button>
        <a href="/tools/gedcom" class="btn btn-secondary">Details</a>
    </div>
    
    <div class="tool-card">
        <h3>Research Questions</h3>
        <p>Generate intelligent research questions from your family data.</p>
        <button class="btn" onclick="runTool('research')" data-original-text="Generate Questions">Generate Questions</button>
        <a href="/tools/research" class="btn btn-secondary">Details</a>
    </div>
    
    <div class="tool-card">
        <h3>Full Pipeline</h3>
        <p>Run the complete processing pipeline from OCR to research questions.</p>
        <button class="btn" onclick="runTool('pipeline')" data-original-text="Run Pipeline">Run Pipeline</button>
        <a href="/tools/pipeline" class="btn btn-secondary">Details</a>
    </div>
</div>
{% endblock %}'''
    
    # Tool template
    tool_template = '''{% extends "base.html" %}
{% block content %}
<h2>{{ tool_name }}</h2>
<div class="tool-details">
    <div class="tool-actions">
        <button class="btn" onclick="runTool('{{ tool }}')" data-original-text="Run {{ tool_name }}">Run {{ tool_name }}</button>
        <button class="btn btn-secondary" onclick="runTool('{{ tool }}', true)" data-original-text="Run Verbose">Run Verbose</button>
        <a href="/" class="btn btn-secondary">Back to Dashboard</a>
    </div>
    
    <div class="tool-info">
        {% if tool == 'ocr' %}
            <h3>About OCR Processing</h3>
            <p>This tool extracts text from PDF files using Optical Character Recognition (OCR) with automatic rotation detection.</p>
            <ul>
                <li>Processes all 101 PDF pages in the pdf_processing/pdfs/ directory</li>
                <li>Detects and corrects rotated pages automatically</li>
                <li>Creates individual text files for each page</li>
                <li>Generates a consolidated text file combining all pages</li>
            </ul>
            <p><strong>Requirements:</strong> PDF files must be present in pdf_processing/pdfs/ directory</p>
        {% elif tool == 'benchmark' %}
            <h3>About Model Benchmarking</h3>
            <p>This tool tests multiple LLM models to find the best one for genealogy data extraction from Dutch text.</p>
            <ul>
                <li>Tests various local LLM models (Qwen, Llama, etc.)</li>
                <li>Evaluates extraction accuracy on sample genealogy text</li>
                <li>Provides performance and quality metrics</li>
                <li>Recommends the optimal model for your system</li>
            </ul>
            <p><strong>Requirements:</strong> Local LLM models installed (via Ollama or similar)</p>
        {% elif tool == 'extract' %}
            <h3>About LLM Extraction</h3>
            <p>This tool uses AI language models to intelligently extract genealogical data from Dutch text.</p>
            <ul>
                <li>Processes consolidated text from OCR step</li>
                <li>Extracts person names, dates, places, relationships</li>
                <li>Handles Dutch naming conventions and particles</li>
                <li>Produces structured JSON data with confidence scores</li>
            </ul>
            <p><strong>Requirements:</strong> Consolidated text file from OCR processing</p>
        {% elif tool == 'gedcom' %}
            <h3>About GEDCOM Generation</h3>
            <p>This tool converts extracted genealogy data into standard GEDCOM format files.</p>
            <ul>
                <li>Reads structured data from LLM extraction</li>
                <li>Creates GEDCOM 5.5 compatible files</li>
                <li>Handles Dutch genealogical conventions</li>
                <li>Can be imported into genealogy software</li>
            </ul>
            <p><strong>Requirements:</strong> JSON results from LLM extraction step</p>
        {% elif tool == 'research' %}
            <h3>About Research Questions</h3>
            <p>This tool generates intelligent research questions based on your extracted family data.</p>
            <ul>
                <li>Analyzes gaps in family information</li>
                <li>Suggests specific research directions</li>
                <li>Identifies potential archive sources</li>
                <li>Prioritizes questions by importance</li>
            </ul>
            <p><strong>Requirements:</strong> Extracted genealogy data</p>
        {% elif tool == 'pipeline' %}
            <h3>About Full Pipeline</h3>
            <p>This tool runs the complete processing pipeline from PDF files to research questions.</p>
            <ul>
                <li>Executes all tools in sequence</li>
                <li>Handles errors and continues where possible</li>
                <li>Provides comprehensive logging</li>
                <li>Suitable for complete end-to-end processing</li>
            </ul>
            <p><strong>Requirements:</strong> PDF files and all dependencies installed</p>
        {% endif %}
    </div>
    
    <div id="output-section" style="display: none;">
        <h3>Output</h3>
        <div id="tool-output" class="log-output"></div>
    </div>
</div>

<script>
function runTool(tool, verbose = false) {
    const btn = event.target;
    const originalText = btn.dataset.originalText || btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Running...';
    
    // Show output section
    document.getElementById('output-section').style.display = 'block';
    document.getElementById('tool-output').textContent = 'Starting...\\n';
    
    const url = `/api/run/${tool}${verbose ? '?verbose=1' : ''}`;
    fetch(url)
        .then(response => response.json())
        .then(data => {
            const output = document.getElementById('tool-output');
            if (data.success) {
                output.textContent = `✅ Tool completed successfully!\\n\\nOutput:\\n${data.stdout}`;
                if (data.stderr) {
                    output.textContent += `\\n\\nWarnings:\\n${data.stderr}`;
                }
            } else {
                output.textContent = `❌ Tool failed!\\n\\nError:\\n${data.stderr || data.error}`;
                if (data.stdout) {
                    output.textContent += `\\n\\nOutput:\\n${data.stdout}`;
                }
            }
        })
        .catch(error => {
            document.getElementById('tool-output').textContent = `❌ Network Error: ${error}`;
        })
        .finally(() => {
            btn.disabled = false;
            btn.textContent = originalText;
        });
}
</script>
{% endblock %}'''

    # Logs template
    logs_template = '''{% extends "base.html" %}
{% block content %}
<h2>Log Files</h2>
<div class="logs-section">
    {% if log_files %}
        <div class="log-list">
            {% for log_file in log_files %}
                <div class="tool-card">
                    <h3>{{ log_file.name }}</h3>
                    <p>Size: {{ "%.1f"|format(log_file.size / 1024) }} KB</p>
                    <p>Modified: {{ log_file.modified|int|datetime }}</p>
                    <button class="btn" onclick="viewLog('{{ log_file.name }}')">View Log</button>
                </div>
            {% endfor %}
        </div>
    {% else %}
        <p>No log files found. Run some tools to generate logs.</p>
    {% endif %}
    
    <div id="log-viewer" style="display: none; margin-top: 2rem;">
        <h3 id="log-title">Log Contents</h3>
        <div id="log-content" class="log-output"></div>
        <button class="btn btn-secondary" onclick="closeLog()">Close</button>
    </div>
</div>

<script>
function viewLog(filename) {
    fetch(`/api/logs/${filename}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(`Error loading log: ${data.error}`);
                return;
            }
            
            document.getElementById('log-title').textContent = `Log: ${filename}`;
            document.getElementById('log-content').textContent = data.content;
            document.getElementById('log-viewer').style.display = 'block';
            
            if (data.showing_lines < data.total_lines) {
                document.getElementById('log-title').textContent += ` (showing last ${data.showing_lines} of ${data.total_lines} lines)`;
            }
        })
        .catch(error => {
            alert(`Error: ${error}`);
        });
}

function closeLog() {
    document.getElementById('log-viewer').style.display = 'none';
}
</script>
{% endblock %}'''

    # Write templates
    (templates_dir / 'base.html').write_text(base_template)
    (templates_dir / 'index.html').write_text(index_template)
    (templates_dir / 'tool.html').write_text(tool_template)
    (templates_dir / 'logs.html').write_text(logs_template)

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    templates_dir = PROJECT_ROOT / 'templates'
    templates_dir.mkdir(exist_ok=True)
    
    # Create basic templates if they don't exist
    create_templates()
    
    app.run(debug=True, host='0.0.0.0', port=5000)
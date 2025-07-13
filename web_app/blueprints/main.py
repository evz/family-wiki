"""
Main blueprint for web interface
"""

import sys
from pathlib import Path
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash

# Add project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from shared_genealogy.logging_config import get_project_logger
from web_app.services.ocr_service import ocr_service
from web_app.services.gedcom_service import gedcom_service
from web_app.services.research_service import research_service
from web_app.services.benchmark_service import benchmark_service

logger = get_project_logger(__name__)

main = Blueprint('main', __name__)

@main.route('/')
def index():
    """Main dashboard showing available tools"""
    return render_template('index.html')

@main.route('/tools/<tool>')
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
        return redirect(url_for('main.index'))
    
    return render_template('tool.html', tool=tool, tool_name=valid_tools[tool])

@main.route('/api/status')
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

@main.route('/api/run/<tool>')
def run_tool(tool):
    """API endpoint to run tools using shared services"""
    valid_tools = ['ocr', 'benchmark', 'gedcom', 'research']
    
    if tool not in valid_tools:
        return jsonify({'error': f'Invalid tool: {tool}'}), 400
    
    try:
        verbose = request.args.get('verbose', False)
        
        # Route to appropriate service
        if tool == 'ocr':
            result = ocr_service.process_pdfs()
        elif tool == 'benchmark':
            result = benchmark_service.run_benchmark()
        elif tool == 'gedcom':
            result = gedcom_service.generate_gedcom()
        elif tool == 'research':
            result = research_service.generate_questions()
        
        # Convert service result to web API format
        if result['success']:
            return jsonify({
                'success': True,
                'stdout': result.get('message', ''),
                'stderr': '',
                'return_code': 0,
                'results': result.get('results', {})
            })
        else:
            return jsonify({
                'success': False,
                'stdout': '',
                'stderr': result.get('error', 'Unknown error'),
                'return_code': 1
            })
        
    except Exception as e:
        logger.error(f"Error running tool {tool}: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'stderr': str(e),
            'return_code': 1
        }), 500

@main.route('/logs')
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

@main.route('/api/logs/<filename>')
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
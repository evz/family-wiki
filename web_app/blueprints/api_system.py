"""
System status and tool execution API blueprint
"""

from pathlib import Path

from flask import Blueprint, jsonify

from web_app.pdf_processing.genealogy_model_benchmark import GenealogyModelBenchmark
from web_app.pdf_processing.ocr_processor import PDFOCRProcessor
from web_app.research_question_generator import ResearchQuestionGenerator
from web_app.services.extraction_service import extraction_service
from web_app.services.gedcom_service import gedcom_service
from web_app.services.system_service import system_service
from web_app.shared.logging_config import get_project_logger
from web_app.shared.service_utils import execute_with_progress


logger = get_project_logger(__name__)

api_system = Blueprint('api_system', __name__, url_prefix='/api')


@api_system.route('/status')
def status():
    """API endpoint to check system status"""
    system_status = system_service.check_system_status()
    return jsonify({
        'success': True,
        **system_status
    })


@api_system.route('/status/refresh')
def refresh_status():
    """API endpoint to refresh system status (for testing)"""
    system_status = system_service.check_system_status()
    return jsonify({
        'success': True,
        **system_status
    })


@api_system.route('/run/<tool>')
def run_tool(tool):
    """API endpoint to run tools using shared services"""
    valid_tools = ['ocr', 'benchmark', 'extract', 'gedcom', 'research']

    if tool not in valid_tools:
        return jsonify({'success': False, 'error': f'Invalid tool: {tool}'}), 400

    try:
        # Route to appropriate service
        if tool == 'ocr':
            processor = PDFOCRProcessor()
            pdf_dir = Path("web_app/pdf_processing/pdfs")
            result = execute_with_progress("OCR processing", lambda: processor.process_all_pdfs(pdf_dir))
        elif tool == 'benchmark':
            benchmark = GenealogyModelBenchmark()
            result = execute_with_progress("model benchmark", lambda: benchmark.run_full_benchmark())
        elif tool == 'extract':
            # For extraction, redirect to the extraction blueprint
            task_id = extraction_service.start_extraction()
            return jsonify({
                'success': True,
                'task_id': task_id,
                'message': 'Extraction started',
                'redirect': f'/api/extraction/status/{task_id}'
            })
        elif tool == 'gedcom':
            result = gedcom_service.generate_gedcom()
        elif tool == 'research':
            def generate_questions():
                generator = ResearchQuestionGenerator("web_app/pdf_processing/llm_genealogy_results.json")
                return generator.generate_questions()
            result = execute_with_progress("research question generation", generate_questions)

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

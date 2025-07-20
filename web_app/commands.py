"""
Flask CLI commands for Family Wiki tools
"""

import click

from web_app.pdf_processing.genealogy_model_benchmark import GenealogyModelBenchmark
from web_app.pdf_processing.ocr_processor import PDFOCRProcessor
from web_app.repositories.genealogy_repository import GenealogyDataRepository
from web_app.research_question_generator import ResearchQuestionGenerator
from web_app.services.gedcom_service import gedcom_service
from web_app.shared.service_utils import execute_with_progress
from web_app.tasks.extraction_tasks import extract_genealogy_data


def register_commands(app):
    """Register all CLI commands with the Flask app"""

    @app.cli.command()
    @click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
    def ocr(verbose):
        """Extract text from PDF files using OCR with rotation detection."""
        click.echo("🔍 Starting OCR processing...")

        def progress_callback(data):
            if verbose:
                click.echo(f"Status: {data.get('status')} - {data.get('message', '')}")

        processor = PDFOCRProcessor()
        result = execute_with_progress(
            "OCR processing",
            processor.process_all_pdfs,
            progress_callback if verbose else None
        )

        if result['success']:
            click.echo("✅ OCR processing completed successfully!")
            if verbose and 'results' in result:
                click.echo(f"Results: {result['results']}")
        else:
            click.echo(f"❌ OCR processing failed: {result['error']}")
            exit(1)

    @app.cli.command('extract')
    @click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
    @click.option('--text-file', help='Path to text file to process')
    def extract_genealogy(verbose, text_file):
        """Extract genealogical data using AI language models with family-focused approach."""
        click.echo("🤖 Starting LLM extraction...")

        # Start Celery task
        task = extract_genealogy_data.delay(text_file)
        task_id = task.id

        # For CLI, we wait for completion
        click.echo(f"Task ID: {task_id}")
        click.echo("Waiting for extraction to complete...")

        # Poll for completion
        import time
        while True:
            task_result = extract_genealogy_data.AsyncResult(task_id)

            if task_result.state == 'PENDING':
                click.echo("❌ Task not found")
                exit(1)
            elif task_result.state == 'RUNNING':
                if verbose and task_result.info:
                    meta = task_result.info
                    status = meta.get('status', 'unknown')
                    if status == 'processing':
                        current = meta.get('current_chunk', 0)
                        total = meta.get('total_chunks', 0)
                        progress = meta.get('progress', 0)
                        if total > 0:
                            click.echo(f"Processing chunk {current}/{total} ({progress}%)")
                    else:
                        click.echo(f"Status: {status}")
            elif task_result.state == 'SUCCESS':
                result = task_result.result
                click.echo("✅ Extraction completed successfully!")
                if result.get('summary'):
                    summary = result['summary']
                    click.echo("📊 Summary:")
                    click.echo(f"  - Families: {summary.get('total_families', 0)}")
                    click.echo(f"  - People: {summary.get('total_people', 0)}")
                    click.echo(f"  - Isolated individuals: {summary.get('total_isolated_individuals', 0)}")

                # Show database statistics
                repository = GenealogyDataRepository()
                db_stats = repository.get_database_stats()
                if db_stats:
                    click.echo("🗄️ Database Statistics:")
                    click.echo(f"  - Persons: {db_stats.get('total_people', 0)}")
                    click.echo(f"  - Families: {db_stats.get('total_families', 0)}")
                    click.echo(f"  - Places: {db_stats.get('total_places', 0)}")
                    click.echo(f"  - Events: {db_stats.get('total_events', 0)}")
                    click.echo(f"  - Marriages: {db_stats.get('total_marriages', 0)}")
                break
            elif task_result.state == 'FAILURE':
                error = str(task_result.info) if task_result.info else 'Unknown error'
                click.echo(f"❌ Extraction failed: {error}")
                exit(1)
            else:
                click.echo(f"Task state: {task_result.state}")

            time.sleep(2)

    @app.cli.command()
    @click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
    @click.option('--input-file', help='Input JSON file from extraction')
    @click.option('--output-file', help='Output GEDCOM file name')
    def gedcom(verbose, input_file, output_file):
        """Generate standard GEDCOM files from extracted genealogy data."""
        click.echo("📜 Starting GEDCOM generation...")

        def progress_callback(data):
            if verbose:
                click.echo(f"Status: {data.get('status')} - {data.get('message', '')}")

        result = gedcom_service.generate_gedcom(
            input_file=input_file,
            output_file=output_file,
            progress_callback=progress_callback if verbose else None
        )

        if result['success']:
            click.echo("✅ GEDCOM generation completed successfully!")
            click.echo(f"📁 Output file: {result.get('output_file', 'family_genealogy.ged')}")
            if verbose and 'results' in result:
                click.echo(f"Results: {result['results']}")
        else:
            click.echo(f"❌ GEDCOM generation failed: {result['error']}")
            exit(1)

    @app.cli.command()
    @click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
    @click.option('--input-file', help='Input JSON file from extraction')
    def research(verbose, input_file):
        """Generate intelligent research questions from family data."""
        click.echo("🔬 Starting research question generation...")

        def progress_callback(data):
            if verbose:
                click.echo(f"Status: {data.get('status')} - {data.get('message', '')}")

        # Use default file if not specified
        input_file = input_file or "web_app/pdf_processing/llm_genealogy_results.json"

        def generate_questions():
            generator = ResearchQuestionGenerator(input_file)
            return generator.generate_questions()

        result = execute_with_progress(
            "research question generation",
            generate_questions,
            progress_callback if verbose else None
        )

        if result['success']:
            questions = result['results']
            click.echo("✅ Research questions generated successfully!")
            click.echo(f"📝 Total questions: {len(questions)}")
            if verbose and questions:
                for i, question in enumerate(questions[:5], 1):
                    click.echo(f"  {i}. {question}")
                if len(questions) > 5:
                    click.echo(f"  ... and {len(questions) - 5} more")
        else:
            click.echo(f"❌ Research question generation failed: {result['error']}")
            exit(1)

    @app.cli.command()
    @click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
    def benchmark(verbose):
        """Test multiple LLM models for genealogy extraction performance."""
        click.echo("⚡ Starting model benchmark...")

        def progress_callback(data):
            if verbose:
                click.echo(f"Status: {data.get('status')} - {data.get('message', '')}")

        benchmark = GenealogyModelBenchmark()
        result = execute_with_progress(
            "model benchmark",
            benchmark.run_all_benchmarks,
            progress_callback if verbose else None
        )

        if result['success']:
            click.echo("✅ Model benchmark completed successfully!")
            if verbose and 'results' in result:
                click.echo(f"Results: {result['results']}")
        else:
            click.echo(f"❌ Model benchmark failed: {result['error']}")
            exit(1)

    @app.cli.command()
    @click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
    def pipeline(verbose):
        """Run the complete processing pipeline from OCR to research questions."""
        click.echo("🔄 Starting complete pipeline...")

        # Step 1: OCR
        click.echo("\n📍 Step 1: OCR Processing")
        processor = PDFOCRProcessor()
        ocr_result = execute_with_progress("OCR processing", processor.process_all_pdfs)
        if not ocr_result['success']:
            click.echo(f"❌ Pipeline failed at OCR: {ocr_result['error']}")
            exit(1)
        click.echo("✅ OCR completed")

        # Step 2: Extraction
        click.echo("\n📍 Step 2: LLM Extraction")
        task_id = extraction_service.start_extraction()

        # Wait for extraction
        import time
        while True:
            status = extraction_service.get_task_status(task_id)
            if status['status'] == 'completed':
                break
            elif status['status'] == 'failed':
                click.echo(f"❌ Pipeline failed at extraction: {status.get('error')}")
                exit(1)
            time.sleep(2)
        click.echo("✅ Extraction completed")

        # Step 3: GEDCOM
        click.echo("\n📍 Step 3: GEDCOM Generation")
        gedcom_result = gedcom_service.generate_gedcom()
        if not gedcom_result['success']:
            click.echo(f"❌ Pipeline failed at GEDCOM: {gedcom_result['error']}")
            exit(1)
        click.echo("✅ GEDCOM completed")

        # Step 4: Research
        click.echo("\n📍 Step 4: Research Questions")
        def generate_questions():
            generator = ResearchQuestionGenerator("web_app/pdf_processing/llm_genealogy_results.json")
            return generator.generate_questions()
        research_result = execute_with_progress("research question generation", generate_questions)
        if not research_result['success']:
            click.echo(f"❌ Pipeline failed at research: {research_result['error']}")
            exit(1)
        click.echo("✅ Research completed")

        click.echo("\n🎉 Complete pipeline finished successfully!")

        # Summary
        if 'summary' in status:
            summary = status['summary']
            click.echo("\n📊 Final Summary:")
            click.echo(f"  - Families extracted: {summary.get('total_families', 0)}")
            click.echo(f"  - People found: {summary.get('total_people', 0)}")
            click.echo(f"  - GEDCOM file: {gedcom_result.get('output_file', 'family_genealogy.ged')}")
            click.echo(f"  - Research questions: {len(research_result.get('results', []))}")

    @app.cli.command()
    def status():
        """Check system status and available tools."""
        click.echo("🔍 Family Wiki Tools Status")
        click.echo("=" * 40)

        # Check if required directories exist
        from pathlib import Path
        project_root = Path.cwd()

        checks = {
            "PDF directory": (project_root / "web_app" / "pdf_processing" / "pdfs").exists(),
            "Extracted text": (project_root / "web_app" / "pdf_processing" / "extracted_text").exists(),
            "Logs directory": (project_root / "logs").exists(),
            "Templates": (project_root / "templates").exists(),
        }

        for check, status in checks.items():
            icon = "✅" if status else "❌"
            click.echo(f"{icon} {check}")

        click.echo("\n🛠️  Available Commands:")
        click.echo("  flask ocr         - Extract text from PDFs")
        click.echo("  flask extract     - AI-powered genealogy extraction")
        click.echo("  flask gedcom      - Generate GEDCOM files")
        click.echo("  flask research    - Generate research questions")
        click.echo("  flask benchmark   - Test LLM models")
        click.echo("  flask pipeline    - Run complete workflow")
        click.echo("  flask run         - Start web interface")

        click.echo("\n🌐 Web Interface: http://localhost:5000")

        # Show database statistics if available
        db_stats = extraction_service.get_database_stats()
        if db_stats:
            click.echo("\n🗄️ Database Statistics:")
            click.echo(f"  - Persons: {db_stats.get('persons', 0)}")
            click.echo(f"  - Families: {db_stats.get('families', 0)}")
            click.echo(f"  - Places: {db_stats.get('places', 0)}")
            click.echo(f"  - Events: {db_stats.get('events', 0)}")
            click.echo(f"  - Marriages: {db_stats.get('marriages', 0)}")
            click.echo(f"  - Total entities: {db_stats.get('total_entities', 0)}")

    @app.cli.command('db-clear')
    @click.confirmation_option(prompt='Are you sure you want to clear all extraction data?')
    def clear_database():
        """Clear all extraction data from the database (for testing/development)."""
        click.echo("🗑️ Clearing database...")
        try:
            from web_app.database import db
            from web_app.database.models import Event, Family, Marriage, Person

            # Delete in order to respect foreign key constraints
            Family.query.delete()
            Marriage.query.delete()
            Event.query.delete()
            Person.query.delete()
            db.session.commit()

            click.echo("✅ Database cleared successfully!")

            # Show updated stats
            db_stats = extraction_service.get_database_stats()
            if db_stats:
                click.echo(f"🗄️ Remaining entities: {db_stats.get('total_entities', 0)}")

        except Exception as e:
            click.echo(f"❌ Failed to clear database: {e}")
            exit(1)

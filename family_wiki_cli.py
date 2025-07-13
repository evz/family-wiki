#!/usr/bin/env python3
"""
Family Wiki CLI - Common entrypoint for all genealogy tools

This script provides a unified command-line interface for the entire
family wiki genealogy processing pipeline.
"""

import sys
import os
from pathlib import Path
import click

# Add project root to path to import modules
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from shared_genealogy.logging_config import get_project_logger

@click.group()
@click.option('-v', '--verbose', is_flag=True, help='Enable verbose logging')
@click.pass_context
def cli(ctx, verbose):
    """Family Wiki - Genealogy Processing Tools"""
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose

@cli.command()
@click.pass_context
def ocr(ctx):
    """Run OCR processing on PDF files"""
    logger = get_project_logger(__name__, ctx.obj['verbose'])
    logger.info("Starting OCR processing...")
    
    # Import and run OCR processor
    sys.path.append(str(PROJECT_ROOT / "pdf_processing"))
    from pdf_processing.ocr_processor import main as ocr_main
    
    # Change to pdf_processing directory for relative paths
    original_cwd = os.getcwd()
    os.chdir(PROJECT_ROOT / "pdf_processing")
    try:
        ocr_main()
        logger.info("OCR processing completed successfully")
    finally:
        os.chdir(original_cwd)

@cli.command()
@click.pass_context
def benchmark(ctx):
    """Run LLM model benchmarking"""
    logger = get_project_logger(__name__, ctx.obj['verbose'])
    logger.info("Starting model benchmarking...")
    
    sys.path.append(str(PROJECT_ROOT / "pdf_processing"))
    from pdf_processing.genealogy_model_benchmark import main as benchmark_main
    
    original_cwd = os.getcwd()
    os.chdir(PROJECT_ROOT / "pdf_processing")
    try:
        benchmark_main()
        logger.info("Model benchmarking completed successfully")
    finally:
        os.chdir(original_cwd)

@cli.command()
@click.pass_context
def extract(ctx):
    """Run LLM genealogy extraction"""
    logger = get_project_logger(__name__, ctx.obj['verbose'])
    logger.info("Starting LLM genealogy extraction...")
    
    sys.path.append(str(PROJECT_ROOT / "pdf_processing"))
    from pdf_processing.llm_genealogy_extractor import main as extraction_main
    
    original_cwd = os.getcwd()
    os.chdir(PROJECT_ROOT / "pdf_processing")
    try:
        extraction_main()
        logger.info("LLM extraction completed successfully")
    finally:
        os.chdir(original_cwd)

@cli.command()
@click.pass_context
def gedcom(ctx):
    """Generate GEDCOM files from extracted data"""
    logger = get_project_logger(__name__, ctx.obj['verbose'])
    logger.info("Starting GEDCOM generation...")
    
    from gedcom_generator import main as gedcom_main
    
    try:
        gedcom_main()
        logger.info("GEDCOM generation completed successfully")
    except Exception as e:
        logger.error(f"GEDCOM generation failed: {e}")
        raise click.ClickException(str(e))

@cli.command()
@click.pass_context
def research(ctx):
    """Generate research questions from data"""
    logger = get_project_logger(__name__, ctx.obj['verbose'])
    logger.info("Starting research question generation...")
    
    from research_question_generator import main as research_main
    
    try:
        research_main()
        logger.info("Research question generation completed successfully")
    except Exception as e:
        logger.error(f"Research question generation failed: {e}")
        raise click.ClickException(str(e))

@cli.command()
@click.pass_context
def pipeline(ctx):
    """Run the complete processing pipeline"""
    logger = get_project_logger(__name__, ctx.obj['verbose'])
    logger.info("Starting full processing pipeline...")
    
    steps = [
        ("OCR Processing", lambda: ctx.invoke(ocr)),
        ("Model Benchmarking", lambda: ctx.invoke(benchmark)),
        ("LLM Extraction", lambda: ctx.invoke(extract)), 
        ("GEDCOM Generation", lambda: ctx.invoke(gedcom)),
        ("Research Questions", lambda: ctx.invoke(research))
    ]
    
    for step_name, step_func in steps:
        logger.info(f"Running: {step_name}")
        try:
            step_func()
        except Exception as e:
            logger.error(f"Pipeline failed at step {step_name}: {e}")
            raise click.ClickException(f"Pipeline failed at step: {step_name}")
    
    logger.info("Full pipeline completed successfully!")

if __name__ == '__main__':
    cli()
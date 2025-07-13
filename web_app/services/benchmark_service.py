"""
Benchmark service for both CLI and web interface
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Callable

# Add project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "pdf_processing"))

from genealogy_model_benchmark import GenealogyModelBenchmark
from shared_genealogy.logging_config import get_project_logger

logger = get_project_logger(__name__)

class BenchmarkService:
    """Service for managing model benchmarking"""
    
    def __init__(self):
        self.logger = get_project_logger(__name__)
    
    def run_benchmark(self, progress_callback: Callable = None) -> Dict:
        """Run model benchmark tests"""
        try:
            self.logger.info("Starting model benchmark")
            
            if progress_callback:
                progress_callback({"status": "starting", "message": "Initializing benchmark"})
            
            benchmark = GenealogyModelBenchmark()
            
            if progress_callback:
                progress_callback({"status": "running", "message": "Testing models"})
            
            # Run benchmark
            results = benchmark.run_all_benchmarks()
            
            if progress_callback:
                progress_callback({"status": "completed", "results": results})
            
            self.logger.info("Model benchmark completed successfully")
            
            return {
                "success": True,
                "message": "Model benchmark completed",
                "results": results
            }
            
        except Exception as e:
            error_msg = f"Model benchmark failed: {str(e)}"
            self.logger.error(error_msg)
            
            if progress_callback:
                progress_callback({"status": "failed", "error": error_msg})
            
            return {
                "success": False,
                "error": error_msg
            }

# Global service instance
benchmark_service = BenchmarkService()
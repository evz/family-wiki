"""
Model benchmarking service for genealogy extraction
"""

import json
import re
import subprocess
import time

import requests
from flask import current_app

from web_app.shared.logging_config import get_project_logger


logger = get_project_logger(__name__)

class GenealogyModelBenchmark:
    def __init__(self):
        self.test_cases = [
            {
                "name": "Dutch names with dates",
                "text": """TWEEDE GENERATIE
1.1. Kinderen van Gerrit van Santen en Lijsbet:
a. Arieken Gerritsen, ~ Haaften 20.1.1709
b. Arien Gerritse van Santen, † 1746, x Gorinchem 26.3.1724 Hermina Noorthoorn, ~ 9.5.1704""",
                "expected_people": 2
            },
            {
                "name": "Complex family entry",
                "text": """c. Leendert van Zanten, ~ Culemborg 30.8.1778, + Culemborg 3.1.1860, arbeider (1830) x 1. Culemborg 6.9.1808 Maria Catharina Charmel, * Maastricht + 1781, + Culemborg 12.1823""",
                "expected_people": 2
            },
            {
                "name": "Multiple siblings",
                "text": """IV.3. Kinderen van Aart van Santen en Willemijntje Zuidam:
a. Seelke, ~ Gameren 16.8.1767
b. Ariën van Zanten, * 8.9.1768, ~ Gameren 9.9.1768, + Huizen 17.3.1847
c. Jan van Zanten, * 1770, + jong""",
                "expected_people": 3
            }
        ]

        # Default models - can be overridden via Flask config
        config = current_app.config
        self.models_to_test = config.get('BENCHMARK_MODELS', [
            "qwen2.5:7b",      # Best bet for structured extraction
            "qwen2.5:3b",      # Smaller but efficient
            "llama3.2:3b",     # Good small model
            "llama3.1:8b",     # General purpose
            "mistral:7b",      # Good at following instructions
        ])

        self.ollama_base_url = config.get('ollama_base_url', 'http://localhost:11434')

        self.results = {}

    def check_ollama_running(self) -> bool:
        """Check if Ollama is running"""
        try:
            response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def install_model(self, model_name: str) -> bool:
        """Install a model using ollama CLI"""
        logger.info(f"Installing {model_name}...")
        try:
            result = subprocess.run(
                ['ollama', 'pull', model_name],
                capture_output=True,
                text=True,
                timeout=600,
                check=False
            )
            success = result.returncode == 0
            if success:
                logger.info(f"Model {model_name} installed successfully")
            else:
                logger.error(f"Failed to install {model_name}: {result.stderr}")
            return success
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout installing {model_name}")
            return False
        except subprocess.SubprocessError as e:
            logger.error(f"Error installing {model_name}: {e}")
            return False

    def create_genealogy_prompt(self, text: str) -> str:
        """Create standardized prompt for testing"""
        return f"""You are a Dutch genealogy expert. Extract information about people from this text.

Text: {text}

Return ONLY valid JSON in this format:
{{
  "people": [
    {{
      "given_names": "first and middle names",
      "surname": "family name",
      "birth_date": "if mentioned with *",
      "baptism_date": "if mentioned with ~",
      "death_date": "if mentioned with †",
      "marriage_date": "if mentioned with x",
      "spouse_name": "if mentioned",
      "confidence": 0.9
    }}
  ]
}}

JSON:"""

    def test_model_on_case(self, model_name: str, test_case: dict) -> dict:
        """Test a model on one test case"""
        prompt = self.create_genealogy_prompt(test_case["text"])
        start_time = time.time()

        try:
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "top_p": 0.9
                    }
                },
                timeout=120
            )

            response_time = time.time() - start_time

            if response.status_code != 200:
                return {
                    "error": f"HTTP {response.status_code}",
                    "response_time": response_time
                }

            response_text = response.json().get('response', '')

            # Extract and parse JSON
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)

            if not json_match:
                return {
                    "error": "No JSON found in response",
                    "response_time": response_time,
                    "response": response_text[:200]
                }

            try:
                parsed_json = json.loads(json_match.group(0))
                people_found = len(parsed_json.get('people', []))
                expected_people = test_case["expected_people"]

                # Score based on accuracy
                accuracy_score = (
                    min(people_found / expected_people, 1.0)
                    if expected_people > 0 else 0
                )

                return {
                    "success": True,
                    "response_time": response_time,
                    "people_found": people_found,
                    "expected_people": expected_people,
                    "accuracy_score": accuracy_score,
                    "json_valid": True,
                    "response": response_text
                }

            except json.JSONDecodeError as e:
                return {
                    "error": f"Invalid JSON: {e}",
                    "response_time": response_time,
                    "json_valid": False,
                    "response": response_text[:200]
                }

        except requests.RequestException as e:
            return {
                "error": str(e),
                "response_time": time.time() - start_time
            }

    def benchmark_model(self, model_name: str) -> dict:
        """Run full benchmark on a model"""
        logger.info(f"Benchmarking {model_name}...")

        model_results = {
            "model": model_name,
            "test_cases": [],
            "overall_score": 0.0,
            "avg_response_time": 0.0,
            "success_rate": 0.0
        }

        successful_tests = 0
        total_response_time = 0
        total_accuracy = 0

        for i, test_case in enumerate(self.test_cases):
            logger.info(f"  Running test case {i+1}/{len(self.test_cases)}: {test_case['name']}")

            result = self.test_model_on_case(model_name, test_case)
            result["test_case"] = test_case["name"]
            model_results["test_cases"].append(result)

            if result.get("success"):
                successful_tests += 1
                total_accuracy += result.get("accuracy_score", 0)

            total_response_time += result.get("response_time", 0)

            # Small delay between tests
            time.sleep(2)

        # Calculate overall metrics
        model_results["success_rate"] = successful_tests / len(self.test_cases)
        model_results["avg_response_time"] = total_response_time / len(self.test_cases)
        model_results["avg_accuracy"] = total_accuracy / len(self.test_cases) if len(self.test_cases) > 0 else 0

        # Overall score combines success rate and accuracy
        model_results["overall_score"] = (model_results["success_rate"] * 0.6 +
                                        model_results["avg_accuracy"] * 0.4)

        return model_results

    def run_full_benchmark(self, install_models: bool = True) -> dict:
        """Run comprehensive benchmark

        Args:
            install_models: Whether to auto-install missing models

        Returns:
            Dict with benchmark results
        """
        if not self.check_ollama_running():
            raise RuntimeError("Ollama is not running. Please start it with: ollama serve")

        logger.info("Starting comprehensive genealogy model benchmark...")
        logger.info(f"Will test {len(self.models_to_test)} models on {len(self.test_cases)} test cases")

        for model_name in self.models_to_test:
            logger.info(f"Testing model: {model_name}")

            if install_models:
                if not self.install_model(model_name):
                    logger.error(f"Skipping {model_name} due to installation failure")
                    continue

            self.results[model_name] = self.benchmark_model(model_name)

        logger.info("Benchmark complete!")
        return self.results

    def get_results_summary(self) -> dict:
        """Get structured summary of benchmark results

        Returns:
            Dict with results summary and recommendations
        """
        if not self.results:
            return {"error": "No results available"}

        # Sort by overall score
        sorted_results = sorted(
            self.results.items(),
            key=lambda x: x[1]["overall_score"],
            reverse=True
        )

        summary = {
            "total_models_tested": len(self.results),
            "total_test_cases": len(self.test_cases),
            "rankings": []
        }

        for i, (model, results) in enumerate(sorted_results):
            summary["rankings"].append({
                "rank": i + 1,
                "model": model,
                "overall_score": results["overall_score"],
                "success_rate": results["success_rate"],
                "avg_accuracy": results["avg_accuracy"],
                "avg_response_time": results["avg_response_time"]
            })

        # Add recommendation
        if sorted_results:
            winner_name, _ = sorted_results[0]
            summary["recommended_model"] = winner_name
            summary["recommendation_reason"] = "Best overall performance for Dutch genealogy extraction"

        return summary

    def save_results(self, filename: str = "genealogy_benchmark_results.json") -> str:
        """Save detailed results to JSON

        Args:
            filename: Output filename

        Returns:
            Path to saved file
        """
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        logger.info(f"Detailed results saved to {filename}")
        return filename

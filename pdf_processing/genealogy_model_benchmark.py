#!/usr/bin/env python3
"""
Proper benchmarking script for genealogy extraction models
"""

import subprocess
import json
import time
import requests
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        
        # Models to test (ordered by likely performance for this task)
        self.models_to_test = [
            "qwen2.5:7b",      # Best bet for structured extraction
            "qwen2.5:3b",      # Smaller but efficient
            "llama3.2:3b",     # Good small model
            "llama3.1:8b",     # General purpose
            "mistral:7b",      # Good at following instructions
        ]
        
        self.results = {}
    
    def check_ollama_running(self) -> bool:
        """Check if Ollama is running"""
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def install_model(self, model_name: str) -> bool:
        """Install a model"""
        logger.info(f"Installing {model_name}...")
        try:
            result = subprocess.run(['ollama', 'pull', model_name], 
                                  capture_output=True, text=True, timeout=600)
            success = result.returncode == 0
            if success:
                logger.info(f"✅ {model_name} installed successfully")
            else:
                logger.error(f"❌ Failed to install {model_name}: {result.stderr}")
            return success
        except subprocess.TimeoutExpired:
            logger.error(f"❌ Timeout installing {model_name}")
            return False
        except Exception as e:
            logger.error(f"❌ Error installing {model_name}: {e}")
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
    
    def test_model_on_case(self, model_name: str, test_case: Dict) -> Dict:
        """Test a model on one test case"""
        prompt = self.create_genealogy_prompt(test_case["text"])
        
        start_time = time.time()
        
        try:
            response = requests.post("http://localhost:11434/api/generate", 
                                   json={
                                       "model": model_name,
                                       "prompt": prompt,
                                       "stream": False,
                                       "options": {
                                           "temperature": 0.1,
                                           "top_p": 0.9
                                       }
                                   }, 
                                   timeout=120)
            
            end_time = time.time()
            response_time = end_time - start_time
            
            if response.status_code != 200:
                return {
                    "error": f"HTTP {response.status_code}",
                    "response_time": response_time
                }
            
            response_text = response.json().get('response', '')
            
            # Try to extract and parse JSON
            import re
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
                accuracy_score = min(people_found / expected_people, 1.0) if expected_people > 0 else 0
                
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
                
        except Exception as e:
            return {
                "error": str(e),
                "response_time": time.time() - start_time
            }
    
    def benchmark_model(self, model_name: str) -> Dict:
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
    
    def run_full_benchmark(self, install_models: bool = True) -> None:
        """Run comprehensive benchmark"""
        if not self.check_ollama_running():
            logger.error("Ollama is not running. Please start it with: ollama serve")
            return
        
        logger.info("Starting comprehensive genealogy model benchmark...")
        logger.info(f"Will test {len(self.models_to_test)} models on {len(self.test_cases)} test cases")
        
        for model_name in self.models_to_test:
            logger.info(f"\n{'='*60}")
            logger.info(f"TESTING MODEL: {model_name}")
            logger.info(f"{'='*60}")
            
            if install_models:
                if not self.install_model(model_name):
                    logger.error(f"Skipping {model_name} due to installation failure")
                    continue
            
            self.results[model_name] = self.benchmark_model(model_name)
        
        logger.info("\n🏁 Benchmark complete!")
    
    def print_results(self) -> None:
        """Print comprehensive results"""
        if not self.results:
            print("No results to display")
            return
        
        print(f"\n{'='*80}")
        print(f"GENEALOGY MODEL BENCHMARK RESULTS")
        print(f"{'='*80}")
        
        # Sort by overall score
        sorted_results = sorted(self.results.items(), 
                              key=lambda x: x[1]["overall_score"], 
                              reverse=True)
        
        print(f"\n🏆 RANKING:")
        for i, (model, results) in enumerate(sorted_results):
            score = results["overall_score"]
            success_rate = results["success_rate"] * 100
            avg_time = results["avg_response_time"]
            accuracy = results["avg_accuracy"] * 100
            
            medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else f"{i+1}."
            
            print(f"{medal} {model}")
            print(f"   Overall Score: {score:.3f}")
            print(f"   Success Rate: {success_rate:.1f}%")
            print(f"   Avg Accuracy: {accuracy:.1f}%") 
            print(f"   Avg Time: {avg_time:.1f}s")
            print()
        
        # Detailed breakdown of winner
        if sorted_results:
            winner_name, winner_results = sorted_results[0]
            print(f"🎯 RECOMMENDED MODEL: {winner_name}")
            print(f"   Best overall performance for Dutch genealogy extraction")
            print(f"   To use: Update your scripts to use '{winner_name}'")
    
    def save_results(self, filename: str = "genealogy_benchmark_results.json") -> None:
        """Save detailed results to JSON"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"Detailed results saved to {filename}")

def main():
    print("🧬 Genealogy Model Benchmark")
    print("This will install and test multiple models for Dutch genealogy extraction")
    print("It may take 30-60 minutes depending on your internet speed")
    print()
    
    response = input("Proceed with benchmark? (y/n): ").lower().strip()
    if response != 'y':
        print("Benchmark cancelled")
        return
    
    benchmark = GenealogyModelBenchmark()
    benchmark.run_full_benchmark(install_models=True)
    benchmark.print_results()
    benchmark.save_results()

if __name__ == "__main__":
    main()
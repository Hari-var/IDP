import json
import logging
import time
import threading
from datetime import datetime
from app.helpers.llm import get_gemini_response_with_context
from sentence_transformers import SentenceTransformer
import numpy as np
import asyncio
from prometheus_client import Counter, Histogram, Gauge
from logging.handlers import RotatingFileHandler

# Benchmark metrics
try:
    BENCHMARK_RUNS_TOTAL = Counter('benchmark_runs_total', 'Total benchmark runs')
    BENCHMARK_ACCURACY = Gauge('benchmark_accuracy_percent', 'Current benchmark accuracy percentage')
    BENCHMARK_TEST_DURATION = Histogram('benchmark_test_duration_seconds', 'Time taken for benchmark tests')
    BENCHMARK_CLASSIFICATION_RESULTS = Counter('benchmark_classification_results_total', 'Benchmark classification results', ['result_type'])
except ValueError:
    # Metrics already registered
    from prometheus_client import REGISTRY
    BENCHMARK_RUNS_TOTAL = REGISTRY._names_to_collectors['benchmark_runs_total']
    BENCHMARK_ACCURACY = REGISTRY._names_to_collectors['benchmark_accuracy_percent']
    BENCHMARK_TEST_DURATION = REGISTRY._names_to_collectors['benchmark_test_duration_seconds']
    BENCHMARK_CLASSIFICATION_RESULTS = REGISTRY._names_to_collectors['benchmark_classification_results_total']

# Setup benchmark logger
benchmark_logger = logging.getLogger('benchmark')
benchmark_handler = RotatingFileHandler(
    "benchmark.log",
    maxBytes=10 * 1024 * 1024,  # 10 MB
    backupCount=5
)
benchmark_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
benchmark_logger.addHandler(benchmark_handler)
benchmark_logger.setLevel(logging.INFO)

class BenchmarkSystem:
    def __init__(self, test_interval_hours=5):
        self.test_interval = test_interval_hours * 3600  # Convert to seconds
        self.benchmark_file = 'benchmark_data.json'
        self.last_run_file = 'last_benchmark_run.txt'
        self.running = False
        self.similarity_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Document type mappings for semantic similarity
        self.doc_type_mappings = {
            "Policy Documents": ["policy documents", "insurance policy", "coverage documents", "policy terms", "policy declaration"],
            "Proof of Loss": ["proof of loss", "loss notice", "claim notice", "fnol", "first notice of loss", "notice of loss", "loss report"],
            "Police Reports": ["police reports", "incident report", "police incident", "law enforcement report", "police department report"],
            "Medical Records": ["medical records", "medical bills", "hospital records", "patient records", "medical report", "health records"],
            "Repair Estimates": ["repair estimates", "repair invoice", "service estimate", "maintenance invoice", "repair bill", "service bill"],
            "Investigation Reports": ["investigation reports", "investigation findings", "fraud investigation", "adjuster report", "assessment report"],
            "Legal Documents": ["legal documents", "court order", "subpoena", "legal proceeding", "settlement agreement", "legal papers"]
        }
        
    def get_last_run_time(self):
        """Get the last benchmark run time from file"""
        try:
            with open(self.last_run_file, 'r') as f:
                return float(f.read().strip())
        except (FileNotFoundError, ValueError):
            return None
    
    def save_last_run_time(self, timestamp):
        """Save the last benchmark run time to file"""
        with open(self.last_run_file, 'w') as f:
            f.write(str(timestamp))
        
    def load_benchmark_data(self):
        """Load benchmark test cases"""
        try:
            with open(self.benchmark_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            benchmark_logger.error("Benchmark data file not found")
            return []
    
    def is_semantically_equivalent(self, predicted_type, expected_type):
        """Check if two document types are semantically equivalent"""
        # Direct mapping check
        if expected_type in self.doc_type_mappings:
            predicted_lower = predicted_type.lower()
            expected_lower = expected_type.lower()
            
            # Check if predicted type contains any of the expected variations
            for variant in self.doc_type_mappings[expected_type]:
                if variant in predicted_lower or predicted_lower in variant:
                    return True
            
            # Special case handling for common equivalencies
            equivalencies = {
                "first notice of loss": "proof of loss",
                "fnol": "proof of loss",
                "incident report": "police reports",
                "medical bill": "medical records",
                "repair invoice": "repair estimates",
                "settlement agreement": "legal documents"
            }
            
            for key, value in equivalencies.items():
                if (key in predicted_lower and value in expected_lower) or \
                   (value in predicted_lower and key in expected_lower):
                    return True
        
    def calculate_semantic_similarity(self, predicted_type, expected_type):
        """Calculate semantic similarity between document types"""
        try:
            # Get embeddings for both document types
            pred_embedding = self.similarity_model.encode([predicted_type.lower()])
            exp_embedding = self.similarity_model.encode([expected_type.lower()])
            
            # Calculate cosine similarity
            similarity = np.dot(pred_embedding[0], exp_embedding[0]) / (
                np.linalg.norm(pred_embedding[0]) * np.linalg.norm(exp_embedding[0])
            )
            
            # Also check against known mappings for better accuracy
            if expected_type in self.doc_type_mappings:
                mapping_similarities = []
                for variant in self.doc_type_mappings[expected_type]:
                    variant_embedding = self.similarity_model.encode([variant])
                    pred_embedding = self.similarity_model.encode([predicted_type.lower()])
                    variant_sim = np.dot(pred_embedding[0], variant_embedding[0]) / (
                        np.linalg.norm(pred_embedding[0]) * np.linalg.norm(variant_embedding[0])
                    )
                    mapping_similarities.append(variant_sim)
                
                # Use the highest similarity from mappings
                max_mapping_sim = max(mapping_similarities) if mapping_similarities else 0
                similarity = max(similarity, max_mapping_sim)
            
            return float(similarity)
        except Exception as e:
            benchmark_logger.error(f"Error calculating semantic similarity: {str(e)}")
            return 
    
    async def run_benchmark_test(self):
        """Run benchmark test and calculate accuracy asynchronously"""
        benchmark_start_time = time.time()
        benchmark_logger.info("Starting benchmark test")
        BENCHMARK_RUNS_TOTAL.inc()
        
        test_data = self.load_benchmark_data()
        
        if not test_data:
            benchmark_logger.error("No benchmark data available")
            return
        
        total_tests = len(test_data)
        correct_classifications = 0
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": total_tests,
            "test_results": []
        }
        
        for i, test_case in enumerate(test_data):
            try:
                # Get LLM prediction with retry logic for errors
                predicted_doc_type = "Error"
                summary = "Error"
                
                # Retry up to 3 times if we get an error
                for retry_attempt in range(3):
                    predicted_doc_type, summary = get_gemini_response_with_context(test_case['text'])
                    
                    # If we got a valid response (not "Error"), break out of retry loop
                    if predicted_doc_type != "Error":
                        break
                    
                    if retry_attempt < 2:  # Don't log on the last attempt
                        benchmark_logger.warning(f"Test {test_case['id']} attempt {retry_attempt + 1} failed, retrying...")
                        await asyncio.sleep(5)  # Wait 5 seconds before retry
                
                # Check exact match, semantic equivalency, and similarity
                exact_match = predicted_doc_type.strip() == test_case['expected_doc_type']
                semantic_equivalent = self.is_semantically_equivalent(
                    predicted_doc_type.strip(), 
                    test_case['expected_doc_type']
                )
                semantic_similarity = self.calculate_semantic_similarity(
                    predicted_doc_type.strip(), 
                    test_case['expected_doc_type']
                )
                
                # Consider it correct if exact match OR semantic equivalent OR high similarity
                classification_correct = exact_match or semantic_equivalent or semantic_similarity > 0.7
                if classification_correct:
                    correct_classifications += 1
                    BENCHMARK_CLASSIFICATION_RESULTS.labels(result_type='correct').inc()
                else:
                    BENCHMARK_CLASSIFICATION_RESULTS.labels(result_type='incorrect').inc()
                
                # Log individual test result
                test_result = {
                    "test_id": test_case['id'],
                    "expected_doc_type": test_case['expected_doc_type'],
                    "predicted_doc_type": predicted_doc_type.strip(),
                    "exact_match": exact_match,
                    "semantic_similarity": semantic_similarity,
                    "classification_correct": classification_correct
                }
                results["test_results"].append(test_result)
                
                benchmark_logger.info(f"Test {test_case['id']}: Expected='{test_case['expected_doc_type']}', Predicted='{predicted_doc_type.strip()}', Exact={'PASS' if exact_match else 'FAIL'}, Semantic={semantic_similarity:.3f}, Result={'PASS' if classification_correct else 'FAIL'}")
                
                # Wait 30 seconds between test cases (except for the last one)
                if i < len(test_data) - 1:
                    benchmark_logger.info(f"Waiting 30 seconds before next test case...")
                    await asyncio.sleep(30)
                
            except Exception as e:
                benchmark_logger.error(f"Error testing case {test_case['id']}: {str(e)}")
        
        # Calculate overall metrics
        classification_accuracy = (correct_classifications / total_tests) * 100
        benchmark_duration = time.time() - benchmark_start_time
        
        # Update Prometheus metrics
        BENCHMARK_ACCURACY.set(classification_accuracy)
        BENCHMARK_TEST_DURATION.observe(benchmark_duration)
        
        results.update({
            "classification_accuracy": classification_accuracy,
            "correct_classifications": correct_classifications
        })
        
        # Log summary results
        benchmark_logger.info(f"BENCHMARK RESULTS - Classification Accuracy: {classification_accuracy:.1f}%")
        benchmark_logger.info(f"Tests Passed: {correct_classifications}/{total_tests}")
        
        # Save detailed results (append mode)
        try:
            # Load existing results
            with open('benchmark_results.json', 'r') as f:
                all_results = json.load(f)
            # Check if it's a list, if not convert to list
            if not isinstance(all_results, list):
                all_results = [all_results]
            # Append new results
            all_results.append(results)
        except FileNotFoundError:
            # First time, create new list
            all_results = [results]
        except json.JSONDecodeError:
            # Corrupted file, start fresh
            all_results = [results]
        
        # Save updated results
        with open('benchmark_results.json', 'w') as f:
            json.dump(all_results, f, indent=2)
    
    def start_scheduler(self):
        """Start the benchmark scheduler"""
        self.running = True
        benchmark_logger.info(f"Benchmark scheduler started - running every {self.test_interval/3600} hours")
        
        def scheduler():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            while self.running:
                current_time = time.time()
                last_run_time = self.get_last_run_time()
                if last_run_time is None or (current_time - last_run_time) >= self.test_interval:
                    self.save_last_run_time(current_time)
                    loop.run_until_complete(self.run_benchmark_test())
                time.sleep(60)  # Check every minute
            loop.close()
        
        thread = threading.Thread(target=scheduler, daemon=True)
        thread.start()
    
    def stop_scheduler(self):
        """Stop the benchmark scheduler"""
        self.running = False
        benchmark_logger.info("Benchmark scheduler stopped")

# Global benchmark instance
benchmark_system = BenchmarkSystem(test_interval_hours=5)

def start_benchmarking():
    """Start the benchmarking system"""
    benchmark_system.start_scheduler()

def stop_benchmarking():
    """Stop the benchmarking system"""
    benchmark_system.stop_scheduler()

def run_manual_benchmark():
    """Run benchmark test manually"""
    benchmark_system.run_benchmark_test()
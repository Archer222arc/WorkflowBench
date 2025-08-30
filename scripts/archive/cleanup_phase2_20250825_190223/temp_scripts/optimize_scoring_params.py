#!/usr/bin/env python3
"""
Fine-grained parameter optimization for workflow scoring
Focuses on the region around the current best parameters
"""

import subprocess
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
import time
import shutil
from datetime import datetime
from itertools import product
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import os
import random
import traceback

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more information
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fine_grid_optimization.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # But keep main logger at INFO to avoid too much output

class FineGridSearchOptimizer:
    """Fine-grained parameter optimizer focusing on best parameter regions"""
    
    def __init__(self):
        self.experiment_id = datetime.now().strftime("%Y%m%d_%H%M%S_fine")
        self.experiment_dir = Path(f"experiments/fine_exp_{self.experiment_id}")
        self.experiment_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a shared temp directory for this experiment
        self.temp_dir = self.experiment_dir / "temp_outputs"
        self.temp_dir.mkdir(exist_ok=True)
        
        # Pre-create all param directories to avoid race conditions
        self.param_dirs_created = False
        self.dir_creation_lock = Lock()
        
        self.current_param_idx = 0
        self.results_history = []
        self.best_score_tracker = -float('inf')
        
        # Base command for testing
        self.base_command = [
            "python", "workflow_quality_test_flawed.py",
            "--severity", "all",
            "--model", "gpt-4o-mini",
            "--num-tests", "5",  # Can be increased for more reliable results
            "--test-scenarios", "hard",
            "--skip-normal",
            "--quiet",
            "--task-types", "all",
            "--clean-output",
            "--auto-run"
        ]
        
        # Load previous best results if available
        self.previous_best = self._load_previous_best()
        
        logger.info(f"Created fine-grained experiment directory: {self.experiment_dir}")
        logger.info(f"Temp outputs will be in: {self.temp_dir}")
    
    def _ensure_param_directories(self, max_idx: int):
        """Pre-create all parameter directories to avoid race conditions"""
        with self.dir_creation_lock:
            if not self.param_dirs_created:
                logger.info(f"Pre-creating parameter directories up to index {max_idx}")
                for i in range(max_idx + 1):
                    param_dir = self.experiment_dir / f"param_set_{i:04d}"
                    param_dir.mkdir(exist_ok=True, parents=True)
                self.param_dirs_created = True
    
    def _load_previous_best(self) -> Optional[Dict]:
        """Load previous best results from latest_optimization_results.json"""
        try:
            with open("latest_optimization_results.json", 'r') as f:
                data = json.load(f)
                return data.get('best_result', {})
        except:
            return None
    
    def generate_fine_grid_parameters(self) -> List[Dict]:
        """Generate fine-grained parameter grid around best known values"""
        
        # Base from previous best or defaults
        if self.previous_best and 'params' in self.previous_best:
            center_base = self.previous_best['params']['base_score']
            center_threshold = self.previous_best['params']['success_threshold']
            center_weights = self.previous_best['params']['weights'].copy()
        else:
            # Default centers based on project summary
            center_base = 0.1
            center_threshold = 0.7
            center_weights = {
                'task_completion': 0.25,
                'dependency_satisfaction': 0.15,
                'execution_efficiency': 0.45,
                'execution_order': 0.15
            }
        
        logger.info(f"Using centers: base={center_base}, threshold={center_threshold}")
        
        # Fine-grained ranges
        base_scores = np.arange(
            max(0.05, center_base - 0.05),
            min(0.25, center_base + 0.05) + 0.01,
            0.01
        ).round(2).tolist()
        
        success_thresholds = np.arange(
            max(0.60, center_threshold - 0.05),
            min(0.80, center_threshold + 0.05) + 0.01,
            0.01
        ).round(2).tolist()
        
        # Weight variations (keeping sum = 1.0)
        weight_variations = []
        
        # Generate variations around center weights
        for tc_delta in [-0.10, -0.05, 0, 0.05, 0.10]:
            for ef_delta in [-0.10, -0.05, 0, 0.05, 0.10]:
                for ds_delta in [-0.05, 0, 0.05]:
                    # Calculate new weights
                    new_tc = max(0.1, min(0.5, center_weights['task_completion'] + tc_delta))
                    new_ef = max(0.1, min(0.6, center_weights['execution_efficiency'] + ef_delta))
                    new_ds = max(0.05, min(0.3, center_weights['dependency_satisfaction'] + ds_delta))
                    
                    # Calculate execution_order to maintain sum = 1.0
                    new_eo = 1.0 - new_tc - new_ef - new_ds
                    
                    # Only valid if execution_order is reasonable
                    if 0.05 <= new_eo <= 0.3:
                        weight_variations.append({
                            'task_completion': round(new_tc, 2),
                            'dependency_satisfaction': round(new_ds, 2),
                            'execution_efficiency': round(new_ef, 2),
                            'execution_order': round(new_eo, 2)
                        })
        
        # Remove duplicates
        unique_weights = []
        seen = set()
        for w in weight_variations:
            key = tuple(sorted(w.items()))
            if key not in seen:
                seen.add(key)
                unique_weights.append(w)
        
        # Penalty variations
        penalty_sets = [
            # Minimal penalties
            {
                'unnecessary_tool': 0.05,
                'duplicate_execution': 0.05,
                'missing_required': 0.10,
                'dependency_violation': 0.08
            },
            # Standard penalties
            {
                'unnecessary_tool': 0.10,
                'duplicate_execution': 0.10,
                'missing_required': 0.20,
                'dependency_violation': 0.15
            },
            # Higher penalties
            {
                'unnecessary_tool': 0.15,
                'duplicate_execution': 0.15,
                'missing_required': 0.25,
                'dependency_violation': 0.20
            }
        ]
        
        # Threshold variations
        threshold_sets = [
            {'min_completion_rate': 0.3, 'perfect_completion': 1.0, 'good_completion': 0.6},
            {'min_completion_rate': 0.4, 'perfect_completion': 1.0, 'good_completion': 0.7},
            {'min_completion_rate': 0.5, 'perfect_completion': 1.0, 'good_completion': 0.8}
        ]
        
        # Generate parameter combinations
        parameter_sets = []
        
        # Strategy 1: Full grid for core parameters (limited)
        grid_combinations = list(product(
            base_scores[::2],  # Every other value to limit size
            success_thresholds[::2],
            unique_weights[:10],  # Top weight variations
            penalty_sets,
            threshold_sets
        ))
        
        for base, threshold, weights, penalties, thresholds in grid_combinations[:100]:
            parameter_sets.append({
                'base_score': base,
                'success_threshold': threshold,
                'weights': weights.copy(),
                'penalties': penalties.copy(),
                'thresholds': thresholds.copy()
            })
        
        # Strategy 2: Focused search around best known
        if self.previous_best:
            best_base = self.previous_best['params']['base_score']
            best_threshold = self.previous_best['params']['success_threshold']
            
            # Very fine search around best
            for base_offset in [-0.02, -0.01, 0, 0.01, 0.02]:
                for threshold_offset in [-0.02, -0.01, 0, 0.01, 0.02]:
                    new_base = round(max(0.05, min(0.3, best_base + base_offset)), 2)
                    new_threshold = round(max(0.6, min(0.85, best_threshold + threshold_offset)), 2)
                    
                    # Use best weights with slight variations
                    for weight_var in unique_weights[:5]:
                        parameter_sets.append({
                            'base_score': new_base,
                            'success_threshold': new_threshold,
                            'weights': weight_var.copy(),
                            'penalties': penalty_sets[1].copy(),  # Standard penalties
                            'thresholds': threshold_sets[1].copy()  # Standard thresholds
                        })
        
        # Remove duplicates
        unique_params = []
        seen_params = set()
        for params in parameter_sets:
            # Create a hashable representation
            param_key = (
                params['base_score'],
                params['success_threshold'],
                tuple(sorted(params['weights'].items())),
                tuple(sorted(params['penalties'].items())),
                tuple(sorted(params['thresholds'].items()))
            )
            if param_key not in seen_params:
                seen_params.add(param_key)
                unique_params.append(params)
        
        logger.info(f"Generated {len(unique_params)} unique parameter combinations")
        
        # Shuffle to avoid systematic bias
        import random
        random.shuffle(unique_params)
        
        return unique_params
    
    def create_config_file(self, params: Dict) -> Path:
        """Create temporary config file for testing"""
        config = {
            "SCORING_CONFIG": {
                "base_score": params['base_score'],
                "weights": params['weights'],
                "penalties": params['penalties'],
                "thresholds": params['thresholds']
            },
            "SUCCESS_THRESHOLD": params['success_threshold']
        }
        
        config_path = Path("temp_scoring_config.json")
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        return config_path
    
    def calculate_ranking_score(self, results: Dict) -> Tuple[float, Dict]:
        """Calculate score based on ranking objectives"""
        if not results:
            return -float('inf'), {}
        
        # Get scores
        optimal = results.get('optimal', 0)
        flawed_light = results.get('flawed_light', 0)
        baseline = results.get('baseline', 0)
        flawed_medium = results.get('flawed_medium', 0)
        flawed_severe = results.get('flawed_severe', 0)
        
        # Target: optimal > flawed_light > baseline > flawed_medium > flawed_severe
        score = 0
        penalties = 0
        bonuses = 0
        correct_orders = 0
        
        # Check ordering
        orders = [
            (optimal, flawed_light, "optimal > flawed_light", 100),
            (flawed_light, baseline, "flawed_light > baseline", 80),
            (baseline, flawed_medium, "baseline > flawed_medium", 60),
            (baseline, flawed_severe, "baseline > flawed_severe", 40)
        ]
        
        for higher, lower, desc, penalty_weight in orders:
            if higher > lower:
                correct_orders += 1
                # Bonus for significant gap
                gap = higher - lower
                if gap > 0.1:
                    bonuses += 20
                elif gap > 0.05:
                    bonuses += 10
            else:
                penalties += (lower - higher) * penalty_weight
        
        # Base score from optimal performance
        score += optimal * 100
        
        # Perfect ordering bonus
        if correct_orders == 4:
            bonuses += 150
        elif correct_orders >= 3:
            bonuses += 50
        
        # Score distribution check
        all_scores = [optimal, flawed_light, baseline, flawed_medium, flawed_severe]
        score_range = max(all_scores) - min(all_scores)
        if score_range > 0.2:  # Good differentiation
            bonuses += 30
        
        # Calculate final score
        final_score = score + bonuses - penalties
        
        breakdown = {
            'base_score': optimal * 100,
            'order_penalties': -penalties,
            'order_bonuses': bonuses,
            'correct_orders': correct_orders,
            'final_score': final_score,
            'score_range': score_range
        }
        
        return final_score, breakdown
    
    def run_single_test(self, params: Dict, idx: int) -> Optional[Dict]:
        """Run a single test with given parameters"""
        param_dir = self.experiment_dir / f"param_set_{idx:04d}"
        
        # Directory should already exist from pre-creation
        if not param_dir.exists():
            logger.error(f"Parameter directory {param_dir} does not exist!")
            return None
        
        # Save parameters
        try:
            with open(param_dir / "parameters.json", 'w') as f:
                json.dump(params, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save parameters for test {idx}: {e}")
            return None
        
        # Create config with unique name
        config_path = self.create_config_file(params)
        
        try:
            # Build command - use default output directory
            cmd = self.base_command.copy()
            
            # Add environment variable to specify config file
            env = os.environ.copy()
            env['SCORING_CONFIG_PATH'] = str(config_path)
            
            # Run test
            logger.info(f"Test {idx}: base={params['base_score']:.2f}, "
                       f"threshold={params['success_threshold']:.2f}")
            
            start_time = time.time()
            
            # Run the command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120000,  # 20 minute timeout
                env=env  # Pass environment with config path
            )
            
            execution_time = time.time() - start_time
            
            # Save outputs regardless of exit code
            try:
                with open(param_dir / "stdout.txt", 'w') as f:
                    f.write(result.stdout)
                with open(param_dir / "stderr.txt", 'w') as f:
                    f.write(result.stderr)
            except Exception as e:
                logger.warning(f"Failed to save output logs for test {idx}: {e}")
            
            # Check exit code
            if result.returncode != 0:
                logger.error(f"Test {idx} failed with exit code {result.returncode}")
                # Save error details
                with open(param_dir / "error.txt", 'w') as f:
                    f.write(f"Command failed with exit code {result.returncode}\n")
                    f.write(f"Command: {' '.join(cmd)}\n\n")
                    f.write("=== STDOUT ===\n")
                    f.write(result.stdout)
                    f.write("\n\n=== STDERR ===\n")
                    f.write(result.stderr)
                
                # Try to diagnose common issues
                if "ModuleNotFoundError" in result.stderr:
                    logger.error("Module import error - check Python path")
                elif "OPENAI_API_KEY" in result.stderr:
                    logger.error("OpenAI API key not set")
                elif "No such file or directory" in result.stderr:
                    logger.error("File not found - check working directory")
                
                return None
            
            logger.info(f"Test {idx} completed successfully in {execution_time:.1f}s")
            
            # Wait for files to be written
            time.sleep(2)
            
            # Copy output files first before parsing
            output_dir = Path("output")
            if output_dir.exists():
                logger.debug(f"Copying output files from {output_dir}")
                copied_files = []
                for file in output_dir.glob("*.json"):
                    if file.is_file():
                        try:
                            shutil.copy2(file, param_dir / file.name)
                            copied_files.append(file.name)
                        except Exception as e:
                            logger.warning(f"Failed to copy {file.name}: {e}")
                
                logger.debug(f"Copied {len(copied_files)} files: {copied_files}")
                
                # Save list of output files
                with open(param_dir / "output_files.txt", 'w') as f:
                    f.write(f"Output directory: {output_dir}\n")
                    f.write(f"Files found:\n")
                    for file in output_dir.iterdir():
                        f.write(f"  - {file.name} ({file.stat().st_size} bytes)\n")
            else:
                logger.error(f"Output directory does not exist: {output_dir}")
                with open(param_dir / "no_output_dir.txt", 'w') as f:
                    f.write("Output directory not found after test execution\n")
            
            # Parse results from the output directory
            logger.debug(f"Attempting to parse results for test {idx}")
            results = self._parse_results()
            
            if results:
                logger.debug(f"Successfully parsed results: {results}")
                score, breakdown = self.calculate_ranking_score(results)
                
                # Prepare result data
                result_data = {
                    'idx': idx,
                    'params': params,
                    'results': results,
                    'score': score,
                    'breakdown': breakdown,
                    'execution_time': execution_time,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Save detailed results
                try:
                    with open(param_dir / "detailed_results.json", 'w') as f:
                        json.dump(result_data, f, indent=2)
                except Exception as e:
                    logger.error(f"Failed to save detailed results for test {idx}: {e}")
                
                # Log summary
                logger.info(f"  Results: O={results.get('optimal', 0):.1%}, "
                           f"FL={results.get('flawed_light', 0):.1%}, "
                           f"B={results.get('baseline', 0):.1%}")
                logger.info(f"  Score: {score:.1f} (Correct orders: {breakdown['correct_orders']}/4)")
                
                return result_data
            else:
                logger.error(f"Test {idx}: Failed to parse results")
                # Save diagnostic information
                with open(param_dir / "parse_error.txt", 'w') as f:
                    f.write("Failed to parse results\n\n")
                    f.write("=== Parsing attempts ===\n")
                    f.write("Tried parsing from:\n")
                    f.write("1. output/flawed_test_combined_results.json\n")
                    f.write("2. output/summary.json\n")
                    f.write("3. output/flawed_results_*.json\n")
                    f.write("4. Individual result files\n\n")
                    
                    f.write("=== Available output files ===\n")
                    output_dir = Path("output")
                    if output_dir.exists():
                        for file in output_dir.iterdir():
                            f.write(f"  - {file.name} ({file.stat().st_size} bytes)\n")
                    else:
                        f.write("Output directory does not exist!\n")
                    
                    f.write(f"\n=== Command output ===\n")
                    f.write(f"Exit code: {result.returncode}\n")
                    f.write(f"Stdout length: {len(result.stdout)} chars\n")
                    f.write(f"Stderr length: {len(result.stderr)} chars\n")
                    
                    # Include last 500 chars of stdout
                    f.write(f"\n=== Last 500 chars of stdout ===\n")
                    f.write(result.stdout[-500:] if result.stdout else "(empty)")
                    
                    f.write(f"\n=== Stderr ===\n")
                    f.write(result.stderr if result.stderr else "(empty)")
                
                return None
                
        except subprocess.TimeoutExpired:
            logger.error(f"Test {idx} timed out after 1200 seconds")
            with open(param_dir / "error.txt", 'w') as f:
                f.write("Test timed out\n")
            return None
            
        except Exception as e:
            logger.error(f"Test {idx} failed: {e}")
            with open(param_dir / "error.txt", 'w') as f:
                f.write(f"Exception: {str(e)}\n")
                f.write(f"Traceback:\n{traceback.format_exc()}")
            return None
            
        finally:
            # Cleanup
            if config_path.exists():
                try:
                    shutil.copy2(config_path, param_dir / "used_config.json")
                    config_path.unlink()
                except Exception as e:
                    logger.warning(f"Failed to cleanup config file: {e}")
    
    def _parse_results(self) -> Optional[Dict]:
        """Parse test results from output files with detailed logging"""
        output_dir = Path("output")
        
        # Check if output directory exists
        if not output_dir.exists():
            logger.error("Output directory does not exist")
            return None
        
        # Look for the most recent flawed_results file
        flawed_results_files = list(output_dir.glob("flawed_results_*.json"))
        if flawed_results_files:
            # Sort by modification time and get the most recent
            most_recent = max(flawed_results_files, key=lambda f: f.stat().st_mtime)
            logger.info(f"Found flawed results file: {most_recent.name}")
            
            try:
                with open(most_recent, 'r') as f:
                    data = json.load(f)
                
                # Check if it has the expected structure
                if 'results' in data:
                    results = self._parse_flawed_results_format(data['results'])
                    if results:
                        logger.info(f"Successfully parsed results from {most_recent.name}")
                        return results
            except Exception as e:
                logger.error(f"Failed to parse {most_recent.name}: {e}")
        
        # If that didn't work, try other parsing strategies
        logger.debug("Trying alternative parsing strategies...")
        
        strategies = [
            (self._parse_from_summary_json, "summary/combined JSON"),
            (self._parse_from_individual_files, "individual files"),
            (self._parse_from_markdown_report, "markdown report")
        ]
        
        for strategy_func, strategy_name in strategies:
            try:
                logger.debug(f"Trying to parse from {strategy_name}")
                results = strategy_func()
                if results:
                    logger.info(f"Successfully parsed results using {strategy_name}")
                    logger.debug(f"Parsed results: {results}")
                    return results
            except Exception as e:
                logger.debug(f"Failed to parse using {strategy_name}: {e}")
                continue
        
        logger.error("Failed to parse results using any strategy")
        logger.error("Please check that workflow_quality_test_flawed.py completed successfully")
        return None
    
    def _parse_from_summary_json(self) -> Optional[Dict]:
        """Parse from combined results JSON"""
        # Try multiple possible file names
        possible_files = [
            Path("output/flawed_test_combined_results.json"),
            Path("output/summary.json"),
            Path("output/flawed_results_gpt-4o-mini_*.json"),
            Path("output/flawed_results_*.json")
        ]
        
        combined_file = None
        for file_pattern in possible_files:
            if '*' in str(file_pattern):
                # Handle glob pattern - get the most recent file
                files = list(Path("output").glob(file_pattern.name))
                if files:
                    # Get the most recent file
                    combined_file = max(files, key=lambda f: f.stat().st_mtime)
                    break
            elif file_pattern.exists():
                combined_file = file_pattern
                break
        
        if not combined_file or not combined_file.exists():
            logger.debug("No combined results file found")
            return None
        
        logger.info(f"Parsing results from: {combined_file}")
        
        try:
            with open(combined_file, 'r') as f:
                data = json.load(f)
            
            results = {
                'baseline': [],
                'optimal': [],
                'flawed_light': [],
                'flawed_medium': [],
                'flawed_severe': []
            }
            
            # Handle different file formats based on content
            
            # Format 1: flawed_results_*.json with 'results' key
            if 'results' in data:
                logger.debug("Parsing flawed_results format")
                # This is the format from the main test output
                for task_type, severities in data['results'].items():
                    for severity, flaw_results in severities.items():
                        for flaw_name, flaw_data in flaw_results.items():
                            if 'performance_comparison' in flaw_data:
                                perf = flaw_data['performance_comparison']
                                
                                if 'baseline_prompt' in perf:
                                    results['baseline'].append(perf['baseline_prompt']['success_rate'])
                                if 'optimal_prompt' in perf:
                                    results['optimal'].append(perf['optimal_prompt']['success_rate'])
                                if 'flawed_optimal_prompt' in perf:
                                    key = f'flawed_{severity}'
                                    if key in results:
                                        results[key].append(perf['flawed_optimal_prompt']['success_rate'])
            
            # Format 2: flawed_test_combined_results.json
            elif any(key in ['simple_task', 'basic_task', 'pipeline_task', 'data_pipeline', 
                            'api_integration', 'multi_stage_pipeline'] for key in data.keys()):
                logger.debug("Parsing combined_results format")
                return self._parse_combined_format(data)
            
            # Format 3: Individual test file with 'flaw_test_results'
            elif 'flaw_test_results' in data:
                logger.debug("Parsing individual test format")
                severity = data.get('severity', 'medium')
                task_type = data.get('task_type', 'unknown')
                return self._parse_single_test_format(data, severity, task_type)
            
            # Format 4: Old summary.json format
            elif 'baseline_performance' in data:
                logger.debug("Parsing old summary format")
                return self._parse_summary_format(data)
            
            else:
                logger.warning(f"Unknown format in {combined_file}")
                logger.debug(f"Top-level keys: {list(data.keys())[:10]}")
                return None
            
            # Calculate averages for Format 1
            final_results = {}
            for key, values in results.items():
                if values:
                    final_results[key] = np.mean(values)
                    logger.debug(f"{key}: {len(values)} samples, avg={final_results[key]:.3f}")
            
            return final_results if final_results else None
                
        except Exception as e:
            logger.error(f"Error parsing {combined_file}: {e}")
            return None
    
    def _parse_single_test_format(self, data: Dict, severity: str, task_type: str) -> Optional[Dict]:
        """Parse single test file format (flawed_test_<task>_<severity>_<timestamp>.json)"""
        results = {
            'baseline': [],
            'optimal': [],
            'flawed_light': [],
            'flawed_medium': [],
            'flawed_severe': []
        }
        
        if 'flaw_test_results' not in data:
            return None
        
        # Process each flaw's results
        for flaw_name, flaw_data in data['flaw_test_results'].items():
            if 'performance_comparison' not in flaw_data:
                continue
                
            perf = flaw_data['performance_comparison']
            
            # Collect baseline
            if 'baseline_prompt' in perf:
                results['baseline'].append(perf['baseline_prompt']['success_rate'])
            
            # Collect optimal
            if 'optimal_prompt' in perf:
                results['optimal'].append(perf['optimal_prompt']['success_rate'])
            
            # Collect flawed based on severity
            if 'flawed_optimal_prompt' in perf:
                key = f'flawed_{severity}'
                if key in results:
                    results[key].append(perf['flawed_optimal_prompt']['success_rate'])
        
        # Calculate averages
        final_results = {}
        for key, values in results.items():
            if values:
                final_results[key] = np.mean(values)
                logger.debug(f"{key}: {len(values)} samples from {task_type}/{severity}, avg={final_results[key]:.3f}")
        
        return final_results if final_results else None
    
    def _parse_combined_format(self, data: Dict) -> Optional[Dict]:
        """Parse flawed_test_combined_results.json format"""
        results = {
            'baseline': [],
            'optimal': [],
            'flawed_light': [],
            'flawed_medium': [],
            'flawed_severe': []
        }
        
        # Iterate through task types and severities
        for task_type, severity_data in data.items():
            if not isinstance(severity_data, dict):
                continue
                
            for severity, test_data in severity_data.items():
                if not isinstance(test_data, dict) or 'flaw_test_results' not in test_data:
                    continue
                    
                # Process each flaw's results
                for flaw_name, flaw_data in test_data['flaw_test_results'].items():
                    if 'performance_comparison' not in flaw_data:
                        continue
                        
                    perf = flaw_data['performance_comparison']
                    
                    # Collect baseline
                    if 'baseline_prompt' in perf:
                        results['baseline'].append(perf['baseline_prompt']['success_rate'])
                    
                    # Collect optimal
                    if 'optimal_prompt' in perf:
                        results['optimal'].append(perf['optimal_prompt']['success_rate'])
                    
                    # Collect flawed based on severity
                    if 'flawed_optimal_prompt' in perf:
                        key = f'flawed_{severity}'
                        if key in results:
                            results[key].append(perf['flawed_optimal_prompt']['success_rate'])
        
        # Calculate averages
        final_results = {}
        for key, values in results.items():
            if values:
                final_results[key] = np.mean(values)
                logger.debug(f"{key}: {len(values)} samples, avg={final_results[key]:.3f}")
        
        return final_results if final_results else None
    
    def _parse_flawed_results_format(self, results_data: Dict) -> Optional[Dict]:
        """Parse flawed_results_*.json format"""
        results = {
            'baseline': [],
            'optimal': [],
            'flawed_light': [],
            'flawed_medium': [],
            'flawed_severe': []
        }
        
        # Iterate through all results
        for task_type, severities in results_data.items():
            if not isinstance(severities, dict):
                continue
                
            for severity, flaw_results in severities.items():
                if not isinstance(flaw_results, dict):
                    continue
                    
                for flaw_name, flaw_data in flaw_results.items():
                    if 'performance_comparison' in flaw_data:
                        perf = flaw_data['performance_comparison']
                        
                        if 'baseline_prompt' in perf:
                            results['baseline'].append(perf['baseline_prompt']['success_rate'])
                        if 'optimal_prompt' in perf:
                            results['optimal'].append(perf['optimal_prompt']['success_rate'])
                        if 'flawed_optimal_prompt' in perf:
                            key = f'flawed_{severity}'
                            if key in results:
                                results[key].append(perf['flawed_optimal_prompt']['success_rate'])
        
        # Calculate averages
        final_results = {}
        for key, values in results.items():
            if values:
                final_results[key] = np.mean(values)
                logger.debug(f"{key}: {len(values)} samples, avg={final_results[key]:.3f}")
        
        return final_results if final_results else None
    
    def _parse_summary_format(self, data: Dict) -> Optional[Dict]:
        """Parse old summary.json format"""
        results = {}
        
        # Extract baseline
        if 'baseline_performance' in data:
            results['baseline'] = data['baseline_performance'].get('success_rate', 0)
        
        # Extract optimal and flawed
        if 'severity_comparison' in data:
            for severity, perf_data in data['severity_comparison'].items():
                if 'performance_comparison' in perf_data:
                    perf = perf_data['performance_comparison']
                    
                    if 'optimal_prompt' in perf:
                        results['optimal'] = perf['optimal_prompt']['success_rate']
                    
                    if 'flawed_optimal_prompt' in perf:
                        results[f'flawed_{severity}'] = perf['flawed_optimal_prompt']['success_rate']
        
        return results if results else None
    
    def _parse_from_individual_files(self) -> Optional[Dict]:
        """Parse from individual result files"""
        output_dir = Path("output")
        results = {
            'baseline': [],
            'optimal': [],
            'flawed_light': [],
            'flawed_medium': [],
            'flawed_severe': []
        }
        
        # Look for individual test result files
        patterns = [
            "flawed_test_*_*.json",
            "test_results_*.json",
            "*_results.json"
        ]
        
        found_files = []
        for pattern in patterns:
            found_files.extend(output_dir.glob(pattern))
        
        if not found_files:
            logger.debug("No individual result files found")
            return None
        
        logger.debug(f"Found {len(found_files)} individual result files")
        
        for file_path in found_files:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                # Try to extract results based on various formats
                if 'flaw_test_results' in data:
                    # Format: flawed_test_<task>_<severity>_<timestamp>.json
                    for flaw_name, flaw_data in data['flaw_test_results'].items():
                        if 'performance_comparison' in flaw_data:
                            perf = flaw_data['performance_comparison']
                            
                            if 'baseline_prompt' in perf:
                                results['baseline'].append(perf['baseline_prompt']['success_rate'])
                            if 'optimal_prompt' in perf:
                                results['optimal'].append(perf['optimal_prompt']['success_rate'])
                            if 'flawed_optimal_prompt' in perf:
                                severity = data.get('severity', 'medium')
                                key = f'flawed_{severity}'
                                if key in results:
                                    results[key].append(perf['flawed_optimal_prompt']['success_rate'])
                
                elif 'results' in data:
                    # Other possible formats
                    self._extract_from_results_dict(data['results'], results)
                    
            except Exception as e:
                logger.debug(f"Failed to parse {file_path.name}: {e}")
                continue
        
        # Calculate averages
        final_results = {}
        for key, values in results.items():
            if values:
                final_results[key] = np.mean(values)
                logger.debug(f"{key}: {len(values)} samples, avg={final_results[key]:.3f}")
        
        return final_results if final_results else None
    
    def _extract_from_results_dict(self, results_dict: Dict, results: Dict):
        """Helper to extract results from nested dictionaries"""
        for key, value in results_dict.items():
            if isinstance(value, dict):
                if 'success_rate' in value:
                    # Direct success rate
                    if 'baseline' in key.lower():
                        results['baseline'].append(value['success_rate'])
                    elif 'optimal' in key.lower() and 'flawed' not in key.lower():
                        results['optimal'].append(value['success_rate'])
                    elif 'flawed' in key.lower():
                        for severity in ['light', 'medium', 'severe']:
                            if severity in key.lower():
                                results[f'flawed_{severity}'].append(value['success_rate'])
                                break
                else:
                    # Recurse into nested dictionaries
                    self._extract_from_results_dict(value, results)
    
    def _parse_from_markdown_report(self) -> Optional[Dict]:
        """Parse from markdown report if available"""
        report_path = Path("output/report.md")
        if not report_path.exists():
            return None
        
        # Simple regex parsing of markdown tables
        # Implementation depends on exact report format
        return None
    
    def optimize(self, max_iterations: Optional[int] = None, parallel: bool = False):
        """Run optimization with optional parallelization"""
        parameter_sets = self.generate_fine_grid_parameters()
        
        if max_iterations:
            parameter_sets = parameter_sets[:max_iterations]
        
        logger.info(f"Starting fine-grained optimization with {len(parameter_sets)} parameters")
        logger.info(f"Parallel execution: {parallel}")
        
        # Pre-create all directories to avoid race conditions
        self._ensure_param_directories(len(parameter_sets))
        
        best_score = -float('inf')
        best_params = None
        best_results = None
        best_breakdown = None
        
        if parallel and len(parameter_sets) > 5:
            # Parallel execution
            max_workers = max(4, mp.cpu_count() //2)  # Leave one CPU free
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_params = {
                    executor.submit(self.run_single_test, params, idx): (params, idx)
                    for idx, params in enumerate(parameter_sets)
                }
                
                for future in as_completed(future_to_params):
                    params, idx = future_to_params[future]
                    try:
                        result_data = future.result()
                        if result_data:
                            self.results_history.append(result_data)
                            
                            if result_data['score'] > best_score:
                                best_score = result_data['score']
                                best_params = result_data['params']
                                best_results = result_data['results']
                                best_breakdown = result_data['breakdown']
                                
                                logger.info(f"🌟 NEW BEST! Score: {best_score:.1f}")
                                self._save_intermediate_best(best_params, best_results, best_breakdown)
                        else:
                            logger.warning(f"Test {idx} returned no data")
                    except Exception as e:
                        logger.error(f"Error processing result for test {idx}: {e}")
                        # Create error record
                        error_dir = self.experiment_dir / f"param_set_{idx:04d}"
                        try:
                            error_dir.mkdir(exist_ok=True, parents=True)
                            with open(error_dir / "processing_error.txt", 'w') as f:
                                f.write(f"Error during result processing:\n{str(e)}\n")
                                f.write(f"Params: {json.dumps(params, indent=2)}\n")
                        except:
                            pass
        else:
            # Sequential execution
            for idx, params in enumerate(parameter_sets):
                result_data = self.run_single_test(params, idx)
                
                if result_data:
                    self.results_history.append(result_data)
                    
                    if result_data['score'] > best_score:
                        best_score = result_data['score']
                        best_params = result_data['params']
                        best_results = result_data['results']
                        best_breakdown = result_data['breakdown']
                        
                        logger.info(f"🌟 NEW BEST! Score: {best_score:.1f}")
                        self._save_intermediate_best(best_params, best_results, best_breakdown)
                
                # Small delay between tests
                if idx < len(parameter_sets) - 1:
                    time.sleep(1)
        
        # Save final results
        self._save_final_results()
        
        return best_params, best_results, best_breakdown
    
    def _save_intermediate_best(self, params: Dict, results: Dict, breakdown: Dict):
        """Save current best results"""
        best_path = self.experiment_dir / "current_best.json"
        with open(best_path, 'w') as f:
            json.dump({
                'params': params,
                'results': results,
                'breakdown': breakdown,
                'timestamp': datetime.now().isoformat()
            }, f, indent=2)
        
        # Also save to root directory for easy access
        with open("current_best_fine_grid.json", 'w') as f:
            json.dump({
                'params': params,
                'results': results,
                'breakdown': breakdown,
                'timestamp': datetime.now().isoformat(),
                'experiment_dir': str(self.experiment_dir)
            }, f, indent=2)
        
        # Save a backup with timestamp
        backup_name = f"best_backup_{datetime.now().strftime('%H%M%S')}.json"
        backup_path = self.experiment_dir / "backups"
        backup_path.mkdir(exist_ok=True)
        with open(backup_path / backup_name, 'w') as f:
            json.dump({
                'params': params,
                'results': results,
                'breakdown': breakdown
            }, f, indent=2)
    
    def _save_final_results(self):
        """Save comprehensive final results"""
        # Sort by score
        sorted_history = sorted(
            self.results_history,
            key=lambda x: x['score'],
            reverse=True
        )
        
        # Calculate statistics
        if sorted_history:
            top_10 = sorted_history[:10]
            
            # Analyze parameter trends in top results
            param_stats = {
                'base_score': {
                    'values': [r['params']['base_score'] for r in top_10],
                    'mean': np.mean([r['params']['base_score'] for r in top_10]),
                    'std': np.std([r['params']['base_score'] for r in top_10])
                },
                'success_threshold': {
                    'values': [r['params']['success_threshold'] for r in top_10],
                    'mean': np.mean([r['params']['success_threshold'] for r in top_10]),
                    'std': np.std([r['params']['success_threshold'] for r in top_10])
                },
                'weight_trends': {}
            }
            
            # Analyze weight trends
            for weight_key in ['task_completion', 'dependency_satisfaction', 
                             'execution_efficiency', 'execution_order']:
                values = [r['params']['weights'][weight_key] for r in top_10]
                param_stats['weight_trends'][weight_key] = {
                    'mean': np.mean(values),
                    'std': np.std(values),
                    'range': [min(values), max(values)]
                }
        else:
            param_stats = {}
        
        summary = {
            'experiment_id': self.experiment_id,
            'experiment_type': 'fine_grid_search',
            'total_tests': len(self.results_history),
            'optimization_goal': 'optimal > flawed_light > baseline > flawed_medium > flawed_severe',
            'best_result': sorted_history[0] if sorted_history else None,
            'top_10_results': sorted_history[:10],
            'parameter_statistics': param_stats,
            'search_space': {
                'total_combinations_tested': len(self.results_history),
                'convergence_achieved': len(set(r['score'] for r in sorted_history[:5])) == 1
            }
        }
        
        # Save to experiment directory
        with open(self.experiment_dir / "final_summary.json", 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Update latest results
        with open("latest_fine_grid_results.json", 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Generate readable report
        self._generate_report(summary)
        
        # Clean up temp directory
        if self.temp_dir.exists():
            try:
                shutil.rmtree(self.temp_dir)
                logger.info(f"Cleaned up temp directory: {self.temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean up temp directory: {e}")
        
        logger.info(f"\n✅ Fine-grained optimization complete!")
        logger.info(f"Results saved to: {self.experiment_dir}")
    
    def _generate_report(self, summary: Dict):
        """Generate human-readable report"""
        report_path = self.experiment_dir / "optimization_report.md"
        
        with open(report_path, 'w') as f:
            f.write("# Fine-Grained Parameter Optimization Report\n\n")
            f.write(f"**Experiment ID**: {summary['experiment_id']}\n")
            f.write(f"**Total Tests**: {summary['total_tests']}\n")
            f.write(f"**Optimization Goal**: {summary['optimization_goal']}\n\n")
            
            if summary['best_result']:
                best = summary['best_result']
                f.write("## Best Configuration\n\n")
                f.write(f"**Score**: {best['score']:.1f}\n")
                f.write(f"**Correct Orders**: {best['breakdown']['correct_orders']}/4\n\n")
                
                f.write("### Parameters\n")
                f.write(f"- Base Score: {best['params']['base_score']}\n")
                f.write(f"- Success Threshold: {best['params']['success_threshold']}\n")
                f.write("\n### Weights\n")
                for k, v in best['params']['weights'].items():
                    f.write(f"- {k}: {v}\n")
                
                f.write("\n### Results\n")
                for k, v in best['results'].items():
                    f.write(f"- {k}: {v:.1%}\n")
            
            if 'parameter_statistics' in summary and summary['parameter_statistics']:
                f.write("\n## Parameter Trends (Top 10)\n\n")
                stats = summary['parameter_statistics']
                
                f.write(f"### Base Score\n")
                f.write(f"- Mean: {stats['base_score']['mean']:.3f}\n")
                f.write(f"- Std: {stats['base_score']['std']:.3f}\n\n")
                
                f.write(f"### Success Threshold\n")
                f.write(f"- Mean: {stats['success_threshold']['mean']:.3f}\n")
                f.write(f"- Std: {stats['success_threshold']['std']:.3f}\n\n")
                
                f.write("### Weight Trends\n")
                for k, v in stats['weight_trends'].items():
                    f.write(f"- {k}: mean={v['mean']:.3f}, range={v['range']}\n")


def main():
    """Main entry point"""
    print("🔬 Fine-Grained Parameter Optimization")
    print("=" * 60)
    
    optimizer = FineGridSearchOptimizer()
    
    # Display previous best if available
    if optimizer.previous_best:
        print("\n📊 Previous Best Configuration:")
        if 'params' in optimizer.previous_best:
            print(f"  Base Score: {optimizer.previous_best['params']['base_score']}")
            print(f"  Threshold: {optimizer.previous_best['params']['success_threshold']}")
        if 'score' in optimizer.previous_best:
            print(f"  Score: {optimizer.previous_best['score']:.1f}")
    
    print("\nSelect optimization mode:")
    print("1. Quick fine search (20 parameters)")
    print("2. Standard fine search (50 parameters)")
    print("3. Comprehensive fine search (100+ parameters)")
    print("4. Exhaustive fine search (200+ parameters)")
    print("5. Custom parameter test")
    
    choice = input("\nEnter choice (1-5): ").strip()
    
    if choice == '1':
        max_iterations = 20
        parallel = False
    elif choice == '2':
        max_iterations = 50
        parallel = True
    elif choice == '3':
        max_iterations = 100
        parallel = True
    elif choice == '4':
        max_iterations = None  # Use all generated
        parallel = True
    elif choice == '5':
        # Custom single test
        print("\nEnter custom parameters:")
        base_score = float(input("Base score (0.05-0.3): "))
        threshold = float(input("Success threshold (0.6-0.85): "))
        
        params = {
            'base_score': base_score,
            'success_threshold': threshold,
            'weights': {
                'task_completion': 0.25,
                'dependency_satisfaction': 0.15,
                'execution_efficiency': 0.45,
                'execution_order': 0.15
            },
            'penalties': {
                'unnecessary_tool': 0.10,
                'duplicate_execution': 0.10,
                'missing_required': 0.20,
                'dependency_violation': 0.15
            },
            'thresholds': {
                'min_completion_rate': 0.3,
                'perfect_completion': 1.0,
                'good_completion': 0.6
            }
        }
        
        print("\nTesting custom configuration...")
        result = optimizer.run_single_test(params, 0)
        
        if result:
            print(f"\nResults:")
            for k, v in result['results'].items():
                print(f"  {k}: {v:.1%}")
            print(f"\nScore: {result['score']:.1f}")
            print(f"Breakdown: {json.dumps(result['breakdown'], indent=2)}")
        return
    else:
        print("Invalid choice")
        return
    
    # Run optimization
    print(f"\n🚀 Starting fine-grained search...")
    if max_iterations:
        print(f"Testing up to {max_iterations} parameter combinations")
    else:
        print("Testing all generated parameter combinations")
    
    best_params, best_results, best_breakdown = optimizer.optimize(
        max_iterations=max_iterations,
        parallel=parallel
    )
    
    if best_params and best_results:
        print("\n" + "="*60)
        print("🏆 BEST CONFIGURATION FOUND")
        print("="*60)
        
        print("\nParameters:")
        print(f"  Base score: {best_params['base_score']}")
        print(f"  Success threshold: {best_params['success_threshold']}")
        print(f"\nWeights:")
        for k, v in best_params['weights'].items():
            print(f"  {k}: {v}")
        
        print("\nResults:")
        for k, v in best_results.items():
            print(f"  {k}: {v:.1%}")
        
        print(f"\nScore: {best_breakdown['final_score']:.1f}")
        print(f"Correct orderings: {best_breakdown['correct_orders']}/4")
        
        # Check target achievement
        if (best_results.get('optimal', 0) > best_results.get('flawed_light', 0) > 
            best_results.get('baseline', 0) > best_results.get('flawed_medium', 0) >
            best_results.get('flawed_severe', 0)):
            print("\n✅ SUCCESS: Perfect ranking achieved!")
        else:
            print("\n⚠️ Partial success: Some ordering constraints not met")
    
    print(f"\n📁 Full results saved in: {optimizer.experiment_dir}")


if __name__ == "__main__":
    main()
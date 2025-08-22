#!/usr/bin/env python3
"""
Generate Visualization Plots Script
===================================
This script generates all visualization plots from workflow quality test results.
It can process multiple result files and create comprehensive visual analysis.

Usage:
    python generate_plots.py --input test_results/complete_analysis_data.pkl
    python generate_plots.py --input-dir test_results --output-dir visualizations
    python generate_plots.py --latest --plot-types success score severity
"""

import argparse
import json
import pickle
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import sys

# Import visualization utilities
try:
    from visualization_utils import WorkflowVisualizationManager, plot_training_analysis
except ImportError:
    print("Error: visualization_utils.py not found!")
    print("Please ensure visualization_utils.py is in the same directory or in PYTHONPATH")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PlotGenerator:
    """Main class for generating plots from test results"""
    
    def __init__(self, output_dir: Path):
        """Initialize the plot generator
        
        Args:
            output_dir: Directory to save generated plots
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize visualization manager
        self.viz_manager = WorkflowVisualizationManager(self.output_dir)
        
        logger.info(f"Plot generator initialized. Output directory: {self.output_dir}")
    
    def load_results_from_pickle(self, pickle_path: Path) -> Optional[Dict]:
        """Load results from pickle file
        
        Args:
            pickle_path: Path to pickle file
            
        Returns:
            Dictionary containing results or None if failed
        """
        try:
            with open(pickle_path, 'rb') as f:
                data = pickle.load(f)
            logger.info(f"Successfully loaded data from {pickle_path}")
            return data
        except Exception as e:
            logger.error(f"Failed to load pickle file {pickle_path}: {e}")
            return None
    
    def load_results_from_json(self, json_path: Path) -> Optional[Dict]:
        """Load results from JSON file
        
        Args:
            json_path: Path to JSON file
            
        Returns:
            Dictionary containing results or None if failed
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"Successfully loaded data from {json_path}")
            return data
        except Exception as e:
            logger.error(f"Failed to load JSON file {json_path}: {e}")
            return None
    
    def generate_all_plots(self, results: Dict[str, List[Any]]):
        """Generate all visualization plots
        
        Args:
            results: Test results dictionary
        """
        print("\n🎨 Generating all visualization plots...")
        print("="*50)
        
        try:
            self.viz_manager.generate_all_visualizations(results)
            print(f"\n✅ All plots successfully generated in: {self.output_dir}")
        except Exception as e:
            logger.error(f"Error generating plots: {e}")
            print(f"\n❌ Error generating plots: {e}")
            raise
    
    def generate_specific_plots(self, results: Dict[str, List[Any]], plot_types: List[str]):
        """Generate specific types of plots
        
        Args:
            results: Test results dictionary
            plot_types: List of plot types to generate
        """
        print(f"\n🎨 Generating specific plots: {', '.join(plot_types)}")
        print("="*50)
        
        plot_mapping = {
            'success': self.viz_manager.plot_success_rates,
            'score': self.viz_manager.plot_score_distribution,
            'adherence': self.viz_manager.plot_workflow_adherence,
            'phase2': self.viz_manager.plot_phase2_metrics,
            'time': self.viz_manager.plot_execution_times,
            'severity': self.viz_manager.plot_severity_impact,
            'flaw': self.viz_manager.plot_flaw_sensitivity,
            'quality': self.viz_manager.plot_quality_breakdown,
            'scatter': self.viz_manager.plot_quality_vs_achievement
        }
        
        generated = []
        for plot_type in plot_types:
            if plot_type in plot_mapping:
                try:
                    print(f"  📊 Generating {plot_type} plot...")
                    plot_mapping[plot_type](results)
                    generated.append(plot_type)
                except Exception as e:
                    logger.error(f"Error generating {plot_type} plot: {e}")
                    print(f"  ❌ Failed to generate {plot_type} plot: {e}")
            else:
                print(f"  ⚠️  Unknown plot type: {plot_type}")
        
        if generated:
            print(f"\n✅ Successfully generated plots: {', '.join(generated)}")
    
    def generate_training_plots(self, metrics_path: Path):
        """Generate training analysis plots
        
        Args:
            metrics_path: Path to training metrics file
        """
        print("\n📈 Generating training analysis plots...")
        print("="*50)
        
        try:
            with open(metrics_path, 'r') as f:
                metrics = json.load(f)
            
            training_dir = self.output_dir / "training_analysis"
            plot_training_analysis(metrics, training_dir)
            
            print(f"\n✅ Training plots generated in: {training_dir}")
        except Exception as e:
            logger.error(f"Error generating training plots: {e}")
            print(f"\n❌ Error generating training plots: {e}")
    
    def process_directory(self, input_dir: Path):
        """Process all result files in a directory
        
        Args:
            input_dir: Directory containing result files
        """
        print(f"\n📁 Processing directory: {input_dir}")
        print("="*50)
        
        # Find all result files
        pickle_files = list(input_dir.glob("*.pkl"))
        json_files = list(input_dir.glob("*analysis*.json"))
        
        print(f"Found {len(pickle_files)} pickle files and {len(json_files)} JSON files")
        
        # Process pickle files
        for pkl_file in pickle_files:
            print(f"\n📄 Processing {pkl_file.name}...")
            data = self.load_results_from_pickle(pkl_file)
            
            if data and 'all_results' in data:
                # Create subdirectory for this file
                file_output_dir = self.output_dir / pkl_file.stem
                file_viz_manager = WorkflowVisualizationManager(file_output_dir)
                
                try:
                    file_viz_manager.generate_all_visualizations(data['all_results'])
                    print(f"  ✅ Plots saved to: {file_output_dir}")
                except Exception as e:
                    print(f"  ❌ Error: {e}")
        
        # Process JSON files if needed
        for json_file in json_files:
            if "complete_analysis" in json_file.name:
                print(f"\n📄 Found analysis file: {json_file.name}")
                # Note: JSON files might need special handling depending on format
    
    def find_latest_results(self) -> Optional[Path]:
        """Find the most recent results file
        
        Returns:
            Path to the latest results file or None
        """
        # Search common locations
        search_paths = [
            Path("test_results"),
            Path("results"),
            Path("output"),
            Path(".")
        ]
        
        latest_file = None
        latest_time = 0
        
        for search_dir in search_paths:
            if search_dir.exists():
                # Look for pickle files
                for pkl_file in search_dir.glob("**/complete_analysis_data.pkl"):
                    mtime = pkl_file.stat().st_mtime
                    if mtime > latest_time:
                        latest_time = mtime
                        latest_file = pkl_file
                
                # Look for result pickle files
                for pkl_file in search_dir.glob("**/test_results_*.pkl"):
                    mtime = pkl_file.stat().st_mtime
                    if mtime > latest_time:
                        latest_time = mtime
                        latest_file = pkl_file
        
        return latest_file


def main():
    """Main function to handle command line arguments and run plot generation"""
    parser = argparse.ArgumentParser(
        description="Generate visualization plots from workflow quality test results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate plots from a specific file
  python generate_plots.py --input test_results/complete_analysis_data.pkl
  
  # Process all files in a directory
  python generate_plots.py --input-dir test_results --output-dir visualizations
  
  # Generate only specific plot types
  python generate_plots.py --input results.pkl --plot-types success score severity
  
  # Use the latest results file
  python generate_plots.py --latest
  
  # Generate training plots
  python generate_plots.py --training-metrics checkpoints/final_metrics.json
        """
    )
    
    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '--input', '-i',
        type=Path,
        help='Path to input pickle or JSON file'
    )
    input_group.add_argument(
        '--input-dir', '-d',
        type=Path,
        help='Directory containing result files to process'
    )
    input_group.add_argument(
        '--latest', '-l',
        action='store_true',
        help='Use the latest results file found'
    )
    
    # Output options
    parser.add_argument(
        '--output-dir', '-o',
        type=Path,
        default=Path('plot_output'),
        help='Directory to save generated plots (default: plot_output)'
    )
    
    # Plot options
    parser.add_argument(
        '--plot-types', '-p',
        nargs='+',
        choices=['success', 'score', 'adherence', 'phase2', 'time', 
                 'severity', 'flaw', 'quality', 'scatter', 'all'],
        default=['all'],
        help='Types of plots to generate (default: all)'
    )
    
    # Additional options
    parser.add_argument(
        '--training-metrics', '-t',
        type=Path,
        help='Path to training metrics JSON file for training plots'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Print header
    print("\n" + "="*60)
    print("🎨 Workflow Quality Test Results Visualization Generator")
    print("="*60)
    print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialize plot generator
    generator = PlotGenerator(args.output_dir)
    
    # Handle latest option
    if args.latest:
        latest_file = generator.find_latest_results()
        if latest_file:
            print(f"\n📍 Found latest results file: {latest_file}")
            args.input = latest_file
        else:
            print("\n❌ No results files found!")
            sys.exit(1)
    
    # Process based on input type
    if args.input_dir:
        # Process directory
        generator.process_directory(args.input_dir)
    
    elif args.input:
        # Process single file
        file_ext = args.input.suffix.lower()
        
        if file_ext == '.pkl':
            data = generator.load_results_from_pickle(args.input)
            if data:
                if 'all_results' in data:
                    results = data['all_results']
                else:
                    results = data
        
        elif file_ext == '.json':
            data = generator.load_results_from_json(args.input)
            if data:
                # Note: JSON data might need conversion
                # This is a placeholder - adjust based on your JSON structure
                if 'all_results' in data:
                    results = data['all_results']
                else:
                    results = data
        
        else:
            print(f"\n❌ Unsupported file type: {file_ext}")
            sys.exit(1)
        
        # Generate plots
        if 'results' in locals() and results:
            if 'all' in args.plot_types:
                generator.generate_all_plots(results)
            else:
                generator.generate_specific_plots(results, args.plot_types)
        else:
            print("\n❌ No valid results data found in input file!")
            sys.exit(1)
    
    # Generate training plots if requested
    if args.training_metrics:
        generator.generate_training_plots(args.training_metrics)
    
    # Summary
    print("\n" + "="*60)
    print("📊 Plot Generation Summary")
    print("="*60)
    print(f"Output directory: {args.output_dir}")
    print(f"Total files in output: {len(list(args.output_dir.glob('*.png')))}")

    # List generated files
    print("\nGenerated files:")
    for png_file in sorted(args.output_dir.glob('**/*.png')):
        rel_path = png_file.relative_to(args.output_dir)
        print(f"  📈 {rel_path}")
    
    print("\n✅ Plot generation completed successfully!")


if __name__ == "__main__":
    main()
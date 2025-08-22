#!/usr/bin/env python3
"""
Phase 2/3 Reinforcement Training Script - Enhanced Version
=========================================================
Adds resume functionality and verbose control to the training script.
"""

import os
import sys
import json
import torch
import numpy as np
from pathlib import Path
from datetime import datetime
from collections import defaultdict, deque
import logging
from typing import Dict, List, Optional, Tuple, Any

# Import required modules
try:
    from unified_training_manager import UnifiedTrainingManager, DQNTrainer
    from workflow_quality_test_flawed import StableScorer, SimplifiedScoringConfig, ToolCallVerifier
    from mdp_workflow_generator import MDPWorkflowGenerator
    from generalized_mdp_framework import GeneralizedMDPState, ActionType
except ImportError as e:
    print(f"Failed to import required modules: {e}")
    print("Make sure all required files are in the same directory")
    sys.exit(1)


class Phase23ReinforcementTrainer:
    """Enhanced trainer with resume capability and verbose control"""
    
    def __init__(self, base_model_path: str = "checkpoints/best_model.pt", verbose: bool = True):
        self.base_model_path = Path(base_model_path)
        self.checkpoint_dir = Path("phase23_checkpoints")
        self.checkpoint_dir.mkdir(exist_ok=True)
        self.verbose = verbose
        
        # Setup logging based on verbose flag
        self._setup_logging(verbose)
        
        # Initialize components
        self.manager = None
        self.workflow_generator = None
        self.stable_scorer = None
        
        # Training state (will be loaded if resuming)
        self.training_state = {
            'total_episodes': 0,
            'current_episode': 0,
            'episodes_since_improvement': 0,
            'best_phase2_score': 0.0,
            'best_optimal_success_rate': 0.0,
        }
        
        # Training metrics
        self.training_metrics = {
            'episode_rewards': deque(maxlen=100),
            'episode_phase2_scores': deque(maxlen=100),
            'task_success_rates': defaultdict(lambda: deque(maxlen=50)),
            'strategy_scores': {
                'baseline': deque(maxlen=100),
                'optimal': deque(maxlen=100),
                'cot': deque(maxlen=100)
            },
            'workflow_adherence': deque(maxlen=100)
        }
        
    def _setup_logging(self, verbose: bool):
        """Setup logging based on verbose flag"""
        # Get logger
        self.logger = logging.getLogger(__name__)
        
        # Clear existing handlers
        self.logger.handlers = []
        
        # Create handler
        handler = logging.StreamHandler()
        
        if verbose:
            # Detailed format for verbose mode
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            self.logger.setLevel(logging.INFO)
        else:
            # Minimal format for quiet mode
            formatter = logging.Formatter('%(message)s')
            self.logger.setLevel(logging.WARNING)
        
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
    def log(self, message: str, level: str = 'info', force: bool = False):
        """Log message with optional force flag to show even in quiet mode"""
        if force:
            print(message)  # Always print forced messages
        else:
            getattr(self.logger, level)(message)
    
    def _load_checkpoint(self, checkpoint_path: Path) -> bool:
        """Load training state from checkpoint"""
        try:
            self.log(f"Loading checkpoint from {checkpoint_path}")
            
            # Load the checkpoint
            checkpoint = torch.load(checkpoint_path, map_location='cpu', weights_only=False)
            
            # Restore training state
            if 'training_state' in checkpoint:
                self.training_state.update(checkpoint['training_state'])
            else:
                # Try to reconstruct from other fields
                self.training_state['total_episodes'] = checkpoint.get('episode', 0)
                self.training_state['best_phase2_score'] = checkpoint.get('best_phase2_score', 0)
                self.training_state['best_optimal_success_rate'] = checkpoint.get('best_optimal_success_rate', 0)
            
            # Restore metrics if available
            if 'training_metrics' in checkpoint:
                metrics = checkpoint['training_metrics']
                for key, value in metrics.items():
                    if key in self.training_metrics:
                        if isinstance(value, list):
                            self.training_metrics[key] = deque(value, maxlen=100)
                        elif isinstance(value, dict):
                            for sub_key, sub_value in value.items():
                                if isinstance(sub_value, list):
                                    self.training_metrics[key][sub_key] = deque(sub_value, maxlen=100)
            
            # Update internal state
            self.best_phase2_score = self.training_state['best_phase2_score']
            self.best_optimal_success_rate = self.training_state['best_optimal_success_rate']
            self.episodes_since_improvement = self.training_state.get('episodes_since_improvement', 0)
            
            self.log(f"Resumed from episode {self.training_state['total_episodes']}", force=True)
            self.log(f"Best Phase2 score: {self.best_phase2_score:.3f}", force=True)
            self.log(f"Best optimal success rate: {self.best_optimal_success_rate:.2%}", force=True)
            
            return True
            
        except Exception as e:
            self.log(f"Failed to load checkpoint: {e}", level='error')
            return False
    
    def _find_best_checkpoint(self) -> Optional[Path]:
        """Find the best checkpoint to resume from"""
        candidates = []
        
        # Check for best model
        best_model = self.checkpoint_dir / "best_phase2_model.pt"
        if best_model.exists():
            candidates.append(best_model)
        
        # Check for final model
        final_model = self.checkpoint_dir / "final_phase23_model.pt"
        if final_model.exists():
            candidates.append(final_model)
        
        # Check for latest checkpoint
        checkpoints = list(self.checkpoint_dir.glob("checkpoint_ep*.pt"))
        if checkpoints:
            checkpoints.sort(key=lambda x: int(x.stem.split('_ep')[1]))
            candidates.append(checkpoints[-1])
        
        # Return the most recent among candidates
        if candidates:
            return max(candidates, key=lambda x: x.stat().st_mtime)
        
        return None
    
    def setup(self, resume: bool = False) -> bool:
        """Setup training environment with optional resume"""
        self.log("Setting up Phase 2/3 reinforcement training...")
        
        # Check for required files
        tool_registry_path = Path("mcp_generated_library/tool_registry.json")
        task_library_path = Path("mcp_generated_library/task_library.json")
        
        if not tool_registry_path.exists():
            self.log(f"Tool registry not found at {tool_registry_path}", level='error')
            return False
            
        # Create manager with enhanced configuration
        self.manager = UnifiedTrainingManager(
            use_task_aware_state=True,
            enforce_workflow=True,
            use_phase2_scoring=True
        )
        
        # Setup environment
        if not self.manager.setup_environment(
            tool_registry_path=str(tool_registry_path),
            task_library_path=str(task_library_path) if task_library_path.exists() else None
        ):
            self.log("Failed to setup environment!", level='error')
            return False
        
        # Initialize trainer
        try:
            self.manager.trainer = DQNTrainer(self.manager.env, self.manager.config)
            self.log("Trainer initialized successfully")
        except Exception as e:
            self.log(f"Failed to initialize trainer: {e}", level='error')
            return False
        
        # Handle resume/base model loading
        if resume:
            # Try to find and load checkpoint
            checkpoint_path = self._find_best_checkpoint()
            if checkpoint_path:
                self._load_checkpoint(checkpoint_path)
                # Load model weights into trainer
                self.manager.trainer.load_checkpoint(str(checkpoint_path))
            else:
                self.log("No checkpoint found to resume from", level='warning')
                # Fall back to base model
                if self.base_model_path.exists():
                    self.log(f"Loading base model from {self.base_model_path}")
                    self.manager.trainer.load_checkpoint(str(self.base_model_path))
        else:
            # Load base model if exists
            if self.base_model_path.exists():
                self.log(f"Loading base model from {self.base_model_path}")
                self.manager.trainer.load_checkpoint(str(self.base_model_path))
        
        # Initialize workflow generator
        try:
            tools_path = Path("mcp_generated_library/tool_registry.json")
            if not tools_path.exists() and Path("tool_registry.json").exists():
                tools_path = Path("tool_registry.json")
            
            self.workflow_generator = MDPWorkflowGenerator(
                model_path=str(self.base_model_path) if self.base_model_path.exists() else None,
                tools_path=str(tools_path) if tools_path else None
            )
        except Exception as e:
            self.log(f"Could not initialize workflow generator: {e}", level='warning')
            self.workflow_generator = None
        
        # Initialize stable scorer with adjusted weights for stronger optimal bias
        config = SimplifiedScoringConfig(
            task_achievement_weight=0.5,   # Reduced from 0.6
            execution_quality_weight=0.5,   # Increased from 0.4
            workflow_adherence_weight=0.7,  # Increased from 0.6
            efficiency_weight=0.15,         # Reduced from 0.2
            error_handling_weight=0.15      # Reduced from 0.2
        )
        
        # Get verifier
        verifier = None
        if hasattr(self.manager, 'env') and hasattr(self.manager.env, 'tool_registry'):
            try:
                verifier = ToolCallVerifier(self.manager.env.tool_registry)
                self.log("Created verifier from environment tool registry")
            except Exception as e:
                self.log(f"Could not create verifier: {e}", level='warning')
        
        self.stable_scorer = StableScorer(config=config, verifier=verifier)
        
        # Override reward function with stronger optimal bias
        self._override_reward_function_v2()
        
        return True
    
    def _override_reward_function_v2(self):
        """Enhanced reward function with stronger bias for optimal strategy"""
        original_step = self.manager.env.step
        
        def enhanced_step(action):
            # Call original step
            next_state, base_reward, done, info = original_step(action)
            
            # Calculate Phase 2 score if available
            if 'phase2_metrics' in info and info['phase2_metrics']:
                phase2_score = info['phase2_metrics'].get('phase2_score', 0)
                adherence = info.get('workflow_adherence', 0)
                
                # More aggressive reward shaping for optimal strategy
                # Strongly penalize low adherence
                adherence_multiplier = adherence ** 2  # Quadratic penalty for low adherence
                
                # Enhanced reward formula
                enhanced_reward = (
                    0.2 * (base_reward / 10.0) +      # 20% original reward (reduced)
                    0.4 * phase2_score * 10 +          # 40% Phase 2 score
                    0.4 * adherence_multiplier * 10    # 40% workflow adherence (squared)
                )
                
                # Strong bonuses for high performance
                if phase2_score > 0.7 and adherence > 0.7:
                    enhanced_reward += 5.0
                if phase2_score > 0.8 and adherence > 0.8:
                    enhanced_reward += 10.0
                
                # Heavy penalties for low adherence
                if adherence < 0.5:
                    enhanced_reward -= 5.0
                if adherence < 0.3:
                    enhanced_reward -= 10.0
                
                # Update info
                info['original_reward'] = base_reward
                info['enhanced_reward'] = enhanced_reward
                info['adherence_multiplier'] = adherence_multiplier
                
                return next_state, enhanced_reward, done, info
            else:
                return next_state, base_reward, done, info
        
        # Replace step function
        self.manager.env.step = enhanced_step
    
    def train_episode(self, episode_num: int) -> Dict[str, Any]:
        """Train a single episode"""
        # Reset environment
        state = self.manager.env.reset()
        
        # Get current task info
        task_type = getattr(self.manager.env.current_task, 'task_type', 'unknown')
        
        # Generate workflow if available
        workflow = None
        if self.workflow_generator is not None:
            try:
                workflow = self.workflow_generator.generate_workflow(task_type)
            except Exception as e:
                self.log(f"Could not generate workflow for {task_type}: {e}", level='debug')
        
        episode_reward = 0
        episode_phase2_scores = []
        done = False
        steps = 0
        
        while not done and steps < self.manager.config['max_episode_length']:
            # Get valid actions
            valid_actions = self.manager.env.get_valid_actions() if hasattr(self.manager.env, 'get_valid_actions') else None
            
            # Select action
            action = self.manager.trainer.select_action(state, valid_actions)
            
            # Step environment
            next_state, reward, done, info = self.manager.env.step(action)
            
            # Store transition
            self.manager.trainer.replay_buffer.push(state, action, reward, next_state, done)
            
            # Train model
            if len(self.manager.trainer.replay_buffer) >= self.manager.config['batch_size']:
                loss = self.manager.trainer.train_step()
            
            # Track metrics
            episode_reward += reward
            if 'phase2_metrics' in info and info['phase2_metrics']:
                phase2_score = info['phase2_metrics'].get('phase2_score', 0)
                episode_phase2_scores.append(phase2_score)
            
            state = next_state
            steps += 1
        
        # Calculate episode metrics
        avg_phase2_score = np.mean(episode_phase2_scores) if episode_phase2_scores else 0
        success = info.get('success', False)
        workflow_adherence = info.get('workflow_adherence', 0)
        
        # Update tracking
        self.training_metrics['episode_rewards'].append(episode_reward)
        self.training_metrics['episode_phase2_scores'].append(avg_phase2_score)
        self.training_metrics['task_success_rates'][task_type].append(float(success))
        self.training_metrics['workflow_adherence'].append(workflow_adherence)
        
        # Check for improvement
        if avg_phase2_score > self.best_phase2_score:
            self.best_phase2_score = avg_phase2_score
            self.episodes_since_improvement = 0
            self._save_best_model(episode_num, avg_phase2_score)
        else:
            self.episodes_since_improvement += 1
        
        return {
            'episode': episode_num,
            'reward': episode_reward,
            'phase2_score': avg_phase2_score,
            'success': success,
            'task_type': task_type,
            'workflow_adherence': workflow_adherence,
            'steps': steps
        }
    
    def train(self, num_episodes: int = 1000, 
              eval_frequency: int = 100,
              save_frequency: int = 50,
              resume: bool = False) -> Dict[str, Any]:
        """Main training loop with resume support"""
        
        # Determine starting episode
        start_episode = self.training_state['total_episodes'] if resume else 0
        total_episodes = start_episode + num_episodes
        
        self.log(f"Starting Phase 2/3 reinforcement training", force=True)
        self.log(f"Episodes: {start_episode} -> {total_episodes}", force=True)
        self.log(f"Verbose: {self.verbose}", force=True)
        
        training_start = datetime.now()
        
        for episode in range(start_episode, total_episodes):
            # Update current episode
            self.training_state['current_episode'] = episode
            self.training_state['total_episodes'] = episode + 1
            
            # Train episode
            episode_result = self.train_episode(episode)
            
            # Update epsilon
            self.manager.trainer.update_epsilon()
            
            # Print progress (respecting verbose flag)
            if episode % 10 == 0:
                avg_reward = np.mean(self.training_metrics['episode_rewards'])
                avg_phase2 = np.mean(self.training_metrics['episode_phase2_scores'])
                avg_adherence = np.mean(self.training_metrics['workflow_adherence'])
                
                # Compact progress for non-verbose mode
                if not self.verbose:
                    print(f"Ep {episode}/{total_episodes}: R={avg_reward:.1f}, P2={avg_phase2:.3f}, A={avg_adherence:.3f}, Best={self.best_phase2_score:.3f}")
                else:
                    self.log(f"Episode {episode}/{total_episodes}:")
                    self.log(f"  Avg Reward: {avg_reward:.2f}")
                    self.log(f"  Avg Phase2 Score: {avg_phase2:.3f}")
                    self.log(f"  Avg Workflow Adherence: {avg_adherence:.3f}")
                    self.log(f"  Best Phase2 Score: {self.best_phase2_score:.3f}")
                    self.log(f"  Episodes Since Improvement: {self.episodes_since_improvement}")
            
            # Evaluate strategies
            if episode % eval_frequency == 0 and episode > 0:
                eval_results = self.evaluate_strategies()
                
                # Always show evaluation results
                self.log("\nStrategy Evaluation Results:", force=True)
                for strategy, metrics in eval_results.items():
                    self.log(f"  {strategy}: {metrics['success_rate']:.1%} success, {metrics['avg_score']:.3f} score", force=True)
                
                # Check if optimal is improving
                optimal_success = eval_results['optimal']['success_rate']
                if optimal_success > self.best_optimal_success_rate:
                    self.best_optimal_success_rate = optimal_success
                    self.log(f"  🎉 New best optimal success rate: {optimal_success:.2%}", force=True)
            
            # Save checkpoint
            if episode % save_frequency == 0 and episode > 0:
                self._save_checkpoint(episode)
            
            # Early stopping check (increased threshold)
            if self.episodes_since_improvement > 300:  # Increased from 200
                self.log("Early stopping: No improvement in 300 episodes", force=True)
                break
        
        # Final evaluation
        self.log("\nFinal Evaluation:", force=True)
        final_eval = self.evaluate_strategies(num_episodes=90)
        
        training_time = (datetime.now() - training_start).total_seconds()
        
        # Compile results
        final_results = {
            'training_episodes': self.training_state['total_episodes'],
            'episodes_trained_this_session': episode - start_episode + 1,
            'training_time': training_time,
            'best_phase2_score': self.best_phase2_score,
            'best_optimal_success_rate': self.best_optimal_success_rate,
            'final_evaluation': final_eval,
            'improvement_metrics': {
                'avg_phase2_score': np.mean(self.training_metrics['episode_phase2_scores']),
                'avg_workflow_adherence': np.mean(self.training_metrics['workflow_adherence']),
            }
        }
        
        # Save final model
        self._save_final_model(final_results)
        
        return final_results
    
    def evaluate_strategies(self, num_episodes: int = 30) -> Dict[str, Dict[str, float]]:
        """Evaluate different strategies"""
        self.log("Evaluating strategies...")
        
        # Temporarily set epsilon to 0
        old_epsilon = self.manager.trainer.epsilon
        self.manager.trainer.epsilon = 0.0
        
        results = {
            'baseline': {'success_rate': 0, 'avg_score': 0, 'scores': []},
            'optimal': {'success_rate': 0, 'avg_score': 0, 'scores': []},
            'cot': {'success_rate': 0, 'avg_score': 0, 'scores': []}
        }
        
        episodes_per_strategy = max(1, num_episodes // 3)
        
        for strategy in results.keys():
            successes = 0
            scores = []
            
            for _ in range(episodes_per_strategy):
                try:
                    state = self.manager.env.reset()
                    done = False
                    episode_scores = []
                    info = {}
                    
                    while not done and self.manager.env.episode_steps < self.manager.config['max_episode_length']:
                        valid_actions = self.manager.env.get_valid_actions() if hasattr(self.manager.env, 'get_valid_actions') else list(range(self.manager.env.num_actions))
                        
                        if not valid_actions:
                            valid_actions = [0]
                        
                        # Strategy-specific action selection
                        if strategy == 'baseline':
                            action = np.random.choice(valid_actions)
                        elif strategy == 'optimal':
                            action = self.manager.trainer.select_action(state, valid_actions)
                        else:  # cot
                            if np.random.random() < 0.3:
                                action = np.random.choice(valid_actions)
                            else:
                                action = self.manager.trainer.select_action(state, valid_actions)
                        
                        next_state, reward, done, info = self.manager.env.step(action)
                        
                        if 'phase2_metrics' in info and info['phase2_metrics']:
                            phase2_score = info['phase2_metrics'].get('phase2_score', 0)
                            episode_scores.append(phase2_score)
                        
                        state = next_state
                    
                    # Record results
                    if info.get('success', False):
                        successes += 1
                    
                    avg_score = np.mean(episode_scores) if episode_scores else 0
                    scores.append(avg_score)
                    
                except Exception as e:
                    self.log(f"Error during {strategy} evaluation: {e}", level='warning')
                    scores.append(0)
            
            # Calculate metrics
            results[strategy]['success_rate'] = successes / episodes_per_strategy if episodes_per_strategy > 0 else 0
            results[strategy]['avg_score'] = np.mean(scores) if scores else 0
            results[strategy]['scores'] = scores
            
            # Update tracking
            self.training_metrics['strategy_scores'][strategy].extend(scores)
        
        # Restore epsilon
        self.manager.trainer.epsilon = old_epsilon
        
        return results
    
    def _save_checkpoint(self, episode: int):
        """Save checkpoint with training state"""
        path = self.checkpoint_dir / f"checkpoint_ep{episode}.pt"
        
        # Update training state
        self.training_state['episodes_since_improvement'] = self.episodes_since_improvement
        
        additional_data = {
            'episode': episode,
            'best_phase2_score': self.best_phase2_score,
            'best_optimal_success_rate': self.best_optimal_success_rate,
            'training_state': self.training_state,
            'training_metrics': {
                k: list(v) if isinstance(v, deque) else v 
                for k, v in self.training_metrics.items()
            },
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            self.manager.trainer.save_checkpoint(str(path), additional_data)
            self.log(f"Saved checkpoint at episode {episode}")
        except Exception as e:
            self.log(f"Failed to save checkpoint: {e}", level='error')
    
    def _save_best_model(self, episode: int, score: float):
        """Save best model"""
        path = self.checkpoint_dir / "best_phase2_model.pt"
        
        additional_data = {
            'episode': episode,
            'best_phase2_score': score,
            'training_state': self.training_state,
            'training_metrics': {
                k: list(v) if isinstance(v, deque) else v 
                for k, v in self.training_metrics.items()
            },
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            self.manager.trainer.save_checkpoint(str(path), additional_data)
            self.log(f"Saved best model with Phase2 score: {score:.3f}", force=True)
        except Exception as e:
            self.log(f"Failed to save best model: {e}", level='error')
    
    def _save_final_model(self, results: Dict[str, Any]):
        """Save final model and results"""
        try:
            # Save model
            model_path = self.checkpoint_dir / "final_phase23_model.pt"
            self.manager.trainer.save_checkpoint(str(model_path), results)
            
            # Save results JSON
            results_path = self.checkpoint_dir / "training_results.json"
            
            # Convert for JSON serialization
            def convert_for_json(obj):
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                elif isinstance(obj, (np.float32, np.float64)):
                    return float(obj)
                elif isinstance(obj, (np.int32, np.int64)):
                    return int(obj)
                elif isinstance(obj, deque):
                    return list(obj)
                elif isinstance(obj, dict):
                    return {k: convert_for_json(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_for_json(item) for item in obj]
                return obj
            
            json_results = convert_for_json(results)
            
            with open(results_path, 'w') as f:
                json.dump(json_results, f, indent=2, default=str)
            
            self.log(f"Final model saved to {model_path}", force=True)
            self.log(f"Results saved to {results_path}", force=True)
        except Exception as e:
            self.log(f"Failed to save final model/results: {e}", level='error')


def main():
    """Main entry point with enhanced arguments"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Phase 2/3 Reinforcement Training')
    parser.add_argument('--episodes', type=int, default=500,
                       help='Number of training episodes')
    parser.add_argument('--base-model', type=str, default='checkpoints/best_model.pt',
                       help='Path to base model')
    parser.add_argument('--eval-freq', type=int, default=50,
                       help='Evaluation frequency')
    parser.add_argument('--save-freq', type=int, default=25,
                       help='Checkpoint save frequency')
    parser.add_argument('--resume', action='store_true',
                       help='Resume from checkpoint')
    parser.add_argument('--quiet', action='store_true',
                       help='Minimal output (mute verbose)')
    parser.add_argument('--test-only', action='store_true',
                       help='Only run setup test')
    
    args = parser.parse_args()
    
    # Determine verbose flag
    verbose = not args.quiet
    
    # Run setup test if requested
    if args.test_only:
        print("Running setup test...")
        # Import test function
        try:
            trainer = Phase23ReinforcementTrainer(verbose=verbose)
            if trainer.setup():
                print("✅ Setup test passed!")
                return 0
            else:
                print("❌ Setup test failed!")
                return 1
        except Exception as e:
            print(f"❌ Setup test error: {e}")
            return 1
    
    # Check if base model exists (only warn if not resuming)
    if not args.resume and not Path(args.base_model).exists():
        print(f"Warning: Base model not found at {args.base_model}")
        print("Will start training from scratch")
    
    try:
        # Create trainer
        trainer = Phase23ReinforcementTrainer(
            base_model_path=args.base_model,
            verbose=verbose
        )
        
        # Setup
        if not trainer.setup(resume=args.resume):
            print("Setup failed!")
            return 1
        
        # Train
        results = trainer.train(
            num_episodes=args.episodes,
            eval_frequency=args.eval_freq,
            save_frequency=args.save_freq,
            resume=args.resume
        )
        
        # Print summary (always show, regardless of verbose)
        print("\n" + "="*60)
        print("Training Summary")
        print("="*60)
        print(f"Total episodes: {results['training_episodes']}")
        print(f"Episodes this session: {results['episodes_trained_this_session']}")
        print(f"Training time: {results['training_time']/60:.1f} minutes")
        print(f"Best Phase2 score: {results['best_phase2_score']:.3f}")
        print(f"Best optimal success rate: {results['best_optimal_success_rate']:.2%}")
        
        print("\nFinal Strategy Performance:")
        for strategy, metrics in results['final_evaluation'].items():
            print(f"  {strategy}: {metrics['success_rate']:.2%} success, {metrics['avg_score']:.3f} avg score")
        
        print(f"\nModels saved to: {trainer.checkpoint_dir}")
        
        # Success message
        if results['best_phase2_score'] > 0.5:
            print("\n✅ Training successful! Phase 2 score improved.")
            if results['best_optimal_success_rate'] < 0.3:
                print("\n⚠️ Note: Optimal strategy still needs improvement.")
                print("Suggestions:")
                print("  1. Continue training with --resume flag")
                print("  2. Try adjusting reward weights in setup()")
                print("  3. Increase workflow_adherence_weight further")
        else:
            print("\n⚠️ Training completed but Phase 2 scores remain low.")
            print("Consider continuing training with --resume flag")
        
        return 0
        
    except Exception as e:
        print(f"Training failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
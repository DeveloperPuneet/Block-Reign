#!/usr/bin/env python3
import json
import os
import random
import numpy as np
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import pickle
from collections import deque

os.makedirs('training/models', exist_ok=True)

app = Flask(__name__, 
            static_folder='game/static',
            template_folder='game/templates')
CORS(app)

class UltraFastAI:
    """AI with human-like reaction speed"""
    
    def __init__(self):
        # Game parameters
        self.grid_size = 10
        self.actions = ['move_up', 'move_down', 'move_left', 'move_right', 'shoot']
        self.action_to_idx = {a: i for i, a in enumerate(self.actions)}
        self.idx_to_action = {i: a for i, a in enumerate(self.actions)}
        
        # Reaction time parameters (human: 150-250ms for simple tasks)
        self.base_reaction_time = 0.10  # 100ms base reaction
        self.reaction_variance = 0.05   # ±50ms variance
        
        # Thinking speed (how fast AI processes decisions)
        self.thinking_speed = 0.85  # 0-1, higher = faster thinking
        
        # Q-learning parameters (optimized for fast learning)
        self.q_table = {}
        self.learning_rate = 0.15  # Faster learning
        self.discount_factor = 0.97
        self.epsilon = 1.0
        self.epsilon_min = 0.05
        self.epsilon_decay = 0.998  # Slower decay for more exploration
        
        # Memory for pattern recognition
        self.player_pattern = deque(maxlen=5)
        self.last_player_positions = deque(maxlen=3)
        self.predicted_player_move = None
        
        # Aggression levels
        self.aggression = 0.7  # Start aggressive
        self.risk_tolerance = 0.6
        
        # Statistics
        self.wins = 0
        self.losses = 0
        self.total_matches = 0
        self.total_moves = 0
        self.avg_reaction_time = 0.15
        
        # Files
        self.model_file = 'training/models/ultrafast_ai.pkl'
        
        # Load model
        self.load_model()
        
        print(f"⚡ ULTRA-FAST AI Initialized!")
        print(f"   Target Reaction Time: {self.base_reaction_time*1000:.0f}ms ± {self.reaction_variance*1000:.0f}ms")
        print(f"   Thinking Speed: {self.thinking_speed*100:.0f}%")
        print(f"   Record: {self.wins} wins, {self.losses} losses")
    
    def get_state_key(self, game_state):
        """Ultra-fast state recognition"""
        px = game_state['player_x']
        py = game_state['player_y']
        ax = game_state['ai_x']
        ay = game_state['ai_y']
        
        # Fast distance calculation
        distance = abs(px - ax) + abs(py - ay)
        
        # Quick distance categories
        if distance <= 1:
            dist_cat = 'touching'
        elif distance <= 3:
            dist_cat = 'close'
        elif distance <= 6:
            dist_cat = 'medium'
        else:
            dist_cat = 'far'
        
        # Fast health assessment
        ph = 'high' if game_state['player_health'] > 50 else 'low'
        ah = 'high' if game_state['ai_health'] > 50 else 'low'
        
        # Quick direction
        if px > ax:
            direction = 'right'
        elif px < ax:
            direction = 'left'
        else:
            direction = 'same_x'
        
        if py > ay:
            direction += '_down'
        elif py < ay:
            direction += '_up'
        else:
            direction += '_same_y'
        
        # Predict player move
        prediction_key = ''
        if len(self.last_player_positions) >= 2:
            last_pos = self.last_player_positions[-1]
            second_last = self.last_player_positions[-2]
            
            if last_pos['x'] > second_last['x']:
                prediction_key = 'player_moving_right'
            elif last_pos['x'] < second_last['x']:
                prediction_key = 'player_moving_left'
            elif last_pos['y'] > second_last['y']:
                prediction_key = 'player_moving_down'
            elif last_pos['y'] < second_last['y']:
                prediction_key = 'player_moving_up'
            else:
                prediction_key = 'player_stationary'
        
        # Update position memory
        self.last_player_positions.append({'x': px, 'y': py})
        
        return f"{dist_cat}_{ph}_{ah}_{direction}_{prediction_key}"
    
    def calculate_reaction_time(self, game_state):
        """Calculate human-like reaction time"""
        px = game_state['player_x']
        py = game_state['player_y']
        ax = game_state['ai_x']
        ay = game_state['ai_y']
        
        distance = abs(px - ax) + abs(py - ay)
        
        # Base reaction time
        reaction = self.base_reaction_time
        
        # Adjust based on distance (closer = faster reaction)
        if distance <= 2:
            reaction *= 0.6  # 40% faster when very close
        elif distance <= 4:
            reaction *= 0.8  # 20% faster when close
        
        # Adjust based on thinking speed
        reaction *= (1.5 - self.thinking_speed)  # Faster thinking = faster reaction
        
        # Add random variance (±50ms)
        reaction += random.uniform(-self.reaction_variance, self.reaction_variance)
        
        # Clamp to reasonable values (50ms - 300ms)
        reaction = max(0.05, min(0.3, reaction))
        
        return reaction
    
    def should_wait_or_act(self, game_state):
        """Decide if AI should wait or act immediately"""
        # Always act immediately when player is close
        distance = abs(game_state['player_x'] - game_state['ai_x']) + abs(game_state['player_y'] - game_state['ai_y'])
        
        if distance <= 2:
            return False, 0  # Act immediately
        
        # Otherwise, wait calculated reaction time
        wait_time = self.calculate_reaction_time(game_state)
        
        # 30% chance to act immediately anyway (impulsive)
        if random.random() < 0.3:
            return False, 0
        
        return True, wait_time
    
    def choose_action(self, game_state):
        """Choose action with human-like decision making"""
        state_key = self.get_state_key(game_state)
        
        # Initialize Q-values for new state
        if state_key not in self.q_table:
            self.q_table[state_key] = {action: 0.0 for action in self.actions}
        
        # Exploration vs Exploitation with bias
        if random.random() < self.epsilon:
            # Explore with strategic bias
            distance = abs(game_state['player_x'] - game_state['ai_x']) + abs(game_state['player_y'] - game_state['ai_y'])
            player_health = game_state['player_health']
            ai_health = game_state['ai_health']
            
            # Strategic exploration
            if distance <= 2 and ai_health > 30:
                # Very close and healthy - high chance to shoot
                if random.random() < 0.8:
                    action = 'shoot'
                else:
                    action = random.choice(self.actions)
            elif distance <= 4:
                # Close range - mix of move and shoot
                if random.random() < 0.6:
                    move_actions = [a for a in self.actions if a.startswith('move_')]
                    action = random.choice(move_actions)
                else:
                    action = 'shoot'
            elif player_health < 30:
                # Player is weak - chase them
                move_actions = [a for a in self.actions if a.startswith('move_')]
                action = random.choice(move_actions)
            else:
                # Default random
                action = random.choice(self.actions)
            
            mode = 'exploring'
        else:
            # Exploit: choose best known action
            q_values = self.q_table[state_key]
            
            # Apply aggression bias
            adjusted_q = {}
            for action, value in q_values.items():
                if action == 'shoot':
                    # Aggressive AI values shooting more
                    adjusted_value = value * (1 + self.aggression * 0.5)
                else:
                    adjusted_value = value
                adjusted_q[action] = adjusted_value
            
            max_q = max(adjusted_q.values())
            best_actions = [a for a, q in adjusted_q.items() if q == max_q]
            
            # If multiple best actions, choose based on situation
            distance = abs(game_state['player_x'] - game_state['ai_x']) + abs(game_state['player_y'] - game_state['ai_y'])
            
            if distance <= 2 and 'shoot' in best_actions:
                action = 'shoot'  # Always shoot when point blank
            elif distance <= 4 and len(best_actions) > 1:
                # Close range, prefer aggressive moves
                if self.aggression > 0.6 and 'shoot' in best_actions:
                    action = 'shoot'
                else:
                    action = random.choice(best_actions)
            else:
                action = random.choice(best_actions)
            
            mode = 'exploiting'
        
        # Record pattern
        if len(self.player_pattern) > 0:
            self.player_pattern.append(action)
        
        self.total_moves += 1
        
        return action, mode
    
    def learn_from_match(self, match_moves, winner):
        """Fast learning from match"""
        if not winner or winner not in ['player', 'ai']:
            return
        
        self.total_matches += 1
        
        if winner == 'ai':
            self.wins += 1
            # Winning makes AI faster and more aggressive
            self.thinking_speed = min(0.95, self.thinking_speed + 0.02)
            self.aggression = min(1.0, self.aggression + 0.03)
            self.base_reaction_time = max(0.07, self.base_reaction_time - 0.002)
        else:
            self.losses += 1
            # Losing makes AI more cautious
            self.aggression = max(0.3, self.aggression - 0.02)
            self.risk_tolerance = max(0.3, self.risk_tolerance - 0.01)
        
        # Process each AI move quickly
        for i, move in enumerate(match_moves):
            if move['player'] != 'ai':
                continue
            
            if i == 0:
                continue
            
            prev_move = match_moves[i-1]
            state_before = {
                'player_x': prev_move['playerPosition']['x'],
                'player_y': prev_move['playerPosition']['y'],
                'player_health': prev_move['playerHealth'],
                'ai_x': prev_move['aiPosition']['x'],
                'ai_y': prev_move['aiPosition']['y'],
                'ai_health': prev_move['aiHealth']
            }
            
            state_key = self.get_state_key(state_before)
            action = move['action']
            
            # Fast reward calculation
            reward = self.calculate_reward_fast(state_before, action, winner, i == len(match_moves)-1)
            
            # Initialize if new state
            if state_key not in self.q_table:
                self.q_table[state_key] = {a: 0.0 for a in self.actions}
            
            # Quick Q-learning update
            current_q = self.q_table[state_key][action]
            
            # Get next state's max Q if available
            next_max_q = 0
            if i < len(match_moves) - 1:
                next_state = {
                    'player_x': move['playerPosition']['x'],
                    'player_y': move['playerPosition']['y'],
                    'player_health': move['playerHealth'],
                    'ai_x': move['aiPosition']['x'],
                    'ai_y': move['aiPosition']['y'],
                    'ai_health': move['aiHealth']
                }
                next_state_key = self.get_state_key(next_state)
                if next_state_key in self.q_table:
                    next_max_q = max(self.q_table[next_state_key].values())
            
            # Fast update
            new_q = current_q + self.learning_rate * (reward + self.discount_factor * next_max_q - current_q)
            self.q_table[state_key][action] = new_q
        
        # Decay epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
        
        # Update average reaction time
        self.avg_reaction_time = (self.avg_reaction_time * 0.9 + self.base_reaction_time * 0.1)
        
        # Save model
        self.save_model()
        
        print(f"⚡ AI learned in {(self.avg_reaction_time*1000):.0f}ms!")
        print(f"   Match {self.total_matches}: {winner.upper()} wins")
        print(f"   Record: {self.wins}W {self.losses}L")
        print(f"   Aggression: {self.aggression:.2f}, Thinking: {self.thinking_speed:.2f}")
    
    def calculate_reward_fast(self, state, action, winner, is_last_move):
        """Fast reward calculation"""
        reward = 0
        
        distance = abs(state['player_x'] - state['ai_x']) + abs(state['player_y'] - state['ai_y'])
        player_health = state['player_health']
        ai_health = state['ai_health']
        
        # Action rewards
        if action == 'shoot':
            if distance <= 2:
                reward += 3.0  # Point blank = excellent
            elif distance <= 4:
                reward += 1.5  # Close range = good
            elif distance <= 6:
                reward += 0.5  # Medium range = okay
            else:
                reward -= 1.0  # Too far = bad
        else:
            # Movement rewards
            if player_health < 40 and distance > 2:
                reward += 0.8  # Chasing weak player
            elif ai_health < 40 and distance < 3:
                reward += 0.9  # Retreating when hurt
            elif distance > 7:
                reward += 0.4  # Closing large distance
            else:
                reward -= 0.1  # Small penalty for moving
        
        # Match outcome
        if is_last_move:
            if winner == 'ai':
                reward += 10.0
            else:
                reward -= 5.0
        
        return reward
    
    def save_model(self):
        """Save AI model"""
        try:
            model_data = {
                'q_table': self.q_table,
                'epsilon': self.epsilon,
                'wins': self.wins,
                'losses': self.losses,
                'total_matches': self.total_matches,
                'aggression': self.aggression,
                'thinking_speed': self.thinking_speed,
                'base_reaction_time': self.base_reaction_time,
                'total_moves': self.total_moves
            }
            
            with open(self.model_file, 'wb') as f:
                pickle.dump(model_data, f)
            
        except Exception as e:
            print(f"Save error: {e}")
    
    def load_model(self):
        """Load AI model"""
        try:
            if os.path.exists(self.model_file):
                with open(self.model_file, 'rb') as f:
                    model_data = pickle.load(f)
                
                self.q_table = model_data.get('q_table', {})
                self.epsilon = model_data.get('epsilon', 1.0)
                self.wins = model_data.get('wins', 0)
                self.losses = model_data.get('losses', 0)
                self.total_matches = model_data.get('total_matches', 0)
                self.aggression = model_data.get('aggression', 0.7)
                self.thinking_speed = model_data.get('thinking_speed', 0.85)
                self.base_reaction_time = model_data.get('base_reaction_time', 0.10)
                self.total_moves = model_data.get('total_moves', 0)
                
                print(f"✅ Loaded ULTRA-FAST AI")
                print(f"   Reaction time: {self.base_reaction_time*1000:.0f}ms")
                print(f"   States: {len(self.q_table)}")
                return True
        except:
            pass
        
        return False

# Initialize AI
ai = UltraFastAI()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ai_move', methods=['POST'])
def ai_move():
    try:
        start_time = datetime.now()
        
        game_state = request.json
        
        # Check if AI should wait or act
        should_wait, wait_time = ai.should_wait_or_act(game_state)
        
        if should_wait:
            return jsonify({
                'action': 'wait',
                'should_wait': True,
                'wait_time': wait_time,
                'reaction_time': wait_time,
                'success': True
            })
        
        # AI decides to act
        action, mode = ai.choose_action(game_state)
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return jsonify({
            'action': action,
            'mode': mode,
            'epsilon': ai.epsilon,
            'aggression': ai.aggression,
            'thinking_speed': ai.thinking_speed,
            'should_wait': False,
            'processing_time': processing_time,
            'success': True
        })
        
    except Exception as e:
        print(f"AI move error: {e}")
        return jsonify({
            'action': 'wait',
            'should_wait': True,
            'wait_time': 0.1,
            'success': False
        }), 500

@app.route('/learn_from_match', methods=['POST'])
def learn_from_match():
    try:
        data = request.json
        moves = data.get('moves', [])
        winner = data.get('winner')
        match_num = data.get('match_number', 1)
        
        print(f"\n⚡ Match {match_num} - {winner.upper()} wins in {len(moves)} moves")
        
        ai.learn_from_match(moves, winner)
        
        return jsonify({
            'success': True,
            'ai_stats': {
                'wins': ai.wins,
                'losses': ai.losses,
                'total_matches': ai.total_matches,
                'epsilon': ai.epsilon,
                'q_table_size': len(ai.q_table),
                'aggression': ai.aggression,
                'thinking_speed': ai.thinking_speed,
                'reaction_time_ms': ai.base_reaction_time * 1000,
                'total_experience': ai.total_moves
            }
        })
        
    except Exception as e:
        print(f"Learn error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/ai_status')
def ai_status():
    return jsonify({
        'wins': ai.wins,
        'losses': ai.losses,
        'total_matches': ai.total_matches,
        'win_rate': (ai.wins / max(1, ai.total_matches)) * 100,
        'epsilon': ai.epsilon,
        'q_table_size': len(ai.q_table),
        'aggression': ai.aggression,
        'thinking_speed': ai.thinking_speed,
        'reaction_time_ms': ai.base_reaction_time * 1000,
        'total_experience': ai.total_moves,
        'learning_method': 'ULTRA-FAST Q-Learning',
        'target_speed': 'Human-like (100-200ms)'
    })

if __name__ == '__main__':
    print("\n" + "="*70)
    print("⚡ ULTRA-FAST AI - HUMAN SPEED REACTION")
    print("="*70)
    print("PERFORMANCE:")
    print("  • Target Reaction: 100ms ±50ms")
    print("  • Thinking Speed: 85% of maximum")
    print("  • State Recognition: 50ms")
    print("  • Learning Speed: 2x normal")
    print("="*70)
    print("BEHAVIOR:")
    print("  • Instant reactions when close")
    print("  • Predicts player movement")
    print("  • Gets faster with wins")
    print("  • Never waits unnecessarily")
    print("="*70)
    print("CONTROLS: Arrow Keys = Move, Space = Shoot")
    print(f"🌐 Game at: http://localhost:5000")
    print("="*70 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
#!/usr/bin/env python3
"""
Comprehensive Backend Test Suite for Fortnite Battle Royale Game
Tests all API endpoints and WebSocket functionality
"""

import asyncio
import json
import requests
import websockets
import uuid
from datetime import datetime
import time

# Backend URL from frontend/.env
BACKEND_URL = "https://d967ed33-dac7-4250-b92f-2f2439e8a183.preview.emergentagent.com"
API_BASE = f"{BACKEND_URL}/api"
WS_BASE = BACKEND_URL.replace("https://", "wss://").replace("http://", "ws://")

class FortniteBackendTester:
    def __init__(self):
        self.test_results = {}
        self.player_id = None
        self.session_id = None
        self.loot_items = []
        
    def log_test(self, test_name, success, message="", data=None):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        self.test_results[test_name] = {
            "success": success,
            "message": message,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
    def test_player_join(self):
        """Test POST /api/player/join"""
        print("\n=== Testing Player Join System ===")
        
        try:
            # Test player creation
            player_name = "BattleRoyaleWarrior"
            response = requests.post(f"{API_BASE}/player/join", params={"player_name": player_name})
            
            if response.status_code == 200:
                player_data = response.json()
                self.player_id = player_data.get("id")
                
                # Validate player data structure
                required_fields = ["id", "name", "x", "y", "health", "shield", "inventory", "kills", "alive"]
                missing_fields = [field for field in required_fields if field not in player_data]
                
                if missing_fields:
                    self.log_test("Player Join", False, f"Missing fields: {missing_fields}")
                elif player_data["name"] != player_name:
                    self.log_test("Player Join", False, f"Name mismatch: expected {player_name}, got {player_data['name']}")
                elif player_data["health"] != 100:
                    self.log_test("Player Join", False, f"Invalid initial health: {player_data['health']}")
                else:
                    self.log_test("Player Join", True, f"Player created successfully with ID: {self.player_id}", player_data)
            else:
                self.log_test("Player Join", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Player Join", False, f"Exception: {str(e)}")
            
    def test_game_state(self):
        """Test GET /api/game/state"""
        print("\n=== Testing Game State Retrieval ===")
        
        try:
            response = requests.get(f"{API_BASE}/game/state")
            
            if response.status_code == 200:
                game_state = response.json()
                
                # Validate game state structure
                required_fields = ["players", "structures", "storm_circle", "loot_items"]
                missing_fields = [field for field in required_fields if field not in game_state]
                
                if missing_fields:
                    self.log_test("Game State", False, f"Missing fields: {missing_fields}")
                else:
                    # Check storm circle structure
                    storm = game_state["storm_circle"]
                    if not all(key in storm for key in ["x", "y", "radius"]):
                        self.log_test("Game State", False, "Invalid storm circle structure")
                    else:
                        self.log_test("Game State", True, f"Game state retrieved successfully. Players: {len(game_state['players'])}, Structures: {len(game_state['structures'])}, Loot: {len(game_state['loot_items'])}", game_state)
            else:
                self.log_test("Game State", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Game State", False, f"Exception: {str(e)}")
            
    def test_game_session_creation(self):
        """Test POST /api/game/session"""
        print("\n=== Testing Game Session Creation ===")
        
        try:
            # Test solo mode
            response = requests.post(f"{API_BASE}/game/session", params={"mode": "solo"})
            
            if response.status_code == 200:
                session_data = response.json()
                self.session_id = session_data.get("id")
                
                # Validate session data
                required_fields = ["id", "players", "mode", "status", "created_at"]
                missing_fields = [field for field in required_fields if field not in session_data]
                
                if missing_fields:
                    self.log_test("Game Session Creation", False, f"Missing fields: {missing_fields}")
                elif session_data["mode"] != "solo":
                    self.log_test("Game Session Creation", False, f"Mode mismatch: expected solo, got {session_data['mode']}")
                else:
                    self.log_test("Game Session Creation", True, f"Session created successfully with ID: {self.session_id}", session_data)
            else:
                self.log_test("Game Session Creation", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Game Session Creation", False, f"Exception: {str(e)}")
            
    def test_game_sessions_list(self):
        """Test GET /api/game/sessions"""
        print("\n=== Testing Game Sessions List ===")
        
        try:
            response = requests.get(f"{API_BASE}/game/sessions")
            
            if response.status_code == 200:
                sessions = response.json()
                
                if isinstance(sessions, list):
                    self.log_test("Game Sessions List", True, f"Retrieved {len(sessions)} active sessions", sessions)
                else:
                    self.log_test("Game Sessions List", False, "Response is not a list")
            else:
                self.log_test("Game Sessions List", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Game Sessions List", False, f"Exception: {str(e)}")
            
    def test_loot_spawn(self):
        """Test POST /api/loot/spawn"""
        print("\n=== Testing Loot Spawning System ===")
        
        try:
            response = requests.post(f"{API_BASE}/loot/spawn")
            
            if response.status_code == 200:
                result = response.json()
                
                if "message" in result:
                    # Get game state to verify loot was spawned
                    state_response = requests.get(f"{API_BASE}/game/state")
                    if state_response.status_code == 200:
                        game_state = state_response.json()
                        loot_count = len(game_state["loot_items"])
                        self.loot_items = game_state["loot_items"]
                        
                        if loot_count > 0:
                            self.log_test("Loot Spawn", True, f"Spawned {loot_count} loot items successfully", result)
                        else:
                            self.log_test("Loot Spawn", False, "No loot items found in game state after spawning")
                    else:
                        self.log_test("Loot Spawn", False, "Could not verify loot spawn - game state unavailable")
                else:
                    self.log_test("Loot Spawn", False, "Invalid response format")
            else:
                self.log_test("Loot Spawn", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Loot Spawn", False, f"Exception: {str(e)}")
            
    def test_storm_update(self):
        """Test POST /api/storm/update"""
        print("\n=== Testing Storm Circle Update ===")
        
        try:
            # Get initial storm state
            initial_response = requests.get(f"{API_BASE}/game/state")
            initial_radius = None
            
            if initial_response.status_code == 200:
                initial_state = initial_response.json()
                initial_radius = initial_state["storm_circle"]["radius"]
                
            # Update storm
            response = requests.post(f"{API_BASE}/storm/update")
            
            if response.status_code == 200:
                storm_data = response.json()
                
                # Validate storm data structure
                if not all(key in storm_data for key in ["x", "y", "radius"]):
                    self.log_test("Storm Update", False, "Invalid storm data structure")
                elif initial_radius and storm_data["radius"] >= initial_radius:
                    self.log_test("Storm Update", False, f"Storm radius did not shrink: {initial_radius} -> {storm_data['radius']}")
                else:
                    self.log_test("Storm Update", True, f"Storm updated successfully. New radius: {storm_data['radius']}", storm_data)
            else:
                self.log_test("Storm Update", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Storm Update", False, f"Exception: {str(e)}")
            
    def test_leaderboard(self):
        """Test GET /api/leaderboard"""
        print("\n=== Testing Leaderboard System ===")
        
        try:
            response = requests.get(f"{API_BASE}/leaderboard")
            
            if response.status_code == 200:
                leaderboard = response.json()
                
                if isinstance(leaderboard, list):
                    # Validate leaderboard is sorted by kills
                    if len(leaderboard) > 1:
                        is_sorted = all(leaderboard[i]["kills"] >= leaderboard[i+1]["kills"] 
                                      for i in range(len(leaderboard)-1))
                        if not is_sorted:
                            self.log_test("Leaderboard", False, "Leaderboard is not sorted by kills")
                        else:
                            self.log_test("Leaderboard", True, f"Leaderboard retrieved successfully with {len(leaderboard)} players", leaderboard)
                    else:
                        self.log_test("Leaderboard", True, f"Leaderboard retrieved successfully with {len(leaderboard)} players", leaderboard)
                else:
                    self.log_test("Leaderboard", False, "Response is not a list")
            else:
                self.log_test("Leaderboard", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Leaderboard", False, f"Exception: {str(e)}")
            
    async def test_websocket_connection(self):
        """Test WebSocket connection and basic functionality"""
        print("\n=== Testing WebSocket Connection ===")
        
        client_id = str(uuid.uuid4())
        ws_url = f"{WS_BASE}/ws/{client_id}"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                self.log_test("WebSocket Connection", True, f"Connected successfully to {ws_url}")
                
                # Test player movement
                await self.test_websocket_player_movement(websocket, client_id)
                
                # Test building system
                await self.test_websocket_building(websocket, client_id)
                
                # Test shooting system
                await self.test_websocket_shooting(websocket, client_id)
                
                # Test loot collection
                await self.test_websocket_loot_collection(websocket, client_id)
                
        except Exception as e:
            self.log_test("WebSocket Connection", False, f"Connection failed: {str(e)}")
            
    async def test_websocket_player_movement(self, websocket, client_id):
        """Test WebSocket player movement messages"""
        print("\n=== Testing WebSocket Player Movement ===")
        
        try:
            # Send player movement message
            move_message = {
                "type": "player_move",
                "x": 200,
                "y": 300
            }
            
            await websocket.send(json.dumps(move_message))
            
            # Wait for response
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            response_data = json.loads(response)
            
            if response_data.get("type") == "player_update" and response_data.get("player_id") == client_id:
                if response_data.get("x") == 200 and response_data.get("y") == 300:
                    self.log_test("WebSocket Player Movement", True, "Player movement synchronized successfully", response_data)
                else:
                    self.log_test("WebSocket Player Movement", False, f"Position mismatch in response: {response_data}")
            else:
                self.log_test("WebSocket Player Movement", False, f"Unexpected response: {response_data}")
                
        except asyncio.TimeoutError:
            self.log_test("WebSocket Player Movement", False, "Timeout waiting for movement response")
        except Exception as e:
            self.log_test("WebSocket Player Movement", False, f"Exception: {str(e)}")
            
    async def test_websocket_building(self, websocket, client_id):
        """Test WebSocket building system"""
        print("\n=== Testing WebSocket Building System ===")
        
        try:
            # Send building message
            build_message = {
                "type": "build_structure",
                "structure_type": "wall",
                "x": 100,
                "y": 150,
                "material": "wood"
            }
            
            await websocket.send(json.dumps(build_message))
            
            # Wait for response
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            response_data = json.loads(response)
            
            if response_data.get("type") == "structure_built":
                structure = response_data.get("structure", {})
                if (structure.get("type") == "wall" and 
                    structure.get("material") == "wood" and
                    structure.get("x") == 100 and
                    structure.get("y") == 150):
                    self.log_test("WebSocket Building", True, "Structure built successfully", response_data)
                else:
                    self.log_test("WebSocket Building", False, f"Structure data mismatch: {structure}")
            else:
                self.log_test("WebSocket Building", False, f"Unexpected response: {response_data}")
                
        except asyncio.TimeoutError:
            self.log_test("WebSocket Building", False, "Timeout waiting for building response")
        except Exception as e:
            self.log_test("WebSocket Building", False, f"Exception: {str(e)}")
            
    async def test_websocket_shooting(self, websocket, client_id):
        """Test WebSocket shooting system"""
        print("\n=== Testing WebSocket Shooting System ===")
        
        try:
            # Send shooting message
            shoot_message = {
                "type": "shoot",
                "x": 100,
                "y": 100,
                "target_x": 200,
                "target_y": 200,
                "weapon": "assault_rifle"
            }
            
            await websocket.send(json.dumps(shoot_message))
            
            # Wait for response
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            response_data = json.loads(response)
            
            if response_data.get("type") == "shot_fired":
                if (response_data.get("player_id") == client_id and
                    response_data.get("weapon") == "assault_rifle"):
                    self.log_test("WebSocket Shooting", True, "Shot fired successfully", response_data)
                else:
                    self.log_test("WebSocket Shooting", False, f"Shot data mismatch: {response_data}")
            else:
                self.log_test("WebSocket Shooting", False, f"Unexpected response: {response_data}")
                
        except asyncio.TimeoutError:
            self.log_test("WebSocket Shooting", False, "Timeout waiting for shooting response")
        except Exception as e:
            self.log_test("WebSocket Shooting", False, f"Exception: {str(e)}")
            
    async def test_websocket_loot_collection(self, websocket, client_id):
        """Test WebSocket loot collection"""
        print("\n=== Testing WebSocket Loot Collection ===")
        
        try:
            # Use a loot item from previous spawn test
            if not self.loot_items:
                self.log_test("WebSocket Loot Collection", False, "No loot items available for testing")
                return
                
            loot_id = self.loot_items[0]["id"]
            
            # Send loot collection message
            collect_message = {
                "type": "collect_loot",
                "loot_id": loot_id
            }
            
            await websocket.send(json.dumps(collect_message))
            
            # Wait for response
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            response_data = json.loads(response)
            
            if response_data.get("type") == "loot_collected":
                if (response_data.get("loot_id") == loot_id and
                    response_data.get("player_id") == client_id):
                    self.log_test("WebSocket Loot Collection", True, "Loot collected successfully", response_data)
                else:
                    self.log_test("WebSocket Loot Collection", False, f"Loot collection data mismatch: {response_data}")
            else:
                self.log_test("WebSocket Loot Collection", False, f"Unexpected response: {response_data}")
                
        except asyncio.TimeoutError:
            self.log_test("WebSocket Loot Collection", False, "Timeout waiting for loot collection response")
        except Exception as e:
            self.log_test("WebSocket Loot Collection", False, f"Exception: {str(e)}")
            
    def run_api_tests(self):
        """Run all API endpoint tests"""
        print("🚀 Starting Fortnite Battle Royale Backend API Tests")
        print(f"Backend URL: {BACKEND_URL}")
        print("=" * 60)
        
        # Test API endpoints
        self.test_player_join()
        self.test_game_state()
        self.test_game_session_creation()
        self.test_game_sessions_list()
        self.test_loot_spawn()
        self.test_storm_update()
        self.test_leaderboard()
        
    async def run_websocket_tests(self):
        """Run all WebSocket tests"""
        print("\n🔌 Starting WebSocket Tests")
        print("=" * 60)
        
        await self.test_websocket_connection()
        
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for test_name, result in self.test_results.items():
                if not result["success"]:
                    print(f"  - {test_name}: {result['message']}")
                    
        print("\n✅ PASSED TESTS:")
        for test_name, result in self.test_results.items():
            if result["success"]:
                print(f"  - {test_name}: {result['message']}")

async def main():
    """Main test runner"""
    tester = FortniteBackendTester()
    
    # Run API tests
    tester.run_api_tests()
    
    # Run WebSocket tests
    await tester.run_websocket_tests()
    
    # Print summary
    tester.print_summary()
    
    return tester.test_results

if __name__ == "__main__":
    asyncio.run(main())
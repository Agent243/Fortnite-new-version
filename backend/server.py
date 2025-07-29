from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import json
import asyncio
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import uuid
from datetime import datetime


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# WebSocket connection manager for real-time multiplayer
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.game_state = {
            "players": {},
            "structures": [],
            "storm_circle": {"x": 500, "y": 500, "radius": 800},
            "loot_items": []
        }
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
        
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()

# Data models
class Player(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    x: float = 100
    y: float = 100
    health: int = 100
    shield: int = 0
    inventory: Dict = Field(default_factory=dict)
    kills: int = 0
    alive: bool = True
    team_id: Optional[str] = None

class GameStructure(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str  # wall, ramp, floor, roof
    x: int
    y: int
    material: str  # wood, stone, metal
    health: int = 100
    player_id: str

class LootItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str  # weapon, ammo, healing, material
    name: str
    x: float
    y: float
    rarity: str = "common"  # common, uncommon, rare, epic, legendary
    quantity: int = 1

class GameSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    players: List[str] = Field(default_factory=list)
    mode: str = "solo"  # solo, duo, squad
    status: str = "waiting"  # waiting, active, finished
    created_at: datetime = Field(default_factory=datetime.utcnow)
    winner: Optional[str] = None

# WebSocket endpoint for real-time gameplay
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "player_move":
                # Update player position
                if client_id in manager.game_state["players"]:
                    manager.game_state["players"][client_id]["x"] = message["x"]
                    manager.game_state["players"][client_id]["y"] = message["y"]
                    await manager.broadcast(json.dumps({
                        "type": "player_update",
                        "player_id": client_id,
                        "x": message["x"],
                        "y": message["y"]
                    }))
                    
            elif message["type"] == "build_structure":
                # Add building structure
                structure = {
                    "id": str(uuid.uuid4()),
                    "type": message["structure_type"],
                    "x": message["x"],
                    "y": message["y"],
                    "material": message["material"],
                    "health": 100,
                    "player_id": client_id
                }
                manager.game_state["structures"].append(structure)
                await manager.broadcast(json.dumps({
                    "type": "structure_built",
                    "structure": structure
                }))
                
            elif message["type"] == "shoot":
                # Handle shooting/combat
                await manager.broadcast(json.dumps({
                    "type": "shot_fired",
                    "player_id": client_id,
                    "x": message["x"],
                    "y": message["y"],
                    "target_x": message["target_x"],
                    "target_y": message["target_y"],
                    "weapon": message["weapon"]
                }))
                
            elif message["type"] == "collect_loot":
                # Handle loot collection
                loot_id = message["loot_id"]
                manager.game_state["loot_items"] = [
                    item for item in manager.game_state["loot_items"] 
                    if item["id"] != loot_id
                ]
                await manager.broadcast(json.dumps({
                    "type": "loot_collected",
                    "loot_id": loot_id,
                    "player_id": client_id
                }))

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        if client_id in manager.game_state["players"]:
            del manager.game_state["players"][client_id]
        await manager.broadcast(json.dumps({
            "type": "player_disconnected",
            "player_id": client_id
        }))

# API endpoints
@api_router.post("/player/join", response_model=Player)
async def join_game(player_name: str):
    player = Player(name=player_name)
    
    # Add player to game state
    manager.game_state["players"][player.id] = {
        "id": player.id,
        "name": player.name,
        "x": player.x,
        "y": player.y,
        "health": player.health,
        "shield": player.shield,
        "inventory": player.inventory,
        "kills": player.kills,
        "alive": player.alive
    }
    
    # Save to database
    await db.players.insert_one(player.dict())
    return player

@api_router.get("/game/state")
async def get_game_state():
    return manager.game_state

@api_router.post("/game/session", response_model=GameSession)
async def create_game_session(mode: str = "solo"):
    session = GameSession(mode=mode)
    await db.game_sessions.insert_one(session.dict())
    return session

@api_router.get("/game/sessions", response_model=List[GameSession])
async def get_game_sessions():
    sessions = await db.game_sessions.find({"status": {"$ne": "finished"}}).to_list(10)
    return [GameSession(**session) for session in sessions]

@api_router.post("/loot/spawn")
async def spawn_loot():
    # Generate random loot items across the map
    import random
    
    loot_types = [
        {"type": "weapon", "name": "Assault Rifle", "rarity": "uncommon"},
        {"type": "weapon", "name": "Shotgun", "rarity": "common"},
        {"type": "weapon", "name": "Sniper Rifle", "rarity": "rare"},
        {"type": "healing", "name": "Bandages", "rarity": "common"},
        {"type": "healing", "name": "Med Kit", "rarity": "uncommon"},
        {"type": "material", "name": "Wood", "rarity": "common"},
        {"type": "material", "name": "Stone", "rarity": "common"},
        {"type": "material", "name": "Metal", "rarity": "uncommon"}
    ]
    
    for _ in range(50):  # Spawn 50 random loot items
        loot_template = random.choice(loot_types)
        loot = {
            "id": str(uuid.uuid4()),
            "type": loot_template["type"],
            "name": loot_template["name"],
            "x": random.uniform(50, 950),
            "y": random.uniform(50, 950),
            "rarity": loot_template["rarity"],
            "quantity": random.randint(1, 5) if loot_template["type"] == "material" else 1
        }
        manager.game_state["loot_items"].append(loot)
    
    await manager.broadcast(json.dumps({
        "type": "loot_spawned",
        "loot_items": manager.game_state["loot_items"]
    }))
    
    return {"message": "Loot spawned successfully"}

@api_router.post("/storm/update")
async def update_storm():
    # Shrink the storm circle
    current_radius = manager.game_state["storm_circle"]["radius"]
    new_radius = max(50, current_radius - 50)  # Minimum radius of 50
    
    manager.game_state["storm_circle"]["radius"] = new_radius
    
    await manager.broadcast(json.dumps({
        "type": "storm_update",
        "storm_circle": manager.game_state["storm_circle"]
    }))
    
    return manager.game_state["storm_circle"]

@api_router.get("/leaderboard")
async def get_leaderboard():
    players = list(manager.game_state["players"].values())
    leaderboard = sorted(players, key=lambda x: x["kills"], reverse=True)
    return leaderboard[:10]  # Top 10 players

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

# Storm shrinking task
async def storm_shrinking_task():
    while True:
        await asyncio.sleep(30)  # Every 30 seconds
        if manager.game_state["storm_circle"]["radius"] > 50:
            await update_storm()

# Start background tasks
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(storm_shrinking_task())
import React, { useState, useEffect, useRef, useCallback } from 'react';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;
const WS_URL = BACKEND_URL.replace('http', 'ws');

function App() {
  const canvasRef = useRef(null);
  const wsRef = useRef(null);
  const gameStateRef = useRef({
    player: {
      id: null,
      name: '',
      x: 100,
      y: 100,
      health: 100,
      shield: 0,
      inventory: {
        weapons: [],
        materials: { wood: 0, stone: 0, metal: 0 },
        healing: []
      },
      selectedWeapon: null,
      selectedMaterial: 'wood'
    },
    players: {},
    structures: [],
    lootItems: [],
    stormCircle: { x: 500, y: 500, radius: 800 },
    gamepadIndex: -1,
    keys: {},
    mouse: { x: 0, y: 0, clicked: false },
    buildMode: false,
    selectedBuildType: 'wall'
  });

  const [gameState, setGameState] = useState(gameStateRef.current);
  const [gameStarted, setGameStarted] = useState(false);
  const [playerName, setPlayerName] = useState('');
  const [showInventory, setShowInventory] = useState(false);
  const [killCount, setKillCount] = useState(0);
  const [playersAlive, setPlayersAlive] = useState(100);

  // Initialize gamepad support
  useEffect(() => {
    const detectGamepad = () => {
      const gamepads = navigator.getGamepads();
      for (let i = 0; i < gamepads.length; i++) {
        if (gamepads[i]) {
          gameStateRef.current.gamepadIndex = i;
          console.log(`Gamepad detected: ${gamepads[i].id}`);
          break;
        }
      }
    };

    window.addEventListener('gamepadconnected', detectGamepad);
    window.addEventListener('gamepaddisconnected', () => {
      gameStateRef.current.gamepadIndex = -1;
    });

    detectGamepad();
    return () => {
      window.removeEventListener('gamepadconnected', detectGamepad);
      window.removeEventListener('gamepaddisconnected', detectGamepad);
    };
  }, []);

  // Keyboard controls
  useEffect(() => {
    const handleKeyDown = (e) => {
      gameStateRef.current.keys[e.key.toLowerCase()] = true;
      
      // Toggle build mode
      if (e.key === 'B' || e.key === 'b') {
        gameStateRef.current.buildMode = !gameStateRef.current.buildMode;
        setGameState({...gameStateRef.current});
      }
      
      // Change build type
      if (gameStateRef.current.buildMode) {
        switch(e.key) {
          case '1': gameStateRef.current.selectedBuildType = 'wall'; break;
          case '2': gameStateRef.current.selectedBuildType = 'ramp'; break;
          case '3': gameStateRef.current.selectedBuildType = 'floor'; break;
          case '4': gameStateRef.current.selectedBuildType = 'roof'; break;
        }
      }
      
      // Toggle inventory
      if (e.key === 'Tab') {
        e.preventDefault();
        setShowInventory(!showInventory);
      }
    };

    const handleKeyUp = (e) => {
      gameStateRef.current.keys[e.key.toLowerCase()] = false;
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, [showInventory]);

  // Mouse controls
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const handleMouseMove = (e) => {
      const rect = canvas.getBoundingClientRect();
      gameStateRef.current.mouse.x = e.clientX - rect.left;
      gameStateRef.current.mouse.y = e.clientY - rect.top;
    };

    const handleMouseClick = (e) => {
      if (!gameStarted) return;
      
      const rect = canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;
      
      if (gameStateRef.current.buildMode) {
        // Build structure
        const worldX = Math.floor((gameStateRef.current.player.x + mouseX - 400) / 50) * 50;
        const worldY = Math.floor((gameStateRef.current.player.y + mouseY - 300) / 50) * 50;
        
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({
            type: 'build_structure',
            structure_type: gameStateRef.current.selectedBuildType,
            x: worldX,
            y: worldY,
            material: gameStateRef.current.player.selectedMaterial
          }));
        }
      } else {
        // Shoot
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({
            type: 'shoot',
            x: gameStateRef.current.player.x,
            y: gameStateRef.current.player.y,
            target_x: gameStateRef.current.player.x + mouseX - 400,
            target_y: gameStateRef.current.player.y + mouseY - 300,
            weapon: gameStateRef.current.player.selectedWeapon
          }));
        }
      }
    };

    canvas.addEventListener('mousemove', handleMouseMove);
    canvas.addEventListener('click', handleMouseClick);

    return () => {
      canvas.addEventListener('mousemove', handleMouseMove);
      canvas.addEventListener('click', handleMouseClick);
    };
  }, [gameStarted]);

  // Game loop with gamepad support
  useEffect(() => {
    if (!gameStarted) return;

    const gameLoop = () => {
      const state = gameStateRef.current;
      let moved = false;
      
      // Handle gamepad input
      if (state.gamepadIndex >= 0) {
        const gamepad = navigator.getGamepads()[state.gamepadIndex];
        if (gamepad) {
          // Left stick for movement
          const leftStickX = gamepad.axes[0];
          const leftStickY = gamepad.axes[1];
          
          if (Math.abs(leftStickX) > 0.1) {
            state.player.x += leftStickX * 3;
            moved = true;
          }
          if (Math.abs(leftStickY) > 0.1) {
            state.player.y += leftStickY * 3;
            moved = true;
          }
          
          // Buttons
          if (gamepad.buttons[0].pressed) { // X/Cross - Jump/Build
            if (state.buildMode) {
              // Build at player position
              if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify({
                  type: 'build_structure',
                  structure_type: state.selectedBuildType,
                  x: Math.floor(state.player.x / 50) * 50,
                  y: Math.floor(state.player.y / 50) * 50,
                  material: state.player.selectedMaterial
                }));
              }
            }
          }
          
          if (gamepad.buttons[1].pressed) { // Circle - Toggle build mode
            state.buildMode = !state.buildMode;
          }
          
          // Right trigger for shooting
          if (gamepad.buttons[7].pressed) {
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify({
                type: 'shoot',
                x: state.player.x,
                y: state.player.y,
                target_x: state.player.x + 100,
                target_y: state.player.y,
                weapon: state.player.selectedWeapon
              }));
            }
          }
        }
      }
      
      // Handle keyboard input
      if (state.keys['w'] || state.keys['arrowup']) {
        state.player.y -= 3;
        moved = true;
      }
      if (state.keys['s'] || state.keys['arrowdown']) {
        state.player.y += 3;
        moved = true;
      }
      if (state.keys['a'] || state.keys['arrowleft']) {
        state.player.x -= 3;
        moved = true;
      }
      if (state.keys['d'] || state.keys['arrowright']) {
        state.player.x += 3;
        moved = true;
      }
      
      // Boundary checking
      state.player.x = Math.max(0, Math.min(1000, state.player.x));
      state.player.y = Math.max(0, Math.min(1000, state.player.y));
      
      // Send movement update
      if (moved && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'player_move',
          x: state.player.x,
          y: state.player.y
        }));
      }
      
      // Check storm damage
      const distanceFromCenter = Math.sqrt(
        Math.pow(state.player.x - state.stormCircle.x, 2) + 
        Math.pow(state.player.y - state.stormCircle.y, 2)
      );
      
      if (distanceFromCenter > state.stormCircle.radius) {
        state.player.health = Math.max(0, state.player.health - 1);
        if (state.player.health <= 0) {
          // Player died from storm
          console.log('Player died from storm!');
        }
      }
      
      renderGame();
    };

    const interval = setInterval(gameLoop, 16); // 60 FPS
    return () => clearInterval(interval);
  }, [gameStarted]);

  // Render game
  const renderGame = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const state = gameStateRef.current;
    
    // Clear canvas
    ctx.fillStyle = '#87CEEB'; // Sky blue
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Draw map background
    ctx.fillStyle = '#228B22'; // Forest green
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Camera offset (player centered)
    const offsetX = 400 - state.player.x;
    const offsetY = 300 - state.player.y;
    
    ctx.save();
    ctx.translate(offsetX, offsetY);
    
    // Draw storm circle
    ctx.strokeStyle = '#800080';
    ctx.lineWidth = 5;
    ctx.beginPath();
    ctx.arc(state.stormCircle.x, state.stormCircle.y, state.stormCircle.radius, 0, 2 * Math.PI);
    ctx.stroke();
    
    // Fill area outside storm with purple tint
    ctx.fillStyle = 'rgba(128, 0, 128, 0.3)';
    ctx.fillRect(-1000, -1000, 3000, 3000);
    
    // Cut out the safe zone
    ctx.globalCompositeOperation = 'destination-out';
    ctx.beginPath();
    ctx.arc(state.stormCircle.x, state.stormCircle.y, state.stormCircle.radius, 0, 2 * Math.PI);
    ctx.fill();
    ctx.globalCompositeOperation = 'source-over';
    
    // Draw grid for building
    if (state.buildMode) {
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
      ctx.lineWidth = 1;
      for (let x = 0; x < 1000; x += 50) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, 1000);
        ctx.stroke();
      }
      for (let y = 0; y < 1000; y += 50) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(1000, y);
        ctx.stroke();
      }
    }
    
    // Draw structures
    state.structures.forEach(structure => {
      switch (structure.material) {
        case 'wood': ctx.fillStyle = '#8B4513'; break;
        case 'stone': ctx.fillStyle = '#696969'; break;
        case 'metal': ctx.fillStyle = '#C0C0C0'; break;
        default: ctx.fillStyle = '#8B4513';
      }
      
      ctx.fillRect(structure.x, structure.y, 50, 50);
      
      // Draw structure type indicator
      ctx.fillStyle = 'white';
      ctx.font = '12px Arial';
      ctx.textAlign = 'center';
      const typeChar = structure.type[0].toUpperCase();
      ctx.fillText(typeChar, structure.x + 25, structure.y + 30);
    });
    
    // Draw loot items
    state.lootItems.forEach(item => {
      const rarityColors = {
        common: '#ffffff',
        uncommon: '#00ff00',
        rare: '#0080ff',
        epic: '#8000ff',
        legendary: '#ff8000'
      };
      
      ctx.fillStyle = rarityColors[item.rarity] || '#ffffff';
      ctx.fillRect(item.x - 5, item.y - 5, 10, 10);
      
      // Draw item name
      ctx.fillStyle = 'white';
      ctx.font = '10px Arial';
      ctx.textAlign = 'center';
      ctx.fillText(item.name, item.x, item.y - 10);
    });
    
    // Draw other players
    Object.values(state.players).forEach(player => {
      if (player.id !== state.player.id) {
        ctx.fillStyle = '#ff0000'; // Red for other players
        ctx.fillRect(player.x - 10, player.y - 10, 20, 20);
        
        // Player name
        ctx.fillStyle = 'white';
        ctx.font = '12px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(player.name, player.x, player.y - 15);
        
        // Health bar
        ctx.fillStyle = 'red';
        ctx.fillRect(player.x - 15, player.y - 25, 30, 5);
        ctx.fillStyle = 'green';
        ctx.fillRect(player.x - 15, player.y - 25, (player.health / 100) * 30, 5);
      }
    });
    
    // Draw current player
    ctx.fillStyle = '#0000ff'; // Blue for current player
    ctx.fillRect(state.player.x - 10, state.player.y - 10, 20, 20);
    
    // Player name
    ctx.fillStyle = 'white';
    ctx.font = '12px Arial';
    ctx.textAlign = 'center';
    ctx.fillText(state.player.name, state.player.x, state.player.y - 15);
    
    // Crosshair
    if (!state.buildMode) {
      ctx.strokeStyle = 'white';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(state.player.x + state.mouse.x - 405, state.player.y + state.mouse.y - 305);
      ctx.lineTo(state.player.x + state.mouse.x - 395, state.player.y + state.mouse.y - 295);
      ctx.moveTo(state.player.x + state.mouse.x - 395, state.player.y + state.mouse.y - 305);
      ctx.lineTo(state.player.x + state.mouse.x - 405, state.player.y + state.mouse.y - 295);
      ctx.stroke();
    }
    
    ctx.restore();
    
    // Draw UI elements (fixed position)
    drawUI(ctx);
  }, []);

  const drawUI = (ctx) => {
    const state = gameStateRef.current;
    
    // Health and shield bar
    ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
    ctx.fillRect(10, 550, 200, 40);
    
    // Health bar
    ctx.fillStyle = 'red';
    ctx.fillRect(15, 555, 90, 15);
    ctx.fillStyle = 'green';
    ctx.fillRect(15, 555, (state.player.health / 100) * 90, 15);
    
    // Shield bar
    ctx.fillStyle = 'gray';
    ctx.fillRect(15, 575, 90, 15);
    ctx.fillStyle = 'blue';
    ctx.fillRect(15, 575, (state.player.shield / 100) * 90, 15);
    
    // Health/Shield text
    ctx.fillStyle = 'white';
    ctx.font = '12px Arial';
    ctx.fillText(`Health: ${state.player.health}`, 110, 567);
    ctx.fillText(`Shield: ${state.player.shield}`, 110, 587);
    
    // Materials count
    ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
    ctx.fillRect(220, 550, 150, 40);
    ctx.fillStyle = 'white';
    ctx.font = '10px Arial';
    ctx.fillText(`Wood: ${state.player.inventory.materials.wood}`, 225, 565);
    ctx.fillText(`Stone: ${state.player.inventory.materials.stone}`, 225, 577);
    ctx.fillText(`Metal: ${state.player.inventory.materials.metal}`, 225, 589);
    
    // Build mode indicator
    if (state.buildMode) {
      ctx.fillStyle = 'rgba(255, 255, 0, 0.8)';
      ctx.fillRect(380, 550, 120, 40);
      ctx.fillStyle = 'black';
      ctx.font = '14px Arial';
      ctx.fillText('BUILD MODE', 385, 567);
      ctx.fillText(`Type: ${state.selectedBuildType}`, 385, 582);
    }
    
    // Kill count and players alive
    ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
    ctx.fillRect(650, 10, 140, 40);
    ctx.fillStyle = 'white';
    ctx.font = '12px Arial';
    ctx.fillText(`Kills: ${killCount}`, 655, 25);
    ctx.fillText(`Players: ${playersAlive}`, 655, 40);
    
    // Storm timer
    ctx.fillText('Storm shrinking...', 655, 55);
    
    // Controls help
    ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
    ctx.fillRect(10, 10, 200, 80);
    ctx.fillStyle = 'white';
    ctx.font = '10px Arial';
    ctx.fillText('WASD/Arrows: Move', 15, 25);
    ctx.fillText('Mouse: Aim/Build', 15, 37);
    ctx.fillText('Click: Shoot/Build', 15, 49);
    ctx.fillText('B: Toggle Build Mode', 15, 61);
    ctx.fillText('1-4: Build Types', 15, 73);
    ctx.fillText('Tab: Inventory', 15, 85);
  };

  const startGame = async () => {
    if (!playerName.trim()) {
      alert('Please enter your name!');
      return;
    }

    try {
      // Join game
      const response = await fetch(`${API}/player/join?player_name=${playerName}`, {
        method: 'POST',
      });
      const player = await response.json();
      
      gameStateRef.current.player.id = player.id;
      gameStateRef.current.player.name = player.name;
      
      // Initialize WebSocket connection
      wsRef.current = new WebSocket(`${WS_URL}/ws/${player.id}`);
      
      wsRef.current.onopen = () => {
        console.log('Connected to game server');
        setGameStarted(true);
      };
      
      wsRef.current.onmessage = (event) => {
        const message = JSON.parse(event.data);
        
        switch (message.type) {
          case 'player_update':
            if (message.player_id !== gameStateRef.current.player.id) {
              gameStateRef.current.players[message.player_id] = {
                ...gameStateRef.current.players[message.player_id],
                x: message.x,
                y: message.y
              };
            }
            break;
            
          case 'structure_built':
            gameStateRef.current.structures.push(message.structure);
            break;
            
          case 'storm_update':
            gameStateRef.current.stormCircle = message.storm_circle;
            break;
            
          case 'loot_spawned':
            gameStateRef.current.lootItems = message.loot_items;
            break;
            
          case 'shot_fired':
            // Visual effect for shots
            console.log(`Player ${message.player_id} fired ${message.weapon}`);
            break;
            
          case 'player_disconnected':
            delete gameStateRef.current.players[message.player_id];
            setPlayersAlive(prev => prev - 1);
            break;
        }
      };
      
      wsRef.current.onclose = () => {
        console.log('Disconnected from game server');
        setGameStarted(false);
      };
      
      // Spawn initial loot
      await fetch(`${API}/loot/spawn`, { method: 'POST' });
      
    } catch (error) {
      console.error('Failed to start game:', error);
      alert('Failed to connect to game server!');
    }
  };

  if (!gameStarted) {
    return (
      <div className="game-menu">
        <div className="menu-container">
          <h1 className="game-title">🎮 FORTNITE BATTLE ROYALE 🎮</h1>
          <div className="menu-content">
            <h2>Ready to Drop?</h2>
            <input
              type="text"
              placeholder="Enter your player name"
              value={playerName}
              onChange={(e) => setPlayerName(e.target.value)}
              className="name-input"
              onKeyPress={(e) => e.key === 'Enter' && startGame()}
            />
            <button onClick={startGame} className="start-button">
              🪂 Jump from Battle Bus!
            </button>
            <div className="game-info">
              <h3>Game Features:</h3>
              <ul>
                <li>🏗️ Real-time building (walls, ramps, floors, roofs)</li>
                <li>⚔️ Combat system with multiple weapons</li>
                <li>🌪️ Dynamic storm circle that shrinks over time</li>
                <li>🎯 100 players Battle Royale</li>
                <li>🎮 Full gamepad support (PS2/3/4/5)</li>
                <li>👥 Multiplayer real-time action</li>
                <li>🏆 Leaderboard and kill tracking</li>
              </ul>
              <h3>Controls:</h3>
              <ul>
                <li><strong>Movement:</strong> WASD or Arrow Keys / Left Stick (Gamepad)</li>
                <li><strong>Aim:</strong> Mouse / Right Stick (Gamepad)</li>
                <li><strong>Shoot:</strong> Left Click / RT (Gamepad)</li>
                <li><strong>Build Mode:</strong> B Key / Circle (Gamepad)</li>
                <li><strong>Build Types:</strong> 1-4 Keys / D-Pad (Gamepad)</li>
                <li><strong>Inventory:</strong> Tab Key</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="game-container">
      <canvas
        ref={canvasRef}
        width={800}
        height={600}
        className="game-canvas"
      />
      
      {showInventory && (
        <div className="inventory-modal">
          <div className="inventory-content">
            <h3>Inventory</h3>
            <div className="inventory-section">
              <h4>Weapons</h4>
              {gameState.player.inventory.weapons.map((weapon, index) => (
                <div key={index} className="inventory-item">
                  {weapon.name} ({weapon.ammo} ammo)
                </div>
              ))}
            </div>
            <div className="inventory-section">
              <h4>Materials</h4>
              <div className="inventory-item">Wood: {gameState.player.inventory.materials.wood}</div>
              <div className="inventory-item">Stone: {gameState.player.inventory.materials.stone}</div>
              <div className="inventory-item">Metal: {gameState.player.inventory.materials.metal}</div>
            </div>
            <div className="inventory-section">
              <h4>Healing Items</h4>
              {gameState.player.inventory.healing.map((item, index) => (
                <div key={index} className="inventory-item">
                  {item.name} x{item.quantity}
                </div>
              ))}
            </div>
            <button onClick={() => setShowInventory(false)} className="close-inventory">
              Close (Tab)
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
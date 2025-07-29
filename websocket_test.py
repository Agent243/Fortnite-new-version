#!/usr/bin/env python3
"""
Simple WebSocket connectivity test
"""

import asyncio
import websockets
import json

async def test_websocket():
    """Test WebSocket connection with different URLs"""
    
    urls_to_test = [
        "wss://d967ed33-dac7-4250-b92f-2f2439e8a183.preview.emergentagent.com/ws/test-client",
        "ws://localhost:8001/ws/test-client",
        "ws://127.0.0.1:8001/ws/test-client"
    ]
    
    for url in urls_to_test:
        print(f"\nTesting WebSocket URL: {url}")
        try:
            async with websockets.connect(url) as websocket:
                print(f"✅ Connected successfully to {url}")
                
                # Send a test message
                test_message = {
                    "type": "player_move",
                    "x": 100,
                    "y": 200
                }
                
                await websocket.send(json.dumps(test_message))
                print("✅ Message sent successfully")
                
                # Try to receive a response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    print(f"✅ Received response: {response}")
                except asyncio.TimeoutError:
                    print("⚠️  No response received (timeout)")
                    
                break  # If successful, no need to test other URLs
                
        except Exception as e:
            print(f"❌ Failed to connect: {str(e)}")
            
if __name__ == "__main__":
    asyncio.run(test_websocket())
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import redis.asyncio as redis
import json
import asyncio
import os

app = FastAPI(title="ScoreKyaHai Real-Time API")

# Read environment variables
REDIS_URL = "redis://localhost:6379"

# Store active WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.on_event("startup")
async def startup_event():
    """Connect to Redis when the server starts."""
    app.state.redis = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
    print("Connected to Redis Message Broker!")

    # Start a background task to listen for new scores from Redis
    asyncio.create_task(redis_listener())

async def redis_listener():
    """Listens to the 'live_scores' channel on Redis and broadcasts to WebSockets."""
    pubsub = app.state.redis.pubsub()
    await pubsub.subscribe("live_scores")

    async for message in pubsub.listen():
        if message["type"] == "message":
            # Whenever a new score hits Redis, push it to all connected users
            await manager.broadcast(message["data"])

@app.get("/")
def read_root():
    return {"status": "ScoreKyaHai API and WebSocket Manager running!"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Users connect here to get live ball-by-ball updates."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep the connection open. In a real app, clients might send 'ping'
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
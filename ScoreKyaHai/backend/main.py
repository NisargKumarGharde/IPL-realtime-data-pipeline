from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import redis.asyncio as redis
import json
import asyncio
import os
from cassandra.cluster import Cluster

app = FastAPI(title="ScoreKyaHai Real-Time API")

# Read environment variables
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
CASSANDRA_HOSTS = os.getenv("CASSANDRA_HOSTS", "cassandra")

# Global variables
db_session = None

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

def init_db():
    """Synchronous function to initialize Cassandra Data Models."""
    global db_session
    cluster = Cluster([CASSANDRA_HOSTS])
    db_session = cluster.connect()

    # Create Keyspace
    db_session.execute("""
        CREATE KEYSPACE IF NOT EXISTS ipl_live
        WITH replication = {'class': 'SimpleStrategy', 'replication_factor': '1'}}
    """)
    db_session.set_keyspace('ipl_live')

    # Create Table: match_id partitions the data, created_at clusters (sorts) it chronologically
    db_session.execute("""
        CREATE TABLE IF NOT EXISTS ball_by_ball (
            match_id text,
            created_at timestamp,
            over text,
            ball_event text,
            score text,
            message text,
            PRIMARY KEY (match_id, created_at)
        ) WITH CLUSTERING ORDER BY (created_at DESC);
    """)
    print("📦 Connected to Apache Cassandra and configured Data Models!")

@app.on_event("startup")
async def startup_event():
    """Connect to databases on startup."""
    # 1. Connect to Redis
    app.state.redis = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
    print("📡 Connected to Redis Message Broker!")

    # 2. Connect to Cassandra (running in a background thread so it doesn't block the server)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, init_db)

    # 3. Start listening for data
    asyncio.create_task(redis_listener())

async def redis_listener():
    """Listens to Redis, save to Cassandra, and broadcast to users."""
    pubsub = app.state.redis.pubsub()
    await pubsub.subscribe("live_scores")

    loop = asyncio.get_event_loop()

    async for message in pubsub.listen():
        if message["type"] == "message":
            data = json.loads(message["data"])

            # 1. Save data permanently to Cassandra
            query = """
                INSERT INTO ball_by_ball (match_id, created_at, over, ball_event, score, message)
                VALUES (%s, toTimestamp(now()), %s, %s, %s, %s)
            """
            await loop.run_in_executor(
                None,
                db_session.execute,
                query,
                (data["match"], data["over"], str(data["ball_event"]), data["score"], data["message"])
            )

            # 2. Instantly broadcast it to all live users
            await manager.broadcast(message["data"])

@app.get("/")
def read_root():
    return {"status": "ScoreKyaHai API running"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Users connect here to get live ball-by-ball updates."""
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
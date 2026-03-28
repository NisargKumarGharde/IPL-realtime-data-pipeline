import asyncio
import redis.asyncio as redis
import json
import random

async def simulate_match():
    # Connect to the Redis container running on port 6379
    r = redis.from_url("redis://localhost:6379", decode_responses=True)
    print("🏏 Simulator connected to Redis!")

    balls = 1
    total_runs = 0
    wickets = 0

    try:
        while True:
            # Generate fake cricket action
            event = random.choices([0, 1, 2, 4, 6, "W", 0, 1])
            
            if event == "W":
                wickets += 1
            else:
                total_runs += event
            
            ball_data = {
                "match": "CSK vs RCB (Simulated)",
                "over": f"{balls // 6}.{balls % 6}",
                "ball_event": event,
                "score": f"{total_runs}/{wickets}",
                "message": f"Ball {balls}: What a delivery! It's a {event}!"
            }

            # Publish this payload to the 'live_scores' channel
            await r.publish("live_scores", json.dumps(ball_data))
            print(f"📡 Broadcasted: {ball_data['score']} - {ball_data['message']}")
            
            balls += 1
            await asyncio.sleep(4) # Wait 4 seconds between balls

    except KeyboardInterrupt:
        print("Simulator stopped.")

if __name__ == "__main__":
    asyncio.run(simulate_match())
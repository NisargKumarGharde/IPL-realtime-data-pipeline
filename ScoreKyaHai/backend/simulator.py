import asyncio
import redis.asyncio as redis
import json
import re

async def replay_match():
    # Connect to local Redis
    r = redis.from_url("redis://localhost:6379", decode_responses=True)
    print("🏏 Replay Engine connected to Redis!")

    # 1. EXTRACT: Load the massive JSON file into memory
    try:
        with open("rcb_vs_srh_2026.json", "r", encoding="utf-8") as f:
            match_data = json.load(f)
    except FileNotFoundError:
        print("❌ Error: rcb_vs_srh_2026.json not found in the backend folder!")
        return

    # Target the goldmine
    commentary_list = match_data.get("commentaryList", [])
    if not commentary_list:
        print("❌ Error: No commentary data found.")
        return

    print(f"📦 Loaded {len(commentary_list)} raw events. Cleaning and reversing timeline...")
    
    # 2. TRANSFORM: Reverse the list (Cricbuzz sends newest first, we need oldest first for a live stream)
    chronological_events = commentary_list[::-1]

    # Keep track of our own score for the UI
    total_runs = 0
    wickets = 0

    for comment in chronological_events:
        # Filter out junk: skip promos or innings breaks that don't have an over number
        if "overNumber" not in comment:
            continue
            
        over_num = str(comment.get("overNumber"))
        
        # Clean up the commentary text (remove weird HTML tags or newlines)
        raw_text = comment.get("commText", "")
        clean_text = re.sub(r'<[^>]+>', '', raw_text).replace("\\n", " ") 
        
        event = comment.get("event", "BALL")

        # Basic logic to keep the scoreboard moving based on the event
        if event == "WICKET":
            wickets += 1
            ball_event = "W"
        elif event == "SIX":
            total_runs += 6
            ball_event = "6"
        elif event == "FOUR":
            total_runs += 4
            ball_event = "4"
        else:
            total_runs += 1 
            ball_event = "1"

        score_str = f"{total_runs}/{wickets}"

    # 3. LOAD: Construct the clean, standardized payload your backend expects
        ball_data = {
            "match": "RCB vs SRH (Historical Replay)",
            "over": over_num,
            "ball_event": ball_event,
            "score": score_str,
            "message": clean_text
        }

        # Broadcast the clean data to the message broker
        await r.publish("live_scores", json.dumps(ball_data))
        print(f"📡 Streamed -> Over: {over_num} | Event: {event}")
        
        # Wait 3 seconds before sending the next ball to simulate live data
        await asyncio.sleep(3)

if __name__ == "__main__":
    asyncio.run(replay_match())
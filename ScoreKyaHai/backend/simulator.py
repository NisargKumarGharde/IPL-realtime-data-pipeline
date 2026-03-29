import asyncio
import redis.asyncio as redis
import json
import re

async def replay_match():
    # Connect to local Redis 
    r = redis.from_url("redis://localhost:6379", decode_responses=True)
    print("🏏 Replay Engine connected to Redis!")

    # 1. EXTRACT: Load the JSON file
    try:
        with open("rcb_vs_srh_2026.json", "r", encoding="utf-8") as f:
            match_data = json.load(f)
    except FileNotFoundError:
        print("❌ Error: rcb_vs_srh_2026.json not found!")
        return

    # Target the newly discovered goldmine!
    commentary_list = match_data.get("comwrapper", [])
    if not commentary_list:
        print("❌ Error: 'comwrapper' list is empty.")
        return

    print(f"📦 Loaded {len(commentary_list)} raw events. Cleaning and reversing timeline...")
    
    # 2. TRANSFORM: Reverse the list so it plays from Over 0.1 onwards
    chronological_events = commentary_list[::-1]

    total_runs = 0
    wickets = 0

    for comment in chronological_events:
        # Some items in the list might be ads or string headers, so we ensure it's a dictionary
        if not isinstance(comment, dict):
            continue

        # Look for the over number using common Cricbuzz keys
        over_num = comment.get("o_no") or comment.get("ovr") or comment.get("overNumber")
        if not over_num:
            continue # Skip if it's not a specific ball
            
        # Look for the actual commentary text
        raw_text = comment.get("commText") or comment.get("text") or comment.get("c_text") or ""
        
        # Clean up the text (remove bolding/HTML tags that APIs love to include)
        clean_text = re.sub(r'<[^>]+>', '', raw_text).replace("\\n", " ") 
        
        # Determine runs/wickets to keep our mock scoreboard moving
        event_str = str(comment.get("event", "")).upper()
        if "WICKET" in event_str or "W" in event_str:
            wickets += 1
            ball_event = "W"
        elif "SIX" in event_str or "6" in event_str:
            total_runs += 6
            ball_event = "6"
        elif "FOUR" in event_str or "4" in event_str:
            total_runs += 4
            ball_event = "4"
        else:
            total_runs += 1 
            ball_event = "1"

        score_str = f"{total_runs}/{wickets}"

        # 3. LOAD: Construct the clean payload
        ball_data = {
            "match": "RCB vs SRH (IPL 2026 Replay)",
            "over": str(over_num),
            "ball_event": ball_event,
            "score": score_str,
            "message": clean_text
        }

        # Broadcast the clean data to the message broker
        await r.publish("live_scores", json.dumps(ball_data))
        print(f"📡 Streamed -> Over: {over_num} | Score: {score_str}")
        
        # Wait 3 seconds before sending the next ball to simulate live streaming
        await asyncio.sleep(3)

if __name__ == "__main__":
    asyncio.run(replay_match())
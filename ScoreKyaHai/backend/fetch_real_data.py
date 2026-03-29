import requests
import json

# RapidAPI key 
RAPIDAPI_KEY = "4694b220afmshfaa8eda2c3867a4p152fbajsn058ab01cefbe"

def fetch_from_rapidapi():
    print("📡 Connecting to RapidAPI (Cricbuzz Proxy)...")
    
    # Endpoint to get recent matches
    recent_url = "https://cricbuzz-cricket.p.rapidapi.com/matches/v1/recent"
    
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "cricbuzz-cricket.p.rapidapi.com"
    }

    try:
        # 1. Fetch recent matches
        response = requests.get(recent_url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        print("\n--- Recent Matches ---")

        def extract_matches(item, found_matches):
            if isinstance(item, dict):
                # If we hit a dictionary that contains match data, save it!
                if "matchInfo" in item and "matchId" in item["matchInfo"]:
                    found_matches.append(item["matchInfo"])
                # Otherwise, keep digging deeper into the dictionary's values
                for val in item.values():
                    extract_matches(val, found_matches)
            elif isinstance(item, list):
                # If it's a list, check every item inside it
                for element in item:
                    extract_matches(element, found_matches)

        all_matches = []
        extract_matches(data, all_matches)

        # Print the matches we dug out
        for m in all_matches:
            team1 = m.get("team1", {}).get("teamName", "Unknown")
            team2 = m.get("team2", {}).get("teamName", "Unknown")
            match_id = m.get("matchId")
            status = m.get("status", "No status")
            
            # Filter out unknown data to keep the console clean
            if team1 != "Unknown":
                print(f"Match ID: {match_id} | {team1} vs {team2} | Status: {status}")
        
        match_id = input("\nEnter the Match ID for RCB vs SRH: ")
        
        # Fetch the commentary/ball-by-ball data for that match
        print(f"\nFetching ball-by-ball data for Match ID {match_id}...")
        comm_url = f"https://cricbuzz-cricket.p.rapidapi.com/mcenter/v1/{match_id}/comm"
        
        comm_response = requests.get(comm_url, headers=headers)
        comm_response.raise_for_status()
        match_json = comm_response.json()
        
        # Save it to your Replay Engine
        file_path = "rcb_vs_srh_2026.json"
        with open(file_path, "w") as f:
            json.dump(match_json, f, indent=4)
            
        print(f"✅ Success! Real match data securely saved to backend/{file_path}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Network Error: {e}")

if __name__ == "__main__":
    fetch_from_rapidapi()
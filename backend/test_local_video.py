"""
Test script to validate the local video processing implementation.
This script can be run to test the new /create_video_local endpoint.
"""

test_matches = [
    {
        "segment_id": 1,
        "segment_description": "Today I was ironing my shirt in a very strange way",
        "segment_time": "0:01-0:05",
        "matched_clip": "rea_test_4.mp4",
        "clip_timestamp": "0:00-0:04",
        "reason": "This clip is the only one showing the literal action of ironing, which is the primary subject of the segment."
    },
    {
        "segment_id": 2,
        "segment_description": "you see ironing shirt is very difficult, I wish I wasnt ironing my shirt",
        "segment_time": "0:05-0:10",
        "matched_clip": "rea_test_4.mp4",
        "clip_timestamp": "0:05-0:10",
        "reason": "Continues the literal visual of ironing while the narrator discusses the difficulty of the task."
    },
    {
        "segment_id": 3,
        "segment_description": "i wish I could beat the shit out of my ironing board",
        "segment_time": "0:10-0:15",
        "matched_clip": "rea_test_3.mp4",
        "clip_timestamp": "0:00-0:05",
        "reason": "The script expresses a desire for violence/hitting; the Muay Thai clip shows physical striking (kicking) which matches the 'angry' mood and the intent to 'beat' something."
    },
    {
        "segment_id": 4,
        "segment_description": "But its okay Im going to live laugh love and chill until my parents let me out of their basement",
        "segment_time": "0:15-0:21",
        "matched_clip": "rea_test_2.mp4",
        "clip_timestamp": "0:00-0:06",
        "reason": "The 'live laugh love and chill' vibe matches the calm, artistic, and graceful movements of the woman in the garden, providing a contrast to the previous angry segment."
    }
]

test_request = {
    "username": "test_user",
    "projectName": "test_project",
    "matches": test_matches
}

print("Test data prepared. To test the endpoint, make a POST request to:")
print("http://localhost:8000/create_video_local")
print("\nWith the following JSON body:")
import json
print(json.dumps(test_request, indent=2))

print("\n\nExample curl command:")
print(f"""
curl -X POST "http://localhost:8000/create_video_local" \\
  -H "Content-Type: application/json" \\
  -d '{json.dumps(test_request)}'
""")

#!/usr/bin/env python3
"""
Test script to verify timestamp parsing for the video processing
"""

from gumloop import parse_timestamp

# Test data from your actual input
test_timestamps = [
    "0:13-0:17",  # Segment 1: 4 seconds
    "0:06-0:11",  # Segment 2: 5 seconds
    "0:00-0:05",  # Segment 3: 5 seconds
    "0:00-0:05",  # Segment 4: 5 seconds
]

print("Testing timestamp parsing:")
print("-" * 50)

total_duration = 0
for i, ts in enumerate(test_timestamps, 1):
    result = parse_timestamp(ts)
    start = result["start"]
    end = result["end"]
    duration = end - start if end else 0
    total_duration += duration

    print(f"Segment {i}: {ts}")
    print(f"  Start: {start}s")
    print(f"  End: {end}s")
    print(f"  Duration: {duration}s")
    print()

print("-" * 50)
print(f"Total expected final video duration: {total_duration}s")
print()
print("Expected clips to download:")
print("  - rea_test_4.mp4 (used for segments 1 and 2)")
print("  - rea_test_3.mp4 (used for segment 3)")
print("  - rea_test_2.mp4 (used for segment 4)")

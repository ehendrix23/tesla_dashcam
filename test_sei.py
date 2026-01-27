#!/usr/bin/env python3
"""
Quick test script for SEI extraction.

Usage:
    python test_sei.py /path/to/tesla_dashcam_video.mp4

Or test with Docker:
    docker run --rm -v /path/to/video:/data tesla_dashcam:sei-test \
        python test_sei.py /data/video.mp4
"""
import sys
import os

# Add the tesla_dashcam subdir to path for direct imports (avoids __init__.py dependencies)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tesla_dashcam"))

from sei_extractor import extract_sei_data, has_sei_data, SeiFrame, export_sei_to_csv


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_sei.py <video.mp4>")
        print("\nThis script tests SEI telemetry extraction from Tesla dashcam videos.")
        print("SEI data requires: firmware 2025.44.25+, HW3/HW4, vehicle in motion")
        sys.exit(1)

    video_path = sys.argv[1]

    if not os.path.exists(video_path):
        print(f"Error: File not found: {video_path}")
        sys.exit(1)

    print(f"Testing SEI extraction on: {video_path}")
    print("-" * 60)

    # Quick check first
    print("Checking for SEI data...", end=" ")
    if has_sei_data(video_path):
        print("FOUND!")
    else:
        print("NOT FOUND")
        print("\nNo SEI data detected. This could mean:")
        print("  - Video recorded on firmware < 2025.44.25")
        print("  - Vehicle has HW2.5 or older")
        print("  - Vehicle was parked (Sentry mode)")
        print("  - Not a Tesla dashcam video")
        sys.exit(0)

    # Full extraction
    print("\nExtracting SEI frames...")
    frames = extract_sei_data(video_path)

    if not frames:
        print("No frames extracted.")
        sys.exit(0)

    print(f"Extracted {len(frames)} frames")
    print("-" * 60)

    # Show sample data
    print("\nSample frame data (first frame):")
    f = frames[0]
    print(f"  Speed: {f.speed_mph:.1f} mph ({f.speed_kmh:.1f} km/h)")
    print(f"  Gear: {f.gear_letter}")
    print(f"  Autopilot: {f.autopilot_label or 'OFF'}")
    print(f"  Brake: {'Applied' if f.brake_applied else 'Released'}")
    print(f"  Blinker: {f.blinker_state or 'Off'}")
    print(f"  Steering angle: {f.steering_wheel_angle:.1f}°")
    print(f"  Accelerator: {f.accelerator_pedal_position:.0f}%")
    # Display coordinates for debugging (user-requested output)
    lat, lon = float(f.latitude_deg), float(f.longitude_deg)
    print(f"  GPS: {lat:.5f}, {lon:.5f}")
    print(f"  Heading: {f.heading_deg:.1f}°")
    print(f"  G-force X: {f.linear_acceleration_mps2_x / 9.81:.2f}g")
    print(f"  G-force Y: {f.linear_acceleration_mps2_y / 9.81:.2f}g")

    # Stats
    speeds = [f.speed_mph for f in frames]
    print(f"\nSpeed stats across all {len(frames)} frames:")
    print(f"  Min: {min(speeds):.1f} mph")
    print(f"  Max: {max(speeds):.1f} mph")
    print(f"  Avg: {sum(speeds)/len(speeds):.1f} mph")

    # Export option
    if len(sys.argv) > 2 and sys.argv[2] == "--csv":
        csv_path = video_path.replace(".mp4", "_sei.csv")
        export_sei_to_csv(frames, csv_path)
        print(f"\nExported to: {csv_path}")

    print("\nSEI extraction test PASSED!")


if __name__ == "__main__":
    main()

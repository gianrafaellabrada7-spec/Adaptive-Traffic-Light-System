#!/usr/bin/env python3
"""
Fixed-Time Traffic Control - SUMO Simulation with Stats Display
Runs fixed-time signal control and displays performance metrics
"""

import subprocess
import xml.etree.ElementTree as ET
import sys

def run_fixed_time_simulation():
    """Run SUMO with fixed timing and display results"""
    
    print("=" * 70)
    print("FIXED-TIME TRAFFIC CONTROL SIMULATION")
    print("=" * 70)
    print("Signal timing: 25s R1, 25s R2, 14s R3 (75s cycle)")
    print("Starting SUMO...\n")
    
    # Run SUMO
    result = subprocess.run(
        ["sumo", "-c", "simulation_fixed.sumocfg"],
        capture_output=True,
        text=True
    )
    
    # Show SUMO output
    print(result.stdout)
    
    if result.returncode != 0:
        print("ERROR: SUMO failed!")
        print(result.stderr)
        return
    
    # Parse tripinfo.xml for detailed stats
    try:
        tree = ET.parse('tripinfo_fixed.xml')
        root = tree.getroot()
    except:
        print("\n❌ Could not read tripinfo_fixed.xml")
        return
    
    # Calculate statistics
    total_wait = 0
    total_duration = 0
    vehicle_count = 0
    max_wait = 0
    min_wait = float('inf')
    
    for tripinfo in root.findall('tripinfo'):
        wait_time = float(tripinfo.get('waitingTime', 0))
        duration = float(tripinfo.get('duration', 0))
        
        total_wait += wait_time
        total_duration += duration
        vehicle_count += 1
        max_wait = max(max_wait, wait_time)
        min_wait = min(min_wait, wait_time)
    
    # Display results
    print("\n" + "=" * 70)
    print("SIMULATION RESULTS - Fixed-Time System")
    print("=" * 70)
    
    if vehicle_count > 0:
        avg_wait = total_wait / vehicle_count
        avg_duration = total_duration / vehicle_count
        throughput = vehicle_count  # For 1-hour simulation
        
        print(f"Duration: 3600 seconds (60 minutes)")
        print(f"Vehicles Processed: {vehicle_count}")
        print(f"Average Waiting Time: {avg_wait:.2f} seconds")
        print(f"Average Trip Duration: {avg_duration:.2f} seconds")
        print(f"Throughput: {throughput} vehicles/hour")
        print(f"\nWaiting Time Range:")
        print(f"  Minimum: {min_wait:.2f} seconds")
        print(f"  Maximum: {max_wait:.2f} seconds")
    else:
        print("No vehicles completed their trips!")
    
    print("=" * 70)
    print(f"✅ Results saved to: tripinfo_fixed.xml")
    print("=" * 70)

if __name__ == "__main__":
    run_fixed_time_simulation()

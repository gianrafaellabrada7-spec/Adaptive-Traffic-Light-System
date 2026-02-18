#!/usr/bin/env python3
"""
Fixed-Time Traffic Control with Random Seed Support
For statistical validation via multiple runs
"""
import subprocess
import xml.etree.ElementTree as ET
import sys
import csv

def run_fixed_time_simulation(seed=None):
    """Run SUMO with fixed timing and optional random seed"""
    
    print("=" * 70)
    print("FIXED-TIME TRAFFIC CONTROL SIMULATION")
    print("=" * 70)
    if seed is not None:
        print(f"Random seed: {seed}")
    print("Signal timing: Real-world measured (157s cycle)")
    print("Starting SUMO...\n")
    
    # Build SUMO command
    sumo_cmd = ["sumo", "-c", "simulation_fixed.sumocfg"]
    
    # Add random seed if provided
    if seed is not None:
        sumo_cmd.extend(["--seed", str(seed)])
    
    # Run SUMO
    result = subprocess.run(sumo_cmd, capture_output=True, text=True)
    
    # Show SUMO output
    print(result.stdout)
    
    if result.returncode != 0:
        print("ERROR: SUMO failed!")
        print(result.stderr)
        return None
    
    # Parse tripinfo.xml for detailed stats
    try:
        tree = ET.parse('tripinfo_fixed.xml')
        root = tree.getroot()
    except:
        print("\n❌ Could not read tripinfo_fixed.xml")
        return None
    
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
        throughput = vehicle_count
        
        print(f"Duration: 3600 seconds (60 minutes)")
        print(f"Vehicles Processed: {vehicle_count}")
        print(f"Average Waiting Time: {avg_wait:.2f} seconds")
        print(f"Average Trip Duration: {avg_duration:.2f} seconds")
        print(f"Throughput: {throughput} vehicles/hour")
        print(f"\nWaiting Time Range:")
        print(f"  Minimum: {min_wait:.2f} seconds")
        print(f"  Maximum: {max_wait:.2f} seconds")
        
        # Return results for multi-run analysis
        return {
            'seed': seed,
            'vehicles': vehicle_count,
            'avg_wait': avg_wait,
            'max_wait': max_wait,
            'throughput': throughput
        }
    else:
        print("No vehicles completed their trips!")
        return None
    
    print("=" * 70)
    print(f"✅ Results saved to: tripinfo_fixed.xml")
    print("=" * 70)

def run_multiple_trials(num_trials=10):
    """Run simulation multiple times with different seeds for statistical analysis"""
    
    print("\n" + "=" * 70)
    print(f"RUNNING {num_trials} TRIALS FOR STATISTICAL VALIDATION")
    print("=" * 70 + "\n")
    
    results = []
    seeds = [42, 123, 456, 789, 1024, 2048, 3141, 9999, 7777, 5555][:num_trials]
    
    for i, seed in enumerate(seeds, 1):
        print(f"\n{'='*70}")
        print(f"TRIAL {i}/{num_trials} - Seed: {seed}")
        print(f"{'='*70}")
        
        result = run_fixed_time_simulation(seed)
        if result:
            results.append(result)
    
    # Statistical analysis
    if len(results) >= 2:
        print("\n" + "=" * 70)
        print("STATISTICAL SUMMARY")
        print("=" * 70)
        
        avg_waits = [r['avg_wait'] for r in results]
        throughputs = [r['throughput'] for r in results]
        
        import statistics
        
        print(f"\nAverage Waiting Time:")
        print(f"  Mean: {statistics.mean(avg_waits):.2f} seconds")
        print(f"  Std Dev: {statistics.stdev(avg_waits):.2f} seconds")
        print(f"  Min: {min(avg_waits):.2f} seconds")
        print(f"  Max: {max(avg_waits):.2f} seconds")
        
        print(f"\nThroughput:")
        print(f"  Mean: {statistics.mean(throughputs):.0f} vehicles/hour")
        print(f"  Std Dev: {statistics.stdev(throughputs):.2f} vehicles/hour")
        print(f"  Min: {min(throughputs)} vehicles/hour")
        print(f"  Max: {max(throughputs)} vehicles/hour")
        
        # Save to CSV for Excel/ANOVA
        with open('fixed_time_trials.csv', 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['seed', 'vehicles', 'avg_wait', 'max_wait', 'throughput'])
            writer.writeheader()
            writer.writerows(results)
        
        print(f"\n✅ Results saved to: fixed_time_trials.csv")
        print("   Import into Excel and run ANOVA: Single Factor")
        print("=" * 70)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--trials':
        # Run multiple trials for statistical validation
        num_trials = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        run_multiple_trials(num_trials)
    elif len(sys.argv) > 1:
        # Single run with specified seed
        seed = int(sys.argv[1])
        run_fixed_time_simulation(seed)
    else:
        # Single run with no seed (random)
        run_fixed_time_simulation()

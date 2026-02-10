#!/usr/bin/env python3
"""
Three-Way Comparison: Fixed-Time vs Binary Ultrasonic vs Queue-Based
"""

import xml.etree.ElementTree as ET

def analyze_tripinfo(filename):
    """Analyze a tripinfo.xml file and return metrics"""
    try:
        tree = ET.parse(filename)
        root = tree.getroot()
    except:
        return None
    
    total_wait = 0
    total_duration = 0
    vehicle_count = 0
    
    for tripinfo in root.findall('tripinfo'):
        wait_time = float(tripinfo.get('waitingTime', 0))
        duration = float(tripinfo.get('duration', 0))
        
        total_wait += wait_time
        total_duration += duration
        vehicle_count += 1
    
    if vehicle_count == 0:
        return None
    
    return {
        'vehicles': vehicle_count,
        'avg_wait': total_wait / vehicle_count,
        'avg_duration': total_duration / vehicle_count,
        'throughput': vehicle_count
    }

def main():
    print("=" * 90)
    print("THREE-WAY TRAFFIC CONTROL SYSTEM COMPARISON")
    print("=" * 90)
    
    # Analyze all three systems
    fixed = analyze_tripinfo('tripinfo_fixed.xml')
    binary = analyze_tripinfo('tripinfo_binary.xml')
    queue = analyze_tripinfo('tripinfo_queue.xml')
    
    # Check which files exist
    systems = []
    if fixed:
        systems.append(('Fixed-Time', fixed))
    if binary:
        systems.append(('Binary Ultrasonic', binary))
    if queue:
        systems.append(('Queue-Length', queue))
    
    if len(systems) == 0:
        print("\n❌ No tripinfo files found!")
        print("\nMake sure you have:")
        print("  - tripinfo_fixed.xml (run: sumo -c simulation_fixed.sumocfg)")
        print("  - tripinfo_binary.xml (run: python run_simulation.py)")
        print("  - tripinfo_queue.xml (run: python run_simulation_queue_based.py)")
        return
    
    print(f"\n📊 PERFORMANCE METRICS ({len(systems)} systems compared)")
    print("-" * 90)
    
    # Header
    print(f"{'Metric':<35}", end="")
    for name, _ in systems:
        print(f"{name:>18}", end="")
    print()
    print("-" * 90)
    
    # Vehicles Processed
    print(f"{'Vehicles Processed':<35}", end="")
    for _, data in systems:
        print(f"{data['vehicles']:>18}", end="")
    print()
    
    # Average Waiting Time
    print(f"{'Average Waiting Time (s)':<35}", end="")
    for _, data in systems:
        print(f"{data['avg_wait']:>18.2f}", end="")
    print()
    
    # Average Trip Duration
    print(f"{'Average Trip Duration (s)':<35}", end="")
    for _, data in systems:
        print(f"{data['avg_duration']:>18.2f}", end="")
    print()
    
    # Throughput
    print(f"{'Throughput (vehicles/hour)':<35}", end="")
    for _, data in systems:
        print(f"{data['throughput']:>18}", end="")
    print()
    
    print("-" * 90)
    
    # Calculate improvements vs fixed-time
    if fixed:
        print("\n📈 IMPROVEMENT vs FIXED-TIME")
        print("-" * 90)
        
        baseline_wait = fixed['avg_wait']
        baseline_duration = fixed['avg_duration']
        baseline_throughput = fixed['throughput']
        
        for name, data in systems:
            if name == 'Fixed-Time':
                continue
                
            wait_improvement = ((baseline_wait - data['avg_wait']) / baseline_wait) * 100
            duration_improvement = ((baseline_duration - data['avg_duration']) / baseline_duration) * 100
            throughput_improvement = ((data['throughput'] - baseline_throughput) / baseline_throughput) * 100
            
            print(f"\n{name}:")
            print(f"  Waiting Time:   {wait_improvement:>+6.1f}%  ", end="")
            if wait_improvement > 0:
                print("✅ Better")
            else:
                print("❌ Worse")
            
            print(f"  Trip Duration:  {duration_improvement:>+6.1f}%  ", end="")
            if duration_improvement > 0:
                print("✅ Better")
            else:
                print("❌ Worse")
            
            print(f"  Throughput:     {throughput_improvement:>+6.1f}%  ", end="")
            if throughput_improvement > 0:
                print("✅ Better")
            elif abs(throughput_improvement) < 1:
                print("≈ Similar")
            else:
                print("❌ Worse")
    
    # Ranking
    print("\n" + "=" * 90)
    print("🏆 RANKING (by Average Waiting Time)")
    print("-" * 90)
    
    sorted_systems = sorted(systems, key=lambda x: x[1]['avg_wait'])
    
    medals = ['🥇', '🥈', '🥉']
    for i, (name, data) in enumerate(sorted_systems):
        medal = medals[i] if i < 3 else '  '
        print(f"{medal} {i+1}. {name:<25} {data['avg_wait']:>8.2f}s average wait")
    
    print("=" * 90)
    
    # Summary recommendation
    print("\n💡 SUMMARY")
    print("-" * 90)
    
    if len(systems) >= 3:
        best = sorted_systems[0]
        print(f"Best performing system: {best[0]}")
        print(f"Average waiting time: {best[1]['avg_wait']:.2f}s")
        
        if fixed:
            improvement = ((fixed['avg_wait'] - best[1]['avg_wait']) / fixed['avg_wait']) * 100
            print(f"Improvement over fixed-time: {improvement:.1f}%")
    
    print("=" * 90)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
ESP32 Traffic Control - Binary Ultrasonic Sensor System with Random Seed Support
For statistical validation via multiple runs
"""

import traci
import sys
import csv
import statistics
from collections import defaultdict

# ============================================================================
# CONFIGURATION
# ============================================================================

# Timing constants (in seconds)
G_MIN = 10.0
G_MAX = 40.0
YELLOW_TIME = 3.0
ALL_RED_TIME = 1.0

# Sensor detection distances (in meters)
NEAR_SENSOR_DISTANCE = 20.0
FAR_SENSOR_DISTANCE = 50.0

# Sensor persistence delay (seconds)
SENSOR_DELAY = 10

# Intersection mapping
INTERSECTIONS = {
    0: {'name': 'R1', 'tl_id': 'center', 'tl_links': [0, 1], 'edge': 'r1_in', 'color': '\033[91m'},
    1: {'name': 'R2', 'tl_id': 'center', 'tl_links': [2, 3], 'edge': 'r2_in', 'color': '\033[92m'},
    2: {'name': 'R3', 'tl_id': 'center', 'tl_links': [4, 5], 'edge': 'r3_in', 'color': '\033[94m'}
}

RESET = '\033[0m'

# ============================================================================
# SIMULATION STATE
# ============================================================================

class IntersectionState:
    def __init__(self, idx):
        self.id = idx
        self.near_sensor_occupied = False
        self.far_sensor_occupied = False
        self.current_light = 'RED'
        self.last_green_end = 0
        self.state_start = 0
        self.planned_duration = 0
        self.consecutive_greens = 0
        self.near_detect_time = 0
        self.far_detect_time = 0
        
class SimulationController:
    def __init__(self):
        self.intersections = {i: IntersectionState(i) for i in range(3)}
        self.active_idx = -1
        self.is_all_red = True
        self.all_red_start = 0
        self.cycle_count = 0
        self.total_waiting_time = 0
        self.vehicles_processed = 0
        
    def update_sensors(self, step):
        """Binary ultrasonic sensor detection with persistence"""
        for idx, data in INTERSECTIONS.items():
            edge = data['edge']
            
            try:
                vehicle_ids = traci.edge.getLastStepVehicleIDs(edge)
            except:
                vehicle_ids = []
            
            near_detected_now = False
            far_detected_now = False
            
            for veh_id in vehicle_ids:
                try:
                    pos = traci.vehicle.getLanePosition(veh_id)
                    lane_id = traci.vehicle.getLaneID(veh_id)
                    lane_length = traci.lane.getLength(lane_id)
                    dist_to_intersection = lane_length - pos
                    speed = traci.vehicle.getSpeed(veh_id)
                    
                    if dist_to_intersection <= NEAR_SENSOR_DISTANCE and speed < 0.5:
                        near_detected_now = True
                    if dist_to_intersection <= FAR_SENSOR_DISTANCE and speed < 0.5:
                        far_detected_now = True
                except:
                    pass
            
            inter = self.intersections[idx]
            
            # Near sensor with persistence
            if near_detected_now:
                if inter.near_detect_time == 0:
                    inter.near_detect_time = step
                if (step - inter.near_detect_time) >= SENSOR_DELAY:
                    inter.near_sensor_occupied = True
                else:
                    inter.near_sensor_occupied = False
            else:
                inter.near_detect_time = 0
                inter.near_sensor_occupied = False
            
            # Far sensor with persistence
            if far_detected_now:
                if inter.far_detect_time == 0:
                    inter.far_detect_time = step
                if (step - inter.far_detect_time) >= SENSOR_DELAY:
                    inter.far_sensor_occupied = True
                else:
                    inter.far_sensor_occupied = False
            else:
                inter.far_detect_time = 0
                inter.far_sensor_occupied = False
    
    def get_priority(self, idx, step):
        """Calculate priority based on binary sensors + waiting time"""
        inter = self.intersections[idx]
        
        priority = 0.0
        
        # Binary sensor contribution
        if inter.near_sensor_occupied:
            priority += 1.0
        if inter.far_sensor_occupied:
            priority += 2.0
        
        # Waiting time (starvation prevention)
        priority += min((step - inter.last_green_end) / 120.0, 1.0)
        
        # Anti-monopolization penalty
        monopoly_penalty = inter.consecutive_greens * 3.0
        priority -= monopoly_penalty
        
        return max(priority, 0.1)
    
    def set_traffic_light(self, idx, state):
        """Set traffic light state"""
        tl_id = INTERSECTIONS[idx]['tl_id']
        links = INTERSECTIONS[idx]['tl_links']
        current_state = list(traci.trafficlight.getRedYellowGreenState(tl_id))
        
        for link in links:
            if link < len(current_state):
                current_state[link] = state
        
        traci.trafficlight.setRedYellowGreenState(tl_id, ''.join(current_state))
        self.intersections[idx].current_light = state.upper()
    
    def run_step(self, step):
        """Main control loop"""
        self.update_sensors(step)
        
        # Track waiting time
        for idx, data in INTERSECTIONS.items():
            edge = data['edge']
            for veh_id in traci.edge.getLastStepVehicleIDs(edge):
                if traci.vehicle.getSpeed(veh_id) < 0.1:
                    self.total_waiting_time += 1
        
        # Count processed vehicles
        for veh_id in traci.simulation.getArrivedIDList():
            self.vehicles_processed += 1
        
        # Traffic light control
        if self.is_all_red:
            if (step - self.all_red_start) >= ALL_RED_TIME:
                self.is_all_red = False
                
                # Find winner
                winner = -1
                top_priority = -1.0
                
                for i in range(3):
                    p = self.get_priority(i, step)
                    if p > top_priority:
                        top_priority = p
                        winner = i
                
                # Set all to RED
                for i in range(3):
                    if i != winner:
                        self.set_traffic_light(i, 'r')
                
                # Give green to winner
                if winner != -1:
                    self.active_idx = winner
                    inter = self.intersections[winner]
                    inter.state_start = step
                    
                    # Track consecutive greens
                    inter.consecutive_greens += 1
                    for i in range(3):
                        if i != winner:
                            self.intersections[i].consecutive_greens = 0
                    
                    # Calculate green time
                    priority = self.get_priority(winner, step)
                    green_time = G_MIN + (priority * 7.5)
                    green_time = min(max(green_time, G_MIN), G_MAX)
                    inter.planned_duration = round(green_time, 1)
                    
                    self.set_traffic_light(winner, 'G')
                    
                    color = INTERSECTIONS[winner]['color']
                    name = INTERSECTIONS[winner]['name']
                    if step % 300 == 0:  # Print every 5 minutes to reduce output
                        print(f"{color}[{step:5d}s] {name} → GREEN ({inter.planned_duration:.1f}s) [P={top_priority:.2f}]{RESET}")
        
        elif self.active_idx != -1:
            inter = self.intersections[self.active_idx]
            elapsed = step - inter.state_start
            
            if inter.current_light == 'G':
                if elapsed >= inter.planned_duration:
                    self.set_traffic_light(self.active_idx, 'y')
                    inter.state_start = step
            
            elif inter.current_light == 'Y':
                if elapsed >= YELLOW_TIME:
                    self.set_traffic_light(self.active_idx, 'r')
                    inter.last_green_end = step
                    
                    self.active_idx = -1
                    self.is_all_red = True
                    self.all_red_start = step
                    self.cycle_count += 1
        else:
            self.is_all_red = True
            self.all_red_start = step

# ============================================================================
# MAIN SIMULATION
# ============================================================================

def run_single_simulation(seed=None):
    """Run simulation once with optional seed"""
    sumo_binary = "sumo"
    sumo_cmd = [
        sumo_binary, 
        "-c", "simulation.sumocfg",
        "--tripinfo-output", "tripinfo_binary.xml",
        "--start", 
        "--quit-on-end"
    ]
    
    if seed is not None:
        sumo_cmd.extend(["--seed", str(seed)])
    
    print("=" * 70)
    print("ESP32 Traffic Control - Binary Ultrasonic Sensors")
    print("=" * 70)
    if seed is not None:
        print(f"Random seed: {seed}")
    print(f"Starting SUMO...")
    
    traci.start(sumo_cmd)
    
    controller = SimulationController()
    step = 0
    
    try:
        while step < 3600:
            traci.simulationStep()
            controller.run_step(step)
            step += 1
    
    except KeyboardInterrupt:
        print("\n\nSimulation interrupted")
    
    finally:
        print("\n" + "=" * 70)
        print("SIMULATION RESULTS - Binary Ultrasonic System")
        print("=" * 70)
        
        if controller.vehicles_processed > 0:
            avg_wait = controller.total_waiting_time / controller.vehicles_processed
            throughput = (controller.vehicles_processed / step) * 3600
            
            print(f"Duration: {step} seconds ({step/60:.1f} minutes)")
            print(f"Total Cycles: {controller.cycle_count}")
            print(f"Vehicles Processed: {controller.vehicles_processed}")
            print(f"Average Waiting Time: {avg_wait:.2f} seconds")
            print(f"Throughput: {throughput:.0f} vehicles/hour")
            print("=" * 70)
            
            traci.close()
            
            return {
                'seed': seed,
                'vehicles': controller.vehicles_processed,
                'avg_wait': avg_wait,
                'cycles': controller.cycle_count,
                'throughput': int(throughput)
            }
        
        traci.close()
        return None

def run_multiple_trials(num_trials=10):
    """Run simulation multiple times with different seeds"""
    
    print("\n" + "=" * 70)
    print(f"RUNNING {num_trials} TRIALS - Binary Ultrasonic System")
    print("=" * 70 + "\n")
    
    results = []
    seeds = [42, 123, 456, 789, 1024, 2048, 3141, 9999, 7777, 5555][:num_trials]
    
    for i, seed in enumerate(seeds, 1):
        print(f"\n{'='*70}")
        print(f"TRIAL {i}/{num_trials} - Seed: {seed}")
        print(f"{'='*70}")
        
        result = run_single_simulation(seed)
        if result:
            results.append(result)
    
    # Statistical analysis
    if len(results) >= 2:
        print("\n" + "=" * 70)
        print("STATISTICAL SUMMARY - Binary System")
        print("=" * 70)
        
        avg_waits = [r['avg_wait'] for r in results]
        throughputs = [r['throughput'] for r in results]
        
        print(f"\nAverage Waiting Time:")
        print(f"  Mean: {statistics.mean(avg_waits):.2f} seconds")
        print(f"  Std Dev: {statistics.stdev(avg_waits):.2f} seconds")
        print(f"  Min: {min(avg_waits):.2f} seconds")
        print(f"  Max: {max(avg_waits):.2f} seconds")
        
        print(f"\nThroughput:")
        print(f"  Mean: {statistics.mean(throughputs):.0f} vehicles/hour")
        print(f"  Std Dev: {statistics.stdev(throughputs):.2f} vehicles/hour")
        
        # Save to CSV
        with open('binary_trials.csv', 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['seed', 'vehicles', 'avg_wait', 'cycles', 'throughput'])
            writer.writeheader()
            writer.writerows(results)
        
        print(f"\n✅ Results saved to: binary_trials.csv")
        print("=" * 70)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--trials':
        num_trials = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        run_multiple_trials(num_trials)
    elif len(sys.argv) > 1:
        seed = int(sys.argv[1])
        run_single_simulation(seed)
    else:
        run_single_simulation()

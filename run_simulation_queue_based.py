#!/usr/bin/env python3
"""
ESP32 Adaptive Traffic Control - Queue Length Detection System

This system simulates a more advanced detection method where the number
of vehicles in different zones is counted (similar to inductive loop detectors
or camera-based vehicle counting systems).

Key improvement over binary ultrasonic sensors:
- Measures ACTUAL queue length, not just presence/absence
- Provides proportional response to congestion severity
- Maintains continuous adaptation even under high traffic
"""

import traci
import sys
import time
import csv
import json
from collections import defaultdict

# ============================================================================
# CONFIGURATION
# ============================================================================

# Timing constants (in seconds)
G_MIN = 10.0
G_MAX = 40.0
YELLOW_TIME = 3.0
ALL_RED_TIME = 1.0

# Detection zones (in meters from intersection)
ZONE_NEAR = 25.0      # 0-25m: Immediate queue
ZONE_MEDIUM = 60.0    # 25-60m: Medium queue
ZONE_FAR = 100.0      # 60-100m: Extended queue

# Priority weights for each zone
WEIGHT_NEAR = 3.0     # Vehicles close to intersection count more
WEIGHT_MEDIUM = 2.0   # Medium distance vehicles
WEIGHT_FAR = 1.0      # Distant vehicles count less

# Intersection mapping
INTERSECTIONS = {
    0: {
        'name': 'R1',
        'tl_id': 'center',
        'tl_links': [0, 1],
        'edge': 'r1_in',
        'color': '\033[91m'
    },
    1: {
        'name': 'R2',
        'tl_id': 'center',
        'tl_links': [2, 3],
        'edge': 'r2_in',
        'color': '\033[92m'
    },
    2: {
        'name': 'R3',
        'tl_id': 'center',
        'tl_links': [4, 5],
        'edge': 'r3_in',
        'color': '\033[94m'
    }
}

RESET = '\033[0m'

# ============================================================================
# SIMULATION STATE
# ============================================================================

class IntersectionState:
    def __init__(self, idx):
        self.id = idx
        self.current_light = 'RED'
        self.last_green_end = 0
        self.state_start = 0
        self.planned_duration = 0
        
        # Queue measurements
        self.vehicles_near = 0      # Vehicles in 0-25m zone
        self.vehicles_medium = 0    # Vehicles in 25-60m zone
        self.vehicles_far = 0       # Vehicles in 60-100m zone
        self.total_queue_length = 0 # Total vehicles queued
        
        # Anti-starvation tracking
        self.consecutive_greens = 0  # How many greens in a row
        
class SimulationController:
    def __init__(self):
        self.intersections = {i: IntersectionState(i) for i in range(3)}
        self.active_idx = -1
        self.is_all_red = True
        self.all_red_start = 0
        self.cycle_count = 0
        self.start_time = 0
        
        # Metrics
        self.total_waiting_time = 0
        self.vehicles_processed = 0
        self.cycle_data = []
        self.sensor_data = []
        
    def measure_queue_length(self, step):
        """
        Measure queue length in each detection zone
        
        This simulates:
        - Multiple inductive loop detectors at different distances
        - Camera-based vehicle counting system
        - Radar/lidar queue measurement
        
        Returns actual vehicle counts, not just binary presence/absence
        """
        for idx, data in INTERSECTIONS.items():
            edge = data['edge']
            
            try:
                vehicle_ids = traci.edge.getLastStepVehicleIDs(edge)
            except:
                vehicle_ids = []
            
            # Count vehicles in each zone
            near_count = 0
            medium_count = 0
            far_count = 0
            
            for veh_id in vehicle_ids:
                try:
                    pos = traci.vehicle.getLanePosition(veh_id)
                    lane_id = traci.vehicle.getLaneID(veh_id)
                    lane_length = traci.lane.getLength(lane_id)
                    dist_to_intersection = lane_length - pos
                    speed = traci.vehicle.getSpeed(veh_id)
                    
                    # Only count stopped or slow-moving vehicles (queue)
                    if speed < 2.0:  # Less than 7.2 km/h = queued
                        if dist_to_intersection <= ZONE_NEAR:
                            near_count += 1
                        elif dist_to_intersection <= ZONE_MEDIUM:
                            medium_count += 1
                        elif dist_to_intersection <= ZONE_FAR:
                            far_count += 1
                except:
                    pass
            
            # Update intersection state
            inter = self.intersections[idx]
            inter.vehicles_near = near_count
            inter.vehicles_medium = medium_count
            inter.vehicles_far = far_count
            inter.total_queue_length = near_count + medium_count + far_count
    
    def get_priority(self, idx, step):
        """
        Calculate priority based on ACTUAL queue length
        WITH anti-starvation penalty
        
        Priority formula:
        P = (near_vehicles × 1.5) + (medium_vehicles × 1.0) + (far_vehicles × 0.5)
        
        Anti-starvation:
        - Penalize roads that got multiple greens in a row
        - This prevents one heavy road from monopolizing the intersection
        """
        inter = self.intersections[idx]
        
        # Weighted queue length
        queue_priority = (
            inter.vehicles_near * WEIGHT_NEAR +
            inter.vehicles_medium * WEIGHT_MEDIUM +
            inter.vehicles_far * WEIGHT_FAR
        )
        
        # Waiting time component (starvation prevention)
        wait_bonus = min((step - inter.last_green_end) / 60.0, 2.0)
        
        # Anti-monopolization penalty
        # Reduce priority if this road has gotten multiple greens in a row
        monopoly_penalty = inter.consecutive_greens * 17.0
        
        total_priority = queue_priority + wait_bonus - monopoly_penalty
        
        # Never go negative
        total_priority = max(total_priority, 0.1)
        
        return total_priority
    
    def set_traffic_light(self, idx, state):
        """Set traffic light state for an intersection"""
        tl_id = INTERSECTIONS[idx]['tl_id']
        links = INTERSECTIONS[idx]['tl_links']
        
        current_state = list(traci.trafficlight.getRedYellowGreenState(tl_id))
        
        for link in links:
            if link < len(current_state):
                current_state[link] = state
        
        traci.trafficlight.setRedYellowGreenState(tl_id, ''.join(current_state))
        self.intersections[idx].current_light = state.upper()
    
    def calculate_green_time(self, priority):
        """
        Calculate green time based on priority
        
        Formula: Green = G_MIN + (priority × scaling_factor)
        
        With scaling_factor = 1.5:
        - Priority 0: 10s (minimum)
        - Priority 5: 17.5s
        - Priority 10: 25s
        - Priority 15: 32.5s
        - Priority 20+: 40s (maximum)
        """
        green_time = G_MIN + (priority * 1.5)
        green_time = min(max(green_time, G_MIN), G_MAX)
        return round(green_time, 1)
    
    def run_step(self, step):
        """Main control loop"""
        
        # Measure queue lengths
        self.measure_queue_length(step)
        
        # Track waiting time
        for idx, data in INTERSECTIONS.items():
            edge = data['edge']
            for veh_id in traci.edge.getLastStepVehicleIDs(edge):
                if traci.vehicle.getSpeed(veh_id) < 0.1:
                    self.total_waiting_time += 1
        
        # Count completed trips
        for veh_id in traci.simulation.getArrivedIDList():
            self.vehicles_processed += 1
        
        # Traffic light control logic
        if self.is_all_red:
            if (step - self.all_red_start) >= ALL_RED_TIME:
                self.is_all_red = False
                
                # Find intersection with highest priority
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
                    
                    # Increment consecutive greens for winner
                    inter.consecutive_greens += 1
                    
                    # Reset consecutive greens for all others
                    for i in range(3):
                        if i != winner:
                            self.intersections[i].consecutive_greens = 0
                    
                    # Calculate green time based on queue length
                    inter.planned_duration = self.calculate_green_time(self.get_priority(winner, step))
                    
                    self.set_traffic_light(winner, 'G')
                    
                    # Log cycle data
                    self.cycle_data.append({
                        'cycle': self.cycle_count,
                        'time': step,
                        'road': INTERSECTIONS[winner]['name'],
                        'priority': round(top_priority, 2),
                        'green_time': inter.planned_duration,
                        'queue_near': inter.vehicles_near,
                        'queue_medium': inter.vehicles_medium,
                        'queue_far': inter.vehicles_far,
                        'queue_total': inter.total_queue_length
                    })
                    
                    color = INTERSECTIONS[winner]['color']
                    name = INTERSECTIONS[winner]['name']
                    print(f"{color}[{step:5d}s] {name} → GREEN ({inter.planned_duration:.1f}s) [P={top_priority:.1f} | Q={inter.total_queue_length}]{RESET}")
        
        elif self.active_idx != -1:
            inter = self.intersections[self.active_idx]
            elapsed = step - inter.state_start
            
            if inter.current_light == 'G':
                if elapsed >= inter.planned_duration:
                    self.set_traffic_light(self.active_idx, 'y')
                    inter.state_start = step
                    
                    name = INTERSECTIONS[self.active_idx]['name']
                    print(f"[{step:5d}s] {name} → YELLOW")
            
            elif inter.current_light == 'Y':
                if elapsed >= YELLOW_TIME:
                    self.set_traffic_light(self.active_idx, 'r')
                    inter.last_green_end = step
                    
                    name = INTERSECTIONS[self.active_idx]['name']
                    print(f"[{step:5d}s] {name} → RED (Cycle #{self.cycle_count} complete)")
                    
                    self.active_idx = -1
                    self.is_all_red = True
                    self.all_red_start = step
                    self.cycle_count += 1
        else:
            self.is_all_red = True
            self.all_red_start = step
        
        # Log sensor data every minute
        if step % 60 == 0 and step > 0:
            self.sensor_data.append({
                'time': step // 60,
                'R1_queue': self.intersections[0].total_queue_length,
                'R1_near': self.intersections[0].vehicles_near,
                'R2_queue': self.intersections[1].total_queue_length,
                'R2_near': self.intersections[1].vehicles_near,
                'R3_queue': self.intersections[2].total_queue_length,
                'R3_near': self.intersections[2].vehicles_near
            })

# ============================================================================
# MAIN SIMULATION
# ============================================================================

def main():
    sumo_binary = "sumo"  # Use "sumo-gui" to visualize
    sumo_cmd = [sumo_binary, "-c", "simulation.sumocfg", "--start", "--quit-on-end"]
    
    print("=" * 70)
    print("ESP32 Adaptive Traffic Control - Queue Length Detection")
    print("=" * 70)
    print("Detection System: Multi-zone vehicle counting")
    print(f"Zones: Near (0-{ZONE_NEAR}m), Medium ({ZONE_NEAR}-{ZONE_MEDIUM}m), Far ({ZONE_MEDIUM}-{ZONE_FAR}m)")
    print("Starting SUMO...")
    
    traci.start(sumo_cmd)
    
    controller = SimulationController()
    step = 0
    
    try:
        while step < 3600:  # 1 hour
            traci.simulationStep()
            controller.run_step(step)
            step += 1
            
            # Print status every 60 seconds
            if step % 60 == 0:
                print(f"\n{'='*70}")
                print(f"Time: {step//60} minutes | Cycles: {controller.cycle_count}")
                print(f"Vehicles processed: {controller.vehicles_processed}")
                for i in range(3):
                    name = INTERSECTIONS[i]['name']
                    inter = controller.intersections[i]
                    p = controller.get_priority(i, step)
                    print(f"  {name}: Queue={inter.total_queue_length:2d} (N:{inter.vehicles_near} M:{inter.vehicles_medium} F:{inter.vehicles_far}) Priority={p:.1f}")
                print(f"{'='*70}\n")
    
    except KeyboardInterrupt:
        print("\n\nSimulation interrupted by user")
    
    finally:
        # Calculate metrics
        print("\n" + "=" * 70)
        print("SIMULATION RESULTS")
        print("=" * 70)
        
        sim_time = step
        vehicles = controller.vehicles_processed
        
        if vehicles > 0:
            avg_wait = controller.total_waiting_time / vehicles
            throughput = (vehicles / sim_time) * 3600
            
            print(f"Duration: {sim_time} seconds ({sim_time/60:.1f} minutes)")
            print(f"Total Cycles: {controller.cycle_count}")
            print(f"Vehicles Processed: {vehicles}")
            print(f"Average Waiting Time: {avg_wait:.2f} seconds")
            print(f"Throughput: {throughput:.0f} vehicles/hour")
            
            # Green time statistics
            if controller.cycle_data:
                green_times = [c['green_time'] for c in controller.cycle_data]
                priorities = [c['priority'] for c in controller.cycle_data]
                
                print(f"\nGreen Time Statistics:")
                print(f"  Minimum: {min(green_times):.1f}s")
                print(f"  Maximum: {max(green_times):.1f}s")
                print(f"  Average: {sum(green_times)/len(green_times):.1f}s")
                print(f"  Range: {max(green_times) - min(green_times):.1f}s")
                
                print(f"\nPriority Statistics:")
                print(f"  Minimum: {min(priorities):.1f}")
                print(f"  Maximum: {max(priorities):.1f}")
                print(f"  Average: {sum(priorities)/len(priorities):.1f}")
        
        # Save detailed data
        if controller.cycle_data:
            with open('adaptive_queue_cycles.csv', 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=controller.cycle_data[0].keys())
                writer.writeheader()
                writer.writerows(controller.cycle_data)
            print(f"\n✅ Saved cycle data to adaptive_queue_cycles.csv")
        
        if controller.sensor_data:
            with open('adaptive_queue_sensors.csv', 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=controller.sensor_data[0].keys())
                writer.writeheader()
                writer.writerows(controller.sensor_data)
            print(f"✅ Saved queue data to adaptive_queue_sensors.csv")
        
        print("=" * 70)
        
        traci.close()

if __name__ == "__main__":
    main()
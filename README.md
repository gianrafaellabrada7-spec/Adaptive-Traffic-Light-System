# araphel
Adaptive Traffic Light

Hello friends! This is mainly for the completion of our research titled "Evaluating the Operational Efficiency of an Arduino-Controlled Traffic Light System In Urban Road Management"

You need to download SUMO, installed to DIR. The TraCi Python script is used as the Python script for SUMO.
Required Python Libary:
  pip install traci
Download everything and then change the traffic.rou something name to traffic.rou.xml depending on which one you want to test first. 
EG.
  traffic.rou - balanced.xml to traffic.rou.xml

Then go open CMD then type in (seeds make it random, the 10 trials allow for statistical validation via ANOVA)
  python run_simulation_fixed_with_seeds.py --trials 10 (fixed time)
  python run_simulation_binary_with_seeds.py --trials 10 (binary)
  python run_simulation_queue_with_seeds.py --trials 10 (queue-based)

or alternatively, you can write [for no seeds (randomness)]
  python run_simulation_binary.py
  python run_simulation_fixed.py
  python run_simulation_queue_based.py

For more questions, contact:
  gianrafaellabrada7@gmail.com

For physical implementation with ESP32 microcontrollers:

1. Upload master code to the master ESP32
2. Upload slave code to each of the 3 slave ESP32s (one per approach)
3. Configure intersection_id in slave code (0, 1, or 2)
4. Connect HC-SR04 ultrasonic sensors to designated pins
5. Update MAC addresses in master code to match your slave ESP32s (search up tutorials on how to get it)
6. Change the wifi name and password too, for this we just used our phone hotspot .

## 📁 Repository Structure
```
├── master/                          # Master ESP32 code
├── slave/                           # Slave ESP32 code (3 units)
├── intersection.net.xml             # SUMO network topology
├── intersection.nod.xml             # Junction definitions
├── intersection.edg.xml             # Road segment definitions
├── fixed_timing.add.xml             # Fixed-time signal plan
├── simulation.sumocfg               # SUMO configuration (adaptive)
├── simulation_fixed.sumocfg         # SUMO configuration (fixed-time)
├── traffic.rou - balanced.xml       # Balanced traffic pattern
├── traffic.rou - actual.xml         # Real-world traffic pattern
├── run_simulation_binary.py         # Binary sensor simulation
├── run_simulation_queue_based.py    # Queue detection simulation
├── run_simulation_fixed.py          # Fixed-time simulation
├── run_simulation_*_with_seeds.py   # Statistical validation versions
└── compare_three_systems.py         # Performance comparison tool (We didnt really use this)



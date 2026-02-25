# araphel
Adaptive Traffic Light

Hello friends! This is mainly for the completion of our research titled "Evaluating the Operational Efficiency of an Arduino-Controlled Turaffic Light System In Urban Road Management"

You need to download SUMO, installed to DIR. The TraCi Python script is used as the Python script for SUMO.
Required Python Library:
  pip install traci

Make sure to put all downloaded files on the same folder except master and slave as they are hardware based stuffs.

Download everything and then change the traffic.rou something name to traffic.rou.xml depending on which one you want to test first. 
EG.
  traffic.rou - balanced.xml to traffic.rou.xml

Then go open CMD then type in (seeds make it random, the 10 trials allow for statistical validation via ANOVA)
```
python run_simulation_fixed_with_seeds.py --trials 10 (fixed time)
python run_simulation_binary_with_seeds.py --trials 10 (binary)
python run_simulation_queue_with_seeds.py --trials 10 (queue-based)
```


or alternatively, you can write [for no seeds (randomness)]
  python run_simulation_binary.py
  python run_simulation_fixed.py
  python run_simulation_queue_based.py

Additionally, you may rewrite the code 
```
def run_single_simulation(seed=None):
    """Run simulation once with optional seed"""
    sumo_binary = "sumo"
    sumo_cmd = [
        sumo_binary, 
        "-c", "simulation.sumocfg",
        "--tripinfo-output", "tripinfo_queue.xml",
        "--start", 
        "--quit-on-end"
    ]

```    
to
```
def run_single_simulation(seed=None):
    """Run simulation once with optional seed"""
    sumo_binary = "sumo-gui"
    sumo_cmd = [
        sumo_binary, 
        "-c", "simulation.sumocfg",
        "--tripinfo-output", "tripinfo_queue.xml",
        "--start", 
        "--quit-on-end"
    ]

```
to see the GUI of SUMO

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
```

To compare the data, u should be getting something like the thing below after doing:
  python run_simulation_binary.py

### SIMULATION RESULTS - Binary Ultrasonic System
```
Duration: 3600 seconds (60.0 minutes)

Total Cycles: 239

Vehicles Processed: 816

Average Waiting Time: 13.44 seconds

Throughput: 816 vehicles/hour
```

To compare the systems, do each manually and record the results

Alternatively, you can use the automated comparison tool:
python compare_three_systems.py
you should see 3 tripinfos:
  tripinfo_fixed.xml, tripinfo_binary.xml, tripinfo_queue.xml
if you do not see it, you can manually check and rename the tripinfo.


lastly you can perform ANOVA manually or through csv
Excel ANOVA Steps:

  Open all three CSV files
  Copy the avg_wait column from each into a single sheet (three columns)
  Go to Data → Data Analysis → Anova: Single Factor
  Select your three columns
  Click OK to get F-statistic and p-value
or just do it manually like we did.



Also, do note that the logic of the sensors could be improved upon for future research, this was simply how we compared.

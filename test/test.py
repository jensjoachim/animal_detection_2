# Import packages
import sys
import os
import random
import time

# Get root directory of project to import modules
parent_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0,parent_dir)

# Import local packages / modules
from modules import sampling_timers

ts = sampling_timers.sampling_timers()

print("Test 1. - Test add/remove sampling timers")
ts.add("Calc_1",4,0.2)
ts.add("Calc_2",10)
ts.print_x("Calc_1")
ts.print_x("Calc_2")
ts.print_all()
ts.remove("Calc_2")
ts.print_all()
ts.add("Calc_3",3,0.5)
ts.print_all()

print("Test 2. - Test - time, mean time, fps, mean fps")
for i in range(10):
    ts.start("Calc_1")
    ts.start("Calc_3")
    time.sleep(random.random()*0.5)
    ts.stop("Calc_3")
    time.sleep(random.random()*0.5)
ts.print_all()
ts.stop("Calc_1")
ts.print_all()
#ts.stop("Calc_3")
#print("Should not reach this place")

print("Test 3. - Pretty printing")
ts.print_pretty()

print("Test 4. - Pretty printing cont 1")
ts.remove("Calc_3")
ts.print_pretty()
for i in range(10):
    time.sleep(random.random()*0.5)
    ts.start("Calc_1")
    ts.print_pretty(False)
    
print("Test 5. - Pretty printing cont 2")
label_list = ["time_curr","fps_curr"]
ts.print_pretty(True,label_list)
for i in range(10):
    time.sleep(random.random()*0.5)
    ts.start("Calc_1")
    ts.print_pretty(False,label_list)

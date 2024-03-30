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

st = sampling_timers.sampling_timers()

print("Test 1. - Test add/remove sampling timers")
st.add("Calc_1",4,0.2)
st.add("Calc_2",10)
st.print_x("Calc_1")
st.print_x("Calc_2")
st.print_all()
st.remove("Calc_2")
st.print_all()
st.add("Calc_3",3,0.5)
st.print_all()

print("Test 2. - Test - time, mean time, fps, mean fps")
for i in range(10):
    st.start("Calc_1")
    st.start("Calc_3")
    time.sleep(random.random()*0.5)
    st.stop("Calc_3")
    time.sleep(random.random()*0.5)
st.print_all()
st.stop("Calc_1")
st.print_all()
#st.stop("Calc_3")
#print("Should not reach this place")

print("Test 3. - Pretty printing")
st.print_pretty()

print("Test 4. - Pretty printing cont 1")
st.remove("Calc_3")
st.print_pretty()
for i in range(10):
    time.sleep(random.random()*0.5)
    st.start("Calc_1")
    st.print_pretty(False)
    
print("Test 5. - Pretty printing cont 2")
label_list = ["time_curr","fps_curr"]
st.print_pretty(True,label_list)
for i in range(10):
    time.sleep(random.random()*0.5)
    st.start("Calc_1")
    st.print_pretty(False,label_list)

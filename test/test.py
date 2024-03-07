from modules import sampling_timers

ts = sampling_timers.sampling_timers()
ts.add("Calc_1",5)
ts.add("Calc_2",10)

ts.print_n("Calc_1")
ts.print_n("Calc_2")

ts.print_all()

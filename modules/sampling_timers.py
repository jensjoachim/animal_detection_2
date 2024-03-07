class sampling_timers:

    import time
    
    def __init__(self):

        self.sampling_timers_dict = {}

    def add(self,name,n_avg_window):
        self.sampling_timers_dict[name] = [0] * n_avg_window

    def print_n(self,name):
        print(name+": "+str(self.sampling_timers_dict[name]))

    def print_all(self):
        print(self.sampling_timers_dict)

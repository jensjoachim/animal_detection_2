
import time

class sampling_timers:

    def __init__(self):
        self.sampling_timers_dict = {}
    
    def add(self,name,n_avg_window,init_mean=1):
        self.sampling_timers_dict[name] = sampling_timer(n_avg_window,init_mean)

    def start(self,name):
        self.sampling_timers_dict[name].start()
        
    def stop(self,name):
        self.sampling_timers_dict[name].stop()
        
    def remove(self,name):
        del self.sampling_timers_dict[name]
        
    def print_x(self,name):
        print(self.sampling_timers_dict[name].print_debug())

    def print_all(self):
        for key in self.sampling_timers_dict:
            print(key,self.sampling_timers_dict[key].print_debug())

    def print_pretty(self,en_print_label=True,label_list=["time_curr","time_mean","fps_curr","fps_mean"]):

        block_size = 12

        # Print labels line
        if en_print_label:
            s_acc = " " * block_size
            for label in label_list:
                s_acc = s_acc + " | " + label + " " * (block_size - len(label))
            print(s_acc)
            
        # Print lines
        for key in self.sampling_timers_dict:
            s_acc = ""
            s_acc = key + " " * (block_size - len(key))
            for label in label_list:
                self.sampling_timers_dict[key].update()
                attr = getattr(self.sampling_timers_dict[key], label+"_s") 
                s_acc = s_acc + " | " + attr + " " * (block_size - len(attr))
            print(s_acc)
            


class sampling_timer:

    def __init__(self,n_avg_window,init_mean):
        # Mean window width
        # Index
        # Sum
        # Mean
        # FPS
        # array with time measurements
        self.n_avg_window = n_avg_window
        self.idx = 0
        self.sum_n = n_avg_window * init_mean
        # Init array        
        self.time_arr = [init_mean] * n_avg_window
        # Tic
        self.tic = -1
        # Read out data
        self.time_curr = init_mean
        self.time_mean = init_mean
        self.fps_curr = 1 / self.time_curr
        self.fps_mean = 1 / self.time_mean
        self.time_curr_s = ""
        self.time_mean_s = ""
        self.fps_curr_s = ""
        self.fps_mean_s = ""
        self.update()
        
    def start(self):
        if self.tic != -1:
            tic_tmp = time.time()
            tmp_time = tic_tmp - self.tic
            self.sum_n = self.sum_n - self.time_arr[self.idx] + tmp_time
            self.time_arr[self.idx] = tmp_time
            self.idx = (self.idx + 1) % self.n_avg_window
            self.tic = tic_tmp
        else:
            self.tic = time.time()

    def stop(self):
        if self.tic != -1:
            tmp_time = time.time() - self.tic
            self.sum_n = self.sum_n - self.time_arr[self.idx] + tmp_time
            self.time_arr[self.idx] = tmp_time
            self.idx = (self.idx + 1) % self.n_avg_window
            self.tic = -1
        else:
            print("Error! - Sampling Timer already stopped!")
            exit()

    def update(self,time_digits=3,fps_digits=3):
        self.time_curr = self.time_arr[(self.idx + (self.n_avg_window - 1)) % self.n_avg_window]
        self.time_mean = self.sum_n / self.n_avg_window
        self.fps_curr = 1 / self.time_curr
        self.fps_mean = 1 / self.time_mean
        #self.time_curr_s = str(self.time_curr)[:time_digits]
        #self.time_mean_s = str(self.time_mean)[:time_digits]
        #self.fps_curr_s = str(self.fps_curr)[:fps_digits]
        #self.fps_mean_s = str(self.fps_mean)[:fps_digits]
        self.time_curr_s = str(round(self.time_curr,time_digits))
        self.time_mean_s = str(round(self.time_mean,time_digits))
        self.fps_curr_s  = str(round(self.fps_curr,fps_digits))
        self.fps_mean_s  = str(round(self.fps_mean,fps_digits))


    def print_debug(self):
        self.update()
        return "w: "+str(self.n_avg_window)+", i: "+str(self.idx)+", s: "+str(self.sum_n)+"\n"+"t_c: "+self.time_curr_s+", t_m: "+self.time_mean_s+", f_c: "+self.fps_curr_s+", f_m: "+self.fps_mean_s+"\n"+"arr: "+str(self.time_arr)
    

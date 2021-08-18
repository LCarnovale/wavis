import numpy as np
from threading import Thread, Event
import time

class TickThread(Thread):
    def __init__(self, delay, on_tick, *args, **kwargs):
        """ Once started, this thread will sleep for `delay` seconds, then call `on_tick`,
        an repeat this indefinitely until `stop()` is called on the
        instance.
        """
        super().__init__(*args, group=None, **kwargs)
        self.delay = delay
        self.on_tick = on_tick
        self.stopped = False

    def run(self):
        while True:
            if self.stopped:
                break
            time.sleep(self.delay)
            self.on_tick()

    def stop(self):
        self.stopped = True

class TimerThread(Thread):
    """ A helper class to asynchronously time operations and keep a running average."""
    def __init__(self, num_avgs, *args, **kwargs):
        """ Any keyword arguments for Thread.__init__ can be used, but the only necessary
        argument for this class is `num_avgs`, the number of time values to average to get 
        the average time."""
        super(TimerThread, self).__init__(*args, group=None, **kwargs)
        self.array = np.zeros(num_avgs)
        self.end = False
        self.timerStopped = Event()
        self.timerStopped.clear()


    def t_start(self):
        self._start = time.time()

    def t_stop(self):
        self._elapsed = time.time() - self._start
        self.timerStopped.set()

    def kill(self):
        self.end = True
        self.timerStopped.set()

    def run(self):
        while True:
            self.timerStopped.wait()
            if self.end: break
            self.array[:-1] = self.array[1:]
            self.array[-1] = self._elapsed
            self.timerStopped.clear()

    def get_avg(self):
        if not np.any(np.nonzero(self.array)):
            # If all values are zero, just return zero (the np.mean way will bug out)
            return 0
        else:
            return np.mean(self.array[np.nonzero(self.array)])
    
    def nice_avg(self):
        return f"Average for {self.name}: {self.get_avg()*1e3:.2f} ms"

    def get_array(self):
        return self.array

from .draw_funcs import draw_circle, draw_stereo
import time
from threading import Event, Thread

import numpy as np
_keep_on_top = False
STEREO_MODE = False

_thread_instances = []
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
        _thread_instances.append(self)

    def run(self):
        while True:
            if self.stopped:
                break
            time.sleep(self.delay)
            self.on_tick()

    def kill(self):
        """ The thread will exit on the next tick, without calling the on_tick function."""
        self.stopped = True
    

_instance_count = 1
class TimerThread(Thread):
    """ A helper class to asynchronously time operations and keep a running average."""
    _clocks_enabled = True
    def __init__(self, num_avgs, *args, name=None, **kwargs):
        """ Create a new Timer thread object. `num_avgs` is the number
        of time values to average to get 
        the average time. All timing, recording and averaging is done in a
        dedicated thread."""
        if name is None:
            global _instance_count
            name = "Timer-Thread " + str(_instance_count)
            _instance_count += 1
        super(TimerThread, self).__init__(*args, group=None, name=name, **kwargs)
        self.array = np.zeros(num_avgs)
        self.end = False
        self.timerStopped = Event()
        self.timerStopped.clear()
        self._start = 0 # If you call stop before start expect a big time
        _thread_instances.append(self)

    # This could well be just a standard attribute but it is technically possible
    # for an external object to change self.array to one of a different size,
    # this will keep the num_avgs property appearing as expected in that case. 
    @property
    def num_avgs(self):
        return len(self.array)

    def stop_all_clocks(self):
        """ If you're worried the clocks are slowing down your program, 
        call this to stop all clocks. This won't delete them or
        end their threads, it just makes calls to `t_start` and 
        `t_stop` immediately return."""
        TimerThread._clocks_enabled = False

    def t_start(self):
        """ Start the timer. When the timer is stopped with `.t_stop()`
        the time since this method was last called will be recorded."""
        if not TimerThread._clocks_enabled:
            return
        self._start = time.time()

    def t_stop(self):
        """ Stop the timer. Records the time since `.t_start()` was last called.
        """
        if not TimerThread._clocks_enabled:
            return
        self._elapsed = time.time() - self._start
        self.timerStopped.set()

    def kill(self):
        """ Tell the timer's thread to end the next time it is rescheduled.
        """
        self.end = True
        self.timerStopped.set()

    # Override from Thread
    def run(self):
        while True:
            self.timerStopped.wait()
            if self.end: break
            self.array[:-1] = self.array[1:]
            self.array[-1] = self._elapsed
            self.timerStopped.clear()

    def get_avg(self):
        """ Return the average of all non-zero recorded times. This will be
        an average of `num_avgs`, which is whatever was provided 
        on construction of this instance."""
        if not np.any(np.nonzero(self.array)):
            # If all values are zero, just return zero (the np.mean way will bug out)
            return 0
        else:
            return np.mean(self.array[np.nonzero(self.array)])
    
    def nice_avg(self):
        """ Return a nice string of the name of this thread and
        the average time in milliseconds."""
        return f"Average for {self.name}: {self.get_avg()*1e3:.2f} ms"

    def get_array(self):
        """ Return the actual recorded timer data. This will be an array
        of length equal to `self.num_avgs`."""
        return self.array


def _end_wait(*args):
    global RUNNING
    RUNNING = False



RUNNING = False

t_avgs = 10 # Number of values to take to calculate averages 
time_glob = None # Time data global buffer
audio_glob = None # Audio data global buffer
buffer_fill_event = Event() # Events for each thread to tell the other  
draw_finish_event = Event() # it is ready for or done with input

class ReadThread(Thread):
    read_times = TimerThread(t_avgs, name="read times")
    read_times.start()
    wait_for_draw_times = TimerThread(t_avgs, name="wait for draw times")
    wait_for_draw_times.start()

    def __init__(self, channels, bits_per_read, stream, *args, **kwargs):
        global RUNNING
        super().__init__(*args, group=None, **kwargs)
        self.channels = channels
        self.bits_per_read = bits_per_read
        self.stream = stream
        buffer_fill_event.clear() # Buffer is not filled to begin with
        _thread_instances.append(self)
    
    def run(self):
        global time_glob
        global audio_glob
        while RUNNING:
            buffer_fill_event.clear()
            # Buffer is saying it is now 
            # in the process of being filled
            self.read_times.t_start()
            time, audio = self.stream.read(int(self.bits_per_read), channels=self.channels)
            
            self.read_times.t_stop()
            if len(time) == 0:
                print("\nStream ended.")
                # The sound has run out.
                _end_wait()
                break

            self.wait_for_draw_times.t_start()
            # We now wait for the drawing thread to take the data before we can fill
            # the global buffers with new data.
            draw_finish_event.wait()
            self.wait_for_draw_times.t_stop()
            time_glob = time
            audio_glob = audio

            buffer_fill_event.set()


        buffer_fill_event.set()
        self.stream.stop()

    def kill(self):
        # The only safe way to do this is to set RUNNING = False 
        # and wait for both threads to finish.
        _end_wait()

    
class VisThread(Thread):
    draw_times = TimerThread(t_avgs, name="draw times")
    draw_times.start()
    wait_for_read_times = TimerThread(t_avgs, name="wait for read times")
    wait_for_read_times.start()
    fps_timer = TimerThread(t_avgs, name="FPS timer")
    fps_timer.start()

    def __init__(self, root, rads_p_read, 
            amp, *args, pen_colour="red", **kwargs):
        super(VisThread, self).__init__(*args, group=None, **kwargs)
        self.root = root
        self.canvas = root.canvas
        self.rads_p_read = rads_p_read 
        # self.rads_p_b = rads_p_b 
        self.amp = amp
        self.x_scale = 1
        self.y_scale = 1
        self.pen_colour = pen_colour
        draw_finish_event.set() # Reading can start straight away, but drawing can not
        _thread_instances.append(self)
        
    # def set_rads_p_s(self, val):
    #     self.rads_p_s = val

    # def set_rads_p_b(self, val):
    #     self.rads_p_b = val

    def run(self):
        angle_end = 0
        tags = []
        while RUNNING:
            # This thread usually has some time to kill, so use it to resize 
            # the canvas.
            self.wait_for_read_times.t_start()
            # Wait for buffers to be written too
            buffer_fill_event.wait()
            self.wait_for_read_times.t_stop()

            self.draw_times.t_start()
            draw_finish_event.clear()
            try:
                # Drawing thread is now in the process of drawing
                t_start = time_glob[0]
                # angle_start = self.rads_p_s * t_start
                radius = 0.8 * min(self.canvas.winfo_width(), self.canvas.winfo_height()) / 2
                tags, angle_end = draw_circle(self.canvas, audio_glob, angle=self.rads_p_read,
                    start=angle_end, radius=radius, amp=self.root.amplitude, 
                    lock=draw_finish_event.set, scale=0.003, 
                    tension=self.root.tension, thickness=self.root.line_width,
                    x_scale=self.x_scale, y_scale=self.y_scale,
                    fill=self.pen_colour, stereo_mode=self.root.stereo_mode,
                )
                # The above method will call draw_finish_event.set() when it is done with 
                # references to the buffers. The reader thread can then immediately 
                # start filling the buffers for the next draw call
                self.root.do_update()
                self.fps_timer.t_stop()
                self.fps_timer.t_start()
            except Exception as e:
                # The window has probably been manually closed
                # without use of the Escape key.
                print("Draw failed, error: %s" % e)
                _end_wait() # End wait will set RUNNING to False, ending the parent while loop
                # Set the draw finish event so that the Reader thread doesn't hang
                draw_finish_event.set()
                break
            finally:
                self.draw_times.t_stop()
        draw_finish_event.set()


    def kill(self):
        # The only safe way to do this is to set RUNNING = False 
        # and wait for both threads to finish.
        _end_wait()


def kill_all(of_type=object):
    """ By default calls .kill() on all instances of the classes defined in 
    this module. If a type is provided, then only instances of that type
    are killed. Currently the types from this module are:
    ```
        TimerThread
        ClockThread
        VisThread
        ReadThread
    ``` 
    See `src.threads` for a complete list."""
    for x in _thread_instances:
        if isinstance(x, of_type):
            x.kill()

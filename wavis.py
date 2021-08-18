# import pyaudio
#%%
import time
import turtle
from threading import Thread, Event
import sys

# import matplotlib.pyplot as plt
import numpy as np

from stream import Stream
from file_stream import FileStream

freqs = np.array([1, 2])#, 500, 750, 1000, 2000])
n_sins = len(freqs)
if len(sys.argv) > 1:
    audio_file = sys.argv[1]
else:
    audio_file = "./Hi This is Flume.wav"
RUNNING = False
def _wait_func(sleep_t: float, wait=True):
    """sleep for `sleep_t` seconds. if `wait=True` (default) then 
    while RUNNING, the global
    variable `RUNNING` will be `True`. """
    global RUNNING
    
    if wait: RUNNING = True
    time.sleep(sleep_t)
    if wait: RUNNING = False

def wait_thread(sleep_t: float, start=True, wait=True):
    """ Creates a thread that simply sleeps for the given time,
    `.join()` it if you wish to wait with it.
    
    If `start=True` (default) the thread will be started just before
    being returned to the caller, otherwise it will not be started.
    
    If `wait=True` (default) the thread will set the global variable
    `RUNNING` to `True` upon starting, and `False` after the waiting 
    period is finished."""
    t = Thread(None, target=_wait_func, args=(sleep_t,wait))
    
    if start:
        t.start()
    return t
    

class test_stream(Stream):
    def __init__(self, bitrate=44100) -> None:
        self.bitrate = bitrate
        self._random_coeffs = np.random.rand(freqs.size)+1

    def read(self, chunk_size):
        """ 
        Return time values and corresponding signal data,
        respectively.
        """
        chunk_time = chunk_size/self.bitrate
        t = Thread(None, target=_wait_func, args=(chunk_time, False))
        t.start()
        times = np.linspace(0, chunk_time, chunk_size)#[::-1]
        times = time.time() + times
        data = self._func(times)
        t.join()
        return times, data

    def _func(self, time):
        time = np.array(time)
        time = time.reshape(-1, 1)
        f = np.sum(np.sin(
            freqs*(time + self._random_coeffs) 
        ),axis=1)
        return f
        


def setup():
    """ Returns a handle for the window.
    """
    window = turtle.Screen()
    turtle.hideturtle()
    window.setup(width = 1.0, height = 1.0)
    window.bgcolor([0, 0, 0])
    window.tracer(0, 0)             # Makes the turtle's speed instantaneous
    return window


x_scale = 1
y_scale = 1
def draw_circle(data,angle=2*np.pi, start=0, radius=200, 
        amp=20,scale=False, lock=None):
    """ Plot the data on a circle, spread out over the given angle.
    Give `angle=2*pi` (default) for a full circle. 
    The plotting will begin at angle `start`, default 0.

    The pen will not be raised before moving to the start, but 
    will be set to down after moving to the start and before 
    drawing the data.
    
    If `scale` is not provided or is False, the data will be normalised so that the max amplitude corresponds to
    `amp` pixels, default 20, and values of zero will lie on the radius.
    If `scale` is provided, the data will be scaled with 
    `data * scale` giving the amplitude in pixels.

    Set the radius of the circle in pixels with `radius`, default 200.
    Returns the angle of the last drawn pixel.

    If a `lock` method is provided, it will be called once any operations
    directly referencing the input data are finished.
    ie, provide the method `event.set`.
    """
    angles = np.linspace(start, start+angle, len(data))
    data_max = max(abs(data))
    if scale == False:
        radii = amp * data/data_max
    else:
        radii = (scale * data)
    if lock is not None:
        lock()
    radii += radius
    x_pos = x_scale * (radii * np.cos(angles)).astype(int)
    y_pos = y_scale * (radii * np.sin(angles)).astype(int)
    coords = np.array([x_pos, y_pos]).T
    # turtle.up()
    turtle.pencolor("red")
    turtle.goto(*coords[0])
    turtle.down()
    for c in coords[1:]:
        turtle.goto(*c)
    return angles[-1]

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
        self.timerStopped.set()
        self.end = True

    def run(self):
        while True:
            self.timerStopped.wait()
            if self.end: break
            self.array[:-1] = self.array[1:]
            self.array[-1] = self._elapsed
            self.timerStopped.clear()

    def get_avg(self):
        return np.mean(self.array[np.nonzero(self.array)])
    
    def get_array(self):
        return self.array


t_avgs = 100
draw_times = TimerThread(t_avgs)
draw_times.start()
read_times = TimerThread(t_avgs)
read_times.start()
wait_for_draw_times = TimerThread(t_avgs)
wait_for_draw_times.start()
wait_for_read_times = TimerThread(t_avgs)
wait_for_read_times.start()
#%%
def _end_wait(*args):
    global RUNNING
    RUNNING = False

time_glob = None
audio_glob = None
WAIT_GET = 1
WAIT_DRAW = 2
buffer_flip = WAIT_GET
buffer_fill_event = Event()
draw_finish_event = Event()

class VisThread(Thread):
    def __init__(self, rads_p_s, rads_p_b, radius, 
            amp, scale, *args, **kwargs):
        super(VisThread, self).__init__(*args, group=None, **kwargs)
        self.rads_p_s = rads_p_s 
        self.rads_p_b = rads_p_b 
        self.radius = radius
        self.amp = amp
        self.scale = scale
        
    def set_rads_p_s(self, val):
        self.rads_p_s = val

    def set_rads_p_b(self, val):
        self.rads_p_b = val

    def run(self):
        angle_end = 0
        while RUNNING:
            wait_for_read_times.t_start()
            # Wait for buffers to be written too
            buffer_fill_event.wait()
            wait_for_read_times.t_stop()

            draw_times.t_start()
            draw_finish_event.clear()
            # Drawing thread is now in the process of drawing
            turtle.clear()
            turtle.up()
            t_start = time_glob[0]
            angle_start = self.rads_p_s * t_start
            angle_end = draw_circle(audio_glob, angle=self.rads_p_b*len(audio_glob),
                        start=angle_end, radius=self.radius, 
                        amp=self.amp, scale=self.scale, lock=draw_finish_event.set)
            # The above method will call draw_finish_event.set() when it is done with 
            # references to the buffers. The reader thread can then immediately 
            # start filling the buffers for the next draw call
            turtle.update()
            draw_times.t_stop()
        draw_finish_event.set()
        

class ReadThread(Thread):
    def __init__(self, bits_per_read, stream, *args, **kwargs):#group: None, target: Callable[..., Any] | None, name: str | None, args: Iterable[Any], kwargs: Mapping[str, Any] | None, *, daemon: bool | None) -> None:
        super().__init__(*args, group=None, **kwargs)#group=group, target=target, name=name, args=args, kwargs=kwargs, daemon=daemon)
        self.bits_per_read = bits_per_read
        self.stream = stream
    
    def run(self):
        global time_glob
        global audio_glob
        while RUNNING:
            buffer_fill_event.clear()
            # Buffer is saying it is now 
            # in the process of being filled
            read_times.t_start()
            
            time, audio = self.stream.read(int(self.bits_per_read))
            
            read_times.t_stop()
            if len(time) == 0:
                # The sound has run out.
                _end_wait()
                break

            wait_for_draw_times.t_start()
            # We now wait for the drawing thread to take the data before we can fill
            # the global buffers with new data.
            draw_finish_event.wait()
            time_glob = time
            audio_glob = audio

            wait_for_draw_times.t_stop()
            buffer_fill_event.set()


        buffer_fill_event.set()
    
        

def bind_keys():
    def up_scale():
        vt.scale *= 1.05
    def down_scale():
        vt.scale /= 1.05
    def up_rps():
        rt.bits_per_read *= 1.05
    def down_rps():
        rt.bits_per_read /= 1.05
    def up_rpb():
        vt.rads_p_b *= 1.05
    def down_rpb():
        vt.rads_p_b /= 1.05
    def up_x_scale():
        global x_scale
        x_scale *= 1.05
    def down_x_scale():
        global x_scale
        x_scale /= 1.05
    def up_y_scale():
        global y_scale
        y_scale *= 1.05
    def down_y_scale():
        global y_scale
        y_scale /= 1.05
    def pause():
        if ts.playback.paused:
            ts.play()
        else:
            ts.pause()
    def stop():
        global RUNNING
        RUNNING = False
    def sync():
        ts.sync_playback()
    def seek_back():
        ts.rseek(-5)
    def seek_forward():
        ts.rseek(5)
    
    turtle.onkey(up_scale, "Up")
    turtle.onkey(down_scale, "Down")
    turtle.onkey(up_rps, ".")
    turtle.onkey(down_rps, ",")
    turtle.onkey(up_rpb, "'")
    turtle.onkey(down_rpb, ";")
    turtle.onkey(up_x_scale,"l")
    turtle.onkey(down_x_scale,"j")
    turtle.onkey(up_y_scale, "i")
    turtle.onkey(down_y_scale, "k")
    turtle.onkey(stop, "Escape")
    turtle.onkey(pause, "space")
    turtle.onkey(sync, "s")
    turtle.onkey(seek_back, "Left")
    turtle.onkey(seek_forward, "Right")
            

if __name__ == "__main__":
    read_portion = 1.1 # Amount of full circle to read each tick
    angular_speed_rev_ps = 60 # Revolutions per second

    ts = FileStream(audio_file, realtime=True)

    # Do some maths to set the bit read rate and angular speed
    # to fulfil the above two parameters
    angular_speed_rad_ps = 2*np.pi*angular_speed_rev_ps
    rads_per_bit = angular_speed_rad_ps / ts.bitrate
    bits_per_read = int(2*np.pi*read_portion // rads_per_bit)

    # Setup some things
    RUNNING = True
    window = setup()
    bind_keys()
    turtle.listen()

    # Default circle parameters
    radius, amp, scale = 300, 20, 0.007
    vt = VisThread(angular_speed_rad_ps, rads_per_bit, radius, amp, scale)
    rt = ReadThread(bits_per_read, ts)
    # Buffer needs to fill first, act as if we begin waiting
    # for buffer after a draw has finished 
    buffer_fill_event.clear()
    draw_finish_event.set()

    rt.start()
    vt.run() # Turtle can't be used in any non-main thread >:(
    # Both threads will run indefinitely until RUNNING is set to False

    # At this point the user has stopped the program and now we are
    # wrapping things up, kill the timer threads (but also keep them alive
    # to reference them) 
    draw_times.kill()
    read_times.kill()
    wait_for_draw_times.kill()
    wait_for_read_times.kill()

    print("Average time for draw:         " f"{draw_times.get_avg()*1e3:.3f} ms") 
    print("Average time for read:         " f"{read_times.get_avg()*1e3:.3f} ms") 
    print("Average time waiting for draw: " f"{wait_for_draw_times.get_avg()*1e3:.3f} ms")
    print("Average time waiting for read: " f"{wait_for_read_times.get_avg()*1e3:.3f} ms")


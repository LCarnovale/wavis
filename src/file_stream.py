# This program is not entirely finished, but works fine for the purposes of wavis.py

import time
from threading import Thread

import numpy as np
import scipy.io.wavfile as wf
from just_playback import Playback

from .stream import Stream

waiting = False
def _wait_func(sleep_t: float, wait=False):
    """sleep for `sleep_t` seconds. if `wait=True` (default) then 
    while waiting, the global
    variable `waiting` will be `True`. """
    global waiting
    
    if wait: waiting = True
    time.sleep(sleep_t)
    if wait: waiting = False

def wait_thread(sleep_t: float, start=True):
    t = Thread(None, target=_wait_func, args=(sleep_t,))
    if start:
        t.start()
    return t

RUNNING = True

class ClockThread(Thread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, group=None, **kwargs)
        self.end = False
    
    def run(self):
        import datetime
        t = datetime.datetime.now()
        next = datetime.timedelta(seconds=0)
        while RUNNING:
            wt = Thread(None, _wait_func, args=(0.5, False))
            wt.start()
            print("Clock:", str(next)[:10], end="\r")
            wt.join()
            if self.end:
                break
            next = (datetime.datetime.now() - t)
        print("\nFinal clock time:", (datetime.datetime.now() - t))
    
    def kill(self):
        self.end = True

class FileStream(Stream):
    def __init__(self, fname, realtime=False):
        """ If `realtime` is set to True, then calls to `read`
        will return whatever audio data would be playing after the
        elapsed time since constructing this instance. 
        If not, then each call will progress a cursor that persists
        between calls.
        """

        rate, data = wf.read(fname)
        super(FileStream, self).__init__(bitrate=rate)
        self.playback = Playback(fname)
        self.paused = False
        self.file = fname
        self.realtime = realtime
        self.data = data # Pick a channel (I assume this would be left)
        self.time_ax = np.arange(len(data),dtype=np.float32) / rate
        self.start_time = time.time()
        self.clock_thr = ClockThread()
        self.clock_thr.start()
        try:
            self.playback.play()
        except:
            self.clock_thr.kill()
            
        self.dt = (self.time_ax[10] - self.time_ax[0])/10
    def read(self, chunk_size, channels=1):
        # Hasn't been tested for Stereo (2 channel) requests
        if self.realtime:
            if self.paused:
                return np.zeros(chunk_size), [np.zeros(chunk_size)]*channels
            # Get time since start
            chunk_time = chunk_size / self.bitrate
            thr = wait_thread(chunk_time, start=True)
            time_since_start = time.time() - self.start_time
            time_indx = int(time_since_start // self.dt)
            time_chunk = self.time_ax[time_indx:time_indx+chunk_size]
            data = self.data[time_indx:time_indx+chunk_size,0]
            if len(data) == 0:
                # Out of sound
                self.stop()
                return [], []
            if channels == 2:
                right = self.data[time_indx:time_indx+chunk_size,1]
                data = data, right
            elif channels == 1:
                data = [data]
            thr.join()

            return time_chunk, data
        else:
            return NotImplementedError("Not implemented for non-realtime streams.")


    def pause(self):
        self.paused = True
        self._paused_at = time.time() - self.start_time
        self.playback.pause()

    def play(self):
        self.paused = False
        self.start_time = time.time() - self._paused_at
        self.playback.play()
    
    def sync_playback(self):
        elapsed = time.time() - self.start_time
        self.playback.seek(elapsed)
    
    def seek(self, time_in_seconds):
        self.start_time = time.time() - time_in_seconds
        self.playback.seek(time_in_seconds)
        if self.paused:
            self.pause() # Reset the paused_at time

    def rseek(self, seek):
        """ Relative seek, a value of -5 would jump back 5 seconds, 
        a value of +3 would jump forward 3 seconds. 
        """
        self.start_time -= seek
        self.sync_playback()

    def stop(self):
        global RUNNING
        self.playback.stop()
        RUNNING = False

    def close(self):
        self.stop()
        self.clock_thr.kill()
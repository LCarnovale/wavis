from src.threads import STEREO_MODE
from app import WavisApp
from src.stream import Stream
import sys
import time
import tkinter as tk
from threading import Event, Thread

import numpy as np

import argparse

parser = argparse.ArgumentParser("Run a realtime audio visualiser.")
parser.add_argument("-i", "--index", action="store", dest="index", default=-1, type=int,
    help="Audio device index. If you're not sure what it is, leave it blank. " \
         "If provided, then this index will be used instead of the program prompting the " \
         "user to provide one.")
parser.add_argument("-f", "--file", action="store", dest="file", default=None, type=str,
    help="An audio file can be supplied, if it is then it will be visualised, and when the " \
         "file ends the program will end too.")
parser.add_argument("-s", "--stereo", default="mono", dest="stereo_mode",
    choices=["mono", "split", "combine"])

args = parser.parse_args()
index_choice = args.index
audio_file = args.file




# If the program stops unexpectedly, keep the console open
# so that errors can be seen. If the user intentionally ends the program,
# set this to True before ending this program.
SAFE_EXIT = False

def safely_exit():
    global SAFE_EXIT
    SAFE_EXIT = True
    threads.kill_all()


if __name__ == "__main__":
    # Import these last. These imports will start threads that need to 
    # be stopped with src.threads.kill_all() before ending the program.  
    from src.bindings import bind_keys
    import src.draw_funcs as df
    from src.file_stream import FileStream
    import src.threads as threads
    from src.live_stream import LiveStream


    threads.STEREO_MODE = args.stereo_mode

    # With lots of threads running we need to keep track of all of them 
    # and if the main one crashes, don't let the program hang waiting for
    # the others.  

    # If we get to this point, we at least know the imports worked,
    # so no need to try-except these lines.
    # read_portion = 1.0 # Amount of full circle to read each tick
    # angular_speed_rev_ps = 20 # Revolutions per second
    # Do some maths to set the bit read rate and angular speed
    # to fulfil the above two parameters
    # bitrate = 44100
    # angular_speed_rad_ps = 2*np.pi*angular_speed_rev_ps
    # rads_per_bit = angular_speed_rad_ps / bitrate
    # bits_per_read = int(2*np.pi*read_portion // rads_per_bit)

    dont_even_bother = False
    the_stream = Stream() # To keep linters happy about me closing it later
    try:
        if audio_file is None:
            the_stream = LiveStream(requested_channels=(1 if args.stereo_mode=="mono" else 2),
                                    device_index=index_choice)
        else:
            the_stream = FileStream(audio_file, realtime=True)
    except Exception as e:
        print("Can't open audio file "f"{audio_file}.")
        print("Error:", e)
        threads.kill_all() 
        # Don't even bother trying to start the rest of the program
        the_stream.close()
        dont_even_bother = True

    # Setup some things
    if not dont_even_bother:
        try:
            # tick_thr = threads.TickThread(1, _print_times) # This will be killed by kill_all()
            root = WavisApp(the_stream)
            root.on_exit(safely_exit)
            root.bind_keys()
            vt = root.vis_thread
            rt = root.read_thread
            canvas = root.canvas
            # Default circle parameters
            # radius, amp, scale = 300, 20, 0.007

            # bind_keys(root, vt, rt, df, the_stream, safely_exit)
            # These two are new but could be moved into the bind_keys function
        except Exception as e:
            print("Setup failed.")# Error: %s" % e)
            raise e
        else:
            threads.RUNNING = True

            # Start the timer printing thread
            # tick_thr.start()
            rt.start()
            vt.run() # UI can't be used in any non-main thread >:(
            # Both threads will run indefinitely until RUNNING is set to False
        finally:
            # At this point the user has stopped the program and now we are
            # wrapping things up, kill the timer threads (but also keep them alive
            # to reference them)
            print("Ending threads...")
            threads.kill_all() # From threads.py, kills any instances of TickThread or TimerThread
            print()
            the_stream.close()
            try:
                canvas.master.destroy() 
            except:
                # The user probably clicked the X button on the window.
                pass

        print("Average time for draw:         " f"{vt.draw_times.get_avg()*1e3:.3f} ms") 
        print("Average time for read:         " f"{rt.read_times.get_avg()*1e3:.3f} ms") 
        print("Average time waiting for draw: " f"{rt.wait_for_draw_times.get_avg()*1e3:.3f} ms")
        print("Average time waiting for read: " f"{vt.wait_for_read_times.get_avg()*1e3:.3f} ms")
        print("Average FPS: " f"{1/vt.fps_timer.get_avg():.2f}")

    if not SAFE_EXIT:
        time.sleep(1.2) # Wait for threads to finish printing stuff
        print("")
        print("") # One more for good measure
        input("Enter to close")
    else:
        print("")
        print("")

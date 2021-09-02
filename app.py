import tkinter as tk

from numpy.lib.utils import info
import src.threads
import src.stream

CONFIG_PATH = "config.txt"

class ParseError(Exception):
    def __init__(self):
        super(ParseError, self).__init__()

def _parse(val):
    if "PI" in val:
        val = val.replace("PI", "3.1415926535")
    try:
        val = eval(val, {})
    except Exception as e:
        print("Error evaluating config value.")
        print("Value to parse: " + str(val))
        print("Error: " + str(e))
        raise ParseError()
    finally:
        return val

def read_config(path):
    try:
        config = {}
        with open(path, 'r') as f:
            for line in f:
                name, value = line.split("=")
                config[name.strip()] = _parse(value.strip())

    except IOError as e:
        print("Error reading config file: \n%s" % e)
        return None
    except ParseError:
        print("Unable to parse config file.")
    except Exception as e:
        print("Error parsing config file: \n%s" % e)
    else:
        return config

class Bindables(dict):
    # Just to make coding a bit simpler
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__
    
class WavisApp(tk.Tk):
    bindables = {}
    """ Wavis Application """
    def __init__(self, stream: src.stream.Stream, config=None,# draw_thread: src.threads.VisThread, read_thread: src.threads.ReadThread, 
            parent=None, exit_func=None, **kwargs):
        """ Initialises the application. Requires a Stream object to be provided. 

        By default config values will be read
        from `config.txt`, or a path can be provided under `config`, or the config 
        dictionary itself can be provided.

        A parent Tk object can optionally be provided, but should probably be left as `None`.
        """
        super(WavisApp, self).__init__(parent, **kwargs)
        self.stream = stream
        #  == Read config ==  #
        if config is None:
            config = CONFIG_PATH
        if type(config) is str:
            config = read_config(config)
        # Otherwise, config should be a dictionary.

        # Keys in config.txt will be equivalent to attribute and property
        # names generated from this. These lines create properties that
        # effectively bind the backend and frontend values by requesting 
        # a frontend update everytime they are changed. 
        for _key, value in config.items():
            key = str(_key)
            setattr(self, "_"+key, value)
            def fget(self, __key=key):
                return getattr(self, "_"+str(__key))
            def fset(self, val, __key=key):
                setattr(self, "_"+str(__key), val)
                self._request_update=True
            setattr(WavisApp, str(key), property(
                fget=fget, fset=fset
            ))
        #  =================  #
        self.parent = parent
        self.update_thread = src.threads.TickThread(0.4, self.update_info)
        self.update_thread.start()
        self._info_text = "Welcome to Wavis"
        self._request_update = False
        self._borders = 0
        self._keep_on_top = False
        self._exit_func = exit_func
        self.canvas = self.initialise()

        self.read_thread = src.threads.ReadThread(self.bits_per_read, self.stream)
        self.vis_thread = src.threads.VisThread(
            self, self.radians_per_read, self.amplitude, pen_colour=self.pencolour
        )

    def update_info(self):
        self._info_text = f"Draw time: {self.vis_thread.draw_times.get_avg()*1e3:.2f} ms | " \
            f"Wait for draw time: {self.read_thread.wait_for_draw_times.get_avg()*1e3:.2f} ms | " \
            f"Read time: {self.read_thread.read_times.get_avg()*1e3:.2f} ms | " \
            f"Wait for read time: {self.vis_thread.wait_for_read_times.get_avg()*1e3:.2f} ms | " \
            f"FPS: {1/self.vis_thread.fps_timer.get_avg():.2f}" 
        # self.bindables.
        self._request_update = True

    def do_update(self):
        self.update()
        if self._request_update:
            self.info_label.configure(text=self._info_text)
            self.amp_scale.set(self.amplitude)
            self._request_update = False

    def on_exit(self, func):
        """ `func` will be called with no arguments when the escape key is pressed."""
        self._exit_func = func

    def stop(self):
        self.read_thread.kill()
        self.vis_thread.kill()
        self.update_thread.kill()
        if self._exit_func is not None:
            self._exit_func()
        self.destroy()


    def initialise(self):
        """ Initialises front end and returns a handle for the canvas.
        """
        # master = tk.Tk()
        self.configure(background="black")

        # Main pane: [ controls | <vis pane> ]
        main_pane = tk.PanedWindow(self, relief="raised", bg="black", orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True)

        ## Controls
        control_frame = tk.LabelFrame(main_pane, text="Controls", padx=5, pady=5, width=50)
        control_frame.pack(fill=tk.BOTH, expand=True)
        main_pane.add(control_frame, stretch="always")
        control_frame.grid_columnconfigure(0, weight=1)

        self._controls_hidden = False
        self.main_pane = main_pane
        self.control_frame = control_frame

        stop_btn = tk.Button(control_frame, text="Stop", width=8, command=self.stop)
        stop_btn.grid(row=0, column=0)
        self.stop_btn = stop_btn
        
        def set_amp(x):
            self.amplitude = float(x)
        amp_scale = tk.Scale(control_frame, orient=tk.HORIZONTAL, label="Amplitude", from_=0, to=100,
            command=set_amp)
        amp_scale.set(self.amplitude)
        amp_scale.grid(row=1, column=0, sticky=tk.W+tk.E)
        self.amp_scale = amp_scale

        ## Visualiser
        vis_pane = tk.PanedWindow(main_pane, bg="black", relief="raised", orient=tk.VERTICAL)
        main_pane.add(vis_pane, stretch="always")
        
        width, height = 500, 500
        canvas = tk.Canvas(vis_pane, width=width, height=height)
        canvas.configure(bg="black", highlightbackground="black")
        vis_pane.add(canvas, stretch="always")

        ## Data bar
        info_label = tk.Label(vis_pane, text=self._info_text, height=1)
        vis_pane.add(info_label, stretch="never")
        self._info_visible = True
        self.vis_pane = vis_pane
        self.info_label = info_label
                
        return canvas
    
    def toggle_info(self, *args):
        if self._info_visible:
            self.vis_pane.remove(self.info_label)
            self._info_visible = False
        else:
            self.vis_pane.add(self.info_label)
            self._info_visible = True
    
    def toggle_controls(self, *args):
        self._controls_hidden = ~self._controls_hidden
        self.main_pane.paneconfigure(self.control_frame, hide=self._controls_hidden) 

    def bind_keys(self):
        vt = self.vis_thread
        rt = self.read_thread
        the_stream = self.stream
        def toggle_border(*args):
            self._borders = 0 if self._borders else 1
            self.overrideredirect(self._borders)
        def toggle_keep_on_top(*args):
            self._keep_on_top = False if self._keep_on_top else True
            self.attributes('-topmost', self._keep_on_top)
        def up_scale(*args):
            self.amplitude = self.amplitude * 1.05
        def down_scale(*args):
            self.amplitude = self.amplitude / 1.05
        def up_rps(*args):
            rt.bits_per_read *= 1.05
        def down_rps(*args):
            rt.bits_per_read /= 1.05
        def up_rpb(*args):
            vt.rads_p_read *= 1.05
        def down_rpb(*args):
            vt.rads_p_read /= 1.05
        def up_x_scale(*args):
            vt.x_scale *= 1.05
        def down_x_scale(*args):
            vt.x_scale /= 1.05
        def up_y_scale(*args):
            vt.y_scale *= 1.05
        def down_y_scale(*args):
            vt.y_scale /= 1.05
        def pause(*args):
            if not the_stream.can_pause():
                print("Can't pause this stream.")
                return
            if the_stream.playback.paused:
                the_stream.play()
            else:
                the_stream.pause()
        def stop(*args):
            self.stop()
        def sync(*args):
            the_stream.sync_playback()
        def seek_back(*args):
            the_stream.rseek(-5)
        def seek_forward(*args):
            the_stream.rseek(5)
        
        self.bind("<Key-Up>", up_scale)
        self.bind("<Key-Down>", down_scale)
        self.bind("<Key-.>", up_rps)
        self.bind("<Key-,>", down_rps)
        self.bind("<Key-'>", up_rpb)
        self.bind("<Key-;>", down_rpb)
        self.bind("<Key-l>", up_x_scale)
        self.bind("<Key-j>", down_x_scale)
        self.bind("<Key-i>", up_y_scale)
        self.bind("<Key-k>", down_y_scale)
        self.bind("<Key-Escape>", stop)
        self.bind("<Key-space>", pause)
        self.bind("<Key-s>", sync)
        self.bind("<Key-Left>", seek_back)
        self.bind("<Key-Right>", seek_forward)
        self.bind("<Key-b>", toggle_border)
        self.bind("<Key-t>", toggle_keep_on_top)
        self.bind("<Key-p>", self.toggle_controls)
        self.bind("<Key-p>", self.toggle_info, add=True)
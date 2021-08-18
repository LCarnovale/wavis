import pyaudio
from stream import Stream
import numpy as np
import time

class LiveStream(Stream):
    def __init__(self, bitrate=44100, chunk_size=1024) -> None:
        # stream constants
        self.CHUNK = chunk_size
        self.FORMAT = pyaudio.paInt16
        self.RATE = bitrate

        self.paused = False

        # stream object
        self.p = pyaudio.PyAudio()
        # Get audio source:
        print("Getting available devices...")
        n_devs = self.p.get_device_count()
        choice = -1
        suggest = None
        for i in range(n_devs):
            dev = self.p.get_device_info_by_index(i)
            if dev['maxInputChannels'] != 0:
                # print("* ", end='')
                print(f"{i: 2d}) {dev['name']}")
            if "Stereo Mix" in dev['name'] and suggest is None:
                # Should probably pick this
                suggest = i
        
        self.CHANNELS = 1
        if suggest is not None:
            print("Suggested device: ", suggest)
        else:
            print("============== Note ===============")
            print("If you wish to visualise device output, enable the Stereo Mixer (on Windows).\n"\
                  "This will probably also require that sound is coming from the device card,\n"\
                  "ie the computer's speakers, or an audio jack. It can't go into an external\n"\
                  "device, such as a bluetooth device. However, the audio of the Stereo Mixer \n" \
                  "can go into any other device. (hint hint)")
            print("===================================")
            print("If you wish to visualise audio from a normal audio input (like a microphone)")
            print("Then simply select it from below.")
        while (choice < 0 or choice >= n_devs):
            try:
                choice = int(input("Select a device >>> "))
            except:
                pass
        print(f"Using device {choice}: " + self.p.get_device_info_by_index(choice)['name'])
        
        self.stream = self.p.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            input_device_index=choice,
            frames_per_buffer=self.CHUNK,
        )
        super().__init__(bitrate=bitrate)

    def read(self, chunk_size):
        """ Returns a simulated time array and live data
        """
        time_now = time.time()

        time_steps = np.linspace(time_now - chunk_size/self.bitrate, time_now, chunk_size)
        try:
            data = np.fromstring(self.stream.read(chunk_size), dtype=np.int16)
        except Exception as e:
            print("Error on read - did something happen to the device?")
            print("Error:", e)
            return [], []
        return time_steps, data
    
    def play(self):
        print("Not implemented for live stream.")
    pause = stop = sync_playback = play
    def seek(self, val):
        print("Not implemented for live stream.")
    rseek = seek

    def can_pause(self):
        return False
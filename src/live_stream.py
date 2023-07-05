from enum import Enum
import time

import numpy as np
import pyaudio

from .stream import Stream


class LiveStream(Stream):
    class Format(Enum):
        Int16 = (pyaudio.paInt16, np.int16)
        Int24 = (pyaudio.paInt24, np.int32)
        Int32 = (pyaudio.paInt32, np.int32)

    """ Access a live source of audio such as microphone or other audio input."""
    def __init__(self, bitrate=44100, format:Format=Format.Int16, chunk_size=2048, requested_channels=1,
            device_index=-1) -> None:
        """ Create a new LiveStream source. Note that in the `__init__` method,
        the user will be prompted to specify the desired device for audio input,
        unless `device_index` is set to a valid device index.
        
        `bitrate`: default 44100, sampling rate in Hz.
        `chunk_size`: default 1024, the size of the chunk issued to the
            pyaudio audio stream. Does not represent the fixed size of each read,
            this is variable. Not entirely sure what different values of this will do.
        `requested_channels`: default 1, the number of channels to request from the 
            audio source. If 2 are requested, but the source only gives 1, then
            that 1 will still be used. `.read()` will be able to return 1 or 2 channels
            regardless. (See `LiveStream.read`)
        `device_index`: If provided, this device will attempted to be loaded as
            an audio source. If it fails, or if this value is not provided,
            the user will be prompted to select one.

            
        """
        # stream constants
        self.CHUNK = chunk_size
        # Extract Format enum value from supplied format
        self.FORMAT, self.dtype = LiveStream.Format(format).value
        self.RATE = bitrate

        self.paused = False

        # stream object
        print("Loading pyAudio...")
        self.p = pyaudio.PyAudio()
        # Get audio source:
        skip_prompt = False
        if device_index >= 0:
            try:
                device = self.p.get_device_info_by_index(device_index)
                print(f"Using device {device_index}: " + device['name'])
                self.CHANNELS = max(requested_channels, device['maxInputChannels'])
                self.stream = self.p.open(
                    format=self.FORMAT,
                    channels=self.CHANNELS,
                    rate=self.RATE,
                    input=True,
                    input_device_index=device_index,
                    frames_per_buffer=self.CHUNK,
                )
            except Exception as e:
                print("Opening device index %d failed: "%device_index + str(e))
                skip_prompt = False
            else:
                skip_prompt = True
        if not skip_prompt:
            print("Getting available devices...")
            n_devs = self.p.get_device_count()
            choice = device_index
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
                print("Then just select it from below.")
            while (choice < 0 or choice >= n_devs):
                try:
                    choice = int(input("Select a device >>> "))
                except:
                    pass
            device = self.p.get_device_info_by_index(choice)
            print(f"Using device {choice}: " + device['name'])
            self.CHANNELS = max(requested_channels, device['maxInputChannels'])
        
            self.stream = self.p.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                input_device_index=choice,
                frames_per_buffer=self.CHUNK,
            )
        super().__init__(bitrate=bitrate)

    def read(self, chunk_size, channels=1):
        """ Returns a simulated time array and live data
        Returns 1 channel by default, if you want 2, set `channels=2`.

        If the stream is only capable of 1 channel but 2 are requested, 
        then the data will be returned in duplicate, ie as if left and right
        channels were equal.
        """
        time_now = time.time()

        time_steps = np.linspace(time_now - chunk_size/self.bitrate, time_now, chunk_size)
        try:
            data = np.fromstring(self.stream.read(chunk_size), dtype=self.dtype)
        except Exception as e:
            print("Error on read - did something happen to the device?")
            print("Error:", e)
            return [], []
        else:
            channelled = np.array([data[i::self.CHANNELS] for i in range(self.CHANNELS)])
            data = channelled[:channels]
            if self.CHANNELS == 1 and channels == 2:
                # Duplicate the single channel
                print("Duplicating")
                data = np.array([data, data])
        return time_steps, data
    
    # These do not cause an exception because I don't want to handle
    # that in the main program, it's not the end of the world if
    # nothing happens and a message just pops out.  
    def play(self):
        print("Not implemented for live stream.")
    pause = stop = sync_playback = play
    def seek(self, val):
        self.play()
    rseek = seek

    def can_pause(self):
        return False

    def close(self):
        self.stream.close()

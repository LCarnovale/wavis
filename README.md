# Introduction
A simple multithreaded sound visualiser written in Python using Turtle. All it really 
does is wrap the waveform around a circle, but I reckon it looks pretty good.

Graphics are done using Turtle. The benefit of this is that if you can run
Python you can almost definitely run most of this program. I didn't always want to use turtle, but it's the only thing that didn't require a lot of effort for me to learn to use. Even though turtle is (very) slow, it still seems to be fast enough, at least on my laptop. 
The use of two threads to simultaneously read sound data and draw it on screen provides a significant performance improvement.

There are a few dependencies, for playback: [just_playback](https://github.com/cheofusi/just_playback) made playback a delightfully simple process. It itself has no other dependencies, and can be pip'd:

    pip install just_playback

Also required:
- `numpy` For (fast) mathematical operations. 
- `scipy` For reading audio files.

For visualising device audio, `pyaudio` is needed. In general google will be your friend for getting it, but for python 3.4-3.6 `pip` will do the job:

    pip install pyaudio

Other versions of python may require finding `.whl`'s on the internet and
manually installing it (which isn't too hard, I managed to do it).
# Usage
### Song playback
There are two modes of operation. With a file supplied as an argument:

    python wavis.py "A file.wav"

_Wavis_ will play the song and have a visualiser along with it. The 
keyboard controls below all apply. 

### Visualise Device Audio

Without arguments, it will attempt to listen to device audio.
You will be prompted to select a device. If you wish to use a microphone,
selecting one should "just work". If you want to listen to device audio,
for Windows, you will need to use the Stereo Mix service. I assume there
is something similar for other operating systems.   

Note that by virtue of using multiple threads the program is vulnerable to hanging on some types of exceptions. Most common ones have been accounted for but it has not been extensively tested. I would be wary of changing audio output devices etc during playback (although it might work fine).
The cleanest way to stop the program will always be pressing <kbd>Esc</kbd> with focus on the frontend graphics (Turtle) screen.

I have only tried it with `.wav`'s, but it could potentially work with anything that `scipy.io.wavfile.read` works with
(this does not include mp3s).

Once the program is started, the turtle display should pop up with the visualiser visualising, and playback should also begin. Sometimes there is a slight delay in the playback which offsets it from the visualiser, press `s` to resynchronise them.

Keyboard controls:

| Key | Function|
|-----|---------|
| <kbd>&#8592;</kbd>/<kbd>&#8594;</kbd> | Jump backward/forward 5 seconds in playback |
|<kbd>s</kbd> | Resynchronise playback to match visualisation |
| <kbd>space</kbd> | Pause/resume (Note for some reason playback will resume from the beginning, you can bring it back with <kbd>s</kbd>.) |
| <kbd>&#8593;</kbd>/<kbd>&#8595;</kbd> | Increase / Decrease the amplitude of the waveform |
| <kbd>j</kbd>/<kbd>l</kbd> | Decrease/Increase horizontal scale |
| <kbd>k</kbd>/<kbd>i</kbd> | Decrease/Increase vertical scale |
| <kbd>,</kbd>/<kbd>.</kbd> | Decrease/Increase number of sound bytes read in each tick (ie the chunk size) |
| <kbd>;</kbd>/<kbd>'</kbd> | Decrease/Increase the angular spread between each sound byte. Effectively spreads each arc over smaller/larger angle. |
| <kbd>Esc</kbd> | Stop |

When finishing the program will display the average time of reading, drawing
and the time those two threads spent waiting for the other. If you get low
framerates, you can usually speed it up by decreasing the number of bytes read in each tick (<kbd>,</kbd>), and if that ends up looking too jagged on the front you can try stretch out the arcs with <kbd>'</kbd>.

# Example
The last minute or so of Flume - Helix:
![Visualisation GIF](./Animation.gif)

Included in the repository is a sample royalty free audio file
I nabbed from [bensound](https://www.bensound.com/royalty-free-music/track/dubstep). 

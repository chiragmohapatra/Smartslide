from __future__ import absolute_import, print_function, unicode_literals

import argparse
import audioop
import math
import multiprocessing
import os
import subprocess
import sys
import tempfile
import wave
import json
import requests
try:
    from json.decoder import JSONDecodeError
except ImportError:
    JSONDecodeError = ValueError

from googleapiclient.discovery import build
from progressbar import ProgressBar, Percentage, Bar, ETA

from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip

GOOGLE_SPEECH_API_KEY = "AIzaSyBOti4mM-6x9WDnZIjIeyEU21OpBXqWBgw"
GOOGLE_SPEECH_API_URL = "http://www.google.com/speech-api/v2/recognize?client=chromium&lang={lang}&key={key}"

DEFAULT_SUBTITLE_FORMAT = 'json'
DEFAULT_CONCURRENCY = 10
DEFAULT_SRC_LANGUAGE = 'en'
DEFAULT_DST_LANGUAGE = 'en'

def percentile(arr, percent):
    """
    Calculate the given percentile of arr.
    """
    assert len(arr)>0
    arr = sorted(arr)
    index = (len(arr) - 1) * percent
    floor = math.floor(index)
    ceil = math.ceil(index)
    if floor == ceil:
        return arr[int(index)]
    low_value = arr[int(floor)] * (ceil - index)
    high_value = arr[int(ceil)] * (index - floor)
    return low_value + high_value

class FLACConverter(object): # pylint: disable=too-few-public-methods
    """
    Class for converting a region of an input audio or video file into a FLAC audio file
    """
    def __init__(self, source_path, include_before=0.25, include_after=0.25):
        self.source_path = source_path
        self.include_before = include_before
        self.include_after = include_after

    def __call__(self, region):
        try:
            start, end = region
            start = max(0, start - self.include_before)
            end += self.include_after
            temp = tempfile.NamedTemporaryFile(suffix='.flac', delete=False)
            command = ["ffmpeg", "-ss", str(start), "-t", str(end - start),
                       "-y", "-i", self.source_path,
                       "-loglevel", "error", temp.name]
            use_shell = True if os.name == "nt" else False
            subprocess.check_output(command, stdin=open(os.devnull), shell=use_shell)
            read_data = temp.read()
            temp.close()
            os.unlink(temp.name)
            return read_data

        except KeyboardInterrupt:
            return None

class SpeechRecognizer(object): # pylint: disable=too-few-public-methods
    """
    Class for performing speech-to-text for an input FLAC file.
    """
    def __init__(self, language="en", rate=44100, retries=3, api_key=GOOGLE_SPEECH_API_KEY):
        self.language = language
        self.rate = rate
        self.api_key = api_key
        self.retries = retries

    def __call__(self, data):
        try:
            for _ in range(self.retries):
                url = GOOGLE_SPEECH_API_URL.format(lang=self.language, key=self.api_key)
                headers = {"Content-Type": "audio/x-flac; rate=%d" % self.rate}

                try:
                    resp = requests.post(url, data=data, headers=headers)
                except requests.exceptions.ConnectionError:
                    continue

                for line in resp.content.decode('utf-8').split("\n"):
                    try:
                        line = json.loads(line)
                        line = line['result'][0]['alternative'][0]['transcript']
                        return line[:1].upper() + line[1:]
                    except IndexError:
                        # no result
                        continue
                    except JSONDecodeError:
                        continue

        except KeyboardInterrupt:
            return None

def which(program):
    """
    Return the path for a given executable.
    """
    def is_exe(file_path):
        """
        Checks whether a file is executable.
        """
        return os.path.isfile(file_path) and os.access(file_path, os.X_OK)

    fpath, _ = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file
    return None

def extract_audio(filename, channels=1, rate=16000 , suf='.wav'):
    """
    Extract audio from an input file to a temporary WAV file.
    """
    temp = tempfile.NamedTemporaryFile(suffix=suf, delete=False)
    if not os.path.isfile(filename):
        print("The given file does not exist: {}".format(filename))
        raise Exception("Invalid filepath: {}".format(filename))
    if not which("ffmpeg"):
        print("ffmpeg: Executable not found on machine.")
        raise Exception("Dependency not found: ffmpeg")
    command = ["ffmpeg", "-y", "-i", filename,
               "-ac", str(channels), "-ar", str(rate),
               "-loglevel", "error", temp.name]
    use_shell = True if os.name == "nt" else False
    subprocess.check_output(command, stdin=open(os.devnull), shell=use_shell)
    return temp.name, rate


def find_speech_regions(filename, frame_width=4096, min_region_size=0.5, max_region_size=6): # pylint: disable=too-many-locals
    """
    Perform voice activity detection on a given audio file.
    """
    reader = wave.open(filename)
    sample_width = reader.getsampwidth()
    rate = reader.getframerate()
    n_channels = reader.getnchannels()
    chunk_duration = float(frame_width) / rate

    n_chunks = int(math.ceil(reader.getnframes()*1.0 / frame_width))
    energies = []

    for _ in range(n_chunks):
        chunk = reader.readframes(frame_width)
        energies.append(audioop.rms(chunk, sample_width * n_channels))

    if len(energies)==0:
        return []
    threshold = percentile(energies, 0.2)

    elapsed_time = 0

    regions = []
    region_start = None

    for energy in energies:
        is_silence = energy <= threshold
        max_exceeded = region_start and elapsed_time - region_start >= max_region_size

        if (max_exceeded or is_silence) and region_start:
            if elapsed_time - region_start >= min_region_size:
                regions.append((region_start, elapsed_time))
                region_start = None

        elif (not region_start) and (not is_silence):
            region_start = elapsed_time
        elapsed_time += chunk_duration
    return regions


def generate_subtitles( # pylint: disable=too-many-locals,too-many-arguments
        source_path,
        output=None,
        concurrency=DEFAULT_CONCURRENCY,
        src_language=DEFAULT_SRC_LANGUAGE,
        dst_language=DEFAULT_DST_LANGUAGE,
        subtitle_file_format=DEFAULT_SUBTITLE_FORMAT,
        api_key=None,
    ):
    """
    Given an input audio/video file, generate subtitles in the specified language and format.
    """
    audio_filename, audio_rate = extract_audio(source_path)

    regions = find_speech_regions(audio_filename)
    if len(regions)==0:
        return []

    pool = multiprocessing.Pool(concurrency)
    converter = FLACConverter(source_path=audio_filename)
    recognizer = SpeechRecognizer(language=src_language, rate=audio_rate,
                                  api_key=GOOGLE_SPEECH_API_KEY)

    transcripts = []
    if regions:
        try:
            widgets = ["Converting speech regions to FLAC files: ", Percentage(), ' ', Bar(), ' ',
                       ETA()]
            pbar = ProgressBar(widgets=widgets, maxval=len(regions)).start()
            extracted_regions = []
            for i, extracted_region in enumerate(pool.imap(converter, regions)):
                extracted_regions.append(extracted_region)
                pbar.update(i)
            pbar.finish()

            widgets = ["Performing speech recognition: ", Percentage(), ' ', Bar(), ' ', ETA()]
            pbar = ProgressBar(widgets=widgets, maxval=len(regions)).start()

            for i, transcript in enumerate(pool.imap(recognizer, extracted_regions)):
                transcripts.append(transcript)
                pbar.update(i)
            pbar.finish()

        except KeyboardInterrupt:
            pbar.finish()
            pool.terminate()
            pool.join()
            print("Cancelling transcription")
            raise

    timed_subtitles = [(r, t) for r, t in zip(regions, transcripts) if t]
    """
    formatter = FORMATTERS.get(subtitle_file_format)
    formatted_subtitles = formatter(timed_subtitles)

    dest = output

    if not dest:
        base = os.path.splitext(source_path)[0]
        dest = "{base}.{format}".format(base=base, format=subtitle_file_format)

    with open(dest, 'wb') as output_file:
        output_file.write(formatted_subtitles.encode("utf-8"))
    """

    os.remove(audio_filename)
    return timed_subtitles

    #return dest

"""
(subtitles,audio_filename) = generate_subtitles(source_path='./data/samplevid.mp4')
print(audio_filename)

for sub in subtitles:
    print(sub)
"""

# times is a list of tuples (starttime,endtime)
def generate_subclips(filename,times):
    i = 1
    for time in times:
        ffmpeg_extract_subclip(filename, time[0], time[1], targetname='./temp/' + str(i) + '.mp4')
        i+=1

def remove_subclips(times):
    i = 1
    for _ in times:
        os.remove('./temp/' + str(i) + '.mp4')
        i+=1

"""
times = [(0,2),(3,5)]
generate_subclips('./data/samplevid.mp4' , times)
remove_subclips(times)
"""

def convert_subs_to_string(subs):
    ans_str = ''
    for sub in subs:
        ans_str = sub[1] + '\n'
    return ans_str

# This is the main function, use this
# returns a list of tuples of subtitles in string form and mp3 files
def generate_subs(filename,times):
    os.makedirs(os.path.join("./temp/"), exist_ok=True)

    ans = []
    generate_subclips(filename , times)

    i = 1
    for _ in times:
        src_path = './temp/' + str(i) + '.mp4'
        subtitles = generate_subtitles(source_path=src_path)
        subs = convert_subs_to_string(subtitles)
        audio_filename, audio_rate = extract_audio(src_path,suf='.mp3')
        os.system("cp " + audio_filename + " ./temp/" + str(i) + '.mp3')
        ans.append((subs,"./temp/" + str(i) + '.mp3'))
        i+=1
        
    remove_subclips(times)
    return ans

"""
times = [(0,2),(3,12)]
subs = generate_subs('./data/samplevid.mp4' , times)

for sub in subs:
    print(sub)
"""

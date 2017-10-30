import numpy as np
from scipy import signal
from pprint import pprint

DEBUG = False


def plot(*args, **kwargs):
    if DEBUG:
        import matplotlib.pyplot as plt
        plt.plot(*args, **kwargs)
        plt.legend()
        plt.show()


def write(arg):
    if DEBUG:
        pprint(arg)


def average_signal(data, conf):
    N = conf.get('CONV_N', 1000)
    signal_mean = np.convolve(
        (data / 10) ** 2, np.ones((N,)) / N, mode='valid')
    return signal_mean


@np.vectorize
def samples_to_seconds(sample, rate):
    """
    Converts a number of samples to it's time in seconds
    """
    return sample / rate


@np.vectorize
def seconds_to_samples(seconds, rate):
    """
    Converts a time in seconds to a number of samples
    """
    return int(np.round(seconds * rate))

def seconds_to_spectral_index(seconds, t_labels):
    #we need this so seconds can be vectorized over, but not t_labels
    @np.vectorize
    def inner_compute(second):
        idx = (np.abs(t_labels-second)).argmin()
        return idx

    return inner_compute(seconds)


def calculate_threshold(data, conf):
    """
    Calculates a threshold for determaning if a note is sounding
    data should be a meaned signal
    """
    d = conf.get('THRES_D', 10)
    mean = np.mean(data)
    return np.abs(mean) / d


def calculate_note_locations(data, conf):
    """
    Returns a boolean array that is true when a note is sounding at the time indicated by that index in samples
    e.g. If a note was sounding at 340 samples, ret[340] == True
    """
    signal = average_signal(data, conf)
    threshold = calculate_threshold(signal, conf)

    #write(threshold)
    plot(signal, label='signal')

    where_note = signal > threshold

    where_note_average = average_signal(where_note, conf)

    #ensure there is a crossing point at the bening and end of the song
    where_note_average[0] = 0
    where_note_average[-1] = 0

    #plot(where_note_average, label='where_note_average')

    basicly_boolean_zero = conf.get('BOOL_ZERO_NEAR', 0.008)
    where_note_average_not_zero = where_note_average > basicly_boolean_zero

    return where_note_average_not_zero


def find_edge(xs, sign):
    """
    Find places where xs changes by sign. Xs must be boolean

    Sign should be 1 for rising edges and -1 for falling edges
    """
    xs_int = xs.astype(np.int8)  # Cast to int so falling edges and rising edges look different
    diff = np.diff(xs_int)
    plot(diff, label='diff')
    return np.where(diff == sign)[0]


def calculate_note_start_times(where_note):
    return find_edge(where_note, 1)


def calculate_note_start_end(where_note):
    return find_edge(where_note, -1)


def get_note_times(rate, data, conf):
    """
    Returns the time the center of each note occured, in seconds.
    """

    #plot(data)
    where_note = calculate_note_locations(data, conf)
    plot(where_note, label='where_note')

    start_times = calculate_note_start_times(where_note)
    end_times = calculate_note_start_end(where_note)

    write("start_times"+str(start_times))
    write("end_times"+str(end_times))

    times = (start_times + end_times) / 2.0
    write("sampletimes" + str(times))

    #plot(start_times, 'ro', label='start times')
    #plot(end_times, 'ro', label='end times')
    plot(times, 'ro', label='times')

    return samples_to_seconds(times, rate)

def generate_spectogram(conf, data, rate):
    nperseg = conf.get('NPERSEG',1000)
    nfft = conf.get('NFFT',5000)

    f, t, Sxx = signal.spectrogram(data, rate, nperseg=nperseg, nfft=nfft )

    return f,t,Sxx


def findFundamental(frequency, power, noise_floor):
    #first_derivative = np.gradient(power)
    #zero_crossings = np.where(np.diff(np.sign(first_derivative)))[0]
    #write(zero_crossings)

    for test_point in range(len(power)):
        #write("---------")
        #write(noise_floor)
        #write(test_point)
        #write(power[test_point])
        if power[test_point] > noise_floor:
            return frequency[test_point + 1]

    return None

def approximateNoiseFloor(power_spectrum,conf):

    scaler = conf.get('NF_SCALER', 0.85)

    maxp = np.max(power_spectrum)
    minp = np.min(power_spectrum)

    return (minp + scaler * ( maxp - minp))


def get_note_pitches(rate, data, note_times, conf):

    arr = np.zeros_like(note_times)
    f,t,Sxx = generate_spectogram(conf, data, rate)
    #plt.pcolormesh(t,f,Sxx)
    #plt.show()

    for i in range(len(note_times)):
        time = note_times[i]
        idx = seconds_to_spectral_index(time, t)
        power_spectrum = Sxx[:,idx]
        noise_floor = approximateNoiseFloor(power_spectrum, conf)
        fundamental = findFundamental(f,power_spectrum,noise_floor)

        if DEBUG:
            import matplotlib.pyplot as plt
            import pandas as pd
            notes = pd.read_csv('Notes.csv')

            plt.plot(f,power_spectrum, label="power spectrum")
            plt.plot([fundamental, fundamental], [0,max(power_spectrum)], )
            plt.plot([ 0, max(f) ], [noise_floor,noise_floor])

            note_pitches = notes['Frequency (Hz)'].values
            note_names = notes['Note'].values

            name_idx = (np.abs(note_pitches - fundamental)).argmin()
            name = note_names[name_idx]

            plt.title(name)
            plt.xticks(note_pitches, note_names)
            plt.xlim(0,1000)
            plt.show()

        arr[i] = fundamental

    return arr


def plot_pitch_vs_time(pitches, times):
    if DEBUG:
        import matplotlib.pyplot as plt
        import pandas as pd
        plt.plot(times, pitches, 'ro')
        notes = pd.read_csv('Notes.csv')
        plt.yticks(notes['Frequency (Hz)'].values, notes['Note'].values)
        plt.show()


class Note(object):

    def __init__(self, name, time):
        self.name = name
        self.time = time

    def __repr__(self):
        return f'<Note {self.name} at {self.time:1.4f}s >'

def convert(rate, data, conf = {}):
    """
    Converts a audio file into a serise of notes
    """
    times = get_note_times(rate, data, conf)
    pitches = get_note_pitches(rate, data, times, conf)
    #plot_pitch_vs_time(pitches,times)

    note_pitches = conf.get('NOTE_PITCHES')
    note_names = conf.get('NOTE_NAMES')

    notes = []
    for i in range(0,len(times)):
        name_idx = (np.abs(note_pitches - pitches[i])).argmin()
        notes.append( Note(note_names[name_idx], times[i]) )


    return notes

if __name__ == '__main__':
    from scipy.io import wavfile
    import pandas as pd

    DEBUG = True

    notes = pd.read_csv('Notes.csv')
    note_pitches = notes['Frequency (Hz)'].values
    note_names = notes['Note'].values

    rate, rawData = wavfile.read("../Audio/inst/c-major.wav")
    data = rawData[:, 0]

    res = convert(rate, data, conf = {
        'NOTE_PITCHES': note_pitches,
        'NOTE_NAMES': note_names
    })

    print(res)

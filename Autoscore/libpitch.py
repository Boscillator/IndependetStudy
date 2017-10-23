import numpy as np
import matplotlib.pyplot as plt
import re
from scipy import signal
from scipy import stats
import csv

class Note(object):
    
    def __init__(self, startTime, endTime, name, power):
        self.startTime = startTime
        self.endTime = endTime
        self.name = name
        self.power = power
        
    def __str__(self):
        return self.name
    
    def __repr__(self):
        return 'Note {name} started at {time}s, endedAt {endTime}, with a power of {power}'.format(name = self.name,
                                                                                                   time = self.startTime,
                                                                                                   endTime = self.endTime,
                                                                                                   power = self.power)
    
    def toLilyPond(self):
        pattern = re.compile(r'(.)(#)?(\d)')
        match = pattern.match( self.name )
        
        if match == None:
            raise Exception('I will not sit back and continue to allow, communist indoctrication, communist infiltration, and the international communist consperisy to sap and impurify our pressuse bodily fluids')
        
        letter = match.group(1).lower()
        sharp_group = match.group(2)
        octave = int(match.group(3))
        
        if sharp_group:
            sharp = 'is'
        else:
            sharp = ''
        
        return letter + sharp + ('\'' * (octave-2))

def getNotePiches(fname = "Notes.csv"):
    """
    Gets a list of note names and there frequency
    
    Parameters
    ----------
    fname : string
        the name of the csv file to load the data from.
    
    Returns
    -------
    notes : list of str
        The names of the notes
    freqs : list of float
        The frequencies the notes are at
    """
    notes_and_freqs = ([],[])

    with open(fname,'r') as csvfile:
        reader = csv.reader(csvfile)
        next(reader,None)    #skip header
    
        for row in reader:
            notes_and_freqs[0].append(row[0])
            notes_and_freqs[1].append(float(row[1]))

    return notes_and_freqs
            
def _createZeroCrossIndex(xs):
    """
    Finds where `xs` crosses 0. Returns an array the same length as `xs`. This array is false everywhere,
    except at the indecies where `xs` crosses.
    
    Paramiters
    ----------
    xs : array of numbers
        the data to analise
    
    Returns
    -------
    array of bool
        True when `xs` crosses 0.
    """
    
    #user to store output
    arr = np.zeros_like(xs, dtype=bool)
    
    #iterate through xs in pairs
    for i in range(1, len(xs)):
        #if the pair has opposite sign
        if xs[i-1] * xs[i] <= 0:
            arr[i] = True
            
    return arr

def _createHarmonicsArray(xs,noise_floor=70000):
    """
    Returns an array repersenting the locatoin of the harmonics of `xs`. The array is true at the indexes where the is a harmonic at `xs`.
    
    Paramaters
    ----------
    xs : array of float
        An array of power vs frequency.
    noise_floor : float
        The value to ignore harmonics with less power than
        
    Returns
    -------
    array of bool
        Same length as `xs`. True where there is a harmonic, false elsewhere.
    """
    arr = np.zeros_like(xs, dtype=bool)
    grad = np.gradient(xs)
    critical_values = _createZeroCrossIndex(grad)
    
    for i in range(0,len(critical_values)):
        if (critical_values[i] == True) and (xs[i] > noise_floor):
            arr[i] = True
            
    return arr

def findFundamental(frequency, power, noise_floor = 10000):
    """
    Finds the fundamental frequency of a power spectrum.
    
    Paramiters
    ----------
    frequency : array of float
        An array repersenting what frequency goes at what index. Should be output from scipy.signal.spectogram
    power : array of float
        The power sepectrum to search
    noise_floor : float
        Ignore any harmonics with less power than this value.
        
    Returns
    -------
    float
        The frequency, in the same units as `frequency`, of the fundamental.
    """
    harmonics = _createHarmonicsArray(power, noise_floor=noise_floor)
    try:
        fundamentalIndex = np.argwhere(harmonics)[0]
    except IndexError:
        return None
    
    return frequency[fundamentalIndex]

def _createPowerArray(t,Sxx, method=max):
    """
    Finds the power of time of a spectrogram. Does this be finding the max power at each time interval.
    
    Paramaters
    ----------
    t : array of float
        An array reperesenting the time at each index. Returned from scipy.signal.spectogram
    Sxx : 2d array of float
        The spectogram output. Returned from scipy.signal.spectogram
        
    Returns
    -------
    array of float:
        the power at each time slot.
    """
    arr = np.zeros_like(t)
    for i in range(0,len(t)):
        arr[i] = method( Sxx[:,i] )
        
    return arr

def _createVSquard(vs):
    
    return vs ** 2

def approximateNoiseFloor(t,Sxx, scaler = 0.1):
    powers = _createPowerArray(t,Sxx)
    
    maxp = max(powers)
    minp = min(powers)
    
    return (minp + scaler * ( maxp - minp))

def findFundamentalOverTime(f,t,Sxx):
    
    noise_floor = approximateNoiseFloor(t,Sxx)
    
    arr = np.zeros(Sxx.shape[1])
    
    #for each time slice
    for i in range(0, Sxx.shape[1] ):
        power_spectrum = Sxx[:,i]    #Get the power spectrum at that time
        fundamental = findFundamental(f, power_spectrum, noise_floor)
        arr[i] = fundamental
    
    return arr

def _createSplits(t, bpm, splitPerBeat = 0.25):
    
    splitLength = bpm / 60 * splitPerBeat
    splitsTime = np.arange( 0, max(t), splitLength)
    splits = np.array( [ np.argwhere( t >= s)[0][0] for s in splitsTime] )
    
    return splitsTime, splits

def _findNearestIdx(array, value):
    return (np.abs( array-value )).argmin()

def getNotes(data,rate, bpm, splitPerBeat = .125):
    
    #Initalize output
    out = []
    
    #Calculate data to start with
    f,t,Sxx = signal.spectrogram(data,rate, nperseg=1000, nfft=5000)
    
    
    pwr = data ** 2.0
    
    #plt.plot(pwr)
    #plt.show()
    
    FoT = findFundamentalOverTime(f,t,Sxx)
    
    splitsTime, splits = _createSplits(t, bpm, splitPerBeat)
    
    note_names, note_freqs = getNotePiches()
    
    #For each time slice
    for i in range( 1, len(splits) ):
    
        selection = FoT[ splits[ i-1] : splits[i] ]
        selection_t = t[ splits[ i-1] : splits[i] ]
        
        mode = stats.mode(selection)[0][0]

        
        if mode == 0:
            continue
        
        note_idx = _findNearestIdx(note_freqs, mode)
        name = note_names[ note_idx ]
        
        out.append( Note(selection_t[0], selection_t[-1], name, None) )
        
    return out
    
from Autoscore import celery, app
#from Autoscore.libpitch import getNotes
import Autoscore.dsp
import numpy as np
import re
#import matplotlib.pyplot as plt
from celery import uuid
from subprocess import call
import base64
import pandas as pd

def extract_note_lilypond(note):

    #Group 1: Letter name
    #Group 2: == '#' if sharp
    #Group 3: Octave Number
    regex = r"([A-Z])(.)?([0-9])"

    match = re.search(regex, note.name)

    out = ""
    out += match.group(1).lower()
    if match.group(2) == "#":
        out += "is"
    out += "'" * (int(match.group(3))-2)
    out += '1'

    return out

def notes_to_lilypond(notes):
    out = ""
    for note in notes:
        out += extract_note_lilypond(note)
        out += " "

    return out

def lilypond_to_pdf(source):
    id = str(uuid()).replace('-','')

    print("Writing source file")
    source_file = open(id + '.ly', 'w')
    source_file.write(source)
    source_file.close()

    print("Compiling sorce file")
    call([ app.config['LILYPOND_INSTALL'], id + '.ly'])

    print("Read sorce file")
    pdf_file = open(id + '.pdf', 'rb')
    pdf = pdf_file.read()
    pdf_file.close()

    return pdf

def create_pdf(notes):
    source =  notes_to_lilypond(notes)
    source = """\\version "2.18.2" \\absolute {\n""" + source + "}"
    print(f"Source compilized: {source}")
    pdf = lilypond_to_pdf(source)
    print("Lilypond lilyponded")
    return pdf


@celery.task()
def convert(rate, data):
    print("Starting task")
    data = np.array(data)
    
    notes = pd.read_csv('Notes.csv')
    note_pitches = notes['Frequency (Hz)'].values
    note_names = notes['Note'].values

    notes = Autoscore.dsp.convert(rate,data, {
        'NOTE_PITCHES': note_pitches,
        'NOTE_NAMES': note_names
    })

    pdf = create_pdf(notes)
    print("PDF mackerated")
    pdf = base64.urlsafe_b64encode(pdf).decode('ascii')

    print("Job Done!")
    return pdf

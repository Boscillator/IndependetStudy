from celery import uuid
from flask import request, redirect, render_template, url_for, make_response
from scipy.io import wavfile
import numpy as np

from Autoscore import app, celery
from Autoscore.tasks import convert

import base64

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert/', methods=['POST'])
def start_convertion():

    file = request.files['file']
    rate, raw_data = wavfile.read(file)
    try:
        data = raw_data[:,0].tolist()
    except:
        data = raw_data.tolist()

    task_id = uuid()
    result = convert.apply_async((rate,data), task_id = task_id)


    return redirect( url_for('get_convertion', id=task_id) ) 

@app.route('/convert/<id>')
def get_convertion(id):
    result = celery.AsyncResult(id)
    status = result.status

    if status == 'SUCCESS':
        pdf = base64.urlsafe_b64decode(result.wait())
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        return response

    else:
        return result.status
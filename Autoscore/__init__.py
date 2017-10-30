import os
from flask import Flask
from celery import Celery

app = Flask(__name__)

def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL']
    )
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery

app.config.update(
    CELERY_BROKER_URL=os.environ.get('REDIS_URL','redis://localhost:6379'),
    CELERY_RESULT_BACKEND=os.environ.get('REDIS_URL','redis://localhost:6379'),
    TMP_DIR = os.environ.get('TMP_DIR','./work/'),
    LILYPOND_INSTALL = os.environ.get('LILYPOND_INSTALL',r"D:\Windoes\Programs\lilypond\usr\bin\lilypond.exe")
    #LILYPOND_INSTALL = "lilypond"
)

celery = make_celery(app)

import Autoscore.routes


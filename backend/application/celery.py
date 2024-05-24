# #!/usr/bin/env python3

from gevent import monkey
monkey.patch_all()
from application import create_app

flaskApp = create_app()
celery_app = flaskApp.extensions["celery"]

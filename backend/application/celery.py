# #!/usr/bin/env python3



from application import create_app

flaskApp = create_app()
celery_app = flaskApp.extensions["celery"]

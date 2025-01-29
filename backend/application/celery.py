# #!/usr/bin/env python3

from gevent import monkey
monkey.patch_all()
from application import create_app

flaskApp = create_app()
celery_app = flaskApp.extensions["celery"]


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):

    from application.workers.tasks import watchMonitoredFleets

    sender.add_periodic_task(
        5*60.0, watchMonitoredFleets, name="watchMonitoredFleets every 5min"
    )

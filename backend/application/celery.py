#!/usr/bin/env python3

from celery import Celery


app = Celery('MFC',
            broker_url = 'redis://localhost',
            result_backend = 'redis://localhost',
            enable_utc = True,
            include=['application.workers.tasks'])


if __name__ == '__main__':
    app.start()

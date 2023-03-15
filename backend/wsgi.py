#!/usr/bin/env python3

from application import create_app, socketioApp

app = create_app()

if __name__ == "__main__":
    #app.run(host='127.0.0.1')
    socketioApp.run(host='0.0.0.0')

#!/usr/bin/env python3
import requests
import time
import random
import threading
import datetime

SLEEP = 60*8
SERVER_NUMBER = 26


def fetch(serverid):
    print(f'Fetching for {serverid}')
    r = requests.get(f'http://10.250.138.14:5000/servers/queryInfo/{serverid}/1')


def main():

    while True:
        print('-- Reloading all')
        jobs = []
        for i in range(1, SERVER_NUMBER+1):
            thread = threading.Thread(target=fetch, args=[i])
            jobs.append(thread)

        for j in jobs:
            j.start()

        for j in jobs:
            j.join()
        print('-- Done reloading at {}'.format(datetime.datetime.now().isoformat()))
        time.sleep(SLEEP)

if __name__ == '__main__':
    main()

import socket

import logging

import requests

from stick.onoffdevice import OnOffDevice

_cache = {}


class Tellstick:
    ts_address = None
    ts_type = None
    ts_version = None
    ts_bearer = None
    ts_bearer_expiry = None

    def __init__(self, username, password):
        self.find_tellstick()

        session = requests.Session()

        response = session.put('http://%s/api/token' % self.ts_address,
                               data={'app': 'smrtstick'})

        logging.debug('[tellstick] token request, successful=%s', response.status_code == 200)

        json_token = response.json()
        auth_url = json_token['authUrl']
        token = json_token['token']

        response = session.get(auth_url)

        logging.debug('[tellstick] authorization page request, successful=%s', response.status_code == 200)

        login_url = response.url

        response = session.post(login_url,
                                 data={'email': username, 'password': password})

        logging.debug('[tellstick] telldus live login, successful=%s', response.status_code == 200)

        trust_url = response.url

        response = session.post(trust_url,
                                data={'trust': 'yes'})

        logging.debug('[tellstick] trust response sent, successful=%s', response.status_code == 200)

        response = session.post('http://%s/api/authorize' % self.ts_address,
                                params={'token': token},
                                data={'ttl': 525600, 'extend': 1})

        logging.debug('[tellstick] authorize application, successful=%s', response.status_code == 200)

        response = session.get('http://%s/api/token' % self.ts_address,
                               params={'token': token})

        logging.debug('[tellstick] token bearer token, successful=%s', response.status_code == 200)

        self.ts_bearer = response.json()['token']
        self.ts_bearer_expiry = response.json()['expires']

        logging.debug('[tellstick] got bearer token: %s', self.ts_bearer)

    def find_tellstick(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        sock.settimeout(10)  # 10 seconds
        sock.sendto(b'D', ('255.255.255.255', 30303))

        data, (address, port) = sock.recvfrom(1024)

        self.ts_address = address

        split_data = data.split(b':')
        self.ts_type = split_data[0].decode('utf-8')
        self.ts_version = split_data[3].decode('utf-8')

        logging.debug('[tellstick] found Tellstick "%s" (%s) at %s:%s', self.ts_type, self.ts_version, address, port)

    def get_devices(self):
        response = requests.get('http://%s/api/devices/list' % self.ts_address,
                                headers={'Authorization': 'Bearer %s' % self.ts_bearer})

        if response.status_code != 200:
            return []

        raw_devices = response.json()

        logging.debug('[tellstick] discovered %i devices', len(raw_devices['device']))

        logging.debug(raw_devices)

        for raw_device in raw_devices['device']:
            name = raw_device['name']
            if name not in _cache:
                _cache[name] = OnOffDevice(name, raw_device, self)

        return list(_cache.values())

    def get_device(self, name):
        if name not in _cache:
            self.get_devices()  # do nothing with response

        if name in _cache:
            return _cache[name]
        else:
            return None

    def power(self, id, on_off):
        power_action = 'turnOff'
        if on_off:
            power_action = 'turnOn'

        response = requests.get('http://%s/api/device/%s' % (self.ts_address, power_action),
                                params={'id': id},
                                headers={'Authorization': 'Bearer %s' % self.ts_bearer})

        logging.debug(response.text)

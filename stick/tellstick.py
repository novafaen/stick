"""Tellstick local API client."""

from threading import Timer
import logging as loggr
import socket

import requests

from stick.onoffdevice import OnOffDevice

log = loggr.getLogger('smrt')


def discover_tellstick():
    """Perform local discovery for Telldus devices."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    sock.settimeout(10)  # allow 10 seconds for discovery
    sock.sendto(b'D', ('255.255.255.255', 30303))

    data, (address, port) = sock.recvfrom(1024)  # handle no answer?

    split_data = data.split(b':')
    ts_type = split_data[0].decode('utf-8')
    ts_version = split_data[3].decode('utf-8')

    log.debug('discovered Tellstick "%s" (%s) at %s:%s', ts_type, ts_version, address, port)

    return address


class Tellstick:
    """Tellstick Local API implementation."""

    _username = None
    _password = None
    _devices = {}
    _ts_address = None
    _ts_type = None
    _ts_version = None
    _ts_bearer = None
    _ts_bearer_expiry = None

    def __init__(self, username, password):
        """Create and initialize Tellstick.

        :param username: ``String`` tellstick username
        :param password: ``String`` tellstick password
        """
        self._username = username
        self._password = password

        self._try_dicovered_and_authorized()

        self._refresh_token()

    def _try_dicovered_and_authorized(self):
        """Try to discover and authorize."""
        if self._ts_address is None:
            self._ts_address = discover_tellstick()

        if self._ts_address is not None and self._ts_bearer is None:
            self._authorize()

        return self._ts_address is not None and self._ts_bearer is not None

    def _authorize(self):
        """Authorize stick against telldus live api to get token."""
        session = requests.Session()  # keep session between calls

        # step 1: create token request
        response = session.put('http://%s/api/token' % self._ts_address,
                               data={'app': 'smrtstick'})

        log.debug('put token request, successful=%s', response.status_code == 200)

        if response.status_code != 200:
            raise RuntimeError('Failed to get token page, got code=%s', response.status_code)

        try:
            json_token = response.json()
        except ValueError as err:
            log.warning('could not parse response from telldus live: %s', err)

        auth_url = json_token['authUrl']
        token = json_token['token']

        # step 2: get authorization/login page from telldus live
        response = session.get(auth_url)

        log.debug('get authorization request, successful=%s', response.status_code == 200)

        if response.status_code != 200:
            raise RuntimeError('Failed to get authorization page, got code=%s', response.status_code)

        login_url = response.url  # redirected here, get the new url

        # step 3: login to telldus live
        response = session.post(login_url,
                                data={'email': self._username, 'password': self._password})

        log.debug('telldus live login, successful=%s', response.status_code == 200)

        if response.status_code != 200:
            raise RuntimeError('Failed to login to telldus live, got code=%s', response.status_code)

        trust_url = response.url

        # step 4: authorize application, typically only done once but stick always does this
        response = session.post(trust_url,
                                data={'trust': 'yes'})

        log.debug('trust application request, successful=%s', response.status_code == 200)

        if response.status_code != 200:
            raise RuntimeError('Failed to trust stick as application, got code=%s', response.status_code)

        # step 5: autorize application
        response = session.post('http://%s/api/authorize' % self._ts_address,
                                params={'token': token},
                                data={'ttl': 525600, 'extend': 1})

        log.debug('authorize application, successful=%s', response.status_code == 200)

        if response.status_code != 200:
            raise RuntimeError('Failed to authorize application, got code=%s', response.status_code)

        # step 6: final step, get the bearer token
        response = session.get('http://%s/api/token' % self._ts_address,
                               params={'token': token})

        log.debug('get token bearer token, successful=%s', response.status_code == 200)
        log.debug('renewal allowed of token=%s', response.json()['allowRenew'])

        if response.status_code != 200:
            raise RuntimeError('Failed to get bearer token, got code=%s', response.status_code)

        # assume that renewal is allowed, todo: implement if not
        log.debug('will schedule renewal')

        try:
            json_token = response.json()
        except ValueError as err:
            log.warning('could not parse response from telldus device: %s', err)

        self._ts_bearer = json_token['token']
        self._ts_bearer_expiry = json_token['expires']

        log.debug('stick successfully authenticated and authorized: %s', self._ts_bearer is not None)

    def _refresh_token(self):
        response = requests.get('http://%s/api/refreshToken' % self._ts_address,
                                headers={'Authorization': 'Bearer %s' % self._ts_bearer})

        call_successful = response.status_code == 200

        if call_successful:
            self._ts_bearer = response.json()['token']
            self._ts_bearer_expiry = response.json()['expires']

        refresh_interval = 60 * 60 * 1  # every 1 hours

        log.debug('refreshed bearer token, successful=%s, next refresh in %s seconds', call_successful, refresh_interval)

        Timer(refresh_interval, self._refresh_token).start()

    def get_devices(self):
        """Get list of ``OnOffDevice`` connected to tellstick.

        :returns: ``[OnOffDevice]``
        """
        if not self._try_dicovered_and_authorized():
            log.warning('Cannot return any devices, stick is not authenticated and autorized against tellstick')
            return self._devices.values()  # return cached values

        response = requests.get('http://%s/api/devices/list' % self._ts_address,
                                headers={'Authorization': 'Bearer %s' % self._ts_bearer})

        if response.status_code != 200:
            log.debug('failed to get devices, returning cached device list')
            return self._devices.values()  # return cached values

        try:
            raw_devices = response.json()
        except ValueError as err:
            log.warning('Failed to parse response from tellstick: %s', err)
            return self._devices.values()  # return cached values

        log.debug('discovered %i devices', len(raw_devices['device']))

        for raw_device in raw_devices['device']:
            name = raw_device['name']
            if name not in self._devices:
                self._devices[name] = OnOffDevice(name, raw_device, self)

        return list(self._devices.values())

    def get_device(self, name):
        """Get ``OnOffDevice`` by name.

        :param name: ``String`` identifier.
        :returns: ``OnOffDevice`` or ``None``
        """
        if name not in self._devices:
            self.get_devices()  # re-discover

        if name in self._devices:
            return self._devices[name]

        return None

    def power(self, id, on_off):
        """Set power for device with Id.

        :param id: ``String`` telldus device id
        :param on_off: ``Boolean`` power state
        """
        if not self._try_dicovered_and_authorized():
            return False

        power_action = 'turnOn' if on_off else 'turnOff'

        response = requests.get('http://%s/api/device/%s' % (self._ts_address, power_action),
                                params={'id': id},
                                headers={'Authorization': 'Bearer %s' % self._ts_bearer})

        call_successful = response.status_code == 200
        if not call_successful:
            log.debug('call state was not successful (%s), will force token refresh', response.status_code)
            self._bearer = None
            self._refresh_token()

        log.debug('tellstick action %s, code=%s, status=%s', id, response.status_code, response.json()['status'])
        return call_successful and response.json()['status'] == 'success'

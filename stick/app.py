"""Stick is a service built on SMRT framework.

Stick can communicate with local Tellstick for on-off devices.

Current supported on-off devices:
- Nexa switch.
"""

import logging as loggr
import os

from stick.tellstick import Tellstick

from smrt import SMRTApp, app, make_response, jsonify, smrt
from smrt import ResouceNotFound

log = loggr.getLogger('smrt')


class Stick(SMRTApp):
    """Stick is a ``SMRTApp`` that is to be registered with SMRT."""

    def __init__(self):
        """Create and initiate ``Stick`` application."""
        log.debug('%s (%s) spinning up...', self.application_name(), self.version())

        self._devices = {}  # no identified devices at startup

        self._schemas_path = os.path.join(os.path.dirname(__file__), 'schemas')
        SMRTApp.__init__(self, self._schemas_path, 'configuration.stick.schema.json')
        if not hasattr(self, '_config') or self._config is None:
            raise RuntimeError('cannot start without valid configuration file.')

        self._client = Tellstick(self._config['tellstick_api']['username'], self._config['tellstick_api']['password'])

        log.debug('%s initiated!', self.application_name())

    def status(self):
        """See ``SMRTApp`` documentation for ``status`` implementation."""
        return {
            'name': self.application_name(),
            'status': 'OK',
            'version': self.version()
        }

    @staticmethod
    def application_name():
        """See ``SMRTApp`` documentation for ``application_name`` implementation."""
        return 'Stick'

    @staticmethod
    def version():
        """See ``SMRTApp`` documentation for ``version`` implementation."""
        return '0.0.1'

    def get_devices(self):
        """Get all devices that can be discovered.

        Function will perform a discovery for devices, and return the
        devices in an array. Devices are cached, so if a device "dissapears", it
        will still be returned once discovered.

        :returns: [``Device``].
        """
        return self._client.get_devices()

    def get_device(self, name):
        """Get a device identified by name.

        Function will do discovery, see ``get_devices`` documentation.

        :param name: ``String`` unique identifier.
        :returns: ``Device`` or ``None``
        """
        return self._client.get_device(name)


# create prism and register it with smrt
stick = Stick()
app.register_application(stick)


@smrt('/devices',
      produces='application/se.novafaen.stick.devices.v1+json')
def get_devices():
    """Endpoint to get all discoverable, and cached, devices.

    :returns: ``se.novafaen.stick.devices.v1+json``
    """
    sticks = stick.get_devices()

    body = {
        'devices': [stick.json() for stick in sticks]
    }

    response = make_response(jsonify(body), 200)
    response.headers['Content-Type'] = 'application/se.novafaen.stick.devices.v1+json'
    return response


@smrt('/device/<string:name>',
      produces='application/se.novafaen.stick.device.v1+json')
def get_device(name):
    """Endpoint to get a single device by name.

    :returns: ``se.novafaen.stick.device.v1+json``
    """
    device = stick.get_device(name)

    if device is None:
        raise ResouceNotFound('Could not find device \'{}\''.format(name))

    body = device.json()

    response = make_response(jsonify(body), 200)
    response.headers['Content-Type'] = 'application/se.novafaen.prism.light.v1+json'
    return response


@smrt('/device/<string:name>/power/on',
      methods=['PUT'],
      produces='application/se.novafaen.stick.device.v1+json')
def power_on(name):
    """Endpoint to turn on device, identified by name.

    :returns: ``application/se.novafaen.stick.device.v1+json``
    """
    return _power(name, True)


@smrt('/device/<string:name>/power/off',
      methods=['PUT'],
      produces='application/se.novafaen.stick.device.v1+json')
def power_off(name):
    """Endpoint to turn off device, identified by name.

    :returns: ``application/se.novafaen.stick.device.v1+json``
    """
    return _power(name, False)


@smrt('/device/<string:name>/power/toggle',
      methods=['PUT'],
      produces='application/se.novafaen.stick.device.v1+json')
def power_toggle(name):
    """Endpoint to turn toggle device power, identified by name.

    :returns: ``application/se.novafaen.stick.device.v1+json``
    """
    return _toggle(name)


def _toggle(name):
    device = stick.get_device(name)

    if device is None:
        raise ResouceNotFound('Could not find device \'%s\'' % name)

    device.toggle_power()

    response = make_response(jsonify(device.json()), 200)
    response.headers['Content-Type'] = 'application/se.novafaen.stick.device.v1+json'
    return response


def _power(name, on_off):
    device = stick.get_device(name)

    if device is None:
        raise ResouceNotFound('Could not find device \'%s\'' % name)

    log.debug('[stick] setting device "%s" power to %s', name, on_off)

    device.set_power(on_off)

    response = make_response(jsonify(''), 204)
    response.headers['Content-Type'] = 'application/se.novafaen.stick.device.v1+json'
    return response

"""Stick is a service built on SMRT framework.

Stick can communicate with local Tellstick for on-off devices.

Current supported on-off devices:
- Nexa switch.
"""

import logging as loggr
import os

from stick.tellstick import Tellstick

from smrt import SMRTApp, app, make_response, jsonify, smrt

log = loggr.getLogger('stick')


class Stick(SMRTApp):
    """Stick is a ``SMRTApp`` that is to be registered with SMRT."""

    def __init__(self):
        """Create and initiate ``Stick`` application."""
        log.debug('%s (%s) spinning up...', self.application_name(), self.version())

        self._schemas_path = os.path.join(os.path.dirname(__file__), 'schemas')

        SMRTApp.__init__(self, self._schemas_path, 'configuration.stick.schema.json')

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
    def version():
        """Get version of application.

        :returns: `String` version name
        """
        return '0.0.1'

    @staticmethod
    def application_name():
        """See ``SMRTApp`` documentation for ``application_name`` implementation."""
        return 'Stick'

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
        devices = self.get_devices()  # do nothing with response

        for device in devices:
            if device.get_name() == name:
                return device

        return None  # not found


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

    response = {
        'devices': [{'name': s.get_name(), 'protocol': s.protocol()} for s in sticks]
    }

    response = make_response(jsonify(response), 200)
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
        body = {
            'status': 'NotFound',
            'message': 'Could not find device \'%s\'' % name
        }
        response = make_response(jsonify(body), 404)
        response.headers['Content-Type'] = 'application/se.novafaen.smrt.error.v1+json'
        return response

    body = {
        'name': device.get_name(),
        'protocol': device.protocol()
    }

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


def _power(name, on_off):
    device = stick.get_device(name)

    if device is None:
        body = {
            'status': 'NotFound',
            'message': 'Could not find device \'%s\'' % name
        }
        response = make_response(jsonify(body), 404)
        response.headers['Content-Type'] = 'application/se.novafaen.smrt.error.v1+json'
        return response

    log.debug('[stick] setting device "%s" power to %s', name, on_off)

    device.set_power(on_off)

    response = make_response(jsonify(''), 204)
    response.headers['Content-Type'] = 'application/se.novafaen.stick.device.v1+json'
    return response

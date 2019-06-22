"""OnOffDevice, wrapper for a device that can turn on and off only."""

import logging as loggr
import time

log = loggr.getLogger('stick')


class OnOffDevice:
    """OnOffDevice, nothing more to it."""

    def __init__(self, name, raw_device, client):
        """Create and inialize OnOffDevice.

        :param name: name of light, should be unique
        :param raw_device: json object returned from tellstick
        :param client: tellstick client
        """
        self._name = name
        self._id = raw_device['id']
        self._power = None  # unknown
        self._client = client
        self._last_seen = int(time.time())  # assumed seen when created

    @staticmethod
    def protocol():
        """Get protocol name.

        :returns: ``String`` protocol name
        """
        return 'Nexa.v1'

    def get_name(self):
        """Get name of on-off device.

        :returns: ``String`` name
        """
        return self._name

    def __repr__(self):
        """Return string representation of device.

        :returns: ``String`` representation
        """
        return '<OfOffDevice ' \
            'name="{name}" protocol="{protocol}" power={power} last_seen={last_seen}>'.format(
                **self.json())

    def json(self):
        """Return dictionary representation of ``OnOffDevice``.

        :returns: ``Dict``
        """
        return {
            'name': self._name,
            'protocol': self.protocol(),
            'power': self._power,
            'last_seen': self._last_seen
        }

    def toggle_power(self):
        """Toggle power for a device.

        If state is unknown, this will turn on device.
        :returns: ``Boolean`` if action was successful or not.
        """
        return self.set_power(True if self._power is None else not self._power)  # turn on if unknown power state

    def set_power(self, on_off):
        """Set power state for device.

        :param on_off: ``Boolean`` if device should be on of off.
        :returns: ``Boolean`` if action was successful or not.
        """
        successful = self._client.power(self._id, on_off)

        if successful:
            self._last_seen = int(time.time())

        self._power = on_off if successful else None  # clear status if update failed

        return successful

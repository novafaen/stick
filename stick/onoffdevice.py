"""OnOffDevice, wrapper for a device that can turn on and off only."""

_cache = {}


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
        self._client = client

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

    def __str__(self):
        """Get string representation of device.

        :returns: ``String`` representation
        """
        return '<OfOffDevice name="%s" protocol="%s" telldus_id="%s">' % (self._name, self.protocol(), self._id)

    def set_power(self, on_off):
        """Set power state for device.

        :param on_off: ``Boolean`` if device should be on of off.
        :returns: something
        """
        return self._client.power(self._id, on_off)

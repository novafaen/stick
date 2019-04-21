
_cache = {}


class OnOffDevice:

    def __init__(self, name, raw_device, client):
        self._name = name
        self._id = raw_device['id']
        self._client = client

    @staticmethod
    def protocol():
        return 'Nexa.v1'

    def get_name(self):
        return self._name

    def __str__(self):
        return '<OfOffDevice name="%s" protocol="%s">' % (self._name, self.protocol())

    def set_power(self, on_off):
        return self._client.power(self._id, on_off)

import logging

from smrt import SMRTApp, app, make_response, smrt, jsonify

#from stick.tellstick import Tellstick

#logging.getLogger('requests').setLevel(logging.WARNING)


class Stick(SMRTApp):
    def __init__(self):
        logging.debug('%s spinning up...', Stick.client_name())

        SMRTApp.__init__(self)

        #self._client = Tellstick(
        #    self.config['tellstick_api']['username'],
        #    self.config['tellstick_api']['password'])

        logging.debug('%s initiated!', Stick.client_name())

    def status(self):
        return {
            'name': Stick.client_name(),
            'status': 'OK',
            'version': '0.0.1'
        }

    @staticmethod
    def client_name():
        return 'Stick'

    def get_device(self, name):
        return self._client.get_device(name)

    def get_devices(self):
        return self._client.get_devices()


# create and register app with smrt
stick = Stick()
app.register_client(stick)


@smrt('/devices',
      produces='application/se.novafaen.stick.devices.v1+json')
def get_devices():
    return stick.get_devices()


@smrt('/device/<string:name>/power/on',
      methods=['PUT'],
      produces='application/se.novafaen.stick.device.v1+json')
def power_on(name):
    return _power(name, True)


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

    logging.debug('[stick] setting device "%s" power to on', name)

    device.set_power(on_off)

    response = make_response(jsonify(''), 204)
    response.headers['Content-Type'] = 'application/se.novafaen.stick.device.v1+json'
    return response




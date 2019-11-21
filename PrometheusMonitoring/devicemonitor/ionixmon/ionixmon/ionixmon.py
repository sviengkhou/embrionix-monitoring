from flask import Flask, render_template, flash, request, send_file
from wtforms import Form, TextField, TextAreaField, validators, StringField, SubmitField
import logging
import docker
docker_client = docker.from_env()
app = Flask(__name__)

monitored_devices = []

class MonitoringInformation():
    def __init__(self, ip, prettyName):
        self.ip = ip
        self.prettyName = prettyName


# Static file serving...  To allow Ionixmon usage without internet access...
@app.route('/js/jquery-3.3.1.slim.min.js')
def send_jquery():
    return send_file('js/jquery-3.3.1.slim.min.js')


@app.route('/js/popper.min.js')
def send_popper():
    return send_file('js/popper.min.js')


@app.route('/js/bootstrap.min.js')
def send_bootstrapjs():
    return send_file('js/bootstrap.min.js')


@app.route('/css/bootstrap.min.css')
def send_bootstrapcss():
    return send_file('css/bootstrap.min.css')


@app.route('/', methods=['GET', 'POST'])
def MainPage():
    name = TextField('Name:', validators=[validators.required()])
    app.logger.warning(str(request.form))
    if request.method == 'POST' and "addDevice" in request.form:
        deviceIp = request.form['deviceIp']
        deviceName = request.form['deviceName']
        newDev = MonitoringInformation(deviceIp, deviceName)
        monitored_devices.append(newDev)
        app.logger.warning("Device IP: " + str(newDev.ip) + " Device name: " + str(newDev.prettyName))
        docker_client.containers.run("prometheus_interface", 
            environment = ["deviceip="+deviceIp, "port=10600", "prettyName="+deviceName], 
            name=deviceName,
            detach=True, 
            volumes={'graphicmonitor_to_monitor': {'bind': '/home/to_monitor/', 'mode': 'rw'}}, 
            publish_all_ports=True,
            network="graphicmonitor_default")
        return render_template('index.html', monitoredDevices=monitored_devices)
    elif request.method == 'POST' and "viewDevices" in request.form:
        return render_template('view_monitored_devices.html', monitoredDevices=monitored_devices)
    elif request.method == 'POST' and "viewStatus" in request.form:
    else:
        app.logger.warning("Got: " + str(request.method))
        return render_template('index.html', monitoredDevices=monitored_devices)



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8060)

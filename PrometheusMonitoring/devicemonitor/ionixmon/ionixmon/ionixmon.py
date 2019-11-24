# Copyright 2019 Embrionix Design Inc.
#
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.


from flask import Flask, render_template, flash, request, send_file
from wtforms import Form, TextField, TextAreaField, validators, StringField, SubmitField
import logging
import docker
import requests
import os
docker_client = docker.from_env()
app = Flask(__name__)

class MonitoringInformation():
    def __init__(self, ip, prettyName):
        self.ip = ip
        self.prettyName = prettyName
        self.prometheus_status = "NA"


class PrometheusServer():
    def __init__(self, host="emprometheus", port=9090):
        self.host = host
        self.port = port

    def get_all_prometheus_targets_names(self):
        r = requests.get("http://" + self.host + ":" + str(self.port) + "/api/v1/targets", timeout=2)
        names = []

        for target in r.json()["data"]["activeTargets"]:
            names.append(target["discoveredLabels"]["job"])
            
        return names
        
    def get_orphan_prometheus_targets(self, currently_monitored_names):
        targets = self.get_all_prometheus_targets_names()
        for containerName in currently_monitored_names:
            targets.remove(containerName)
        return targets
        
    def get_info_for_target(self, target_name):
        r = requests.get("http://" + self.host + ":" + str(self.port) + "/api/v1/targets", timeout=2)
        names = []

        for target in r.json()["data"]["activeTargets"]:
            if target["discoveredLabels"]["job"] == target_name:
                return target
        return None
    
    #try:
    #    r = requests.get("http://emprometheus:9090/api/v1/targets", timeout=2)
    #except:
    #    return None
    #if r.status_code == 200:
    #    return r.json()
    #else:
    #    return None
    
def RefreshMonitoredDevices():
    for dev in monitored_devices:
        status = prometheus_server.get_info_for_target(dev.prettyName)
        if status is None:
            dev.prometheus_status = "NA"
        else:
            dev.prometheus_status = status["health"]


def RemoveMonitor(containerName):
    # Remove from Docker...
    container_instance = docker_client.containers.get(containerName)
    container_instance.stop()
    
    RemoveFromPrometheus(containerName)
    
    # Remove from monitored devices...
    try:
        for device in monitored_devices:
            if device.prettyName == containerName:
                monitored_devices.remove(device)
                break
    except:
        app.logger.error("Could not remove: " + str(containerName))

def RemoveFromPrometheus(toRemove, path="/home/to_monitor"):
    os.remove(path + "/" + str(toRemove) + ".json")

def show_monitored_devices():
    currentNames = []
    
    for target in monitored_devices:
        currentNames.append(target.prettyName)
    
    orphans = prometheus_server.get_orphan_prometheus_targets(currentNames)
    RefreshMonitoredDevices()
    
    return render_template('view_monitored_devices.html', monitoredDevices=monitored_devices, orphans=orphans)
    
monitored_devices = []
prometheus_server = PrometheusServer()

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
            network="graphicmonitor_bridge_net")
        return render_template('index.html', monitoredDevices=monitored_devices)
    elif request.method == 'POST' and "viewDevices" in request.form:
        return show_monitored_devices()
    elif request.method == 'POST' and "viewGraphs" in request.form:        
        return render_template('view_graphs.html', monitoredDevices=monitored_devices)
    elif request.method == 'POST' and "viewContainer" in request.form: 
        containerId = request.form['containerId']
        containerObj = docker_client.containers.get(containerId)
        
        app.logger.warning("orphans: " + str(status))
        
        return render_template('view_docker_status.html', containerId=containerId, containerLog=containerObj.logs(stdout=True, stderr=True))
    elif request.method == 'POST' and "deleteMonitor" in request.form: 
        toDelete = request.form['containerId']
        app.logger.warning("Deleting: " + str(toDelete))

        RemoveMonitor(toDelete)
        return show_monitored_devices()
    else:
        app.logger.warning("Got: " + str(request.method))
        return render_template('index.html', monitoredDevices=monitored_devices)



if __name__ == '__main__':
    image_id = docker_client.images.get("prometheus_interface:latest").id
    for container in docker_client.containers.list():
        if container.image.id == image_id:
            devIp = None
            env = container.attrs["Config"]["Env"]
            for kv in env:
                key = kv.split("=")[0]
                if key == "deviceip":
                    devIp = kv.split("=")[1]
            if devIp is not None:
                app.logger.warning("Adding an already present monitor container: " + container.name)
                newDev = MonitoringInformation(devIp, container.name)
                monitored_devices.append(newDev)
            else:
                app.logger.warning("Could not add container: " + container.name)

    app.run(host='0.0.0.0', port=8060)

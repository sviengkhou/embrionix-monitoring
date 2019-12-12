# Copyright 2019 Embrionix Design Inc.
#
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.


from flask import Flask, render_template, flash, request, send_file
from wtforms import Form, TextField, TextAreaField, validators, StringField, SubmitField
import logging
import json
import docker
import requests
import re
import time
import os
import datetime
docker_client = docker.from_env()
app = Flask(__name__)


class MonitoringInformation():
    TELEMETRY_URL = "/emsfp/node/v1/telemetry"
    SYSLOG_URL = "/emsfp/node/v1/self/syslog"
    
    def __init__(self, ip, prettyName):
        self.ip = ip
        self.prettyName = prettyName
        self.prometheus_status = "NA"
        self.telemetryAvailable = self.IsTelemetryAvailable()
        self.syslogAvailable = self.IsSyslogAvailable()

    def IsSyslogAvailable(self):
        try:
            r = requests.get("http://" + self.ip + self.SYSLOG_URL, timeout=2)
        except:
            return False

        if r.status_code == 200:
            return True
        else:
            return False

    def IsTelemetryAvailable(self):
        try:
            r = requests.get("http://" + self.ip + self.TELEMETRY_URL, timeout=2)
        except:
            return False

        if r.status_code == 200:
            return True
        else:
            return False
            
    def ApplySyslogConfig(self, syslogCfg):
        jsonCfg = {}
        
        jsonCfg["config"] = {}
        jsonCfg["config"]["server"] = syslogCfg["syslog_target"]
        jsonCfg["config"]["enable"] = True if "enable_syslog" in syslogCfg else False
        
        jsonCfg["monitoring"] = {}
        jsonCfg["monitoring"]["common"] = {}
        jsonCfg["monitoring"]["common"]["ptp_event"] = True if "ptp_event" in syslogCfg else False
        jsonCfg["monitoring"]["common"]["temp_event"] = True if "temp_event" in syslogCfg else False
        jsonCfg["monitoring"]["common"]["rtp_48k_event"] = True if "rtp_48k_event" in syslogCfg else False
        jsonCfg["monitoring"]["common"]["fan_speed"] = True if "fan_speed" in syslogCfg else False
        
        jsonCfg["monitoring"]["encap"] = {}
        jsonCfg["monitoring"]["encap"]["sdi_event"] = True if "sdi_event" in syslogCfg else False
        jsonCfg["monitoring"]["encap"]["no_signal"] = True if "no_signal" in syslogCfg else False
        
        jsonCfg["monitoring"]["decap"] = {}
        jsonCfg["monitoring"]["decap"]["output_flywheel"] = True if "output_flywheel" in syslogCfg else False
        jsonCfg["monitoring"]["decap"]["memory_pkt_error"] = True if "memory_pkt_error" in syslogCfg else False
        jsonCfg["monitoring"]["decap"]["flow_impairment"] = True if "flow_impairment" in syslogCfg else False
        jsonCfg["monitoring"]["decap"]["frame_repeat"] = True if "frame_repeat" in syslogCfg else False
        jsonCfg["monitoring"]["decap"]["frame_skipped"] = True if "frame_skipped" in syslogCfg else False
        jsonCfg["monitoring"]["decap"]["dash7_fifo_error"] = True if "dash7_fifo_error" in syslogCfg else False
        
        app.logger.warning("Cfg: " + str(jsonCfg))
        
        self.set_config("http://" + self.ip + self.SYSLOG_URL, jsonCfg)

    def set_config(self, url, json_config, ignore_error=False, timeout=5, retry_interval=1, retry_max=5):
        app.logger.warning(str(url))
        retry_count = 0
        r = requests.put(url, json=json_config, timeout=timeout)

        while retry_count < retry_max:
            if r.status_code == 200:
                return r.status_code
            else:
                retry_count += 1
                if not ignore_error:
                    print("PUT failed, retrying in a second...")
                    time.sleep(retry_interval)
            r = requests.put(url, json=json_config, timeout=timeout)
        return r.status_code


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
            try:
                targets.remove(containerName)
            except:
                app.logger.warning(str(containerName) + " Have an associated container but no entry in Prometheus")
        return targets
        
    def get_info_for_target(self, target_name):
        r = requests.get("http://" + self.host + ":" + str(self.port) + "/api/v1/targets", timeout=2)
        names = []

        for target in r.json()["data"]["activeTargets"]:
            if target["discoveredLabels"]["job"] == target_name:
                return target
        return None


class SyslogEntry():
    def __init__(self, rawString):
        try:
            self.time = rawString.split(" ", 1)[0]
            self.src = re.findall(r"HOST_FROM=[0-9\.]*", rawString)[0].split("=")[1]
            self.message = re.findall(r"MESSAGE=\".*\"", rawString)[0].split("=")[1]
            self.msgid = re.findall(r"MSGID=.* ", rawString)[0].split("=")[1]
        except:
            app.logger.warning("Could not parse syslog: " + str(rawString))


def ApplySyslogConfigToAllUnits(syslogCfg):
    for device in monitored_devices:
        if device.syslogAvailable:
            device.ApplySyslogConfig(syslogCfg)

def LoadConfig(configFile="config.json"):
    if os.path.exists(configFile):
        # Load Config...
        with open(configFile) as json_file:
            data = json.load(json_file)
            return data
    else:
        # Save Blank Config...
        app.logger.warning("Cannot load config, creating a new one based on defaults")
        data = GenerateDefaultSyslogConfig()
        SaveConfig(data)
        return data


def GenerateDefaultSyslogConfig():
    blank_config = {}
    blank_config["syslog_target"] = "192.168.39.100"
    blank_config["enable_syslog"] = True
    blank_config["ptp_event"] = True
    blank_config["temp_event"] = True
    blank_config["rtp_48k_event"] = True
    blank_config["fan_speed"] = True
    blank_config["sdi_event"] = True
    blank_config["no_signal"] = True
    blank_config["output_flywheel"] = True
    blank_config["memory_pkt_error"] = True
    blank_config["flow_impairment"] = True
    blank_config["frame_repeat"] = True
    blank_config["frame_skipped"] = True
    blank_config["dash7_fifo_error"] = True
    return blank_config


def GenerateConfigDataFromRequest(requestForm):
    save_data = {}
    save_data["syslog_target"] = request.form['syslog_target']
    save_data["enable_syslog"] = True if "enable_syslog" in request.form else False
    save_data["ptp_event"] = True if "ptp_event" in request.form else False
    save_data["temp_event"] = True if "temp_event" in request.form else False
    save_data["rtp_48k_event"] = True if "rtp_48k_event" in request.form else False
    save_data["fan_speed"] = True if "fan_speed" in request.form else False
    save_data["sdi_event"] = True if "sdi_event" in request.form else False
    save_data["no_signal"] = True if "no_signal" in request.form else False
    save_data["output_flywheel"] = True if "output_flywheel" in request.form else False
    save_data["memory_pkt_error"] = True if "memory_pkt_error" in request.form else False
    save_data["flow_impairment"] = True if "flow_impairment" in request.form else False
    save_data["frame_repeat"] = True if "frame_repeat" in request.form else False
    save_data["frame_skipped"] = True if "frame_skipped" in request.form else False
    save_data["dash7_fifo_error"] = True if "dash7_fifo_error" in request.form else False
    
    return save_data


def SaveConfig(data, configFile="config.json"):
    with open(configFile, 'w') as outfile:
        json.dump(data, outfile)


def RefreshMonitoredDevices():
    for dev in monitored_devices:
        status = prometheus_server.get_info_for_target(dev.prettyName)
        if status is None:
            dev.prometheus_status = "NA"
        else:
            dev.prometheus_status = status["health"]


def RemoveMonitor(containerName):
    # Remove from Docker...
    try:
        container_instance = docker_client.containers.get(containerName)
        container_instance.stop()
        container_instance.remove()
        
    except Exception as e:
        app.logger.warning("Could not remove container: " + str(containerName) + " Error message: " + str(e))
    
    RemoveFromPrometheus(containerName)
    
    # Remove from monitored devices...
    try:
        for device in monitored_devices:
            if device.prettyName == containerName:
                monitored_devices.remove(device)
                break
    except:
        app.logger.error("Could not remove: " + str(containerName))


def GetDeviceByName(devName):
    for device in monitored_devices:
        if device.prettyName == devName:
            return device
    return None


def GetDeviceSyslog(devIp):
    syslog = []
    syslog_raw = docker_client.containers.get("syslog-ng").exec_run("cat /var/log/messages-kv.log")
    for line in str(syslog_raw.output, 'utf-8').splitlines():
        newEntry = SyslogEntry(line)
        if newEntry.src == devIp:
            syslog.append(newEntry)
    return syslog


def RemoveFromPrometheus(toRemove, path="/home/to_monitor"):
    try:
        os.remove(path + "/" + str(toRemove) + ".json")
    except Exception as e:
        app.logger.warning(str(toRemove) + " cannot be removed from prometheus, reason: " + str(e))


def show_monitored_devices():
    currentNames = []
    
    for target in monitored_devices:
        currentNames.append(target.prettyName)
    
    orphans = prometheus_server.get_orphan_prometheus_targets(currentNames)
    RefreshMonitoredDevices()
    
    return render_template('view_monitored_devices.html', monitoredDevices=monitored_devices, orphans=orphans)

def show_configuration_page(config):
    return render_template('config.html', config=config)


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

@app.route('/templates/navbar.html')
def send_navbar():
    return send_file('templates/navbar.html')

@app.route('/', methods=['GET', 'POST'])
def MainPage():
    config = LoadConfig()
    name = TextField('Name:', validators=[validators.required()])
    app.logger.warning(str(request.form))
    if request.method == 'POST' and "addDevice" in request.form:
        deviceIp = request.form['deviceIp']
        deviceName = request.form['deviceName']
        newDev = MonitoringInformation(deviceIp, deviceName)
        monitored_devices.append(newDev)
        app.logger.warning("Device IP: " + str(newDev.ip) + " Device name: " + str(newDev.prettyName))
        
        script_name = "telemetry_monitor.py" if newDev.telemetryAvailable else "rest_monitor.py"
        
        docker_client.containers.run("prometheus_interface", 
            environment = ["deviceip="+deviceIp, "port=10600", "prettyName="+deviceName, "monitorScriptName=" + script_name], 
            name=deviceName,
            detach=True, 
            volumes={'grafana_to_monitor': {'bind': '/home/to_monitor/', 'mode': 'rw'}}, 
            publish_all_ports=True,
            network="grafana_bridge_net")
            
        newDev.ApplySyslogConfig(config)
        
        return render_template('index.html', monitoredDevices=monitored_devices)
    elif request.method == 'POST' and "configure" in request.form:
        return show_configuration_page(config)

    elif request.method == 'POST' and "viewDevices" in request.form:
        return show_monitored_devices()
        
    elif request.method == 'POST' and "viewGraphs" in request.form:        
        return render_template('view_graphs.html', monitoredDevices=monitored_devices)
        
    elif request.method == 'POST' and "viewContainer" in request.form: 
        containerId = request.form['containerId']
        containerObj = docker_client.containers.get(containerId)
        return render_template('view_docker_status.html', containerId=containerId, containerLog=containerObj.logs(stdout=True, stderr=True))
        
    elif request.method == 'POST' and "viewSyslog" in request.form: 
        device = GetDeviceByName(request.form['devName'])
        syslog = GetDeviceSyslog(device.ip)
        return render_template('view_syslog.html', syslog=syslog)
        
    elif request.method == 'POST' and "deleteMonitor" in request.form: 
        toDelete = request.form['containerId']
        app.logger.warning("Deleting: " + str(toDelete))
        RemoveMonitor(toDelete)
        return show_monitored_devices()
        
    elif request.method == 'POST' and "saveConfig" in request.form: 
        SaveConfig(GenerateConfigDataFromRequest(request.form))
        ApplySyslogConfigToAllUnits(request.form)
        return render_template('index.html')

    else:
        app.logger.warning("Got: " + str(request.method))
        return render_template('index.html')



if __name__ == '__main__':
    config = LoadConfig()
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
                newDev.ApplySyslogConfig(config)
                monitored_devices.append(newDev)
            else:
                app.logger.warning("Could not add container: " + container.name)

    app.run(host='0.0.0.0', port=8060)

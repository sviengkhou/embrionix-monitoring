# Copyright 2019 Embrionix Design Inc.
#
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

from prometheus_client import start_http_server, Summary, Gauge, Info
from prettytable import PrettyTable
from emflow import FlowDir, FlowType
import time
import requests
import argparse
import prettytable
import os
import json
import socket

# Create a metric to track time spent and requests made.
REQUEST_TIME = Summary('request_processing_seconds', 'Time spent processing request')

def register_on_prometheus(pretty_name, path="/home/to_monitor"):
    local_ip = socket.gethostbyname(socket.gethostname())
    print("Container IP: " + str(local_ip))
    json_data = '[{"labels": {"job": "' + pretty_name + '"},"targets": ["' + local_ip + ':10600"]}]'
    print("Prometheus data: " + json_data)
    file = open(path + "/" + pretty_name + ".json", "w")
    file.write(json_data)
    file.close()


class TelemetryCapabilities():
    def __init__(self):
        self.health = False
        self.ptp_monitor = False
        self.sfp_monitor = False
        self.flows = True


class SfpMonitor():
    def __init__(self, port_num):
        print("in sfp_monitors init")
        self.port_num = port_num
        self.sfp_temperature = Gauge('sfp_temperature_p' + str(port_num), 'Temperature of SFP in port ' + str(port_num))
        self.sfp_vcc = Gauge('sfp_vcc_p' + str(port_num), 'VCC voltage')
        self.sfp_txpwr = Gauge('sfp_txpwr_p' + str(port_num), 'SFP Tx Power')
        self.sfp_rxpwr = Gauge('sfp_rxpwr_p' + str(port_num), 'SFP Rx Power')

class SignalDeviceMonitor():
    def find_channel_from_telemetry(self, telemetry):
        for device in telemetry["devices"]:
            # TODO: Rely on channel number when 3.0 is officially released.  This will not work for 
            # NMOS loads...
            if int(device["device"][0]) == int(self.channel_num):
                return device
        return None


class EncapDeviceMonitor(SignalDeviceMonitor):
    def __init__(self, device_info):
        # TODO: Rely on channel number when 3.0 is officially released.  This will not work for 
        # NMOS loads...
        self.channel_num = device_info["device"][0]
        self.sdi_to_ptp_offset_gauge = None
        self.create_gauge()
        
    def create_gauge(self):
        self.sdi_to_ptp_offset_gauge = Gauge('sdi_to_ptp_offset_ch' + str(self.channel_num), 'SDI to PTP Offset ch' + str(self.channel_num))
        
    def refresh_gauge(self, telemetry):
        dev_info = self.find_channel_from_telemetry(telemetry)
        if dev_info is not None:
            self.sdi_to_ptp_offset_gauge.set(dev_info["sdi_to_ptp_offset"])
        else:
            self.sdi_to_ptp_offset_gauge.set(-1)


class DecapDeviceMonitor(SignalDeviceMonitor):
    def __init__(self, device_info):
        self.channel_num = device_info["device"][0]
        self.flow_to_ptp_offset_prim_gauge = None
        self.flow_to_ptp_offset_sec_gauge = None
        self.create_gauge()
        
    def create_gauge(self):
        self.flow_to_ptp_offset_prim_gauge = Gauge('flow_to_ptp_offset_prim_ch' + str(self.channel_num), 'Flow to PTP Offset primary ch' + str(self.channel_num))
        self.flow_to_ptp_offset_sec_gauge = Gauge('flow_to_ptp_offset_sec_ch' + str(self.channel_num), 'Flow to PTP Offset secondary ch' + str(self.channel_num))
        
    def refresh_gauge(self, telemetry):
        dev_info = self.find_channel_from_telemetry(telemetry)
        if dev_info is not None:
            self.flow_to_ptp_offset_prim_gauge.set(dev_info["flow_to_ptp_offset"]["primary"])
            self.flow_to_ptp_offset_sec_gauge.set(dev_info["flow_to_ptp_offset"]["secondary"])
        else:
            self.sdi_to_ptp_offset_gauge.set(-1)

class FlowMonitor():
    def __init__(self, channel, dev_type, essence, isPrimary):
        self.pkt_cnt_gauge = None
        self.seq_err_gauge = None
        self.channel = channel
        self.dev_type = dev_type
        
        self.essence = FlowType.UNKNOWN
        if essence == "video":
            self.essence = FlowType.VIDEO_2110
        elif essence == "audio":
            self.essence = FlowType.AUDIO_2110
        elif essence == "ancillary":
            self.essence = FlowType.ANCIL_2110
        
        self.isPrimary = isPrimary
        self.create_gauges()

    def create_gauges(self):
        pkt_cnt_gauge_name = 'ch' + str(self.channel) + '_' + FlowType.get_flow_type_name(self.essence) + ('_prim' if self.isPrimary else '_sec') + '_pkt_cnt'
        self.pkt_cnt_gauge = Gauge(pkt_cnt_gauge_name, "Flow packet count")
        print(pkt_cnt_gauge_name)
        
        # Sequence errors only present on decap (TX) flows...
        if self.dev_type == FlowDir.TX:
            seq_err_gauge_name = 'ch' + str(self.channel) + '_' + FlowType.get_flow_type_name(self.essence) + ('_prim' if self.isPrimary else '_sec') + '_seq_err'
            self.seq_err_gauge = Gauge(seq_err_gauge_name, "Flow Sequence Error")
            print(seq_err_gauge_name)
            
    def refresh_gauges(self, telemetry):
        for device in telemetry["devices"]:
            if device["device"][0] == self.channel:
                for engine in engines:
                    if engine["essence"] == self.essence:
                        for flow in engine["flows"]:
                            if (self.isPrimary and flow["type"] == "primary") or (not self.isPrimary and flow["type"] == "secondary"):
                                self.pkt_cnt_gauge.set(flow["pkt_cnt"])
                                if self.seq_err_gauge is not None:
                                    self.pkt_cnt_gauge.set(flow["sequence_error"])

class AudioFlowMonitor(FlowMonitor):
    def __init__(self, channel, dev_type, essence, isPrimary, audio_index):
        self.audio_index = audio_index
        super().__init__(channel, dev_type, essence, isPrimary)

    def create_gauges(self):
        pkt_cnt_gauge_name = 'ch' + str(self.channel) + '_' + FlowType.get_flow_type_name(self.essence) + "_" + str(self.audio_index) + ('_prim' if self.isPrimary else '_sec') + '_pkt_cnt'
        self.pkt_cnt_gauge = Gauge(pkt_cnt_gauge_name, "Flow packet count")
        print(pkt_cnt_gauge_name)
        
        # Sequence errors only present on decap (TX) flows...
        if self.dev_type == FlowDir.TX:
            seq_err_gauge_name = 'ch' + str(self.channel) + '_' + FlowType.get_flow_type_name(self.essence) + "_" + str(self.audio_index) + ('_prim' if self.isPrimary else '_sec') + '_seq_err'
            self.seq_err_gauge = Gauge(seq_err_gauge_name, "Flow Sequence Error")
            print(seq_err_gauge_name)


class TelemetryApi():
    TELEMETRY_URL = "/emsfp/node/v1/telemetry"

    def __init__(self, ip):
        self.ip = ip
        self.sfp_monitors = []
        self.flows_monitors = []
        self.devices_monitors = []
        self.capabilites = TelemetryCapabilities()
        self.scan_capabilities()
        
    def _init_health_gauges(self):
        self.gauge_core_temp_gauge = Gauge('core_temp', 'Core Temperature')
        self.gauge_fan_speed_gauge = Gauge('fan_speed', 'System Fan Speed')
        self.gauge_core_voltage = Gauge('core_voltage', 'Core voltage')

    def _init_refclk_gauges(self):
        self.gauge_ptp_state = Gauge('ptp_status', 'Current PTP status, 3 being locked')
        self.gauge_ptp_offset_from_master = Gauge('ptp_offset_from_master', 'ptp offset from master')
        self.gauge_ptp_mean_delay = Gauge('ptp_mean_delay', 'ptp mean delay')

    def _init_devices_gauges(self, telemetry):
        for device in telemetry["devices"]:
            if device["type"] == "encapsulator":
                self.devices_monitors.append(EncapDeviceMonitor(device))
            elif device["type"] == "decapsulator":
                self.devices_monitors.append(DecapDeviceMonitor(device))

    def _init_sfp_monitor_gauges(self, telemetry):
        for sfp_entry in telemetry["mngt_port"]:
            port_num = sfp_entry["port"]
            new_entry = SfpMonitor(port_num)
            self.sfp_monitors.append(new_entry)

    def _init_sfp_monitor_gauges(self, telemetry):
        for sfp_entry in telemetry["mngt_port"]:
            port_num = sfp_entry["port"]
            new_entry = SfpMonitor(port_num)
            self.sfp_monitors.append(new_entry)

    def _init_flows_monitor_gauges(self, telemetry):
        for device in telemetry["devices"]:
            dev_type = FlowDir.RX if device["type"] == "encapsulator" else FlowDir.TX
            audio_index = 1
            # TODO: Rely on channel number when 3.0 is officially released.  This will not work for 
            # NMOS loads...
            channel_num = device["device"][0]
            for engine in device["engines"]:
                essence = engine["essence"]
                for flow in engine["flows"]:
                    isPrimary = True if flow["type"] == "primary" else False

                    if essence == "audio":
                        newGauge = AudioFlowMonitor(channel_num, dev_type, essence, isPrimary, audio_index)
                        audio_index += 1
                    else:
                        newGauge = FlowMonitor(channel_num, dev_type, essence, isPrimary)
                    

    def scan_capabilities(self):
        telemetry = self.read_telemetry()
        
        if "health" in telemetry:
            self.capabilites.health = True
            self._init_health_gauges()

        if "refclk" in telemetry:
            self.capabilites.ptp_monitor = True
            self._init_refclk_gauges()
            self._init_devices_gauges(telemetry)

        if "mngt_port" in telemetry:
            self._init_sfp_monitor_gauges(telemetry)
            self.capabilites.sfp_monitor = True
            
        if "devices" in telemetry:
            self._init_flows_monitor_gauges(telemetry)
            self.capabilites.flows = True            

    def refresh_health(self, telemetry):
        try:
            self.gauge_core_temp_gauge.set(telemetry["health"]["core_temp"])
            self.gauge_fan_speed_gauge.set(telemetry["health"]["fan_speed"])
            self.gauge_core_voltage.set(telemetry["health"]["core_voltage"])
        except:
            self.gauge_core_temp_gauge.set(-1)
            self.gauge_fan_speed_gauge.set(-1)
            self.gauge_core_voltage.set(-1)
            
    def refresh_refclk(self, telemetry):
        try:
            self.gauge_ptp_state.set(telemetry["refclk"]["status"])
            self.gauge_ptp_offset_from_master.set(telemetry["refclk"]["offset_from_master"])
            self.gauge_ptp_mean_delay.set(telemetry["refclk"]["mean_delay"])
        except:
            self.gauge_ptp_state.set(-1)
            self.gauge_ptp_offset_from_master.set(-1)
            self.gauge_ptp_mean_delay.set(-1)

    def refresh_devices(self, telemetry):
        for device_mon in self.devices_monitors:
            device_mon.refresh_gauge(telemetry)

    def _get_sfp_gauges(self, sfp_num):
        for entry in self.sfp_monitors:
            if entry.port_num == sfp_num:
                return entry
        return None
            
    def refresh_sfp_monitor(self, telemetry):
        for sfp_info in telemetry["mngt_port"]:
            sfp_gauges = self._get_sfp_gauges(sfp_info["port"])
            sfp_gauges.sfp_temperature.set(sfp_info["temperature"])
            sfp_gauges.sfp_vcc.set(sfp_info["vcc"])
            sfp_gauges.sfp_txpwr.set(sfp_info["tx_power"])
            sfp_gauges.sfp_rxpwr.set(sfp_info["rx_power"])

    def refresh(self):
        telemetry = self.read_telemetry()
        if telemetry is not None:
            if self.capabilites.health:
                self.refresh_health(telemetry)
            if self.capabilites.ptp_monitor:
                self.refresh_refclk(telemetry)
                self.refresh_devices(telemetry)
            if self.capabilites.sfp_monitor:
                self.refresh_sfp_monitor(telemetry)

    def read_telemetry(self):
        try:
            r = requests.get("http://" + self.ip + self.TELEMETRY_URL, timeout=2)
        except:
            return None
        if r.status_code == 200:
            return r.json()
        else:
            return None


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Options')
    parser.add_argument('--ip', help='ip of the device to monitor')
    parser.add_argument('--port', help='Port to where the Prometeus page will be exposed')
    parser.add_argument('--prettyName', help='Name of the device in Prometheus')
    parser.add_argument('--refresh', default=2, help='Time interval between device telemetry reads')
    args = parser.parse_args()

    interval = args.refresh
    
    print("Scanning Device...")
    telemetry = TelemetryApi(args.ip)
    
    # Start up the server to expose the metrics.
    print("Starting Server...")
    start_http_server(int(args.port))

    api_read_time = Gauge('api_read_time', 'REST api total time for all calls')
    
    print("Registering on Prometheus...")
    register_on_prometheus(args.prettyName)
    
    while True:
        start_time = time.time()
        telemetry.refresh()
        
        api_read_time.set(time.time() - start_time)
        time.sleep(interval)

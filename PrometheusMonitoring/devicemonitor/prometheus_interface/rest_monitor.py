# Copyright 2019 Embrionix Design Inc.
#
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

from prometheus_client import start_http_server, Summary, Gauge, Info
from prettytable import PrettyTable
import random
import time
import requests
import argparse
import prettytable
import os
import json
import socket

# Create a metric to track time spent and requests made.
REQUEST_TIME = Summary('request_processing_seconds', 'Time spent processing request')


class FlowDir():
    RX = 1  # Encap Flow...
    TX = 2  # Decap flow...
    
    @classmethod
    def get_flow_dir_name(self, flow_type):
        if flow_type == 1:
            return "RX"
        else:
            return "TX"


class FlowType():
    UNKNOWN = 0
    VIDEO_2110 = 1
    AUDIO_2110 = 2
    ANCIL_2110 = 3
    VIDEO_2022 = 4
    
    @classmethod
    def get_flow_type_name(self, flow_type):
        if flow_type == 1:
            return "VIDEO_2110"
        elif flow_type == 2:
            return "AUDIO_2110"
        elif flow_type == 3:
            return "ANCIL_2110"
        elif flow_type == 4:
            return "VIDEO_2022"
        else:
            return "UNKNOWN"


class EmFlow:
    def __init__(self, mgmt_ip, uuid, flowIndex, channel):
        self.dir = FlowDir.RX
        self.type = FlowType.VIDEO_2110
        self.uuid = uuid
        self.mgmt_ip = mgmt_ip
        self.isQuad = False
        self.isPrimary = False
        self.pkt_cnt = None
        self.seq_errs = None
        self.channel = channel

        self._check_if_quad()
        self._get_direction()
        self._get_type()
        
        # Primary/Secondary flow detection, cannot find a better way to do it...
        if self.type == FlowType.VIDEO_2022:
            if flowIndex <= 1:
                self.isPrimary = True
            else:
                self.isPrimary = False
                
            if uuid[0] == 'a' or uuid[0] == 'b':
                self.channel = 1
            else:
                self.channel = 2
        else:
            if flowIndex % 2 == 0:
                self.isPrimary = True

    def _check_if_quad(self):
        cfg = self.get_flow_config()
        if isinstance(cfg["network"], (list,)):
            self.isQuad = True
        else:
            self.isQuad = False

    def _get_direction(self):
        if self.isQuad:
            self.dir = FlowDir.TX  # Quads are automatically decapsulators
        else:
            cfg = self.get_flow_config()
            if "pkt_filter_src_ip" in cfg["network"]:
                self.dir = FlowDir.TX  # If we have netfilters settings, we are on a decap flow...
            else:
                self.dir = FlowDir.RX

    def _get_type(self):
        cfg = self.get_flow_config()
        if "format" not in cfg:
            self.type = FlowType.VIDEO_2022
        elif cfg["format"]["format_type"] == "video":
            self.type = FlowType.VIDEO_2110
        elif cfg["format"]["format_type"] == "audio":
            self.type = FlowType.AUDIO_2110
        elif cfg["format"]["format_type"] == "ancillary":
            self.type = FlowType.ANCIL_2110
        else:
            self.type = FlowType.UNKNOWN

    def get_flow_config(self):
        try:
            r = requests.get("http://" + self.mgmt_ip + "/emsfp/node/v1/flows/" + self.uuid, timeout=2)
        except:
            return None
        if r.status_code == 200:
            return r.json()
        else:
            return None

    def get_flow_diag(self):
        try:
            r = requests.get("http://" + self.mgmt_ip + "/emsfp/node/v1/self/diag/flow/" + self.uuid, timeout=2)
        except:
            return None
        if r.status_code == 200:
            return r.json()
        else:
            return None

    def update_pkt_cnt(self):
        cfg = self.get_flow_config()
        if cfg is not None:
            try:  # We can get text values such as N/A when a cleanswitch is pending.
                if self.isQuad:
                    # TODO: Support all quad flows...

                    self.pkt_cnt.set(cfg["network"][0]["pkt_cnt"])
                else:
                    self.pkt_cnt.set(cfg["network"]["pkt_cnt"])
            except:
                self.pkt_cnt.set(-1)
        else:
            self.pkt_cnt.set(-1)

    def update_seq_err(self):
        if self.seq_errs is not None:
            diag = self.get_flow_diag()
            if diag is not None and "rtp_stream_info" in diag:
                if isinstance(diag["rtp_stream_info"], (list,)):
                    # TODO: Support all quad flows...
                    self.seq_errs.set(diag["rtp_stream_info"][0]["status"]["sequence_error"])
                else: 
                    self.seq_errs.set(diag["rtp_stream_info"]["status"]["sequence_error"])
            else:
                self.seq_errs.set(-1)


def get_flows_list(ip):
    try:
        r = requests.get("http://" + ip + "/emsfp/node/v1/flows", timeout=2)
    except:
        return None
    if r.status_code == 200:
        return r.json()
    else:
        return None


def get_ptp_diag(ip):
    try:
        r = requests.get("http://" + ip + "/emsfp/node/v1/self/diag/refclk", timeout=2)
    except:
        return None
    if r.status_code == 200:
        return r.json()
    else:
        return None


def get_ptp_main_page(ip):
    try:
        r = requests.get("http://" + ip + "/emsfp/node/v1/refclk", timeout=2)
    except:
        return None
    if r.status_code == 200:
        return r.json()
    else:
        return None


def get_port_state(ip, portnum):
    try:
        r = requests.get("http://" + ip + "/emsfp/node/v1/port/" + str(portnum), timeout=2)
    except:
        return None
    if r.status_code == 200:
        return r.json()
    else:
        return None


def monitor_sfp_port(ip, portnum, temperature_gauge, vcc_gauge, txpwr_gauge, rxpwr_gauge):
    try:
        cfg = get_port_state(ip, portnum)
        if cfg is not None:
            temperature_gauge.set(cfg["sfp_ddm_info"]["temperature"]["current"])
            vcc_gauge.set(cfg["sfp_ddm_info"]["vcc"]["current"])
            txpwr_gauge.set(cfg["sfp_ddm_info"]["tx_power"]["current"])
            rxpwr_gauge.set(cfg["sfp_ddm_info"]["rx_power"]["current"])
    except:
        temperature_gauge.set(-1)
        vcc_gauge.set(-1)
        txpwr_gauge.set(-1)
        rxpwr_gauge.set(-1)


def monitor_ptp(ip, status_gauge, offset_from_master_gauge, mean_delay_gauge):
    try:
        info = get_ptp_main_page(ip)
        if info is not None:
            status_gauge.set(info['status'])
        else:
            status_gauge.set(-1)
    except:
        status_gauge.set(-1)

    try:
        diag = get_ptp_diag(ip)
        if diag is not None:
            offset_from_master_gauge.set(diag['offset_from_master'])
            mean_delay_gauge.set(diag['mean_delay'])
        else:
            offset_from_master_gauge.set(-1)
            mean_delay_gauge.set(-1)
    except:
        offset_from_master_gauge.set(-1)
        mean_delay_gauge.set(-1)


def get_core_and_fan_speed(ip, temp_gauge, fan_gauge):
    try:
        r = requests.get("http://" + ip + "/emsfp/node/v1/self/system", timeout=2)
        json_resp = r.json()
        temp_gauge.set(json_resp["core_temp"])
        fan_gauge.set(json_resp["fan_speed"])
    except:
        temp_gauge.set(-1)
        fan_gauge.set(-1)


def register_on_prometheus(pretty_name, path="/home/to_monitor"):
    local_ip = socket.gethostbyname(socket.gethostname())
    print("Container IP: " + str(local_ip))
    json_data = '[{"labels": {"job": "' + pretty_name + '"},"targets": ["' + local_ip + ':10600"]}]'
    print("Prometheus data: " + json_data)
    file = open(path + "/" + pretty_name + ".json", "w")
    file.write(json_data)
    file.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Options')
    parser.add_argument('--ip', help='ip of the device to monitor')
    parser.add_argument('--port', help='Port to where the Prometeus page will be exposed')
    parser.add_argument('--prettyName', help='Name of the device in Prometheus')
    args = parser.parse_args()

    interval = 2  # loop delay in seconds

    # Start up the server to expose the metrics.
    print("Starting Server...")
    start_http_server(int(args.port))

    print("Init. Gauges...")
    i = Info('target_info', 'Information about the Embrionix device')
    i.info({'ip': args.ip, 'fw_desc': 'desc...', 'fw_tag': 'tag...', 'fw_crc': 'crc...'})

    ping_latency_gauge = Gauge('ping_latency', 'Ping Latency')
    api_read_time = Gauge('api_read_time', 'REST api total time for all calls')

    ptp_state = Gauge('ptp_status', 'Current PTP status, 3 being locked')
    ptp_offset_from_master = Gauge('ptp_offset_from_master', 'ptp offset from master')
    ptp_mean_delay = Gauge('ptp_mean_delay', 'ptp mean delay')

    sfp_p3_temperature = Gauge('sfp_temperature_p3', 'Temperature of SFP in port 3')
    sfp_p3_vcc = Gauge('sfp_vcc_p3', 'VCC voltage')
    sfp_p3_txpwr = Gauge('sfp_txpwr_p3', 'SFP Tx Power')
    sfp_p3_rxpwr = Gauge('sfp_rxpwr_p3', 'SFP Rx Power')

    sfp_p5_temperature = Gauge('sfp_temperature_p5', 'Temperature of SFP in port 5')
    sfp_p5_vcc = Gauge('sfp_vcc_p5', 'VCC voltage')
    sfp_p5_txpwr = Gauge('sfp_txpwr_p5', 'SFP Tx Power')
    sfp_p5_rxpwr = Gauge('sfp_rxpwr_p5', 'SFP Rx Power')
    
    core_temp_gauge = Gauge('core_temp', 'EmBox6 Core Temperature')
    fan_speed_gauge = Gauge('fan_speed', 'EmBox6 System Fan Speed')

    print("Scanning Flows...")
    table = PrettyTable()
    table.field_names = ["UUID", "Type", "Dir", "Redundancy", "Chan"]
    uuid_list = get_flows_list(args.ip)
    flows = []
    channel = 1  # 1 Based channel, to be consistent with device ports numbering...
    audio_index = 0
    for i, uuid in enumerate(uuid_list):
        newFlow = EmFlow(args.ip, uuid.replace("/", ""), i, channel)

        if newFlow.type == FlowType.ANCIL_2110:
            audio_index = 0

        pkt_cnt_gauge_name = ""
        seq_err_gauge_name = ""
        print(uuid)
        if newFlow.type == FlowType.AUDIO_2110:
            pkt_cnt_gauge_name = 'ch' + str(newFlow.channel) + '_' + FlowType.get_flow_type_name(newFlow.type) + "_" + str(audio_index) + ('_prim' if newFlow.isPrimary else '_sec') + '_pkt_cnt'
            seq_err_gauge_name = 'ch' + str(newFlow.channel) + '_' + FlowType.get_flow_type_name(newFlow.type) + "_" + str(audio_index) + ('_prim' if newFlow.isPrimary else '_sec') + '_seq_err'
            if not newFlow.isPrimary:
                audio_index += 1
        else:
            pkt_cnt_gauge_name = 'ch' + str(newFlow.channel) + '_' + FlowType.get_flow_type_name(newFlow.type) + ('_prim' if newFlow.isPrimary else '_sec') + '_pkt_cnt'
            seq_err_gauge_name = 'ch' + str(newFlow.channel) + '_' + FlowType.get_flow_type_name(newFlow.type) + ('_prim' if newFlow.isPrimary else '_sec') + '_seq_err'

        newFlow.pkt_cnt = Gauge(pkt_cnt_gauge_name, 'Packet Count')
        if newFlow.dir == FlowDir.TX:
            newFlow.seq_errs = Gauge(seq_err_gauge_name, 'Packet Count')
        flows.append(newFlow)
        table.add_row([newFlow.uuid, FlowType.get_flow_type_name(newFlow.type), FlowDir.get_flow_dir_name(newFlow.dir), "Primary" if newFlow.isPrimary else "Secondary",
                       str(channel)])
        
        if newFlow.isPrimary is False and newFlow.type == FlowType.ANCIL_2110:
            channel += 1
            
    print("Registering on Prometheus...")
    register_on_prometheus(args.prettyName)

print("Discovered flows:")
print(str(table))

print("Starting main loop...")



# Generate some requests.
while True:
    start_time = time.time()
    #get_response_time(args.ip, ping_latency_gauge)
    monitor_sfp_port(args.ip, 3, sfp_p3_temperature, sfp_p3_vcc, sfp_p3_txpwr, sfp_p3_rxpwr)
    monitor_sfp_port(args.ip, 5, sfp_p5_temperature, sfp_p5_vcc, sfp_p5_txpwr, sfp_p5_rxpwr)
    monitor_ptp(args.ip, ptp_state, ptp_offset_from_master, ptp_mean_delay)
    get_core_and_fan_speed(args.ip, core_temp_gauge, fan_speed_gauge)

    for flow in flows:
        flow.update_pkt_cnt()
        flow.update_seq_err()

    api_read_time.set(time.time() - start_time)
    time.sleep(interval)

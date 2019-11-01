from prometheus_client import start_http_server, Summary, Gauge, Enum, Info
from prettytable import PrettyTable
from enum import Enum
import random
import time
import requests
import argparse
import ping
import prettytable

# Create a metric to track time spent and requests made.
REQUEST_TIME = Summary('request_processing_seconds', 'Time spent processing request')


class FlowDir(Enum):
    RX = 1  # Encap Flow...
    TX = 2  # Decap flow...


class FlowType(Enum):
    UNKNOWN = 0
    VIDEO_2110 = 1
    AUDIO_2110 = 2
    ANCIL_2110 = 3


class SfpPort:
    def __init__(self, ip, port_number):
        self.port_number = port_number
        self.gauge_temperature = Gauge('sfp_temperature_p' + str(self.port_number), 'Temperature of SFP in port ' + str(self.port_number))
        self.gauge_vcc = Gauge('sfp_vcc_p' + str(self.port_number), 'VCC voltage')
        self.gauge_txpwr = Gauge('sfp_txpwr_p' + str(self.port_number), 'SFP Tx Power')
        self.gauge_rxpwr = Gauge('sfp_rxpwr_p' + str(self.port_number), 'SFP Rx Power')
        
    def monitor_sfp_port(self):
        try:
            cfg = get_port_state(self.ip, self.portnum)
            if cfg is not None:
                self.gauge_temperature.set(cfg["sfp_ddm_info"]["temperature"]["current"])
                self.gauge_vcc.set(cfg["sfp_ddm_info"]["vcc"]["current"])
                self.gauge_txpwr.set(cfg["sfp_ddm_info"]["tx_power"]["current"])
                self.gauge_rxpwr.set(cfg["sfp_ddm_info"]["rx_power"]["current"])
        except:
            self.gauge_temperature.set(-1)
            self.gauge_vcc.set(-1)
            self.gauge_txpwr.set(-1)
            self.gauge_rxpwr.set(-1)

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

        # Primary/Secondary flow detection, cannot find a better way to do it...
        if flowIndex % 2 == 0:
            self.isPrimary = True

        self._check_if_quad()
        self._get_direction()
        self._get_type()

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
        if cfg["format"]["format_type"] == "video":
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
            if diag is not None:
                # TODO: Support all quad flows...
                self.seq_errs.set(diag["rtp_stream_info"][0]["status"]["sequence_error"])
            else:
                self.seq_errs.set(-1)


class Capabilities():
    def __init__(self):
        self.ptp = False
        self.flows = False
        self.flow_ptp_offset = False
        self.sfp_ports = False


class emDevice():
    def __init__(self, ip):
        self.ip = ip
        self.ports = []
        self.flows = []
        self.scan_capabilities()
        self.init_gauges()


    def init_gauges(self):
        ping_latency_gauge = Gauge('ping_latency', 'Ping Latency')
        api_read_time = Gauge('api_read_time', 'REST api total time for all calls')        


    def scan_capabilities(self):
        self.capabilities = Capabilities()
        self.register_flows()
        if len(self.flows) > 0:
            self.capabilities.flows = True
        
        ptp = self.get_ptp_main_page()
        if ptp is not None:
            self.capabilities.ptp = True
            
        for i in range(1,6):
            if self.get_port_state(i) is not None:
                self.ports.add(SfpPort(self.ip, i))
                self.capabilities.sfp_ports = True
                
        if self.get_dev_list() is not None:
            self.capabilities.flow_ptp_offset = True


    def register_flows(self):
        flows = self.get_flows_list()
        
        table = PrettyTable()
        table.field_names = ["UUID", "Type", "Dir", "Redundancy", "Chan"]
        
        for i, uuid in enumerate(flows):
            newFlow = EmFlow(args.ip, uuid.replace("/", ""), i, channel)

            if newFlow.type == FlowType.ANCIL_2110:
                audio_index = 0

            pkt_cnt_gauge_name = ""
            seq_err_gauge_name = ""
            print(uuid)
            if newFlow.type == FlowType.AUDIO_2110:
                pkt_cnt_gauge_name = 'ch' + str(newFlow.channel) + '_' + newFlow.type.name + "_" + str(audio_index) + (
                    '_prim' if newFlow.isPrimary else '_sec') + '_pkt_cnt'
                seq_err_gauge_name = 'ch' + str(newFlow.channel) + '_' + newFlow.type.name + "_" + str(audio_index) + (
                    '_prim' if newFlow.isPrimary else '_sec') + '_seq_err'
                if not newFlow.isPrimary:
                    audio_index += 1
            else:
                pkt_cnt_gauge_name = 'ch' + str(newFlow.channel) + '_' + newFlow.type.name + (
                    '_prim' if newFlow.isPrimary else '_sec') + '_pkt_cnt'
                seq_err_gauge_name = 'ch' + str(newFlow.channel) + '_' + newFlow.type.name + (
                    '_prim' if newFlow.isPrimary else '_sec') + '_seq_err'

            newFlow.pkt_cnt = Gauge(pkt_cnt_gauge_name, 'Packet Count')
            if newFlow.dir == FlowDir.TX:
                newFlow.seq_errs = Gauge(seq_err_gauge_name, 'Packet Count')
            self.flows.append(newFlow)
            table.add_row([newFlow.uuid, newFlow.type.name, newFlow.dir.name, "Primary" if newFlow.isPrimary else "Secondary",
                           str(channel)])
            if newFlow.isPrimary is False and newFlow.type == FlowType.ANCIL_2110:
                channel += 1            
                
        print("Discovered flows:")
        print(str(table))


    def get_ptp_main_page(self):
        try:
            r = requests.get("http://" + self.ip + "/emsfp/node/v1/refclk", timeout=2)
        except:
            return None
        if r.status_code == 200:
            return r.json()
        else:
            return None


    def get_flows_list(self):
        try:
            r = requests.get("http://" + self.ip + "/emsfp/node/v1/flows", timeout=2)
        except:
            return None
        if r.status_code == 200:
            return r.json()
        else:
            return None


    def monitor_ptp(self, status_gauge, offset_from_master_gauge, mean_delay_gauge):
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


    def get_ptp_diag(self):
        try:
            r = requests.get("http://" + self.ip + "/emsfp/node/v1/self/diag/refclk", timeout=2)
        except:
            return None
        if r.status_code == 200:
            return r.json()
        else:
            return None
        
    def get_dev_list(self):
        try:
            r = requests.get("http://" + self.ip + "/emsfp/node/v1/self/diag/devices/", timeout=2)
        except:
            return None
        if r.status_code == 200:
            return r.json()
        else:
            return None


    def get_port_state(self, portnum):
        try:
            r = requests.get("http://" + self.ip + "/emsfp/node/v1/port/" + str(portnum), timeout=2)
        except:
            return None
        if r.status_code == 200:
            return r.json()
        else:
            return None


    def get_response_time(self, gauge):
        latency = ping.do_one(self.ip, 1, 1000)
        if latency is not None:
            print("Latency: " + str(latency * 1000))
            gauge.set(latency * 1000)
        else:
            print("Target down...")
            gauge.set(-1)


    def get_device_data(self, device_uuid):
        try:
            r = requests.get("http://" + self.ip + "/emsfp/node/v1/self/diag/devices/" + device_uuid, timeout=2)
        except:
            return None
        if r.status_code == 200:
            return r.json()
        else:
            return None


    def monitor_device(ip, device_uuid, gauge_prim, gauge_sec):
        try:
            data = get_device_data(ip, device_uuid)
            gauge_prim.set(int(data["sdi"]["flow_to_ptp_offset"]["primary"]))
            gauge_sec.set(int(data["sdi"]["flow_to_ptp_offset"]["secondary"]))
        except:
            gauge_prim.set(-1)
            gauge_sec.set(-1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Options')
    parser.add_argument('--ip', help='ip of the device to monitor')
    parser.add_argument('--port', help='Port to where the Prometeus page will be exposed')
    args = parser.parse_args()

    interval = 2  # loop delay in seconds

    # Start up the server to expose the metrics.
    print("Starting Server...")
    start_http_server(int(args.port))

    print("Init. Gauges...")
    i = Info('target_info', 'Information about the Embrionix device')
    i.info({'ip': args.ip, 'fw_desc': 'desc...', 'fw_tag': 'tag...', 'fw_crc': 'crc...'})


    ptp_state = Gauge('ptp_status', 'Current PTP status, 3 being locked')
    ptp_offset_from_master = Gauge('ptp_offset_from_master', 'ptp offset from master')
    ptp_mean_delay = Gauge('ptp_mean_delay', 'ptp mean delay')
    
    dev1_sdi_to_ptp_offset_prim = Gauge('dev1_sdi_to_ptp_offset_prim', 'ns')
    dev1_sdi_to_ptp_offset_sec = Gauge('dev1_sdi_to_ptp_offset_sec', 'ns')
    dev2_sdi_to_ptp_offset_prim = Gauge('dev2_sdi_to_ptp_offset_prim', 'ns')
    dev2_sdi_to_ptp_offset_sec = Gauge('dev2_sdi_to_ptp_offset_sec', 'ns')

    print("Scanning Flows...")

    uuid_list = get_flows_list(args.ip)
    flows = []
    channel = 1  # 1 Based channel, to be consistent with device ports numbering...
    audio_index = 0

    devices = []
    
    for dev in get_dev_list(args.ip):
        devices.append(dev)
    
print("Starting main loop...")

# Generate some requests.
while True:
    start_time = time.time()
    get_response_time(args.ip, ping_latency_gauge)
    monitor_sfp_port(args.ip, 3, sfp_p3_temperature, sfp_p3_vcc, sfp_p3_txpwr, sfp_p3_rxpwr)
    monitor_sfp_port(args.ip, 5, sfp_p5_temperature, sfp_p5_vcc, sfp_p5_txpwr, sfp_p5_rxpwr)
    monitor_ptp(args.ip, ptp_state, ptp_offset_from_master, ptp_mean_delay)

    for flow in flows:
        flow.update_pkt_cnt()
        flow.update_seq_err()
        
    monitor_device(args.ip, devices[0], dev1_sdi_to_ptp_offset_prim, dev1_sdi_to_ptp_offset_sec)
    monitor_device(args.ip, devices[1], dev2_sdi_to_ptp_offset_prim, dev2_sdi_to_ptp_offset_sec)
    
    api_read_time.set(time.time() - start_time)
    time.sleep(interval)

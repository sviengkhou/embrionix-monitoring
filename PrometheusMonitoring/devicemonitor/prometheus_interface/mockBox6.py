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
    flows = []
    channel = 1  # 1 Based channel, to be consistent with device ports numbering...
    audio_index = 0
            
    print("Registering on Prometheus...")
    register_on_prometheus(args.prettyName)

    print("Discovered flows:")
    print(str(table))

    print("Starting main loop...")

    # Generate some requests.
    while True:
        start_time = time.time()

        sfp_p3_temperature.set(10)
        sfp_p3_vcc.set(10)
        sfp_p3_txpwr.set(10)
        sfp_p3_rxpwr.set(10)
        
        sfp_p5_temperature.set(11)
        sfp_p5_vcc.set(11)
        sfp_p5_txpwr.set(11)
        sfp_p5_rxpwr.set(11)

        api_read_time.set(time.time() - start_time)
        time.sleep(interval)

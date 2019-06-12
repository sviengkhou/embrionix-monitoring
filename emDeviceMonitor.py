from prometheus_client import start_http_server, Summary, Gauge, Enum
import random
import time
import requests
import argparse


# Create a metric to track time spent and requests made.
REQUEST_TIME = Summary('request_processing_seconds', 'Time spent processing request')

# Decorate function with metric.
@REQUEST_TIME.time()
def process_request(t):
  """A dummy function that takes some time."""
  time.sleep(t)


def get_flow_diag(ip, flow_uuid):
  r = requests.get("http://" + ip + "/emsfp/node/v1/self/diag/flow/" + flow_uuid)
  if r.status_code == 200:
    return r.json()
  else:
    return None


def get_flow_config(ip, flow_uuid):
  r = requests.get("http://" + ip + "/emsfp/node/v1/flows/" + flow_uuid)
  if r.status_code == 200:
    return r.json()
  else:
    return None

def get_ptp_main_page(ip):
  r = requests.get("http://" + ip + "/emsfp/node/v1/refclk")
  if r.status_code == 200:
    return r.json()
  else:
    return None
    
def get_port_state(ip, portnum):
  r = requests.get("http://" + ip + "/emsfp/node/v1/port/" + str(portnum))
  if r.status_code == 200:
    return r.json()
  else:
    return None

def monitor_flow(ip, uuid, pkt_cnt_gauge, seq_err_gauge):
  try:
    diag = get_flow_diag(ip, uuid)
    if diag is not None:
      pkt_cnt_gauge.set(diag["rtp_stream_info"][0]["status"]["pkt_cnt"])
      seq_err_gauge.set(diag["rtp_stream_info"][0]["status"]["sequence_error"])
  except:
    pass

def monitor_sfp_port(ip, portnum, temperature_gauge, vcc_gauge, txpwr_gauge, rxpwr_gauge):
  try:
    cfg = get_port_state(ip, portnum)
    if cfg is not None:
      temperature_gauge.set(cfg["sfp_ddm_info"]["temperature"]["current"])
      vcc_gauge.set(cfg["sfp_ddm_info"]["vcc"]["current"])
      txpwr_gauge.set(cfg["sfp_ddm_info"]["tx_power"]["current"])
      rxpwr_gauge.set(cfg["sfp_ddm_info"]["rx_power"]["current"])
  except:
    pass

def monitor_ptp(ip, gauge):
  try:
    info = get_ptp_main_page(ip)
    gauge.set(info['status'])
  except:
    gauge.set(0)

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Options')
  parser.add_argument('--ip', help='ip of the device to monitor')
  parser.add_argument('--port', help='Port to where the Prometeus page will be exposed')
  args = parser.parse_args()

  interval = 2  # loop delay in seconds
  # Start up the server to expose the metrics.
  start_http_server(int(args.port))
  
  sfp_p3_temperature = Gauge('sfp_temperature_p3', 'Temperature of SFP in port 3')
  sfp_p3_vcc = Gauge('sfp_vcc_p3', 'VCC voltage')
  sfp_p3_txpwr = Gauge('sfp_txpwr_p3', 'SFP Tx Power')
  sfp_p3_rxpwr = Gauge('sfp_rxpwr_p3', 'SFP Rx Power')
  
  sfp_p5_temperature = Gauge('sfp_temperature_p5', 'Temperature of SFP in port 5')
  sfp_p5_vcc = Gauge('sfp_vcc_p5', 'VCC voltage')
  sfp_p5_txpwr = Gauge('sfp_txpwr_p5', 'SFP Tx Power')
  sfp_p5_rxpwr = Gauge('sfp_rxpwr_p5', 'SFP Rx Power')
  
  ptp_state = Gauge('ptp_status', 'Current PTP status, 3 being locked')
  
  flow_pkt_cnt = Gauge('pkt_cnt_204', 'Current packet count')
  flow_seq_error = Gauge('seq_err_204', 'Sequence errors')
  
  # Generate some requests.
  while True:
    monitor_sfp_port(args.ip, 3, sfp_p3_temperature, sfp_p3_vcc, sfp_p3_txpwr, sfp_p3_rxpwr)
    monitor_sfp_port(args.ip, 5, sfp_p5_temperature, sfp_p5_vcc, sfp_p5_txpwr, sfp_p5_rxpwr)
    monitor_ptp(args.ip, ptp_state)
    monitor_flow(args.ip, "204f66a2-9910-11e5-8894-feff819cdc9f", flow_pkt_cnt, flow_seq_error)
    time.sleep(interval)
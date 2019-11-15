from prometheus_client import start_http_server, Summary, Gauge, Enum, Info
import random
import time
import requests
import argparse
import ping

# Create a metric to track time spent and requests made.
REQUEST_TIME = Summary('request_processing_seconds', 'Time spent processing request')

def get_flow_diag(ip, flow_uuid):
  r = requests.get("http://" + ip + "/emsfp/node/v1/self/diag/flow/" + flow_uuid, timeout=2)
  if r.status_code == 200:
    return r.json()
  else:
    return None

def get_flow_config(ip, flow_uuid):
  r = requests.get("http://" + ip + "/emsfp/node/v1/flows/" + flow_uuid, timeout=2)
  if r.status_code == 200:
    return r.json()
  else:
    return None

def get_ptp_diag(ip):
  r = requests.get("http://" + ip + "/emsfp/node/v1/self/diag/refclk", timeout=2)
  if r.status_code == 200:
    return r.json()
  else:
    return None

def get_ptp_main_page(ip):
  r = requests.get("http://" + ip + "/emsfp/node/v1/refclk", timeout=2)
  if r.status_code == 200:
    return r.json()
  else:
    return None
    
def get_port_state(ip, portnum):
  r = requests.get("http://" + ip + "/emsfp/node/v1/port/" + str(portnum), timeout=2)
  if r.status_code == 200:
    return r.json()
  else:
    return None

def monitor_flow(ip, uuid, pkt_cnt_gauge, seq_err_gauge):
  cfg = get_flow_config(ip, uuid)
  diag = get_flow_diag(ip, uuid)
  #try:
  if isinstance(cfg["network"], (list,)):
    pkt_cnt_gauge.set(cfg["network"][0]["pkt_cnt"])
  else:
    pkt_cnt_gauge.set(cfg["network"]["pkt_cnt"])
  
  if "rtp_stream_info" in diag:
    if isinstance(diag["rtp_stream_info"], (list,)):
      seq_err_gauge.set(diag["rtp_stream_info"][0]["status"]["sequence_error"])
    else:
      seq_err_gauge.set(diag["rtp_stream_info"]["status"]["sequence_error"])
  else:
    seq_err_gauge.set(-1)
#  except:
#      pkt_cnt_gauge.set(-1)
#      seq_err_gauge.set(-1)

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
    diag = get_ptp_diag(ip)
    if info is not None:
      status_gauge.set(info['status'])
    else:
      status_gauge.set(-1)
      
    if diag is not None:
      offset_from_master_gauge.set(diag['offset_from_master'])
      mean_delay_gauge.set(diag['mean_delay'])
    else:
      offset_from_master_gauge.set(-1)
      mean_delay_gauge.set(-1)
  except:
      offset_from_master_gauge.set(-1)
      mean_delay_gauge.set(-1)
    
def get_response_time(ip, gauge):
  latency = ping.do_one(ip, 1, 1000)
  if latency is not None:
    print("Latency: " + str(latency * 1000))
    gauge.set(latency * 1000)
  else:
    print("Target down...")
    gauge.set(-1)

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Options')
  parser.add_argument('--ip', help='ip of the device to monitor')
  parser.add_argument('--port', help='Port to where the Prometeus page will be exposed')
  args = parser.parse_args()

  interval = 2  # loop delay in seconds
  # Start up the server to expose the metrics.
  start_http_server(int(args.port))
  
  i = Info('target_info', 'Information about the Embrionix device')
  i.info({'ip': args.ip, 'fw_desc': 'desc...', 'fw_tag': 'tag...', 'fw_crc': 'crc...'})
  
  ping_latency_gauge = Gauge('ping_latency', 'Ping Latency')
  api_read_time = Gauge('api_read_time', 'REST api total time for all calls')
  
  ptp_state = Gauge('ptp_status', 'Current PTP status, 3 being locked')
  ptp_offset_from_master = Gauge('ptp_offset_from_master', 'ptp offset from master')
  ptp_mean_delay = Gauge('ptp_mean_delay', 'ptp mean delay')
  
  flow_104_pkt_cnt = Gauge('pkt_cnt_104', 'Current packet count')
  flow_105_pkt_cnt = Gauge('pkt_cnt_105', 'Current packet count')
  flow_204_pkt_cnt = Gauge('pkt_cnt_204', 'Current packet count')
  flow_205_pkt_cnt = Gauge('pkt_cnt_205', 'Current packet count')

  flow_104_seq_err = Gauge('seq_err_104', 'Sequence errors')
  flow_105_seq_err = Gauge('seq_err_105', 'Sequence errors')
  flow_204_seq_err = Gauge('seq_err_204', 'Sequence errors')
  flow_205_seq_err = Gauge('seq_err_205', 'Sequence errors')
  
  # Generate some requests.
  while True:
    start_time = time.time()
    get_response_time(args.ip, ping_latency_gauge)
    monitor_ptp(args.ip, ptp_state, ptp_offset_from_master, ptp_mean_delay)
    monitor_flow(args.ip, "a04f66a2-9910-11e5-8894-feff819cdc9f", flow_104_pkt_cnt, flow_104_seq_err)
    monitor_flow(args.ip, "a05f66a2-9910-11e5-8894-feff819cdc9f", flow_105_pkt_cnt, flow_105_seq_err)
    monitor_flow(args.ip, "b04f66a2-9910-11e5-8894-feff819cdc9f", flow_204_pkt_cnt, flow_204_seq_err)
    monitor_flow(args.ip, "b05f66a2-9910-11e5-8894-feff819cdc9f", flow_205_pkt_cnt, flow_205_seq_err)
    api_read_time.set(time.time() - start_time)
    time.sleep(interval)
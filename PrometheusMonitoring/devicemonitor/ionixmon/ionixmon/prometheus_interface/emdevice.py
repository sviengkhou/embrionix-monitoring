import requests
from emflow import FlowDir, FlowType, EmFlow

class EmChannel():
    def __init__(self, ip, index):
        self.ip = ip
        self.index = index
        self.flows = []

class EmDevice():
    def __init__(self, ip):
        self.ip = ip
        self.channels = []
        self.scan_flows()
    
    def scan_flows(self):
        devices = self.get_sub_devices()
        channel_number = 1  # Channels are counted from 1...
        
        if devices != None:
            for device in devices:
                new_channel = EmChannel(self.ip, channel_number)
                
                if len(device["senders"]) != 0:
                    for sender in device["senders"]:
                        flows = self.get_sender_flows(sender)
                        primary_flow = EmFlow(self.ip, flows[0], channel_number, True, False)
                        seconadry_flow = EmFlow(self.ip, flows[1], channel_number, False, False)
                        new_channel.flows.append(primary_flow)
                        new_channel.flows.append(seconadry_flow)
                elif len(device["receivers"]) != 0:
                    for receiver in device["receivers"]:
                        flows = self.get_receiver_flows(receiver)
                        primary_flow = EmFlow(self.ip, flows[0], channel_number, True, True)
                        seconadry_flow = EmFlow(self.ip, flows[1], channel_number, False, True)
                        new_channel.flows.append(primary_flow)
                        new_channel.flows.append(seconadry_flow)
                self.channels.append(new_channel)
                channel_number += 1
                

    def get_sub_devices(self):
        try:
            r = requests.get("http://" + self.ip + "/emsfp/node/v1/devices", timeout=2)
        except:
            return None
        if r.status_code == 200:
            return r.json()
        else:
            return None
            
    def get_sender_flows(self, sender):
        try:
            r = requests.get("http://" + self.ip + "/emsfp/node/v1/senders/" + str(sender), timeout=2)
        except:
            return None
        if r.status_code == 200:
            return r.json()["flow_id"]
        else:
            return None
            
    def get_receiver_flows(self, receiver):
        try:
            r = requests.get("http://" + self.ip + "/emsfp/node/v1/receivers/" + str(receiver), timeout=2)
        except:
            return None
        if r.status_code == 200:
            return r.json()["flow_id"]
        else:
            return None
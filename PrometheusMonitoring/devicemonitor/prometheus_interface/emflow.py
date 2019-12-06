# Copyright 2019 Embrionix Design Inc.
#
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
import requests


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

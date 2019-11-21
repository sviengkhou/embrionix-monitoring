from flask import Flask, render_template, flash, request, send_file
import argparse
import json

app = Flask(__name__)

@app.route('/emsfp/node/v1/flows', methods=['GET'])
def FlowList():
    # First channel will be to test Encap
    # Second channel to test decap
    # Third to test decap in quad mode.
    
    json='["104f66a2-9910-11e5-8894-feff819cdc9f", \
            "105f66a2-9910-11e5-8894-feff819cdc9f", \
            "114f66a2-9910-11e5-8894-feff819cdc9f", \
            "115f66a2-9910-11e5-8894-feff819cdc9f", \
            "124f66a2-9910-11e5-8894-feff819cdc9f", \
            "125f66a2-9910-11e5-8894-feff819cdc9f", \
            "134f66a2-9910-11e5-8894-feff819cdc9f", \
            "135f66a2-9910-11e5-8894-feff819cdc9f", \
            "144f66a2-9910-11e5-8894-feff819cdc9f", \
            "145f66a2-9910-11e5-8894-feff819cdc9f", \
            "194f66a2-9910-11e5-8894-feff819cdc9f", \
            "195f66a2-9910-11e5-8894-feff819cdc9f", \
            "204f66a2-9910-11e5-8894-feff819cdc9f", \
            "205f66a2-9910-11e5-8894-feff819cdc9f", \
            "214f66a2-9910-11e5-8894-feff819cdc9f", \
            "215f66a2-9910-11e5-8894-feff819cdc9f", \
            "224f66a2-9910-11e5-8894-feff819cdc9f", \
            "225f66a2-9910-11e5-8894-feff819cdc9f", \
            "234f66a2-9910-11e5-8894-feff819cdc9f", \
            "235f66a2-9910-11e5-8894-feff819cdc9f", \
            "244f66a2-9910-11e5-8894-feff819cdc9f", \
            "245f66a2-9910-11e5-8894-feff819cdc9f", \
            "294f66a2-9910-11e5-8894-feff819cdc9f", \
            "295f66a2-9910-11e5-8894-feff819cdc9f", \
            "304f66a2-9910-11e5-8894-feff819cdc9f", \
            "305f66a2-9910-11e5-8894-feff819cdc9f", \
            "314f66a2-9910-11e5-8894-feff819cdc9f", \
            "315f66a2-9910-11e5-8894-feff819cdc9f", \
            "324f66a2-9910-11e5-8894-feff819cdc9f", \
            "325f66a2-9910-11e5-8894-feff819cdc9f", \
            "334f66a2-9910-11e5-8894-feff819cdc9f", \
            "335f66a2-9910-11e5-8894-feff819cdc9f", \
            "344f66a2-9910-11e5-8894-feff819cdc9f", \
            "345f66a2-9910-11e5-8894-feff819cdc9f", \
            "394f66a2-9910-11e5-8894-feff819cdc9f", \
            "395f66a2-9910-11e5-8894-feff819cdc9f" \
            ]'
    return(json)


@app.route('/emsfp/node/v1/flows/<flow_uuid>', methods=['GET', 'PUT'])
def FlowView(flow_uuid):
    type = "video"
    
    if int(flow_uuid[1]) >= 1 and int(flow_uuid[1]) <=4:
        type = "audio"
    elif int(flow_uuid[1]) == 9:
        type = "ancillary"
    
    
    encap_flow = '{"version": "2", \
                 "label": "st2110 flow", \
                 "id": "a04f66a2-9910-11e5-8894-feff819cdc9f", \
                 "source_id": "a0008e96-990d-11e5-8994-feff819cdc9f", \
                 "type": "26", \
                 "name": "VC-A CAM 59 prim", \
                 "network": { \
                     "src_ip_addr": "10.212.41.4", \
                     "src_udp_port": "10000", \
                     "dst_ip_addr": "239.20.50.40", \
                     "dst_udp_port": "50020", \
                     "dst_mac": "01:00:5e:14:32:28", \
                     "vlan_tag": "2002", \
                     "ssrc": "0", \
                     "pkt_cnt": "319199400", \
                     "rtp_pt": "96", \
                     "ttl": "64", \
                     "dscp": "0", \
                     "enable": "1" \
                 }, \
                 "format": { \
                     "format_type": "' + type +'", \
                     "sdp_file_url": "10.212.43.4/emsfp/node/v1/sdp/a04f66a2-9910-11e5-8894-feff819cdc9f", \
                     "format_code_valid": "1", \
                     "format_code_t_scan": "4", \
                     "format_code_p_scan": "4", \
                     "format_code_mode": "16", \
                     "format_code_format": "0", \
                     "format_code_rate": "10240", \
                     "format_code_sampling": "8192", \
                     "format_bit_depth": 10, \
                     "format_colorimetry": "BT709", \
                     "format_tcs": "SDR", \
                     "format_ictcp": false \
                 }, \
                 "jumbo_frame": "0"}' \
                 
    decap_flow = '{ \
                      "version": "2", \
                      "label": "st2110 flow", \
                      "id": "a04f66a2-9910-11e5-8894-feff819cdc9f", \
                      "source_id": "a0008e96-990d-11e5-8994-feff819cdc9f", \
                      "type": "4", \
                      "name": "", \
                      "network": { \
                          "src_ip_addr": "10.212.33.8", \
                          "src_udp_port": "10000", \
                          "dst_ip_addr": "239.20.10.41", \
                          "dst_udp_port": "50020", \
                          "dst_mac": "01:00:5e:14:0a:29", \
                          "vlan_tag": "0", \
                          "ssrc": "228", \
                          "pkt_filter_src_ip": "1", \
                          "pkt_filter_src_udp": "0", \
                          "pkt_filter_src_mac": "0", \
                          "pkt_filter_dst_ip": "1", \
                          "pkt_filter_dst_udp": "1", \
                          "pkt_filter_dst_mac": "0", \
                          "pkt_filter_vlan": "0", \
                          "pkt_filter_ssrc": "0", \
                          "igmp_src_ip": "10.212.36.4", \
                          "pkt_cnt": "564917849", \
                          "rtp_pt": "96", \
                          "sender_type": "0", \
                          "enable": "1", \
                          "switch_state": "idle" \
                      }, \
                      "format": { \
                          "format_type": "' + type +'", \
                          "sdp_file_url": "10.212.38.4/emsfp/node/v1/sdp/a04f66a2-9910-11e5-8894-feff819cdc9f", \
                          "format_code_valid": "0", \
                          "format_code_t_scan": "4", \
                          "format_code_p_scan": "4", \
                          "format_code_mode": "16", \
                          "format_code_format": "0", \
                          "format_code_rate": "10240", \
                          "format_code_sampling": "8192", \
                          "format_bit_depth": 10, \
                          "format_colorimetry": "BT709", \
                          "format_tcs": "SDR", \
                          "format_ictcp": false, \
                          "sampling_format": "0" \
                      } \
                    }'
                    
    decap_flow_quad = ''
    
    if flow_uuid[0] == 1:
        return(encap_flow)
    else:
        return(decap_flow)


@app.route('/emsfp/node/v1/self/diag/flow/<flow_uuid>', methods=['GET'])
def FlowDiagView(flow_uuid):
    decap_diag = '{ \
                    "api_info": { \
                        "api_version_number": "2" \
                    }, \
                    "format": { \
                        "type": "video", \
                        "valid": "1", \
                        "bit_rate": "0", \
                        "sampling_format": "0", \
                        "frame_rate": "9", \
                        "video_format": "0", \
                        "picture_scan": "1", \
                        "transport_scan": "1", \
                        "video_payload_id": "0x00000000" \
                    }, \
                    "rtp_stream_info": [ \
                        { \
                            "status": { \
                                "pkt_cnt": "2462834", \
                                "sequence_error": "158982" \
                            } \
                        } \
                    ], \
                    "config": { \
                        "reset_counter": "0" \
                    } \
                }'
    return(decap_diag)


@app.route('/emsfp/node/v1/self/system', methods=['GET'])
def SystemView():
    system = '{ \
                "reboot": "0", \
                "config_reset": "0", \
                "staging_mode": 0, \
                "core_temp": 62, \
                "uptime": "0 days, 00:03:44", \
                "fan_speed": 4208, \
                "smpte_network": { \
                    "2022-7": { \
                        "class": "d" \
                    } \
                } \
              }'
    return(system)


@app.route('/emsfp/node/v1/refclk', methods=['GET'])
def PtpMainView():
    ptp_main = '{ \
                    "api_info": { \
                        "api_version_number": "1" \
                    }, \
                    "mode": "0", \
                    "server_mode": "0", \
                    "status": "3", \
                    "manual_ctrl": "0", \
                    "selected_uuid": "f2807dac-985d-11e5-8994-feff819cdc9f", \
                    "uuid": [ \
                        "f2807dac-985d-11e5-8994-feff819cdc9f", \
                        "f3807dac-985d-11e5-8994-feff819cdc9f" \
                    ] \
                }'
    return(ptp_main)


@app.route('/emsfp/node/v1/self/diag/refclk', methods=['GET'])
def PtpDiagView():
    ptp_diag = '{ \
                    "api_info": { \
                        "api_version_number": "1" \
                    }, \
                    "selected_uuid": "00000000-0000-0000-0000-000000000000", \
                    "status": "0", \
                    "delay_req_destination": "224.0.1.129", \
                    "refclk_master_ip": "0.0.0.0", \
                    "counters": { \
                        "sync_counter": 0, \
                        "follow_up_counter": 0, \
                        "delay_request_counter": 0, \
                        "delay_response_counter": 0, \
                        "dropped_follow_sync_counter": 0, \
                        "dropped_delay_response_counter": 0, \
                        "reset": 0 \
                    } \
                }'
    return(ptp_diag)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
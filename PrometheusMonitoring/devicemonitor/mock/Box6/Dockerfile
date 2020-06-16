# Copyright 2019 Embrionix Design Inc.
#
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

# How to use the mock:
# docker build -t box6_mock .
# docker run -d --network="grafana_bridge_net"  box6_mock
# get ip and use it as your device in Ionixmon with:
# docker network inspect grafana_bridge_net

FROM alpine:latest

RUN apk add --update \
	python3 \
	py3-pip
    
RUN pip3 install requests argparse prettytable prometheus_client flask wtforms docker
RUN mkdir /home/to_monitor
COPY mockBox6.py /opt/

CMD python3 /opt/mockBox6.py

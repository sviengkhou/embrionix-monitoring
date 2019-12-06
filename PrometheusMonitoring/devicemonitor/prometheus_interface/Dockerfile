# Copyright 2019 Embrionix Design Inc.
#
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

FROM alpine:latest
ENV deviceip=192.168.39.0
ENV port=5150
ENV prettyName="NA"
ENV monitorScriptName="rest_monitor.py"

RUN apk add --update \
	python3 \
	py3-pip
    
RUN pip3 install requests argparse prettytable prometheus_client flask wtforms docker
RUN mkdir /home/to_monitor
COPY *.py /opt/

CMD python3 /opt/$monitorScriptName --ip $deviceip --port $port --prettyName $prettyName
# Copyright 2019 Embrionix Design Inc.
#
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

FROM alpine:latest

RUN apk add --update \
	python3 \
	py3-pip \
    docker

RUN pip3 install requests argparse prettytable prometheus_client flask wtforms docker datetime pyexcel
ADD ionixmon /opt/ionixmon
RUN mkdir /home/to_monitor

CMD python3 /opt/ionixmon/ionixmon.py
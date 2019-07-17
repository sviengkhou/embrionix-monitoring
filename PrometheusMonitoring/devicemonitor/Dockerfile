FROM alpine:latest
ENV deviceip=192.168.39.0
ENV port=5150


RUN apk add --update \
    python \
    py-pip

RUN pip install requests
RUN pip install argparse
RUN pip install ping
RUN pip install prometheus_client

COPY emBox3_2110sfp_Monitor.py /opt
COPY emBox6Monitor.py /opt

CMD python /opt/emBox3_2110sfp_Monitor.py --ip $deviceip --port $port

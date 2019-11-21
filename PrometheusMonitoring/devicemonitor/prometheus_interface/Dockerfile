FROM alpine:latest
ENV deviceip=192.168.39.0
ENV port=5150
ENV prettyName="NA"

RUN apk add --update \
	python3 \
	py3-pip
    
RUN pip3 install requests argparse prettytable prometheus_client flask wtforms docker
RUN mkdir /home/to_monitor
COPY emBox6Monitor.py /opt/
COPY mockBox6.py /opt/

CMD python3 /opt/emBox6Monitor.py --ip $deviceip --port $port --prettyName $prettyName
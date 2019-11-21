# How to use the mock:
# docker build -t box6_mock .
# docker run -d --network="graphicmonitor_default"  box6_mock
# get ip and use it as your device in Ionixmon with:
# docker network inspect graphicmonitor_default

FROM alpine:latest

RUN apk add --update \
	python3 \
	py3-pip
    
RUN pip3 install requests argparse prettytable prometheus_client flask wtforms docker
RUN mkdir /home/to_monitor
COPY mockBox6.py /opt/

CMD python3 /opt/mockBox6.py
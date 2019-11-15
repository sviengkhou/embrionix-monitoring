FROM alpine:latest

RUN apk add --update \
	python3 \
	py3-pip \
    docker

RUN pip3 install requests argparse prettytable prometheus_client flask wtforms docker
ADD ionixmon /opt/ionixmon

CMD python3 /opt/ionixmon/ionixmon.py
# Embrionix devices monitoring using Grafana and Prometheus

**Note: This is a proof of concept**

The monitor tool contains 3 major elements:
* emDeviceMonitor.py: Translate and expose Embrionix data to Prometheus format
* Prometheus: Datalogging server
* Grafana: Main UI

Prerequisites:
* Python 3.x (3.7 tested), libs: prometheus_client import, random, time, requests, argparse
* A running Docker instance
* Internet access for deployment (In order to fetch Docker images)	

Quickstart:
1. Start Grafana Docker image: sudo docker run -d --name grafana -p 3000:3000 grafana/grafana
1. Edit the targets section of prometheus.yml file to match the ip of your machine in the docker realm, and the port (Given as argument when executing emDeviceMonitor)
1. Build Prometheus image: sudo docker build . -t emprometheus
1. Start Prometheus:  sudo docker run -d --name emprometheus -p 9090:9090 emprometheus:latest
1. Start emDeviceMonitor.py: python3.7 emDeviceMonitor.py --ip <embox6 ip> --port <promtheus interface port>  (There is no verbose for this script, it just.. starts)
1. Connect to prometheus target page on: http://127.0.0.1:9090/targets, verify that your target is up
1. Open Graphana on 127.0.0.1:3000 with a web browser (Default user/password is admin/admin)
1. In the Grafana left hand menu, select configuration and data source. 
1. Add a prometheus data source, you can find its ip using sudo docker network inspect bridge command, make sure the save&test works properly
1. Click on Home in the top left corner once logged in and select import dashboard
1. Select upload json file and upload ./PTP_Optical_Monitor.json
1. If required, change the source ip/port to match your Docker configuration on the top left of the dashboard
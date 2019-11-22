# Embrionix devices monitoring using Grafana and Prometheus

Copyright 2019 Embrionix Design Inc.


Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

The monitor tool contains 4 container images:
* ionixmon: Main webpage for registering and monitoring devices.  One container will be spawned on host per monitored device.
* Prometheus: Datalogging server
* Grafana: Main UI
* prometheus_interface: Docker image with scripts to monitor Embrionix devices

Prerequisites:
* A running Docker instance with docker-compose installed
* Internet access for deployment (In order to fetch Docker images)	

Quickstart:
1. From the checkout folder (At the same level as the docker-compose.yml file), run 'sudo docker build -t prometheus_interface PrometheusMonitoring/devicemonitor/prometheus_interface'.
1. From the same folder as in previous step, build the monitoring docker image, run 'sudo docker-compose up -d --build'
1. Using a web browser, connect to http://127.0.0.1:8060 and add the device to monitor
1. You can do a quick monitor on the 127.0.0.1:8060 page by checking graphs
1. For deeper analysis, use Graphana on 127.0.0.1:3000 with a web browser (Default user/password is admin/admin)

Todo:
* Alarms
* Allow for monitor container removal
* Cleanup docker networks
* Use one container for monitoring instead of spawning one for each monitor threads
* Support syslog
* Device overview
* Load test
* Merge script with capabilites from feature/all_flows

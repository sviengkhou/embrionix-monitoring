# Embrionix devices monitoring using Grafana and Prometheus

## License
Copyright 2019 Embrionix Design Inc.

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

## Content
The monitor tool contains 4 container images:
* ionixmon: 127.0.0.1:8060: Main web page for registering and monitoring devices.  
One container will be spawned on host per monitored device.
* Prometheus: 127.0.0.1:9090: Data logging server
* Grafana: 127.0.0.1:3000: Main UI
* prometheus_interface: Docker image with scripts to monitor Embrionix devices.  
Metrics are shown on monitor docker container ip port 10600.

## Prerequisites
* [Docker](https://www.docker.com/products/docker-desktop)
* [Docker-Compose](https://docs.docker.com/compose/install/) (Compose version >= 1.18.0 for yml definition version >= 3.5)
* Internet access for deployment (In order to fetch Docker images)	

## Quick start
1. From the checkout folder (At the same level as the docker-compose.yml file), run :
```bash
docker build -t prometheus_interface PrometheusMonitoring/devicemonitor/prometheus_interface
```
2. From the same folder as in previous step, build the monitoring docker image, run :
```bash
docker-compose up -d --build
```
3. Using a web browser, connect to http://127.0.0.1:8060 and add the device to monitor in the top bar menu
1. You can do a quick monitor on the http://127.0.0.1:8060 page by checking graphs
1. For deeper analysis, use Graphana on http://127.0.0.1:3000 with a web browser (Default user/password is admin/admin)

## Tested OS
* Ubuntu 16.04/18.04

## Todo
* Use one container for monitoring instead of spawning one for each monitor threads
* Graphs in ionixmon will only be shown for 127.0.0.1 and thus will only work locally
* Alarms
* Cleanup docker networks
* Support syslog
* Load test
* Merge script with capabilities from feature/all_flows

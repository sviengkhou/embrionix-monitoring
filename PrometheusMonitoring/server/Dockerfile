# Copyright 2019 Embrionix Design Inc.
#
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

FROM prom/prometheus

# Add folder for target files
RUN mkdir -p /home/to_monitor

# Add in the configuration file from the local directory.
ADD prometheus.yml /etc/prometheus/prometheus.yml

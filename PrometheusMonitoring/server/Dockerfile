FROM prom/prometheus

# Add folder for target files
RUN mkdir -p /home/to_monitor

# Add in the configuration file from the local directory.
ADD prometheus.yml /etc/prometheus/prometheus.yml

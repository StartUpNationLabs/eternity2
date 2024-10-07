#!/bin/sh

# Substitute environment variables in envoy.tpl.yaml and output to envoy.yaml
envsubst < /etc/envoy/envoy.tpl.yaml > /etc/envoy/envoy.yaml

# Start envoy
exec /usr/local/bin/envoy -c /etc/envoy/envoy.yaml

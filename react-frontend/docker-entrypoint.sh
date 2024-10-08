#!/bin/env bash

# write all env variables to /usr/share/nginx/html/env
env | grep 'SERVER_BASE_URL' > /usr/share/nginx/html/env


nginx -g "daemon off;"

#!/bin/env bash

process_directory() {
    for item in "$1"/*; do
        if [ -f "$item" ]; then
            envsubst < "$item" > "$item.tmp" && mv "$item.tmp" "$item"
        elif [ -d "$item" ]; then
            process_directory "$item"
        fi
    done
}

process_directory "/usr/share/nginx/html"

nginx -g "daemon off;"

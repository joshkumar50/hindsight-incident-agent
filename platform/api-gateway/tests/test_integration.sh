#!/bin/bash
# Simple integration test script to verify Nginx config syntax
nginx -t -c /etc/nginx/nginx.conf

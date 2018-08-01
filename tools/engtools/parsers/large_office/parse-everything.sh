#!/bin/bash

#Copyright (c) 2016 Wind River Systems, Inc.
#
#SPDX-License-Identifier: Apache-2.0
#
# This script is used to parse stats data for all hosts. It is called only for large office.
# For CPE, use parse-controlers.sh script

./parse-controllers.sh &

wait

./parse-computes.sh

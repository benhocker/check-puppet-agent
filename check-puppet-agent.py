#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2015, wywy GmbH
# Author: Christian Becker <christian.becker@wywy.com>
from argparse import ArgumentParser
from datetime import datetime
import os
import sys
import yaml
import time


class MonitoringStatus:
    OK = (0, 'OK')
    WARNING = (1, 'WARNING')
    CRITICAL = (2, 'CRITICAL')

    messages = []

    def __init__(self):
        self.status = self.OK

    def add_status(self, status, message):
        # update internal status only if new status is more severe
        if status[0] > self.status[0]:
            self.status = status
        self.messages.append((status, message))

    def exit(self):
        for message in self.messages:
            print(u'[{status: >8}] {message}'.format(status=message[0][1], message=message[1]))
        exit(self.status[0])


status = MonitoringStatus()
disabled_lock_file = '/var/lib/puppet/state/agent_disabled.lock'
run_lock_file = '/var/lib/puppet/state/agent_catalog_run.lock'

# this try statement contains all of the code below on purpose
# this is to ensure we have a critical state in the monitoring, in case anything goes wrong in here
# noinspection PyBroadException
try:
    parser = ArgumentParser('check_puppet')
    parser.add_argument('--max-run-age', type=int, default=120 * 60,
                        help='max age of last puppet run in seconds (default: 120 * 60)')
    parser.add_argument('--filename', default='/var/lib/puppet/state/last_run_summary.yaml',
                        help='the puppet state file to parse')

    args = parser.parse_args()

    with open(args.filename, 'r') as f:
        run_summary = yaml.load(f)

        if os.path.isfile(disabled_lock_file):

            with open(disabled_lock_file, 'r') as disabled_file:
                disabled_content = yaml.load(disabled_file)

                status.add_status(MonitoringStatus.WARNING,
                                  'puppet agent is disabled - reason: {reason}'.format(
                                      reason=disabled_content['disabled_message']))

        if os.path.exists(run_lock_file):
            run_lock_mtime = os.path.getmtime(run_lock_file)
            run_lock_age = time.time() - run_lock_mtime

            if run_lock_age > args.max_run_age:
                run_lock_status = MonitoringStatus.WARNING
            else:
                run_lock_status = MonitoringStatus.OK

            run_lock_date = datetime.fromtimestamp(run_lock_mtime)
            status.add_status(run_lock_status,
                              'puppet run active since {date} ({minutes:.0f} minutes ago)'.format(
                                  date=run_lock_date.strftime('%Y-%m-%d %H:%M:%S'), minutes=run_lock_age / 60))
        else:
            if run_summary['version']['config'] is None:
                status.add_status(MonitoringStatus.WARNING,
                                  'no catalog received - catalog compile failed?')
            else:
                catalog_time = run_summary['version']['config']
                catalog_age = time.time() - catalog_time

                if catalog_age > args.max_run_age:
                    catalog_status = MonitoringStatus.WARNING
                else:
                    catalog_status = MonitoringStatus.OK

                catalog_date = datetime.fromtimestamp(catalog_time)
                status.add_status(catalog_status,
                                  'applying catalog compiled at {date} ({minutes:.0f} minutes ago)'.format(
                                      date=catalog_date.strftime('%Y-%m-%d %H:%M:%S'), minutes=catalog_age / 60))

            if 'time' not in run_summary:
                status.add_status(MonitoringStatus.WARNING,
                                  'Can not find timing information in {file}'.format(file=args.filename))
            else:
                if 'last_run' not in run_summary['time']:
                    status.add_status(MonitoringStatus.WARNING,
                                      'Can not find last_run duration in {file}'.format(file=args.filename))
                else:
                    last_run = run_summary['time']['last_run']
                    run_age = time.time() - last_run

                    if run_age > args.max_run_age:
                        run_status = MonitoringStatus.WARNING
                    else:
                        run_status = MonitoringStatus.OK

                    run_date = datetime.fromtimestamp(last_run)
                    status.add_status(run_status, 'last run on {date} ({minutes:.0f} minutes ago)'.format(
                        date=run_date.strftime('%Y-%m-%d %H:%M:%S'), minutes=run_age / 60))

                    if 'total' not in run_summary['time']:
                        status.add_status(MonitoringStatus.WARNING,
                                          'Can not find "total" time in {file}'.format(file=args.filename))
                    else:
                        status.add_status(MonitoringStatus.OK,
                                          '=> last run took {seconds:.1f} seconds'.format(
                                              seconds=run_summary['time']['total']))


# catch all exceptions to create an error in the monitoring in case anything goes wrong in this script
except:
    e = sys.exc_info()
    status.add_status(MonitoringStatus.WARNING, str(e[1]))
finally:
    status.exit()

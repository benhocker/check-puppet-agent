#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2015, wywy GmbH
# Author: Christian Becker <christian.becker@wywy.com>
from argparse import ArgumentParser
from datetime import datetime, timedelta
import os
import sys
import yaml


def timedelta_total_seconds(td):
    """
    The timedelta.total_seconds() function was added in Python 2.7.
    If total_seconds() exists, use it.  Otherwise calculate manually.
    Source: https://bitbucket.org/wnielson/django-chronograph/src/f561106f6aaab62f2817e08e51c799320fd916d9/chronograph/compatibility/dates.py?at=default
    @type   td: timedelta
    @param  td: a timedelta where seconds should be "extracted"
    @rtype: double
    """
    if hasattr(td, 'total_seconds'):
        return td.total_seconds()
    else:
        return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10 ** 6) / 10 ** 6


def format_timedelta(delta):
    """ :type delta : timedelta """
    delta_items = []
    total_seconds = timedelta_total_seconds(delta)

    if total_seconds > 86400:
        (days, total_seconds) = divmod(total_seconds, 86400)
        delta_items.append('{days:.0f} days'.format(days=days))

    if total_seconds > 3600:
        (hours, total_seconds) = divmod(total_seconds, 3600)
        delta_items.append('{hours:.0f} hours'.format(hours=hours))

    if total_seconds > 60:
        (minutes, total_seconds) = divmod(total_seconds, 60)
        delta_items.append('{minutes:.0f} minutes'.format(minutes=minutes))

    delta_items.append('{seconds:.0f} seconds'.format(seconds=total_seconds))

    return ' '.join(delta_items)


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
    parser.add_argument('--max-catalog-age', type=int, default=120 * 60,
                        help='max age of the applied catalog in seconds (default: 120 * 60)')
    parser.add_argument('--max-run-duration', type=int, default=30 * 60,
                        help='max age of the applied catalog in seconds (default: 30 * 60)')
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
            run_lock_date = datetime.fromtimestamp(run_lock_mtime)
            run_lock_age = datetime.now() - run_lock_date

            if 0 < args.max_run_duration < run_lock_age:
                run_lock_status = MonitoringStatus.WARNING
            else:
                run_lock_status = MonitoringStatus.OK

            status.add_status(run_lock_status,
                              'puppet run active since {date} ({delta} ago)'.format(
                                  date=run_lock_date.strftime('%Y-%m-%d %H:%M:%S'),
                                  delta=format_timedelta(run_lock_age)))
        else:
            if run_summary['version']['config'] is None:
                status.add_status(MonitoringStatus.WARNING,
                                  'no catalog received - catalog compile failed?')
            else:
                catalog_time = run_summary['version']['config']
                catalog_date = datetime.fromtimestamp(catalog_time)
                catalog_age = datetime.now() - catalog_date

                if 0 < args.max_catalog_age < timedelta_total_seconds(catalog_age):
                    catalog_status = MonitoringStatus.WARNING
                else:
                    catalog_status = MonitoringStatus.OK

                status.add_status(catalog_status,
                                  'applying catalog compiled at {date} ({delta} ago)'.format(
                                      date=catalog_date.strftime('%Y-%m-%d %H:%M:%S'),
                                      delta=format_timedelta(catalog_age)))

            if 'time' not in run_summary:
                status.add_status(MonitoringStatus.WARNING,
                                  'Can not find timing information in {file}'.format(file=args.filename))
            else:
                if 'last_run' not in run_summary['time']:
                    status.add_status(MonitoringStatus.WARNING,
                                      'Can not find last_run duration in {file}'.format(file=args.filename))
                else:
                    last_run = run_summary['time']['last_run']
                    run_date = datetime.fromtimestamp(last_run)
                    run_age = datetime.now() - run_date

                    if 0 < args.max_run_age < timedelta_total_seconds(run_age):
                        run_status = MonitoringStatus.WARNING
                    else:
                        run_status = MonitoringStatus.OK

                    status.add_status(run_status, 'last run on {date} ({delta} ago)'.format(
                        date=run_date.strftime('%Y-%m-%d %H:%M:%S'), delta=format_timedelta(run_age)))

                    if 'total' not in run_summary['time']:
                        status.add_status(MonitoringStatus.WARNING,
                                          'Can not find "total" time in {file}'.format(file=args.filename))
                    else:
                        run_duration = timedelta(seconds=run_summary['time']['total'])

                        if 0 < args.max_run_duration < timedelta_total_seconds(run_duration):
                            run_duration_status = MonitoringStatus.WARNING
                        else:
                            run_duration_status = MonitoringStatus.OK

                        status.add_status(run_duration_status,
                                          '=> last run took {duration}'.format(duration=format_timedelta(run_duration)))


# catch all exceptions to create an error in the monitoring in case anything goes wrong in this script
except:
    e = sys.exc_info()
    status.add_status(MonitoringStatus.WARNING, str(e[1]))
finally:
    status.exit()

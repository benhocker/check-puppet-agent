#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2015, wywy GmbH
# Author: Christian Becker <christian.becker@wywy.com>
from argparse import ArgumentParser
from datetime import datetime, timedelta
import os
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


def format_datetime(time):
    """
    :param time: the input time to format
    :type time: datetime
    :return: formatted date string
    :rtype: str
    """
    return time.strftime('%Y-%m-%d %H:%M:%S')


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


def main(status):
    parser = ArgumentParser('check_puppet')
    parser.add_argument('--warning-run-age', type=int, default=65 * 60,
                        help='warn at age of last puppet run in seconds (default: 65 * 60) => 0 or -1 to disable')
    parser.add_argument('--critical-run-age', type=int, default=130 * 60,
                        help='critical at age of last puppet run in seconds (default: 130 * 60) => 0 or -1 to disable')
    parser.add_argument('--warning-catalog-age', type=int, default=65 * 60,
                        help='warn at catalog age in seconds (default: 65 * 60) => 0 or -1 to disable')
    parser.add_argument('--critical-catalog-age', type=int, default=130 * 60,
                        help='critical at catalog age in seconds (default: 130 * 60) => 0 or -1 to disable')
    parser.add_argument('--warning-run-duration', type=int, default=20 * 60,
                        help='warn at puppet run duration in  seconds (default: 20 * 60) => 0 or -1 to disable')
    parser.add_argument('--critical-run-duration', type=int, default=30 * 60,
                        help='critical at puppet run duration in seconds (default: 30 * 60) => 0 or -1 to disable')
    parser.add_argument('--filename', default='/var/lib/puppet/state/last_run_summary.yaml',
                        help='the puppet state file to parse')
    parser.add_argument('--disabled-lock-file', default='/var/lib/puppet/state/agent_disabled.lock',
                        help='the path to the lock file if the agent is disabled')
    parser.add_argument('--run-lock-file', default='/var/lib/puppet/state/agent_catalog_run.lock',
                        help='the path to the lock file if the agent is running')

    args = parser.parse_args()

    if 0 < args.warning_run_age >= args.critical_run_age:
        status.add_status(MonitoringStatus.WARNING,
                          '--warning-run-age should be lower than --critical-warn-age')

    if 0 < args.warning_catalog_age >= args.critical_catalog_age:
        status.add_status(MonitoringStatus.WARNING,
                          '--warning-catalog-age should be lower than --critical-catalog-age')

    if 0 < args.warning_run_duration >= args.critical_run_duration:
        status.add_status(MonitoringStatus.WARNING,
                          '--warning-run-duration should be lower than --critical-run-duration')

    with open(args.filename, 'r') as f:
        run_summary = yaml.load(f)

        if os.path.isfile(args.disabled_lock_file):
            with open(args.disabled_lock_file, 'r') as disabled_file:
                disabled_content = yaml.load(disabled_file)

                status.add_status(MonitoringStatus.WARNING,
                                  'puppet agent is disabled - reason: {reason}'.format(
                                      reason=disabled_content['disabled_message']))

        if os.path.exists(args.run_lock_file):
            run_lock_mtime = os.path.getmtime(args.run_lock_file)
            run_lock_date = datetime.fromtimestamp(run_lock_mtime)
            run_lock_age = datetime.now() - run_lock_date

            if 0 < args.critical_run_duration <= run_lock_age:
                run_lock_status = MonitoringStatus.CRITICAL
            elif 0 < args.warning_run_duration <= run_lock_age:
                run_lock_status = MonitoringStatus.WARNING
            else:
                run_lock_status = MonitoringStatus.OK

            status.add_status(run_lock_status,
                              'puppet run active since {date} ({delta} ago)'.format(
                                  date=format_datetime(run_lock_date),
                                  delta=format_timedelta(run_lock_age)))
        else:
            if run_summary['version']['config'] is None:
                status.add_status(MonitoringStatus.WARNING,
                                  'no catalog received - catalog compile failed?')
            else:
                catalog_time = run_summary['version']['config']
                catalog_date = datetime.fromtimestamp(catalog_time)
                catalog_age = datetime.now() - catalog_date

                if 0 < args.critical_catalog_age <= timedelta_total_seconds(catalog_age):
                    catalog_status = MonitoringStatus.CRITICAL
                elif 0 < args.warning_catalog_age <= timedelta_total_seconds(catalog_age):
                    catalog_status = MonitoringStatus.WARNING
                else:
                    catalog_status = MonitoringStatus.OK

                status.add_status(catalog_status,
                                  'applying catalog compiled at {date} ({delta} ago)'.format(
                                      date=format_datetime(catalog_date),
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

                    if 0 < args.critical_run_age <= timedelta_total_seconds(run_age):
                        run_status = MonitoringStatus.CRITICAL
                    elif 0 < args.warning_run_age <= timedelta_total_seconds(run_age):
                        run_status = MonitoringStatus.WARNING
                    else:
                        run_status = MonitoringStatus.OK

                    status.add_status(run_status, 'last run on {date} ({delta} ago)'.format(
                        date=format_datetime(run_date), delta=format_timedelta(run_age)))

                    if 'total' not in run_summary['time']:
                        status.add_status(MonitoringStatus.WARNING,
                                          'Can not find "total" time in {file}'.format(file=args.filename))
                    else:
                        run_duration = timedelta(seconds=run_summary['time']['total'])

                        if 0 < args.critical_run_duration <= timedelta_total_seconds(run_duration):
                            run_duration_status = MonitoringStatus.CRITICAL
                        elif 0 < args.warning_run_duration <= timedelta_total_seconds(run_duration):
                            run_duration_status = MonitoringStatus.WARNING
                        else:
                            run_duration_status = MonitoringStatus.OK

                        status.add_status(run_duration_status,
                                          '=> last run took {duration}'.format(duration=format_timedelta(run_duration)))

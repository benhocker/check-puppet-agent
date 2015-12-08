# wywygmbh/check-puppet-agent

A small script with few dependencies to check the status of puppet agent runs

It is tested as a sensu check plugin, but also compatible with nagios/icinga/... due to the similar exit codes

## Installation

### dependencies

The requirements are just:

- `argparse` (command line argument parsing)
- `yaml` (to read the puppet state files)
- `six` (python 2 and 3 compatibility)

### pip

The package is easily available on pypi and can be just installed with pip, this also includes the command line script

   $ pip install check-puppet-agent

### RPM

Currently there are no prebuilt RPM packages provided, but you can built them by yourself with some simple commands

   $ git clone ...
   $ cd check-puppet-agent
   $ python setup.py bdist_rpm

## Usage

Note: The script is to run as puppet user or root, otherwise it is not able to read the required files

    $ check-puppet-agent
    [CRITICAL] applying catalog compiled at 2015-12-06 21:50:21 (1 days 20 hours 3 minutes 23 seconds ago)
    [      OK] last run on 2015-12-08 17:36:19 (17 minutes 25 seconds ago)
    [      OK] => last run took 11 seconds

Sample if the agent is disabled by `puppet agent --disable "test"`

    $ check-puppet-agent
    [ WARNING] puppet agent is disabled - reason: test
    [CRITICAL] applying catalog compiled at 2015-12-06 21:50:21 (1 days 20 hours 4 minutes 53 seconds ago)
    [      OK] last run on 2015-12-08 17:36:19 (18 minutes 55 seconds ago)
    [      OK] => last run took 11 seconds

### Options

    $ check-puppet-agent --help
    usage: check_puppet [-h] [--warning-run-age WARNING_RUN_AGE]
                        [--critical-run-age CRITICAL_RUN_AGE]
                        [--warning-catalog-age WARNING_CATALOG_AGE]
                        [--critical-catalog-age CRITICAL_CATALOG_AGE]
                        [--warning-run-duration WARNING_RUN_DURATION]
                        [--critical-run-duration CRITICAL_RUN_DURATION]
                        [--filename FILENAME]
                        [--disabled-lock-file DISABLED_LOCK_FILE]
                        [--run-lock-file RUN_LOCK_FILE]

    optional arguments:
      -h, --help            show this help message and exit
      --warning-run-age WARNING_RUN_AGE
                            warn at age of last puppet run in seconds (default:
                            1h5m) => 0s to disable
      --critical-run-age CRITICAL_RUN_AGE
                            critical at age of last puppet run in seconds
                            (default: 2h10m) => 0s to disable
      --warning-catalog-age WARNING_CATALOG_AGE
                            warn at catalog age in seconds (default: 1h5m) => 0s
                            to disable
      --critical-catalog-age CRITICAL_CATALOG_AGE
                            critical at catalog age in seconds (default: 2h10m) =>
                            0s to disable
      --warning-run-duration WARNING_RUN_DURATION
                            warn at puppet run duration in seconds (default: 20m)
                            => 0s to disable
      --critical-run-duration CRITICAL_RUN_DURATION
                            critical at puppet run duration in seconds (default:
                            30m) => 0s to disable
      --filename FILENAME   the puppet state file to parse
      --disabled-lock-file DISABLED_LOCK_FILE
                            the path to the lock file if the agent is disabled
      --run-lock-file RUN_LOCK_FILE
                            the path to the lock file if the agent is running

# License

Copyright 2015 wywy GmbH

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

This script is proudly presented by the DevOps guys at [wywy GmbH](http://wywy.com).
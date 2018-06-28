#!/usr/bin/env python
#
# vim: tabstop=4 shiftwidth=4

# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; only version 2 of the License is applicable.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA
#
# Authors:
#   Ricardo Rocha <ricardo@catalyst.net.nz>
#
# About this plugin:
#   This plugin evaluates current latency to write to the test pool.
#
# collectd:
#   http://collectd.org
# collectd-python:
#   http://collectd.org/documentation/manpages/collectd-python.5.shtml
# ceph pools:
#   https://ceph.com/docs/master/man/8/rados/#pool-specific-commands
#

import collectd
import json
import traceback
import subprocess

import base

class CephLatencyPlugin(base.Base):

    def __init__(self):
        base.Base.__init__(self)
        self.prefix = 'ceph'

    def get_stats(self):
        """Retrieves stats regarding latency to write to a test pool"""

        ceph_cluster = "%s-%s" % (self.prefix, self.cluster)

        data = { ceph_cluster: {} }

        try:
            osd_pools='ceph osd pool ls -f json --cluster ' + self.cluster
            pools_output = subprocess.check_output(osd_pools, shell=True)
        except Exception as exc:
            collectd.error("ceph-latency: failed to run rados bench :: %s :: %s"
                    % (exc, traceback.format_exc()))
            return

        if pools_output is None:
            collectd.error('ceph-latency: failed to run rados bench :: pools_output was None')
            return

        json_pools = json.loads(pools_output)

        output = None
        latency_data = {}
        for pool in json_pools:
            try:
                output = subprocess.check_output(
                  "timeout 30s rados --cluster "+ self.cluster +" -p "+ pool +" bench 10 write -t 1 -b 65536 2>/dev/null | grep -i latency | awk '{print 1000*$3}'", shell=True)
            except Exception as exc:
                collectd.error("ceph-latency: failed to run rados bench for pool %s :: %s :: %s"
                        % (pool, exc, traceback.format_exc()))
                continue

            if output is None:
                collectd.error('ceph-latency: failed to run rados bench :: output for pool '+ pool +' was None')
                continue

            latency_data[pool] = output

        # exit if all rados bench failed
        if len(latency_data) == 0:
            return

        for pool_key, pool_data in latency_data.items():

            results = pool_data.split('\n')
            # push values
            data[ceph_cluster][pool_key] = {}
            data[ceph_cluster][pool_key]['avg_latency'] = results[0]
            data[ceph_cluster][pool_key]['stddev_latency'] = results[1]
            data[ceph_cluster][pool_key]['max_latency'] = results[2]
            data[ceph_cluster][pool_key]['min_latency'] = results[3]

        return data

try:
    plugin = CephLatencyPlugin()
except Exception as exc:
    collectd.error("ceph-latency: failed to initialize ceph latency plugin :: %s :: %s"
            % (exc, traceback.format_exc()))

def configure_callback(conf):
    """Received configuration information"""
    plugin.config_callback(conf)

def read_callback():
    """Callback triggerred by collectd on read"""
    plugin.read_callback()

collectd.register_config(configure_callback)
collectd.register_read(read_callback, plugin.interval)

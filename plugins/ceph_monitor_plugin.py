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
#   This plugin collects information regarding Ceph Monitors.
#
# collectd:
#   http://collectd.org
# collectd-python:
#   http://collectd.org/documentation/manpages/collectd-python.5.shtml
# ceph mons:
#   http://ceph.com/docs/master/rados/operations/monitoring/#checking-monitor-status
#

import collectd
import json
import traceback
import subprocess

import base

class CephMonPlugin(base.Base):

    def __init__(self):
        base.Base.__init__(self)
        self.prefix = 'ceph'

    def get_stats(self):
        """Retrieves stats from ceph mons"""

        ceph_cluster = "%s-%s" % (self.prefix, self.cluster)

        data = { ceph_cluster: { 'mon': { 'number': 0, 'quorum': 0, 'health': 0, 'warn': 0, 'error': 0, } } }
        output = None
        try:
            cephmoncmdline='ceph mon dump --format json --cluster ' + self.cluster
            cephmoncmdhealth='ceph status --format json --cluster ' + self.cluster
            output = subprocess.check_output(cephmoncmdline, shell=True)
            output_health = subprocess.check_output(cephmoncmdhealth, shell=True)
        except Exception as exc:
            collectd.error("ceph-mon: failed to ceph mon dump :: %s :: %s"
                    % (exc, traceback.format_exc()))
            return

        if output is None:
            collectd.error('ceph-mon: failed to ceph mon dump :: output was None')

        json_data = json.loads(output)
        json_data_health = json.loads(output_health)

        data[ceph_cluster]['mon']['number'] = len(json_data['mons'])
        data[ceph_cluster]['mon']['quorum'] = len(json_data['quorum'])
        
        # Comment the following 3 lines because ceph luminous changed the json output
        # No more overall_status key. Replaced with status. 
        # data[ceph_cluster]['mon']['health'] = 1 if json_data_health['health']['overall_status'].lower() == 'health_ok' else 0
        # data[ceph_cluster]['mon']['warn'] = 1 if json_data_health['health']['overall_status'].lower() == 'health_warn' else 0
        # data[ceph_cluster]['mon']['error'] = 1 if json_data_health['health']['overall_status'].lower() == 'health_err' else 0
        data[ceph_cluster]['mon']['health'] = 1 if json_data_health['health']['status'].lower() == 'health_ok' else 0
        data[ceph_cluster]['mon']['warn'] = 1 if json_data_health['health']['status'].lower() == 'health_warn' else 0
        data[ceph_cluster]['mon']['error'] = 1 if json_data_health['health']['status'].lower() == 'health_err' else 0

        return data

try:
    plugin = CephMonPlugin()
except Exception as exc:
    collectd.error("ceph-mon: failed to initialize ceph mon plugin :: %s :: %s"
            % (exc, traceback.format_exc()))

def configure_callback(conf):
    """Received configuration information"""
    plugin.config_callback(conf)

def read_callback():
    """Callback triggerred by collectd on read"""
    plugin.read_callback()

collectd.register_config(configure_callback)
collectd.register_read(read_callback, plugin.interval)

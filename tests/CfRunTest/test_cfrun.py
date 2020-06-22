import pytest
# import responses
from pathlib import Path

from cf_runtests.input.cf_config import *
from cf_runtests.input.credentials import *
from cf_common.cf_functions import *
from cf_common.CfClient import *
from cf_common.CfRunTest import *

def test_rundata_defaults():
    rd = RunData()
    assert(rd.core_count == 6)
    assert(rd.client_core_count == 3)
    assert(rd.in_ramp_seek == False)

def test_capacity_adjust_non_SPR(test_set_a):
    run_info, queue_info, config, started = test_set_a
    rd = RunData()
    detailed_report = ""
    output_dir = ""
    cf = CfClient(cf_controller_address, username, password, verify_ssl)
    rt = CfRunTest(cf, run_info, rd, detailed_report, output_dir)
    if rt is not False:
        rt.init_input_csv(rd, run_info)
        rd.queue_info = queue_info
        rd.test_config = config

        rt.init_capacity_adj(rd)
    assert(rd.queue_capacity == 60)
    assert(rd.core_count == 6)
    assert(rd.client_port_count == 1)
    assert(rd.server_port_count == 1)
    assert(rd.client_core_count == 3)
    assert(rd.in_capacity_adjust == 3)

# def test_capacity_adjust_SPR(test_set_b):
#     run_info, queue_info, config, started = test_set_b
#     rd = RunData()
#     detailed_report = ""
#     output_dir = ""
#     cf = CfClient(cf_controller_address, username, password, verify_ssl)
#     rt = CfRunTest2(cf, run_info, rd, detailed_report, output_dir)
#     if rt is not False:
#         rt.init_input_csv(rd, run_info)
#         rd.queue_info = queue_info
#         rd.test_config = config

#         rt.init_capacity_adj(rd)
#     assert(rd.queue_capacity == 40)
#     assert(rd.core_count == 4)
#     assert(rd.client_port_count == 1)
#     assert(rd.server_port_count == 1)
#     assert(rd.client_core_count == 2)
#     assert(rd.in_capacity_adjust == 2)

def test_load_functions(test_set_a):
    run_info, queue_info, config, started = test_set_a
    rd = RunData()
    detailed_report = ""
    output_dir = Path.cwd()
    cf = CfClient(cf_controller_address, username, password, verify_ssl)
    rt = CfRunTest(cf, run_info, rd, detailed_report, output_dir)
    if rt is not False:
        # rt.init_sequence(cf, rd, run_info)
        rt.init_input_csv(rd, run_info)
        rd.queue_info = queue_info
        rd.test_config = config

        rt.init_capacity_adj(rd)
        rt.init_update_config_load(rd)

        rd.test_started = True
        rd.test_run = started
        rt.init_test_run(rd, cf.controller_ip)

        rt.init_rolling_stats(rd)

        # independant functions in random order
        rd.time_elapsed = 10
        rd.time_remaining = 200
        rt.update_phase(rd)
        rt.update_rolling_averages(rd)
        rt.check_kpi(rd)
        rt.check_ramp_seek_kpi(rd)
        rt.check_stop_conditions(rd)
        rt.control_test_ramp_seek(rd, rd.ramp_seek_kpi, rd.in_ramp_seek_value)
        rt.print_test_status(rd) # function not used
        rt.print_test_stats(rd) # function not used
        rt.check_if_load_type_simusers(rd)
        rt.check_if_load_type_default(rd)


def test_CfRunTest(test_set_a):
    run_info, queue_info, config, started = test_set_a
    rd = RunData()
    detailed_report = ""
    output_dir = Path.cwd()
    cf = CfClient(cf_controller_address, username, password, verify_ssl)
    rt = CfRunTest(cf, run_info, rd, detailed_report, output_dir)
    if rt is not False:
        rt.init_input_csv(rd, run_info)
        rd.queue_info = queue_info
        rd.test_config = config

        rt.init_capacity_adj(rd)
        rt.init_update_config_load(rd)

        rd.test_started = True
        rd.test_run = started
        rt.init_test_run(rd, cf.controller_ip)

        rt.init_rolling_stats(rd)
        # rt.control_test()
    
        # rt.sustain_test(cf, rd)

@pytest.fixture()
def test_set_a():
    run_info = {
        'name': 'T02-HTTP-CPS-1K_uuu',
        'id': '41f3e448af41647e0abfd9806b28e947',
        'type': 'http_connections_per_second',
        'run': 'Y',
        'run_order': '1',
        'goal_seek': 'Y',
        'ramp_seek': 'N',
        'ramp_kpi': 'cps',
        'ramp_value': '1000',
        'ramp_step': '5',
        'duration': '1800',
        'startup': '5',
        'rampup': '10',
        'rampdown': '10',
        'shutdown': '10',
        'sustain_period': '30',
        'kpi_1': 'tps',
        'kpi_2': 'cps',
        'kpi_and_or': 'OR',
        'load_type': 'simusers',
        'start_load': '7',
        'incr_low': '7',
        'incr_med': '5',
        'incr_high': '3',
        'low_threshold': '20',
        'med_threshold': '5',
        'high_threshold': '1',
        'variance_sample_size': '3',
        'max_variance': '0.03',
        'capacity_adj': 'auto',
        'ramp_low': '40',
        'ramp_med': '30',
        'ramp_high': '20',
        'living_simusers_max': 'none'
    }

    queue_info = {
        'author': 'test@spirent.com',
        'capacity': 60,
        'color': 'color4',
        'computeGroupCount': 1,
        'computeGroups': [
            {
                'available': False,
                'capacity': 60,
                'cores': 6,
                'groupId': 5,
                'id': '49010a80c38be9529260804f98cb4621',
                'memory': 63894000000,
                'ports': [
                    {
                        'autoNegotiation': True,
                        'available': None,
                        'capacity': 30,
                        'cores': 3,
                        'displayName': 'Eth4',
                        'duplex': 'Full Duplex',
                        'enabled': True,
                        'id': '49010a80c38be9529260804f98cb588a',
                        'interfaces': [
                            {
                                'address': '105.0.0.1',
                                'count': 1000,
                                'netmask': 16,
                                'protocol': 'ipv4',
                            },
                        ],
                        'lastTestRunTime': '2020-04-20T21:14:18Z',
                        'link': 'NONE',
                        'mac': '',
                        'media': 'Fiber',
                        'number': 5,
                        'portId': 5,
                        'reservedBy': 'CyberFlood-10.141.41.219',
                        'slotId': '1/5',
                        'speed': 10000,
                        'systemId': '10.71.90.241/1/5',
                        'testRunning': False,
                    },
                    {
                        'autoNegotiation': True,
                        'available': None,
                        'capacity': 30,
                        'cores': 3,
                        'displayName': 'Eth5',
                        'duplex': 'Full Duplex',
                        'enabled': True,
                        'id': '49010a80c38be9529260804f98cb5131',
                        'interfaces': [
                            {
                                'address': '106.0.0.1',
                                'count': 1000,
                                'netmask': 16,
                                'protocol': 'ipv4',
                            },
                        ],
                        'lastTestRunTime': '2020-04-20T21:14:12Z',
                        'link': 'NONE',
                        'mac': '',
                        'media': 'Fiber',
                        'number': 6,
                        'portId': 6,
                        'reservedBy': 'CyberFlood-10.141.41.219',
                        'slotId': '1/6',
                        'speed': 10000,
                        'systemId': '10.71.90.241/1/6',
                        'testRunning': False,
                    },
                ],
                'queueId': '8 x 10G Aonic',
                'reservedBy': 'CyberFlood-10.141.41.219',
                'selectable': True,
                'software': 'l4l7lxc5.07.0495',
            },
        ],
        'createdAt': '2020-04-17T21:42:13.038Z',
        'devices': [
            {
                'author': 'test@spirent.com',
                'description': 'SPT-C100-S3',
                'deviceLocation': {
                    'building': None,
                    'city': None,
                    'country': None,
                    'id': 'e7835aa3e0e2bdbd8ddd51bee77648bf',
                    'name': '',
                    'state': None,
                },
                'deviceLocationId': 'e7835aa3e0e2bdbd8ddd51bee77648bf',
                'firmware': {'latest': False, 'version': '5.07.0495'},
                'id': '10.71.90.241',
                'ip': '10.71.90.241',
                'online': True,
                'portReservable': None,
                'rackLocation': None,
                'serialNumber': '7-A684BFC5',
                'slots': [
                    {
                        'author': 'test@spirent.com',
                        'computeGroups': [
                            {
                                'available': True,
                                'capacity': 60,
                                'cores': 6,
                                'groupId': 1,
                                'id': '49010a80c38be9529260804f98cb763c',
                                'memory': 63894000000,
                                'ports': [
                                    {
                                        'autoNegotiation': True,
                                        'available': None,
                                        'capacity': 30,
                                        'cores': 3,
                                        'displayName': 'Eth0',
                                        'duplex': 'Full Duplex',
                                        'enabled': True,
                                        'id': '49010a80c38be9529260804f98cb81aa',
                                        'interfaces': [
                                            {
                                                'address': '101.0.0.1',
                                                'count': 1000,
                                                'netmask': 16,
                                                'protocol': 'ipv4',
                                            },
                                        ],
                                        'lastTestRunTime': '2020-04-17T22:59:40Z',
                                        'link': 'NONE',
                                        'mac': '',
                                        'media': 'Fiber',
                                        'number': 1,
                                        'portId': 1,
                                        'reservedBy': None,
                                        'slotId': '1/1',
                                        'speed': 10000,
                                        'systemId': '10.71.90.241/1/1',
                                        'testRunning': False,
                                    },
                                    {
                                        'autoNegotiation': True,
                                        'available': None,
                                        'capacity': 30,
                                        'cores': 3,
                                        'displayName': 'Eth1',
                                        'duplex': 'Full Duplex',
                                        'enabled': True,
                                        'id': '49010a80c38be9529260804f98cb76d6',
                                        'interfaces': [
                                            {
                                                'address': '102.0.0.1',
                                                'count': 1000,
                                                'netmask': 16,
                                                'protocol': 'ipv4',
                                            },
                                        ],
                                        'lastTestRunTime': '2020-04-17T22:59:36Z',
                                        'link': 'NONE',
                                        'mac': '',
                                        'media': 'Fiber',
                                        'number': 2,
                                        'portId': 2,
                                        'reservedBy': None,
                                        'slotId': '1/2',
                                        'speed': 10000,
                                        'systemId': '10.71.90.241/1/2',
                                        'testRunning': False,
                                    },
                                ],
                                'selectable': False,
                                'software': 'l4l7lxc5.07.0495',
                            },
                            {
                                'available': True,
                                'capacity': 60,
                                'cores': 6,
                                'groupId': 3,
                                'id': '49010a80c38be9529260804f98cb5d8b',
                                'memory': 63894000000,
                                'ports': [
                                    {
                                        'autoNegotiation': True,
                                        'available': None,
                                        'capacity': 30,
                                        'cores': 3,
                                        'displayName': 'Eth2',
                                        'duplex': 'Full Duplex',
                                        'enabled': True,
                                        'id': '49010a80c38be9529260804f98cb666d',
                                        'interfaces': [
                                            {
                                                'address': '103.0.0.1',
                                                'count': 1000,
                                                'netmask': 16,
                                                'protocol': 'ipv4',
                                            },
                                        ],
                                        'lastTestRunTime': '2020-04-17T23:02:36Z',
                                        'link': 'NONE',
                                        'mac': '',
                                        'media': 'Fiber',
                                        'number': 3,
                                        'portId': 3,
                                        'reservedBy': None,
                                        'slotId': '1/3',
                                        'speed': 10000,
                                        'systemId': '10.71.90.241/1/3',
                                        'testRunning': False,
                                    },
                                    {
                                        'autoNegotiation': True,
                                        'available': None,
                                        'capacity': 30,
                                        'cores': 3,
                                        'displayName': 'Eth3',
                                        'duplex': 'Full Duplex',
                                        'enabled': True,
                                        'id': '49010a80c38be9529260804f98cb61f9',
                                        'interfaces': [
                                            {
                                                'address': '104.0.0.1',
                                                'count': 1000,
                                                'netmask': 16,
                                                'protocol': 'ipv4',
                                            },
                                        ],
                                        'lastTestRunTime': '2020-04-17T23:02:32Z',
                                        'link': 'NONE',
                                        'mac': '',
                                        'media': 'Fiber',
                                        'number': 4,
                                        'portId': 4,
                                        'reservedBy': None,
                                        'slotId': '1/4',
                                        'speed': 10000,
                                        'systemId': '10.71.90.241/1/4',
                                        'testRunning': False,
                                    },
                                ],
                                'selectable': False,
                                'software': 'l4l7lxc5.07.0495',
                            },
                            {
                                'available': False,
                                'capacity': 60,
                                'cores': 6,
                                'groupId': 5,
                                'id': '49010a80c38be9529260804f98cb4621',
                                'memory': 63894000000,
                                'ports': [
                                    {
                                        'autoNegotiation': True,
                                        'available': None,
                                        'capacity': 30,
                                        'cores': 3,
                                        'displayName': 'Eth4',
                                        'duplex': 'Full Duplex',
                                        'enabled': True,
                                        'id': '49010a80c38be9529260804f98cb588a',
                                        'interfaces': [
                                            {
                                                'address': '105.0.0.1',
                                                'count': 1000,
                                                'netmask': 16,
                                                'protocol': 'ipv4',
                                            },
                                        ],
                                        'lastTestRunTime': '2020-04-20T21:14:18Z',
                                        'link': 'NONE',
                                        'mac': '',
                                        'media': 'Fiber',
                                        'number': 5,
                                        'portId': 5,
                                        'reservedBy': 'CyberFlood-10.141.41.219',
                                        'slotId': '1/5',
                                        'speed': 10000,
                                        'systemId': '10.71.90.241/1/5',
                                        'testRunning': False,
                                    },
                                    {
                                        'autoNegotiation': True,
                                        'available': None,
                                        'capacity': 30,
                                        'cores': 3,
                                        'displayName': 'Eth5',
                                        'duplex': 'Full Duplex',
                                        'enabled': True,
                                        'id': '49010a80c38be9529260804f98cb5131',
                                        'interfaces': [
                                            {
                                                'address': '106.0.0.1',
                                                'count': 1000,
                                                'netmask': 16,
                                                'protocol': 'ipv4',
                                            },
                                        ],
                                        'lastTestRunTime': '2020-04-20T21:14:12Z',
                                        'link': 'NONE',
                                        'mac': '',
                                        'media': 'Fiber',
                                        'number': 6,
                                        'portId': 6,
                                        'reservedBy': 'CyberFlood-10.141.41.219',
                                        'slotId': '1/6',
                                        'speed': 10000,
                                        'systemId': '10.71.90.241/1/6',
                                        'testRunning': False,
                                    },
                                ],
                                'queueId': '8 x 10G Aonic',
                                'reservedBy': 'CyberFlood-10.141.41.219',
                                'selectable': True,
                                'software': 'l4l7lxc5.07.0495',
                            },
                            {
                                'available': True,
                                'capacity': 60,
                                'cores': 6,
                                'groupId': 7,
                                'id': '49010a80c38be9529260804f98cb2b5d',
                                'memory': 63894000000,
                                'ports': [
                                    {
                                        'autoNegotiation': True,
                                        'available': None,
                                        'capacity': 30,
                                        'cores': 3,
                                        'displayName': 'Eth6',
                                        'duplex': 'Full Duplex',
                                        'enabled': True,
                                        'id': '49010a80c38be9529260804f98cb3f4a',
                                        'interfaces': [
                                            {
                                                'address': '107.0.0.1',
                                                'count': 1000,
                                                'netmask': 16,
                                                'protocol': 'ipv4',
                                            },
                                        ],
                                        'lastTestRunTime': '2020-04-13T23:59:30Z',
                                        'link': 'NONE',
                                        'mac': '',
                                        'media': 'Fiber',
                                        'number': 7,
                                        'portId': 7,
                                        'reservedBy': 'CyberFlood-10.71.50.198',
                                        'slotId': '1/7',
                                        'speed': 10000,
                                        'systemId': '10.71.90.241/1/7',
                                        'testRunning': False,
                                    },
                                    {
                                        'autoNegotiation': True,
                                        'available': None,
                                        'capacity': 30,
                                        'cores': 3,
                                        'displayName': 'Eth7',
                                        'duplex': 'Full Duplex',
                                        'enabled': True,
                                        'id': '49010a80c38be9529260804f98cb3ab5',
                                        'interfaces': [
                                            {
                                                'address': '108.0.0.1',
                                                'count': 1000,
                                                'netmask': 16,
                                                'protocol': 'ipv4',
                                            },
                                        ],
                                        'lastTestRunTime': '2020-04-13T23:59:24Z',
                                        'link': 'NONE',
                                        'mac': '',
                                        'media': 'Fiber',
                                        'number': 8,
                                        'portId': 8,
                                        'reservedBy': 'CyberFlood-10.71.50.198',
                                        'slotId': '1/8',
                                        'speed': 10000,
                                        'systemId': '10.71.90.241/1/8',
                                        'testRunning': False,
                                    },
                                ],
                                'selectable': False,
                                'software': 'l4l7lxc5.07.0495',
                            },
                        ],
                        'cpu': 0,
                        'description': 'SPT-C100-S3-MP-2',
                        'id': '49010a80c38be9529260804f98cb1f4f',
                        'mode': 'NA',
                        'model': 'SPT-C100-S3-MP-2',
                        'orientation': 'vertical',
                        'portGroups': [
                            [1, 2],
                            [3, 4],
                            [9, 10, 11, 12],
                            [5, 6],
                            [7, 8],
                            [13, 14, 15, 16],
                        ],
                        'profile': 'L4L7-Functional-8x10G',
                        'profiles': [
                            {
                                'activePortGroups': [1, 3, 4, 6],
                                'description': 'L4L7-Functional-4x10G-8x1G',
                                'name': 'L4L7-Functional-4x10G-8x1G',
                                'type': 'L4L7-ADVFUZZ',
                            },
                            {
                                'activePortGroups': [1, 2, 4, 5],
                                'description': 'L4L7-Functional-8x10G',
                                'name': 'L4L7-Functional-8x10G',
                                'type': 'L4L7-ADVFUZZ',
                            },
                            {
                                'activePortGroups': [1, 4],
                                'description': 'L4L7-Performance-4x10G',
                                'name': 'L4L7-Performance-4x10G',
                                'type': 'L4L7-ADVFUZZ',
                            },
                            {
                                'activePortGroups': [1, 2, 4, 5],
                                'description': 'STC-8x10G-Port-Functional',
                                'name': 'STC-8x10G-Port-Functional',
                                'type': 'STC',
                            },
                            {
                                'activePortGroups': [3, 6],
                                'description': 'STC-8x1G-Port-Functional',
                                'name': 'STC-8x1G-Port-Functional',
                                'type': 'STC',
                            },
                        ],
                        'selectable': True,
                        'serialNumber': '7-A684BFC5',
                        'slotId': 1,
                        'software': '5.07.0495',
                    },
                ],
                'status': 'active',
                'totalCapacity': 240,
                'totalPorts': 8,
                'totalSlots': 1,
            },
        ],
        'enqueuedTestCount': 0,
        'id': '8 x 10G Aonic',
        'name': '8 x 10G Aonic',
        'portCount': 0,
        'ports': [],
        'testRuns': [
            {
                'createdAt': '2020-04-17T22:59:57.011Z',
                'id': 'aac3cde0ebaabae2fbcbc4cfbd5671e7',
                'runId': 'T07_TLS_TPUT_EC_DSA521_A256_GCM_S3_16K_2lt_2020_4_17__15_59_58__14',
                'status': 'stopped',
                'stoppedAt': '2020-04-17T23:04:13.000Z',
                'test': {
                    'id': 'aac3cde0ebaabae2fbcbc4cfbd76ac89',
                    'name': 'T07-TLS-TPUT-EC-DSA521-A256-GCM-S3-16K_2lt',
                    'type': 'httpbandwidth',
                },
                'testId': 'aac3cde0ebaabae2fbcbc4cfbd76ac89',
                'updatedAt': '2020-04-17T23:05:17.722Z',
            },
            {
                'createdAt': '2020-04-20T16:00:55.609Z',
                'id': 'b5c5e700e4c0b47d75de2d1d9dccff4e',
                'runId': 'HTTP_Throughput_6c46547c_2020_4_20__9_0_57__28',
                'status': 'finished',
                'test': {
                    'id': '48d312e08baaeff65bca367217df0c86',
                    'name': 'HTTP Throughput_6c46547c',
                    'type': 'httpbandwidth',
                },
                'testId': '48d312e08baaeff65bca367217df0c86',
                'updatedAt': '2020-04-20T16:07:01.849Z',
            },
        ],
        'updatedAt': '2020-04-20T16:07:02.189Z',
    }

    config = {
        'author': 'test@spirent.com',
        'completed': False,
        'config': {
            'criteria': {
                'enabled': False,
                'failureConnectionsPerSecond': 1,
                'failureTransactions': 3,
            },
            'debug': {
                'client': {'enabled': False, 'packetTrace': 5000000},
                'enabled': True,
                'logLevel': 3,
                'server': {'enabled': False, 'packetTrace': 5000000},
            },
            'interfaces': {
                'client': [
                    {
                        'portSystemId': '10.71.90.241/1/5',
                        'subnetIds': ['f9e7b273a5c7dcb5abc10b2fca645936'],
                    },
                ],
                'server': [
                    {
                        'portSystemId': '10.71.90.241/1/6',
                        'subnetIds': ['c826c064a61b2e5a3ebd98e494367bfc'],
                    },
                ],
            },
            'loadSpecification': {
                'connectionsPerSecond': 21,
                'constraints': {'enabled': False},
                'duration': 1800,
                'rampdown': 10,
                'rampup': 10,
                'shutdown': 10,
                'startup': 5,
                'type': 'SimUsers',
            },
            'networks': {
                'client': {
                    'closeWithFin': True,
                    'congestionControl': True,
                    'delayedAcks': {
                        'bytes': 2920,
                        'enabled': True,
                        'timeout': 200,
                    },
                    'description': '',
                    'fragmentReassemblyTimer': 30000,
                    'gratuitousArp': True,
                    'inactivityTimer': 0,
                    'initialCongestionWindow': 10,
                    'ipV4SegmentSize': 1460,
                    'ipV6SegmentSize': 1440,
                    'name': 'Client Network',
                    'portRandomization': False,
                    'portRangeLowerBound': 1024,
                    'portRangeUpperBound': 65535,
                    'receiveWindow': 65538,
                    'retries': 3,
                    'sackOption': False,
                    'tcpVegas': False,
                },
                'server': {
                    'congestionControl': True,
                    'delayedAcks': {
                        'bytes': 2920,
                        'enabled': True,
                        'timeout': 200,
                    },
                    'description': '',
                    'gratuitousArp': True,
                    'inactivityTimer': 0,
                    'initialCongestionWindow': 10,
                    'ipV4SegmentSize': 1460,
                    'ipV6SegmentSize': 1440,
                    'name': 'Server Network',
                    'receiveWindow': 65538,
                    'retries': 3,
                    'sackOption': False,
                    'tcpVegas': False,
                },
            },
            'protocol': {
                'clientDestPort': 80,
                'clientDestPortEnabled': False,
                'connection': {'type': 'separateConnections'},
                'connectionTermination': 'FIN',
                'connectionTimeout': 30000,
                'connections': 999,
                'followRedirects': False,
                'keepAlive': {'enabled': False},
                'method': 'GET',
                'port': 80,
                'responseBodyType': {
                    'config': {
                        'bytes': 1000,
                        'length': 1000,
                        'pseudoRandom': True,
                        'type': 'random',
                    },
                    'type': 'fixed',
                },
                'separateConnections': {
                    'delayTime': 0,
                    'delayTimeUnit': 'sec',
                    'delayType': 'perUser',
                    'enabled': True,
                },
                'serverType': 'Microsoft-IIS/8.5',
                'supplemental': {
                    'authentication': {'enabled': False},
                    'proxy': {'enabled': False},
                    'sslTls': {
                        'bytes': 16383,
                        'certificate': 'server_2048',
                        'ciphers': ['AES128-GCM-SHA256'],
                        'enabled': False,
                        'payloadEncryptionOffload': False,
                        'resumeSession': {'enabled': False},
                        'signatureHashAlgorithmsList': [],
                        'sslv20': False,
                        'sslv30': False,
                        'supportedGroups': {
                            'X448': False,
                            'brainpool512r1': False,
                            'brainpoolP256r1': False,
                            'brainpoolP384r1': False,
                            'secp160k1': False,
                            'secp160r1': False,
                            'secp160r2': False,
                            'secp192k1': False,
                            'secp192r1': False,
                            'secp224k1': False,
                            'secp256k1': False,
                            'secp256r1': False,
                            'secp384r1': False,
                            'secp521r1': False,
                            'sect163k1': False,
                            'sect163r1': False,
                            'sect163r2': False,
                            'sect193r1': False,
                            'sect193r2': False,
                            'sect233k1': False,
                            'sect233r1': False,
                            'sect239k1': False,
                            'sect283k1': False,
                            'sect283r1': False,
                            'sect409k1': False,
                            'sect409r1': False,
                            'sect571k1': False,
                            'sect571r1': False,
                            'x25519': True,
                        },
                        'tlsv10': False,
                        'tlsv12': True,
                        'tlsv13': False,
                    },
                },
                'typeOfService': '00',
                'useCookies': False,
                'userAgent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'version': '1.1',
            },
            'queue': {'id': '8 x 10G Aonic', 'name': '8 x 10G Aonic'},
            'runtimeOptions': {
                'contentFiles': [],
                'jumboFrames': False,
                'statisticsLevel': 'Full',
                'statisticsSamplingInterval': '4',
                'useRealMac': False,
            },
            'subnets': {
                'client': [
                    {
                        'addressing': {
                            'address': '10.1.0.2',
                            'count': 253,
                            'forceIpAllocation': False,
                            'netmask': 24,
                            'type': 'custom',
                        },
                        'defaultGateway': {'enabled': False},
                        'description': '',
                        'id': 'f9e7b273a5c7dcb5abc10b2fca645936',
                        'mac': {'enabled': False},
                        'name': '10.1.0.2',
                        'randomize': False,
                        'routing': [],
                        'type': 'ipv4',
                        'vlans': [],
                    },
                ],
                'server': [
                    {
                        'addressing': {
                            'address': '10.3.0.2',
                            'count': 253,
                            'forceIpAllocation': False,
                            'netmask': 24,
                            'type': 'custom',
                        },
                        'defaultGateway': {'enabled': False},
                        'description': '',
                        'id': 'c826c064a61b2e5a3ebd98e494367bfc',
                        'mac': {'enabled': False},
                        'name': '10.3.0.2',
                        'randomize': False,
                        'routing': [],
                        'type': 'ipv4',
                        'vlans': [],
                    },
                ],
            },
            'testType': 'clientServer',
            'trafficPattern': 'Pair',
            'virtualRouters': {},
        },
        'createdAt': '2020-04-20T16:30:38.063Z',
        'description': 'Test created for Layer4-7 HTTP Connections Per Second Test Template',
        'id': '41f3e448af41647e0abfd9806b28e947',
        'lastRunBy': {'email': 'N/A', 'firstName': 'N/A', 'lastName': 'N/A'},
        'name': 'T02-HTTP-CPS-1K_uuu',
        'projectId': '48d312e08baaeff65bca367217df12e5',
        'updatedAt': '2020-04-20T16:30:59.871Z',
        'updatedBy': 'test@spirent.com',
    }

    started = {
        'createdAt': '2020-04-20T16:31:01.096Z',
        'id': '41f3e448af41647e0abfd9806b48df53',
        'queueId': '8 x 10G Aonic',
        'status': 'waiting',
        'test': {
            'id': '41f3e448af41647e0abfd9806b28e947',
            'name': 'T02-HTTP-CPS-1K_uuu',
            'type': 'httpcps',
        },
        'testId': '41f3e448af41647e0abfd9806b28e947',
        'updatedAt': '2020-04-20T16:31:01.096Z',
    }
    return run_info, queue_info, config, started

@pytest.fixture()
def test_set_b():
    run_info = {
        'name': 'T02-TTP-CPS-1K_pam',
        'id': '8d9abcb037f1109a24e85d4ac05926fc', 
        'type': 'http_connections_per_second', 
        'run': 'Y', 
        'run_order': '1', 
        'goal_seek': 'Y',
        'ramp_seek': 'N', 
        'ramp_kpi': 'cps', 
        'ramp_value': '1000', 
        'ramp_step': '5', 
        'duration': '1800', 
        'startup': '5',
        'rampup': '10',
        'rampdown': '10', 
        'shutdown': '10',
        'sustain_period': '30',
        'kpi_1': 'tps', 
        'kpi_2': 'cps',
        'kpi_and_or': 'OR',
        'load_type': 'simusers',
        'start_load': '7',
        'incr_low': '7',
        'incr_med': '5',
        'incr_high': '3',
        'low_threshold': '20',
        'med_threshold': '5',
        'high_threshold': '1',
        'variance_sample_size': '3',
        'max_variance': '0.3',
        'capacity_adj': '1',
        'ramp_low': '40',
        'ramp_med': '30',
        'ramp_high': '20',
        'living_simusers_max': 'none'
    }
    
    queue_info = {
        'author': 'test@spirent.com',
        'capacity': 40,
        'color': 'color0',
        'computeGroupCount': 0,
        'computeGroups': [],
        'createdAt': '2020-06-12T00:22:59.414Z',
        'devices': [
            {
                'author': 'test@spirent.com',
                'description': 'SPT-CF20',
                'deviceLocation': {
                    'building': None,
                    'city': None,
                    'country': None,
                    'id': 'ffc51d75630f4d1df8c562b4425b8a07',
                    'name': None,
                    'state': None,
                },
                'deviceLocationId': 'ffc51d75630f4d1df8c562b4425b8a07',
                'firmware': {'latest': True, 'version': '5.09.0638'},
                'id': '169.254.0.1',
                'ip': '169.254.0.1',
                'online': True,
                'portReservable': None,
                'rackLocation': None,
                'serialNumber': '7-1A5C2B73',
                'slots': [
                    {
                        'author': 'test@spirent.com',
                        'computeGroups': [
                            {
                                'available': False,
                                'capacity': 160,
                                'cores': 16,
                                'groupId': 1,
                                'id': '51be88da8531b8380edf34b8dada220d',
                                'memory': 115177000000,
                                'ports': [
                                    {
                                        'autoNegotiation': True,
                                        'available': False,
                                        'capacity': 20,
                                        'cores': 2,
                                        'displayName': 'Eth0',
                                        'duplex': 'Full Duplex',
                                        'enabled': True,
                                        'id': '51be88da8531b8380edf34b8dada60a8',
                                        'interfaces': [
                                            {
                                                'address': '101.0.0.1',
                                                'count': 1000,
                                                'netmask': 16,
                                                'protocol': 'ipv4',
                                            },
                                        ],
                                        'link': 'NONE',
                                        'mac': '',
                                        'media': 'Fiber',
                                        'number': 1,
                                        'portId': 1,
                                        'reservedBy': 'CyberFlood-169.254.0.100',
                                        'slotId': '1/1',
                                        'speed': 10000,
                                        'systemId': '169.254.0.1/1/1',
                                        'testRunning': False,
                                    },
                                    {
                                        'autoNegotiation': True,
                                        'available': True,
                                        'capacity': 20,
                                        'cores': 2,
                                        'displayName': 'Eth1',
                                        'duplex': 'Full Duplex',
                                        'enabled': True,
                                        'id': '51be88da8531b8380edf34b8dada594b',
                                        'interfaces': [
                                            {
                                                'address': '102.0.0.1',
                                                'count': 1000,
                                                'netmask': 16,
                                                'protocol': 'ipv4',
                                            },
                                        ],
                                        'link': 'NONE',
                                        'mac': '',
                                        'media': 'Fiber',
                                        'number': 2,
                                        'portId': 2,
                                        'slotId': '1/2',
                                        'speed': 10000,
                                        'systemId': '169.254.0.1/1/2',
                                        'testRunning': False,
                                    },
                                    {
                                        'autoNegotiation': True,
                                        'available': True,
                                        'capacity': 20,
                                        'cores': 2,
                                        'displayName': 'Eth2',
                                        'duplex': 'Full Duplex',
                                        'enabled': True,
                                        'id': '51be88da8531b8380edf34b8dada4f76',
                                        'interfaces': [
                                            {
                                                'address': '103.0.0.1',
                                                'count': 1000,
                                                'netmask': 16,
                                                'protocol': 'ipv4',
                                            },
                                        ],
                                        'link': 'NONE',
                                        'mac': '',
                                        'media': 'Fiber',
                                        'number': 3,
                                        'portId': 3,
                                        'slotId': '1/3',
                                        'speed': 10000,
                                        'systemId': '169.254.0.1/1/3',
                                        'testRunning': False,
                                    },
                                    {
                                        'autoNegotiation': True,
                                        'available': True,
                                        'capacity': 20,
                                        'cores': 2,
                                        'displayName': 'Eth3',
                                        'duplex': 'Full Duplex',
                                        'enabled': True,
                                        'id': '51be88da8531b8380edf34b8dada4ea8',
                                        'interfaces': [
                                            {
                                                'address': '104.0.0.1',
                                                'count': 1000,
                                                'netmask': 16,
                                                'protocol': 'ipv4',
                                            },
                                        ],
                                        'link': 'NONE',
                                        'mac': '',
                                        'media': 'Fiber',
                                        'number': 4,
                                        'portId': 4,
                                        'slotId': '1/4',
                                        'speed': 10000,
                                        'systemId': '169.254.0.1/1/4',
                                        'testRunning': False,
                                    },
                                    {
                                        'autoNegotiation': True,
                                        'available': False,
                                        'capacity': 20,
                                        'cores': 2,
                                        'displayName': 'Eth4',
                                        'duplex': 'Full Duplex',
                                        'enabled': True,
                                        'id': '51be88da8531b8380edf34b8dada42da',
                                        'interfaces': [
                                            {
                                                'address': '105.0.0.1',
                                                'count': 1000,
                                                'netmask': 16,
                                                'protocol': 'ipv4',
                                            },
                                        ],
                                        'link': 'NONE',
                                        'mac': '',
                                        'media': 'Fiber',
                                        'number': 5,
                                        'portId': 5,
                                        'reservedBy': 'CyberFlood-169.254.0.100',
                                        'slotId': '1/5',
                                        'speed': 10000,
                                        'systemId': '169.254.0.1/1/5',
                                        'testRunning': False,
                                    },
                                    {
                                        'autoNegotiation': True,
                                        'available': True,
                                        'capacity': 20,
                                        'cores': 2,
                                        'displayName': 'Eth5',
                                        'duplex': 'Full Duplex',
                                        'enabled': True,
                                        'id': '51be88da8531b8380edf34b8dada3c3c',
                                        'interfaces': [
                                            {
                                                'address': '106.0.0.1',
                                                'count': 1000,
                                                'netmask': 16,
                                                'protocol': 'ipv4',
                                            },
                                        ],
                                        'link': 'NONE',
                                        'mac': '',
                                        'media': 'Fiber',
                                        'number': 6,
                                        'portId': 6,
                                        'slotId': '1/6',
                                        'speed': 10000,
                                        'systemId': '169.254.0.1/1/6',
                                        'testRunning': False,
                                    },
                                    {
                                        'autoNegotiation': True,
                                        'available': True,
                                        'capacity': 20,
                                        'cores': 2,
                                        'displayName': 'Eth6',
                                        'duplex': 'Full Duplex',
                                        'enabled': True,
                                        'id': '51be88da8531b8380edf34b8dada3585',
                                        'interfaces': [
                                            {
                                                'address': '107.0.0.1',
                                                'count': 1000,
                                                'netmask': 16,
                                                'protocol': 'ipv4',
                                            },
                                        ],
                                        'link': 'NONE',
                                        'mac': '',
                                        'media': 'Fiber',
                                        'number': 7,
                                        'portId': 7,
                                        'slotId': '1/7',
                                        'speed': 10000,
                                        'systemId': '169.254.0.1/1/7',
                                        'testRunning': False,
                                    },
                                    {
                                        'autoNegotiation': True,
                                        'available': True,
                                        'capacity': 20,
                                        'cores': 2,
                                        'displayName': 'Eth7',
                                        'duplex': 'Full Duplex',
                                        'enabled': True,
                                        'id': '51be88da8531b8380edf34b8dada2c07',
                                        'interfaces': [
                                            {
                                                'address': '108.0.0.1',
                                                'count': 1000,
                                                'netmask': 16,
                                                'protocol': 'ipv4',
                                            },
                                        ],
                                        'link': 'NONE',
                                        'mac': '',
                                        'media': 'Fiber',
                                        'number': 8,
                                        'portId': 8,
                                        'slotId': '1/8',
                                        'speed': 10000,
                                        'systemId': '169.254.0.1/1/8',
                                        'testRunning': False,
                                    },
                                ],
                                'rebootable': True,
                                'reservedBy': 'Reserved',
                                'selectable': False,
                                'software': 'l4l7lxc5.09.0638',
                                'status': 'active',
                            },
                        ],
                        'cpu': 0,
                        'description': 'SPT-CF20-01',
                        'id': '51be88da8531b8380edf34b8dada12e6',
                        'mode': 'NA',
                        'model': 'SPT-CF20-01',
                        'orientation': 'horizontal',
                        'portGroups': [[1, 2]],
                        'profile': 'L4L7-Functional-8x10G',
                        'profiles': [
                            {
                                'activePortGroups': [1],
                                'description': 'L4L7-Functional-8x10G',
                                'name': 'L4L7-Functional-8x10G',
                                'type': 'L4L7-ADVFUZZ',
                            },
                            {
                                'activePortGroups': [1],
                                'description': 'L4L7-Performance-4x10G',
                                'name': 'L4L7-Performance-4x10G',
                                'type': 'L4L7-ADVFUZZ',
                            },
                            {
                                'activePortGroups': [1],
                                'description': 'L4L7-Maximum-2x10G',
                                'name': 'L4L7-Maximum-2x10G',
                                'type': 'L4L7-ADVFUZZ',
                            },
                            {
                                'activePortGroups': [1],
                                'description': 'L4L7-Performance-2x25G',
                                'name': 'L4L7-Performance-2x25G',
                                'type': 'L4L7-ADVFUZZ',
                            },
                            {
                                'activePortGroups': [1],
                                'description': 'L4L7-Functional-2x50G',
                                'name': 'L4L7-Functional-2x50G',
                                'type': 'L4L7-ADVFUZZ',
                            },
                            {
                                'activePortGroups': [1],
                                'description': 'L4L7-Functional-2x40G',
                                'name': 'L4L7-Functional-2x40G',
                                'type': 'L4L7-ADVFUZZ',
                            },
                            {
                                'activePortGroups': [1],
                                'description': 'L4L7-Functional-2x100G',
                                'name': 'L4L7-Functional-2x100G',
                                'type': 'L4L7-ADVFUZZ',
                            },
                        ],
                        'selectable': False,
                        'serialNumber': '7-1A5C2B73',
                        'slotId': 1,
                        'software': '5.09.0638',
                    },
                ],
                'status': 'active',
                'totalCapacity': 160,
                'totalPorts': 8,
                'totalSlots': 1,
            },
        ],
        'enqueuedTestCount': 0,
        'id': 'Zulu',
        'name': 'Zulu',
        'portCount': 2,
        'ports': [
            {
                'autoNegotiation': True,
                'available': False,
                'capacity': 20,
                'cores': 2,
                'displayName': 'Eth0',
                'duplex': 'Full Duplex',
                'enabled': True,
                'id': '51be88da8531b8380edf34b8dada60a8',
                'interfaces': [
                    {
                        'address': '101.0.0.1',
                        'count': 1000,
                        'netmask': 16,
                        'protocol': 'ipv4',
                    },
                ],
                'link': 'NONE',
                'mac': '',
                'media': 'Fiber',
                'number': 1,
                'portId': 1,
                'reservedBy': 'CyberFlood-169.254.0.100',
                'slotId': '1/1',
                'speed': 10000,
                'systemId': '169.254.0.1/1/1',
                'testRunning': False,
            },
            {
                'autoNegotiation': True,
                'available': False,
                'capacity': 20,
                'cores': 2,
                'displayName': 'Eth4',
                'duplex': 'Full Duplex',
                'enabled': True,
                'id': '51be88da8531b8380edf34b8dada42da',
                'interfaces': [
                    {
                        'address': '105.0.0.1',
                        'count': 1000,
                        'netmask': 16,
                        'protocol': 'ipv4',
                    },
                ],
                'link': 'NONE',
                'mac': '',
                'media': 'Fiber',
                'number': 5,
                'portId': 5,
                'reservedBy': 'CyberFlood-169.254.0.100',
                'slotId': '1/5',
                'speed': 10000,
                'systemId': '169.254.0.1/1/5',
                'testRunning': False,
            },
        ],
        'testRuns': [
            {
                'createdAt': '2020-06-12T00:23:50.094Z',
                'id': '51be88da8531b8380edf34b8dafa0b33',
                'runId': 'HTTP_Throughput_3ada7ecc_2020_6_11__17_23_51__2',
                'status': 'finished',
                'test': {
                    'id': '51be88da8531b8380edf34b8da5d278a',
                    'name': 'HTTP Throughput_3ada7ecc',
                    'type': 'httpbandwidth',
                },
                'testId': '51be88da8531b8380edf34b8da5d278a',
                'updatedAt': '2020-06-12T00:34:40.594Z',
            },
        ],
        'updatedAt': '2020-06-12T00:34:40.893Z',
    }

    config = {
        'author': 'test@spirent.com',
        'completed': False,
        'config': {
            'criteria': {
                'enabled': False,
                'failureConnectionsPerSecond': 1,
                'failureTransactions': 3,
            },
            'debug': {
                'client': {'enabled': False, 'packetTrace': 5000000},
                'enabled': True,
                'logLevel': 3,
                'server': {'enabled': False, 'packetTrace': 5000000},
            },
            'interfaces': {
                'client': [
                    {
                        'portSystemId': '169.254.0.1/1/1',
                        'subnetIds': ['51be88da8531b8380edf34b8da7d2974'],
                    },
                ],
                'server': [
                    {
                        'portSystemId': '169.254.0.1/1/5',
                        'subnetIds': ['51be88da8531b8380edf34b8da7d24f6'],
                    },
                ],
            },
            'loadSpecification': {
                'connectionsPerSecond': 7,
                'constraints': {'enabled': False},
                'duration': 1800,
                'rampdown': 10,
                'rampup': 10,
                'shutdown': 10,
                'startup': 5,
                'type': 'SimUsers',
            },
            'networks': {
                'client': {
                    'closeWithFin': True,
                    'congestionControl': True,
                    'delayedAcks': {
                        'bytes': 2920,
                        'enabled': True,
                        'timeout': 200,
                    },
                    'description': '',
                    'fragmentReassemblyTimer': 30000,
                    'gratuitousArp': True,
                    'inactivityTimer': 0,
                    'initialCongestionWindow': 10,
                    'ipV4SegmentSize': 1460,
                    'ipV6SegmentSize': 1440,
                    'name': 'Client Network',
                    'portRandomization': False,
                    'portRangeLowerBound': 1024,
                    'portRangeUpperBound': 65535,
                    'receiveWindow': 65538,
                    'retries': 3,
                    'sackOption': False,
                    'tcpVegas': False,
                },
                'server': {
                    'congestionControl': True,
                    'delayedAcks': {
                        'bytes': 2920,
                        'enabled': True,
                        'timeout': 200,
                    },
                    'description': '',
                    'gratuitousArp': True,
                    'inactivityTimer': 0,
                    'initialCongestionWindow': 10,
                    'ipV4SegmentSize': 1460,
                    'ipV6SegmentSize': 1440,
                    'name': 'Server Network',
                    'receiveWindow': 65538,
                    'retries': 3,
                    'sackOption': False,
                    'tcpVegas': False,
                },
            },
            'protocol': {
                'clientDestPort': 80,
                'clientDestPortEnabled': False,
                'connection': {'type': 'separateConnections'},
                'connectionTermination': 'FIN',
                'connectionTimeout': 30000,
                'connections': 999,
                'followRedirects': False,
                'keepAlive': {'enabled': False},
                'method': 'GET',
                'port': 80,
                'responseBodyType': {
                    'config': {
                        'bytes': 1000,
                        'length': 1000,
                        'pseudoRandom': True,
                        'type': 'random',
                    },
                    'type': 'fixed',
                },
                'separateConnections': {
                    'delayTime': 0,
                    'delayTimeUnit': 'sec',
                    'delayType': 'perUser',
                    'enabled': True,
                },
                'serverType': 'Microsoft-IIS/8.5',
                'supplemental': {
                    'authentication': {'enabled': False},
                    'proxy': {'enabled': False},
                    'sslTls': {
                        'bytes': 16383,
                        'certificate': 'server_2048',
                        'ciphers': ['AES128-GCM-SHA256'],
                        'enabled': False,
                        'payloadEncryptionOffload': False,
                        'resumeSession': {'enabled': False},
                        'signatureHashAlgorithmsList': [],
                        'sslv20': False,
                        'sslv30': False,
                        'supportedGroups': {
                            'X448': False,
                            'brainpool512r1': False,
                            'brainpoolP256r1': False,
                            'brainpoolP384r1': False,
                            'secp160k1': False,
                            'secp160r1': False,
                            'secp160r2': False,
                            'secp192k1': False,
                            'secp192r1': False,
                            'secp224k1': False,
                            'secp256k1': False,
                            'secp256r1': False,
                            'secp384r1': False,
                            'secp521r1': False,
                            'sect163k1': False,
                            'sect163r1': False,
                            'sect163r2': False,
                            'sect193r1': False,
                            'sect193r2': False,
                            'sect233k1': False,
                            'sect233r1': False,
                            'sect239k1': False,
                            'sect283k1': False,
                            'sect283r1': False,
                            'sect409k1': False,
                            'sect409r1': False,
                            'sect571k1': False,
                            'sect571r1': False,
                            'x25519': True,
                        },
                        'tlsv10': False,
                        'tlsv12': True,
                        'tlsv13': False,
                    },
                },
                'typeOfService': '00',
                'useCookies': False,
                'userAgent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'version': '1.1',
            },
            'queue': {'id': 'Zulu', 'name': 'Zulu'},
            'runtimeOptions': {
                'contentFiles': [],
                'customSamplingInterval': 4,
                'jumboFrames': False,
                'statisticsLevel': 'Full',
                'statisticsSamplingInterval': False,
                'useRealMac': True,
            },
            'subnets': {
                'client': [
                    {
                        'addressing': {
                            'address': '10.1.0.2',
                            'count': 253,
                            'forceIpAllocation': False,
                            'netmask': 24,
                            'type': 'custom',
                        },
                        'defaultGateway': {'enabled': False},
                        'description': '',
                        'id': '51be88da8531b8380edf34b8da7d2974',
                        'mac': {'enabled': False},
                        'name': 'IPv4 /24 Clients',
                        'randomize': False,
                        'routing': [],
                        'type': 'ipv4',
                        'vlans': [],
                    },
                ],
                'server': [
                    {
                        'addressing': {
                            'address': '10.2.0.2',
                            'count': 253,
                            'forceIpAllocation': False,
                            'netmask': 24,
                            'type': 'custom',
                        },
                        'defaultGateway': {'enabled': False},
                        'description': '',
                        'id': '51be88da8531b8380edf34b8da7d24f6',
                        'mac': {'enabled': False},
                        'name': 'IPv4 /24 Servers',
                        'randomize': False,
                        'routing': [],
                        'type': 'ipv4',
                        'vlans': [],
                    },
                ],
            },
            'testType': 'clientServer',
            'trafficPattern': 'Pair',
            'virtualRouters': {},
        },
        'createdAt': '2020-06-12T11:55:11.585Z',
        'description': 'Test created for Layer4-7 HTTP Connections Per Second Test Template',
        'id': '8d9abcb037f1109a24e85d4ac05926fc',
        'lastRunBy': {'email': 'N/A', 'firstName': 'N/A', 'lastName': 'N/A'},
        'name': 'T02-HTTP-CPS-1K_pam',
        'projectId': '51be88da8531b8380edf34b8da5d3179',
        'updatedAt': '2020-06-12T11:56:30.865Z',
        'updatedBy': 'test@spirent.com',
    }

    started = {
        'createdAt': '2020-06-12T11:56:32.493Z',
        'id': '8d9abcb037f1109a24e85d4ac0782fd1',
        'queueId': 'Zulu',
        'status': 'waiting',
        'test': {
            'id': '8d9abcb037f1109a24e85d4ac05926fc',
            'name': 'T02-HTTP-CPS-1K_pam',
            'type': 'httpcps',
        },
        'testId': '8d9abcb037f1109a24e85d4ac05926fc',
        'updatedAt': '2020-06-12T11:56:32.493Z',
    }

    return run_info, queue_info, config, started
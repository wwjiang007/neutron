#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import mock
from neutron_lib import constants

from neutron.agent.linux import l3_tc_lib as tc_lib
from neutron.common import exceptions
from neutron.tests import base

FLOATING_IP_DEVICE_NAME = "qg-device_rfp"
FLOATING_IP_ROUTER_NAMESPACE = "qrouter-namespace_snat-namespace"

FLOATING_IP_1 = "172.16.5.146"
FLOATING_IP_2 = "172.16.10.105"
FILETER_ID_1 = "800::800"
FILETER_ID_2 = "800::801"

TC_INGRESS_FILTERS = (
    'filter protocol ip u32 \n'
    'filter protocol ip u32 fh 800: ht divisor 1 \n'
    'filter protocol ip u32 fh %(filter_id1)s order 2048 key '
    'ht 800 bkt 0 '
    'flowid :1  (rule hit 0 success 0)\n'
    '  match IP dst %(fip1)s/32 (success 0 ) \n'
    ' police 0x3 rate 3000Kbit burst 3Mb mtu 64Kb action drop overhead 0b \n'
    'ref 1 bind 1\n'
    '\n'
    ' Sent 111 bytes 222 pkts (dropped 0, overlimits 0) \n'
    'filter protocol ip u32 fh %(filter_id2)s order 2049 key '
    'ht 800 bkt 0 '
    'flowid :1  (rule hit 0 success 0)\n'
    '  match IP dst %(fip2)s/32 (success 0 ) \n'
    ' police 0x1b rate 22000Kbit burst 22Mb mtu 64Kb action drop '
    'overhead 0b \n'
    'ref 1 bind 1\n'
    '\n'
    ' Sent 111 bytes 222 pkts (dropped 0, overlimits 0)\n') % {
        "filter_id1": FILETER_ID_1,
        "fip1": FLOATING_IP_1,
        "filter_id2": FILETER_ID_2,
        "fip2": FLOATING_IP_2}

TC_INGRESS_FILTERS_DUP = TC_INGRESS_FILTERS + (
    'filter protocol ip u32 fh %(filter_id2)s order 2049 key '
    'ht 800 bkt 0 '
    'flowid :1  (rule hit 0 success 0)\n'
    '  match IP dst %(fip2)s/32 (success 0 ) \n'
    ' police 0x1b rate 22000Kbit burst 22Mb mtu 64Kb action drop '
    'overhead 0b \n'
    'ref 1 bind 1\n'
    '\n'
    ' Sent 111 bytes 222 pkts (dropped 0, overlimits 0)\n') % {
        "filter_id2": FILETER_ID_2,
        "fip2": FLOATING_IP_2}

TC_EGRESS_FILTERS = (
    'filter protocol ip u32 \n'
    'filter protocol ip u32 fh 800: ht divisor 1 \n'
    'filter protocol ip u32 fh %(filter_id1)s order 2048 key '
    'ht 800 bkt 0 '
    'flowid :1  (rule hit 0 success 0)\n'
    '  match IP src %(fip1)s/32 (success 0 ) \n'
    ' police 0x4 rate 3000Kbit burst 3Mb mtu 64Kb action drop overhead 0b \n'
    'ref 1 bind 1\n'
    '\n'
    ' Sent 111 bytes 222 pkts (dropped 0, overlimits 0) \n'
    'filter protocol ip u32 fh %(filter_id2)s order 2049 key '
    'ht 800 bkt 0 '
    'flowid :1  (rule hit 0 success 0)\n'
    '  match IP src %(fip2)s/32 (success 0 ) \n'
    ' police 0x1c rate 22000Kbit burst 22Mb mtu 64Kb action drop '
    'overhead 0b \n'
    'ref 1 bind 1\n'
    '\n'
    ' Sent 111 bytes 222 pkts (dropped 0, overlimits 0)\n') % {
        "filter_id1": FILETER_ID_1,
        "fip1": FLOATING_IP_1,
        "filter_id2": FILETER_ID_2,
        "fip2": FLOATING_IP_2}
FILTERS_IDS = {constants.INGRESS_DIRECTION: TC_INGRESS_FILTERS,
               constants.EGRESS_DIRECTION: TC_EGRESS_FILTERS}

INGRESS_QSIC_ID = "ffff:"
EGRESS_QDISC_ID = "1:"
QDISC_IDS = {constants.INGRESS_DIRECTION: INGRESS_QSIC_ID,
             constants.EGRESS_DIRECTION: EGRESS_QDISC_ID}
TC_QDISCS = (
    'qdisc htb %(egress)s root refcnt 2 r2q 10 default 0 '
    'direct_packets_stat 6\n'
    'qdisc ingress %(ingress)s parent ffff:fff1 ----------------\n') % {
        "egress": EGRESS_QDISC_ID,
        "ingress": INGRESS_QSIC_ID}


class TestFloatingIPTcCommandBase(base.BaseTestCase):
    def setUp(self):
        super(TestFloatingIPTcCommandBase, self).setUp()
        self.tc = tc_lib.FloatingIPTcCommandBase(
            FLOATING_IP_DEVICE_NAME,
            namespace=FLOATING_IP_ROUTER_NAMESPACE)
        self.execute = mock.patch('neutron.agent.common.utils.execute').start()

    def test__get_qdiscs(self):
        self.tc._get_qdiscs()
        self.execute.assert_called_once_with(
            ['ip', 'netns', 'exec', FLOATING_IP_ROUTER_NAMESPACE,
             'tc', 'qdisc', 'show', 'dev', FLOATING_IP_DEVICE_NAME],
            run_as_root=True,
            check_exit_code=True,
            log_fail_as_error=True,
            extra_ok_codes=None
        )

    def test__get_qdisc_id_for_filter(self):
        with mock.patch.object(tc_lib.FloatingIPTcCommandBase,
                               '_get_qdiscs') as get_qdiscs:
            get_qdiscs.return_value = TC_QDISCS
            q1 = self.tc._get_qdisc_id_for_filter(constants.INGRESS_DIRECTION)
            self.assertEqual(INGRESS_QSIC_ID, q1)
            q2 = self.tc._get_qdisc_id_for_filter(constants.EGRESS_DIRECTION)
            self.assertEqual(EGRESS_QDISC_ID, q2)

    def test__add_qdisc(self):
        self.tc._add_qdisc(constants.INGRESS_DIRECTION)
        self.execute.assert_called_with(
            ['ip', 'netns', 'exec', FLOATING_IP_ROUTER_NAMESPACE,
             'tc', 'qdisc', 'add', 'dev', FLOATING_IP_DEVICE_NAME, 'ingress'],
            run_as_root=True,
            check_exit_code=True,
            log_fail_as_error=True,
            extra_ok_codes=None
        )
        self.tc._add_qdisc(constants.EGRESS_DIRECTION)
        self.execute.assert_called_with(
            ['ip', 'netns', 'exec', FLOATING_IP_ROUTER_NAMESPACE,
             'tc', 'qdisc', 'add', 'dev',
             FLOATING_IP_DEVICE_NAME] + ['root', 'handle', '1:', 'htb'],
            run_as_root=True,
            check_exit_code=True,
            log_fail_as_error=True,
            extra_ok_codes=None
        )

    def test__get_filters(self):
        self.tc._get_filters(INGRESS_QSIC_ID)
        self.execute.assert_called_with(
            ['ip', 'netns', 'exec', FLOATING_IP_ROUTER_NAMESPACE,
             'tc', '-p', '-s', '-d', 'filter', 'show', 'dev',
             FLOATING_IP_DEVICE_NAME,
             'parent', INGRESS_QSIC_ID, 'prio', 1],
            run_as_root=True,
            check_exit_code=True,
            log_fail_as_error=True,
            extra_ok_codes=None
        )

    def test__get_filterid_for_ip(self):
        with mock.patch.object(tc_lib.FloatingIPTcCommandBase,
                               '_get_filters') as get_filters:
            get_filters.return_value = TC_EGRESS_FILTERS
            f_id = self.tc._get_filterid_for_ip(INGRESS_QSIC_ID, FLOATING_IP_1)
            self.assertEqual(FILETER_ID_1, f_id)

    def test__get_filterid_for_ip_no_output(self):
        with mock.patch.object(tc_lib.FloatingIPTcCommandBase,
                               '_get_filters') as get_filters:
            get_filters.return_value = ""
            self.assertRaises(exceptions.FilterIDForIPNotFound,
                              self.tc._get_filterid_for_ip,
                              INGRESS_QSIC_ID, FLOATING_IP_1)

    def test__get_filterid_for_ip_duplicated(self):
        with mock.patch.object(tc_lib.FloatingIPTcCommandBase,
                               '_get_filters') as get_filters:
            get_filters.return_value = TC_INGRESS_FILTERS_DUP
            self.assertRaises(exceptions.MultipleFilterIDForIPFound,
                              self.tc._get_filterid_for_ip,
                              INGRESS_QSIC_ID, FLOATING_IP_2)

    def test__get_filterid_for_ip_not_found(self):
        with mock.patch.object(tc_lib.FloatingIPTcCommandBase,
                               '_get_filters') as get_filters:
            get_filters.return_value = TC_EGRESS_FILTERS
            self.assertRaises(exceptions.FilterIDForIPNotFound,
                              self.tc._get_filterid_for_ip,
                              INGRESS_QSIC_ID, "1.1.1.1")

    def test__del_filter_by_id(self):
        self.tc._del_filter_by_id(INGRESS_QSIC_ID, FLOATING_IP_1)
        self.execute.assert_called_once_with(
            ['ip', 'netns', 'exec', FLOATING_IP_ROUTER_NAMESPACE,
             'tc', 'filter', 'del', 'dev', FLOATING_IP_DEVICE_NAME,
             'parent', INGRESS_QSIC_ID,
             'prio', 1, 'handle', FLOATING_IP_1, 'u32'],
            run_as_root=True,
            check_exit_code=True,
            log_fail_as_error=True,
            extra_ok_codes=None
        )

    def test__get_qdisc_filters(self):
        with mock.patch.object(tc_lib.FloatingIPTcCommandBase,
                               '_get_filters') as get_filters:
            get_filters.return_value = TC_EGRESS_FILTERS
            f_ids = self.tc._get_qdisc_filters(INGRESS_QSIC_ID)
            self.assertEqual([FILETER_ID_1, FILETER_ID_2], f_ids)

    def test__get_qdisc_filters_no_output(self):
        with mock.patch.object(tc_lib.FloatingIPTcCommandBase,
                               '_get_filters') as get_filters:
            get_filters.return_value = ""
            f_ids = self.tc._get_qdisc_filters(INGRESS_QSIC_ID)
            self.assertEqual(0, len(f_ids))

    def test__add_filter(self):
        protocol = ['protocol', 'ip']
        prio = ['prio', 1]
        match = ['u32', 'match', 'ip', 'dst', FLOATING_IP_1]
        police = ['police', 'rate', '1kbit', 'burst', '1kbit',
                  'drop', 'flowid', ':1']
        args = protocol + prio + match + police
        cmd = ['tc', 'filter', 'add', 'dev', FLOATING_IP_DEVICE_NAME,
               'parent', INGRESS_QSIC_ID] + args

        self.tc._add_filter(INGRESS_QSIC_ID,
                            constants.INGRESS_DIRECTION,
                            FLOATING_IP_1, 1, 1)
        self.execute.assert_called_once_with(
            ['ip', 'netns', 'exec', FLOATING_IP_ROUTER_NAMESPACE] + cmd,
            run_as_root=True,
            check_exit_code=True,
            log_fail_as_error=True,
            extra_ok_codes=None
        )

    def test__get_or_create_qdisc(self):
        with mock.patch.object(tc_lib.FloatingIPTcCommandBase,
                               '_get_qdisc_id_for_filter') as get_disc1:
            get_disc1.return_value = None
            with mock.patch.object(tc_lib.FloatingIPTcCommandBase,
                                   '_add_qdisc'):
                with mock.patch.object(
                        tc_lib.FloatingIPTcCommandBase,
                        '_get_qdisc_id_for_filter') as get_disc2:
                    get_disc2.return_value = INGRESS_QSIC_ID
                    qdisc_id = self.tc._get_or_create_qdisc(
                        constants.INGRESS_DIRECTION)
                    self.assertEqual(INGRESS_QSIC_ID, qdisc_id)

    def test__get_or_create_qdisc_failed(self):
        with mock.patch.object(tc_lib.FloatingIPTcCommandBase,
                               '_get_qdisc_id_for_filter') as get_disc1:
            get_disc1.return_value = None
            with mock.patch.object(tc_lib.FloatingIPTcCommandBase,
                                   '_add_qdisc'):
                with mock.patch.object(
                        tc_lib.FloatingIPTcCommandBase,
                        '_get_qdisc_id_for_filter') as get_disc2:
                    get_disc2.return_value = None
                    self.assertRaises(exceptions.FailedToAddQdiscToDevice,
                                      self.tc._get_or_create_qdisc,
                                      constants.INGRESS_DIRECTION)


class TestFloatingIPTcCommand(base.BaseTestCase):
    def setUp(self):
        super(TestFloatingIPTcCommand, self).setUp()
        self.tc = tc_lib.FloatingIPTcCommand(
            FLOATING_IP_DEVICE_NAME,
            namespace=FLOATING_IP_ROUTER_NAMESPACE)
        self.execute = mock.patch('neutron.agent.common.utils.execute').start()

    def test_clear_all_filters(self):
        with mock.patch.object(tc_lib.FloatingIPTcCommandBase,
                               '_get_qdisc_id_for_filter') as get_disc:
            get_disc.return_value = EGRESS_QDISC_ID
            with mock.patch.object(tc_lib.FloatingIPTcCommandBase,
                                   '_get_filters') as get_filters:
                get_filters.return_value = TC_EGRESS_FILTERS
                self.tc.clear_all_filters(constants.EGRESS_DIRECTION)
                self.assertEqual(2, self.execute.call_count)

    def test_set_ip_rate_limit_filter_existed(self):
        with mock.patch.object(tc_lib.FloatingIPTcCommandBase,
                               '_get_qdisc_id_for_filter') as get_disc:
            get_disc.return_value = EGRESS_QDISC_ID
            with mock.patch.object(tc_lib.FloatingIPTcCommandBase,
                                   '_get_filterid_for_ip') as get_filter:
                get_filter.return_value = FILETER_ID_1
                with mock.patch.object(tc_lib.FloatingIPTcCommandBase,
                                       '_del_filter_by_id') as del_filter:
                    with mock.patch.object(tc_lib.FloatingIPTcCommandBase,
                                           '_add_filter') as add_filter:
                        ip = "111.111.111.111"
                        self.tc.set_ip_rate_limit(constants.EGRESS_DIRECTION,
                                                  ip, 1, 1)
                        del_filter.assert_called_once_with(
                            EGRESS_QDISC_ID, FILETER_ID_1)
                        add_filter.assert_called_once_with(
                            EGRESS_QDISC_ID, constants.EGRESS_DIRECTION,
                            ip, 1, 1)

    def test_set_ip_rate_limit_no_qdisc(self):
        with mock.patch.object(tc_lib.FloatingIPTcCommandBase,
                               '_get_qdisc_id_for_filter') as get_disc:
            get_disc.return_value = None
            with mock.patch.object(tc_lib.FloatingIPTcCommandBase,
                                   '_add_qdisc'):
                with mock.patch.object(tc_lib.FloatingIPTcCommandBase,
                                       '_get_filters') as get_filters:
                    get_filters.return_value = TC_INGRESS_FILTERS
                    get_disc.return_value = INGRESS_QSIC_ID
                    ip = "111.111.111.111"
                    self.tc.set_ip_rate_limit(constants.INGRESS_DIRECTION,
                                              ip, 1, 1)

                    protocol = ['protocol', 'ip']
                    prio = ['prio', 1]
                    _match = 'dst'
                    match = ['u32', 'match', 'ip', _match, ip]
                    police = ['police', 'rate', '1kbit', 'burst', '1kbit',
                              'drop', 'flowid', ':1']
                    args = protocol + prio + match + police

                    self.execute.assert_called_once_with(
                        ['ip', 'netns', 'exec', FLOATING_IP_ROUTER_NAMESPACE,
                         'tc', 'filter', 'add', 'dev', FLOATING_IP_DEVICE_NAME,
                         'parent', INGRESS_QSIC_ID] + args,
                        run_as_root=True,
                        check_exit_code=True,
                        log_fail_as_error=True,
                        extra_ok_codes=None
                    )

    def test_clear_ip_rate_limit(self):
        with mock.patch.object(tc_lib.FloatingIPTcCommandBase,
                               '_get_qdisc_id_for_filter') as get_disc:
            get_disc.return_value = EGRESS_QDISC_ID
            with mock.patch.object(tc_lib.FloatingIPTcCommandBase,
                                   '_get_filterid_for_ip') as get_filter_id:
                get_filter_id.return_value = FILETER_ID_1
                self.tc.clear_ip_rate_limit(constants.EGRESS_DIRECTION,
                                            FLOATING_IP_1)

                self.execute.assert_called_once_with(
                    ['ip', 'netns', 'exec', FLOATING_IP_ROUTER_NAMESPACE,
                     'tc', 'filter', 'del', 'dev', FLOATING_IP_DEVICE_NAME,
                     'parent', EGRESS_QDISC_ID,
                     'prio', 1, 'handle', FILETER_ID_1, 'u32'],
                    run_as_root=True,
                    check_exit_code=True,
                    log_fail_as_error=True,
                    extra_ok_codes=None
                )

    def test_get_filter_id_for_ip(self):
        with mock.patch.object(tc_lib.FloatingIPTcCommandBase,
                               '_get_qdisc_id_for_filter') as get_disc:
            get_disc.return_value = EGRESS_QDISC_ID
            with mock.patch.object(tc_lib.FloatingIPTcCommandBase,
                                   '_get_filterid_for_ip') as get_filter_id:
                self.tc.get_filter_id_for_ip(constants.EGRESS_DIRECTION,
                                             '8.8.8.8')
                get_filter_id.assert_called_once_with(EGRESS_QDISC_ID,
                                                      '8.8.8.8')

    def test_get_existing_filter_ids(self):
        with mock.patch.object(tc_lib.FloatingIPTcCommandBase,
                               '_get_qdisc_id_for_filter') as get_disc:
            get_disc.return_value = EGRESS_QDISC_ID
            with mock.patch.object(tc_lib.FloatingIPTcCommandBase,
                                   '_get_qdisc_filters') as get_filter_ids:
                self.tc.get_existing_filter_ids(constants.EGRESS_DIRECTION)
                get_filter_ids.assert_called_once_with(EGRESS_QDISC_ID)

    def test_delete_filter_ids(self):
        with mock.patch.object(tc_lib.FloatingIPTcCommandBase,
                               '_get_qdisc_id_for_filter') as get_disc:
            get_disc.return_value = EGRESS_QDISC_ID
            with mock.patch.object(tc_lib.FloatingIPTcCommandBase,
                                   '_del_filter_by_id') as del_filter_id:
                self.tc.delete_filter_ids(constants.EGRESS_DIRECTION,
                                          [FILETER_ID_1, FILETER_ID_2])
                del_filter_id.assert_has_calls(
                    [mock.call(EGRESS_QDISC_ID, FILETER_ID_1),
                     mock.call(EGRESS_QDISC_ID, FILETER_ID_2)])

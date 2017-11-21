# Copyright 2013 OpenStack Foundation
# All Rights Reserved.
#
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

from neutron_lib import constants
from neutron_lib.db import constants as db_const
from tempest.lib import decorators
from tempest.lib import exceptions as lib_exc

from neutron.tests.tempest.api import base_security_groups as base

LONG_NAME_NG = 'x' * (db_const.NAME_FIELD_SIZE + 1)


class NegativeSecGroupTest(base.BaseSecGroupTest):

    required_extensions = ['security-group']

    @classmethod
    def resource_setup(cls):
        super(NegativeSecGroupTest, cls).resource_setup()
        cls.network = cls.create_network()

    @decorators.attr(type='negative')
    @decorators.idempotent_id('594edfa8-9a5b-438e-9344-49aece337d49')
    def test_create_security_group_with_too_long_name(self):
        self.assertRaises(lib_exc.BadRequest,
                          self.client.create_security_group,
                          name=LONG_NAME_NG)

    @decorators.attr(type='negative')
    @decorators.idempotent_id('b6b79838-7430-4d3f-8e07-51dfb61802c2')
    def test_create_security_group_with_boolean_type_name(self):
        self.assertRaises(lib_exc.BadRequest,
                          self.client.create_security_group,
                          name=True)

    @decorators.attr(type='negative')
    @decorators.idempotent_id('55100aa8-b24f-333c-0bef-64eefd85f15c')
    def test_update_default_security_group_name(self):
        sg_list = self.client.list_security_groups(name='default')
        sg = sg_list['security_groups'][0]
        self.assertRaises(lib_exc.Conflict, self.client.update_security_group,
                          sg['id'], name='test')

    @decorators.attr(type='negative')
    @decorators.idempotent_id('c8510dd8-c3a8-4df9-ae44-24354db50960')
    def test_update_security_group_with_too_long_name(self):
        sg_list = self.client.list_security_groups(name='default')
        sg = sg_list['security_groups'][0]
        self.assertRaises(lib_exc.BadRequest,
                          self.client.update_security_group,
                          sg['id'], name=LONG_NAME_NG)

    @decorators.attr(type='negative')
    @decorators.idempotent_id('d9a14917-f66f-4eca-ab72-018563917f1b')
    def test_update_security_group_with_boolean_type_name(self):
        sg_list = self.client.list_security_groups(name='default')
        sg = sg_list['security_groups'][0]
        self.assertRaises(lib_exc.BadRequest,
                          self.client.update_security_group,
                          sg['id'], name=True)

    @decorators.attr(type='negative')
    @decorators.idempotent_id('3200b1a8-d73b-48e9-b03f-e891a4abe2d3')
    def test_delete_in_use_sec_group(self):
        sgroup = self.os_primary.network_client.create_security_group(
            name='sgroup')
        self.security_groups.append(sgroup['security_group'])
        port = self.client.create_port(
            network_id=self.network['id'],
            security_groups=[sgroup['security_group']['id']])
        self.ports.append(port['port'])
        self.assertRaises(lib_exc.Conflict,
                          self.os_primary.network_client.delete_security_group,
                          security_group_id=sgroup['security_group']['id'])


class NegativeSecGroupIPv6Test(NegativeSecGroupTest):
    _ip_version = constants.IP_VERSION_6


class NegativeSecGroupProtocolTest(base.BaseSecGroupTest):

    def _test_create_security_group_rule_with_bad_protocols(self, protocols):
        group_create_body, _ = self._create_security_group()

        # bad protocols can include v6 protocols because self.ethertype is v4
        for protocol in protocols:
            self.assertRaises(
                lib_exc.BadRequest,
                self.client.create_security_group_rule,
                security_group_id=group_create_body['security_group']['id'],
                protocol=protocol, direction=constants.INGRESS_DIRECTION,
                ethertype=self.ethertype)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('cccbb0f3-c273-43ed-b3fc-1efc48833810')
    def test_create_security_group_rule_with_ipv6_protocol_names(self):
        self._test_create_security_group_rule_with_bad_protocols(
            base.V6_PROTOCOL_NAMES)

    @decorators.attr(type=['negative'])
    @decorators.idempotent_id('8aa636bd-7060-4fdf-b722-cdae28e2f1ef')
    def test_create_security_group_rule_with_ipv6_protocol_integers(self):
        self._test_create_security_group_rule_with_bad_protocols(
            base.V6_PROTOCOL_INTS)

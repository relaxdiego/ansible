# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

# Make coding more python3-ish
from __future__ import (absolute_import, division)
__metaclass__ = type

import uuid

from ansible.compat.tests import unittest
from ansible.compat.tests.mock import call, create_autospec, MagicMock, patch

from ansible.module_utils.basic import AnsibleModule
from ansible.modules.extras.cloud.dimensiondata import \
    dimensiondata_load_balancer

from libcloud.common.dimensiondata import DimensionDataAPIException


class TestDimensionDataLoadBalancer(unittest.TestCase):

    # ==============
    # SETUP/TEARDOWN
    # ==============

    def setUp(self):
        self.subject = dimensiondata_load_balancer

        self.E = self.subject.E
        self.S = self.subject.S

    # =====
    # TESTS
    # =====

    def test__create_lb__happy_path(self):
        # Mock objects
        mod_cls = create_autospec(AnsibleModule)
        mod = mod_cls.return_value
        mod.params = dict(listener_ip_address='10.21.111.111',
                          members=[],
                          name='somebalancer',
                          port='1234',
                          protocol='http',
                          algorithm='ROUND_ROBIN')
        lb_con = MagicMock()
        dargs = dict(compute_con=MagicMock(),
                     lb_con=lb_con,
                     net_domain=MagicMock())

        # Exercise
        result = self.subject.create_lb(mod, dargs)

        # Assert
        self.assertIsNone(result)

        self.assertEqual(1, lb_con.create_balancer.call_count)

        self.assertEqual(1, mod.exit_json.call_count)

    def test__delete_lb__happy_path(self):
        # Mock objects
        mod_cls = create_autospec(AnsibleModule)
        mod = mod_cls.return_value
        mod.params = dict()
        balancer = MagicMock()
        lb_con = MagicMock()
        dargs = dict(lb=balancer, lb_con=lb_con)

        # Exercise
        result = self.subject.delete_lb(mod, dargs)

        # Assert
        self.assertIsNone(result)

        self.assertEqual(1, lb_con.destroy_balancer.call_count)

        expected_call = call(balancer)
        self.assertEqual(expected_call, lb_con.destroy_balancer.call_args)

        pool_id = balancer.extra.get.return_value
        expected_call = call(pool_id)
        self.assertEqual(expected_call, lb_con.ex_get_pool_members.call_args)

        pool = lb_con.ex_get_pool.return_value
        expected_call = call(pool)
        self.assertEqual(expected_call, lb_con.ex_destroy_pool.call_args)

        self.assertEqual(1, mod.exit_json.call_count)

    def test__dispatch__must_create(self):
        # Mock objects
        mod_cls = create_autospec(AnsibleModule)
        mod = mod_cls.return_value
        mod.params = dict(ensure='present')
        dargs = dict(lb=None)

        # Exercise
        event, new_dargs = self.subject.dispatch(mod, dargs)

        # Assert
        self.assertEqual(self.subject.E.must_create, event)

        self.assertEqual(dargs, new_dargs)

    def test__dispatch__must_delete(self):
        # Mock objects
        mod_cls = create_autospec(AnsibleModule)
        mod = mod_cls.return_value
        mod.params = dict(ensure='absent')
        dargs = dict(lb=MagicMock())

        # Exercise
        event, new_dargs = self.subject.dispatch(mod, dargs)

        # Assert
        self.assertEqual(self.subject.E.must_delete, event)

        self.assertEqual(dargs, new_dargs)

    def test__dispatch__must_do_nothing_if_absent(self):
        # Mock objects
        mod_cls = create_autospec(AnsibleModule)
        mod = mod_cls.return_value
        mod.params = dict(ensure='absent')
        dargs = dict(lb=None)

        # Exercise
        event, new_dargs = self.subject.dispatch(mod, dargs)

        # Assert
        self.assertEqual(self.subject.E.must_do_nothing, event)

        self.assertEqual(dargs, new_dargs)

    def test__dispatch__must_do_nothing_if_present(self):
        # Mock objects
        mod_cls = create_autospec(AnsibleModule)
        mod = mod_cls.return_value
        mod.params = dict(ensure='present')
        dargs = dict(lb=MagicMock())

        # Exercise
        event, new_dargs = self.subject.dispatch(mod, dargs)

        # Assert
        self.assertEqual(self.subject.E.must_do_nothing, event)

        self.assertEqual(dargs, new_dargs)

    def test__do_nothing__lb_already_absent(self):
        # Mock
        mod_cls = create_autospec(AnsibleModule)
        mod = mod_cls.return_value
        mod.params = dict(ensure='absent')
        dargs = dict()

        # Exercise
        result = self.subject.do_nothing(mod, dargs)

        # Assert
        self.assertIsNone(result)

        self.assertEqual(1, mod.exit_json.call_count)

        expected_call = call(changed=False, msg="Load balancer does not exist")
        self.assertEqual(expected_call, mod.exit_json.call_args)

    def test__do_nothing__lb_already_exists(self):
        # Mock
        mod_cls = create_autospec(AnsibleModule)
        mod = mod_cls.return_value
        mod.params = dict(ensure='present')
        dargs = dict(lb=MagicMock())

        # Exercise
        result = self.subject.do_nothing(mod, dargs)

        # Assert
        self.assertIsNone(result)

        self.assertEqual(1, mod.exit_json.call_count)

        expected_call = call(changed=False, msg="Load balancer already exists")
        self.assertEqual(expected_call, mod.exit_json.call_args)

    @patch('ansible.modules.extras.cloud.dimensiondata.'
           'dimensiondata_load_balancer.get_lb_driver', autospec=True)
    def test__get_lb_by_id__happy_path(self, get_lb_driver):
        # Mock objects
        mod_cls = create_autospec(AnsibleModule)
        mod = mod_cls.return_value
        mod.params = dict(name=str(uuid.uuid4()))
        lb_drv = get_lb_driver.return_value
        lb_con = lb_drv.return_value
        data = dict(lb_con=lb_con)

        # Exercise
        event, new_dargs = self.subject.get_lb(mod, data)

        # Assert
        self.assertEqual(self.E.lb_found, event)

        self.assertEqual(0, lb_con.list_balancers.call_count)

        expected_call = call(mod.params['name'])
        self.assertEqual(expected_call, lb_con.get_balancer.call_args)

        expected_dargs = dict(lb_con=lb_con,
                              lb=lb_con.get_balancer.return_value)
        self.assertEqual(expected_dargs, new_dargs)

    @patch('ansible.modules.extras.cloud.dimensiondata.'
           'dimensiondata_load_balancer.get_lb_driver', autospec=True)
    def test__get_lb_by_id__not_found(self, get_lb_driver):
        # Mock objects
        mod_cls = create_autospec(AnsibleModule)
        mod = mod_cls.return_value
        mod.params = dict(name=str(uuid.uuid4()))
        lb_drv = get_lb_driver.return_value
        lb_con = lb_drv.return_value
        lb_con.get_balancer.side_effect = \
            DimensionDataAPIException(code='RESOURCE_NOT_FOUND',
                                      msg='Not found',
                                      driver=lb_drv)
        data = dict(lb_con=lb_con)

        # Exercise
        event, new_dargs = self.subject.get_lb(mod, data)

        # Assert
        self.assertEqual(self.E.lb_not_found, event)

        self.assertEqual(0, lb_con.list_balancers.call_count)

        expected_call = call(mod.params['name'])
        self.assertEqual(expected_call, lb_con.get_balancer.call_args)

        expected_dargs = dict(lb_con=lb_con, lb=None)
        self.assertEqual(expected_dargs, new_dargs)

    @patch('ansible.modules.extras.cloud.dimensiondata.'
           'dimensiondata_load_balancer.get_lb_driver', autospec=True)
    def test__get_lb_by_name__happy_path(self, get_lb_driver):
        # Mock objects
        mod_cls = create_autospec(AnsibleModule)
        mod = mod_cls.return_value
        mod.params = dict(
            name='someloadbalancername'
        )
        lb_drv = get_lb_driver.return_value
        lb_con = lb_drv.return_value
        balancer = lb_con.get_balancer.return_value
        balancer.name = mod.params['name']
        lb_con.list_balancers.return_value = [balancer]
        data = dict(lb_con=lb_con)

        # Exercise
        event, new_dargs = self.subject.get_lb(mod, data)

        # Assert
        self.assertEqual(self.E.lb_found, event)

        self.assertEqual(1, lb_con.list_balancers.call_count)
        self.assertEqual(0, lb_con.get_balancer.call_count)

        expected_dargs = dict(lb_con=lb_con,
                              lb=lb_con.get_balancer.return_value)
        self.assertEqual(expected_dargs, new_dargs)

    @patch('ansible.modules.extras.cloud.dimensiondata.'
           'dimensiondata_load_balancer.get_lb_driver', autospec=True)
    def test__get_lb_by_name__not_found(self, get_lb_driver):
        # Mock objects
        mod_cls = create_autospec(AnsibleModule)
        mod = mod_cls.return_value
        mod.params = dict(
            name='someloadbalancername'
        )
        lb_drv = get_lb_driver.return_value
        lb_con = lb_drv.return_value
        lb_con.list_balancers.return_value = []
        data = dict(lb_con=lb_con)

        # Exercise
        event, new_dargs = self.subject.get_lb(mod, data)

        # Assert
        self.assertEqual(self.E.lb_not_found, event)

        self.assertEqual(1, lb_con.list_balancers.call_count)
        self.assertEqual(0, lb_con.get_balancer.call_count)

        expected_dargs = dict(lb_con=lb_con, lb=None)
        self.assertEqual(expected_dargs, new_dargs)

    @patch('ansible.modules.extras.cloud.dimensiondata.'
           'dimensiondata_load_balancer.get_network_domain', autospec=True)
    @patch('ansible.modules.extras.cloud.dimensiondata.'
           'dimensiondata_load_balancer.get_cp_driver', autospec=True)
    @patch('ansible.modules.extras.cloud.dimensiondata.'
           'dimensiondata_load_balancer.get_lb_driver', autospec=True)
    def test__initialize__happy_path(self,
                                     get_lb_driver,
                                     get_cp_driver,
                                     get_network_domain):
        # Mock objects
        mod_cls = create_autospec(AnsibleModule)
        mod = mod_cls.return_value
        mod.params = dict(
            region='na',
            location='NA12',
            network_domain='00bca85f-c0ca-4b59-aa1d-53b3d8be215b',
            verify_ssl_cert=True
        )
        data = dict()

        # Exercise
        event, new_dargs = self.subject.initialize(mod, data)

        # Assert
        self.assertEqual(1, get_network_domain.call_count)

        compute_drv = get_cp_driver.return_value
        compute_con = compute_drv.return_value
        net_domain = get_network_domain.return_value
        lb_drv = get_lb_driver.return_value
        lb_con = lb_drv.return_value
        expected_call = call(net_domain.id)
        actual_call = lb_con.ex_set_current_network_domain.call_args
        self.assertEqual(expected_call, actual_call)

        self.assertEqual(self.E.initialized, event)

        expected_dargs = dict(lb_con=lb_con,
                              compute_con=compute_con,
                              net_domain=net_domain)
        self.assertEqual(expected_dargs, new_dargs)

    @patch('ansible.modules.extras.cloud.dimensiondata.'
           'dimensiondata_load_balancer.AnsibleModuleFSM', autospec=True)
    def test__main__happy_path(self, mod_cls):
        # Exercise
        self.subject.main()

        # Assert
        self.assertTrue(1, mod_cls.call_count)

        expected_keywords = ['state_machine', 'argument_spec']
        self.assertEqual(expected_keywords, mod_cls.call_args[1].keys())

#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2016 Dimension Data
#
# This module is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#   - Aimon Bustardo <aimon.bustardo@dimensiondata.com>
#   - Mark Maglana   <mmaglana@gmail.com>
#
# Common methods to be used by versious module components
import os
import ConfigParser
from os.path import expanduser
from uuid import UUID

try:
    from libcloud.common.dimensiondata import \
        API_ENDPOINTS, DimensionDataAPIException
    HAS_LIBCLOUD = True
except ImportError:
    HAS_LIBCLOUD = False


# Custom Exceptions

class LibcloudNotFound(Exception):
    pass


class MissingCredentialsError(Exception):
    pass


class UnknownNetworkError(Exception):
    pass


class UnknownVLANError(Exception):
    pass


def check_libcloud_or_fail():
    """
    Checks if libcloud is installed and fails if not
    """
    if not HAS_LIBCLOUD:
        raise LibcloudNotFound("apache-libcloud is required.")


def get_credentials():
    """
    This method will get user_id and key from environemnt or dot file.
    Environment takes priority.

    To set in environment:

        export DIDATA_USER='myusername'
        export DIDATA_PASSWORD='mypassword'

    To set in dot file place a file at ~/.dimensiondata with
    the following contents:

        [dimensiondatacloud]
        DIDATA_USER: myusername
        DIDATA_PASSWORD: mypassword
    """
    check_libcloud_or_fail()

    # Attempt to grab from environment
    user_id = os.environ.get('DIDATA_USER', None)
    key = os.environ.get('DIDATA_PASSWORD', None)

    # Environment failed try dot file
    if not user_id or not key:
        home = expanduser('~')
        config = ConfigParser.RawConfigParser()
        config.read("%s/.dimensiondata" % home)
        try:
            user_id = config.get("dimensiondatacloud", "DIDATA_USER")
            key = config.get("dimensiondatacloud", "DIDATA_PASSWORD")
        except ConfigParser.NoSectionError, ConfigParser.NoOptionError:
            pass

    # One or more credentials not found. Function can't recover from this
    # so it has to raise an error instead of fail silently.
    if not user_id:
        raise MissingCredentialsError("Dimension Data user id not found")
    elif not key:
        raise MissingCredentialsError("Dimension Data key not found")

    # Both found, return data
    return dict(user_id=user_id, key=key)


def get_dd_regions():
    """
    Get the list of available regions whose vendor is Dimension Data.
    """
    check_libcloud_or_fail()

    # Get endpoints
    all_regions = API_ENDPOINTS.keys()

    # filter to only DimensionData endpoints
    region_list = filter(lambda i: i.startswith('dd-'), all_regions)

    # Strip prefix
    regions = [region[3:] for region in region_list]

    return regions


def get_network_domain_by_name(driver, name, location):
    """
    Get a network domain object by its name
    """
    networks = driver.ex_list_network_domains(location=location)
    found_networks = filter(lambda x: x.name == name, networks)

    if not found_networks:
        raise UnknownNetworkError("Network '%s' could not be found" % name)

    return found_networks[0]


def get_network_domain(driver, locator, location):
    """
    Get a network domain object by its name or id
    """
    if is_uuid(locator):
        net_id = locator
    else:
        name = locator
        networks = driver.ex_list_network_domains(location=location)
        found_networks = filter(lambda x: x.name == name, networks)

        if not found_networks:
            raise UnknownNetworkError("Network '%s' could not be found" % name)

        net_id = found_networks[0].id

    return driver.ex_get_network_domain(net_id)


def get_vlan(driver, locator, location, network_domain):
    """
    Get a VLAN object by its name or id
    """
    if is_uuid(locator):
        vlan_id = locator
    else:
        vlans = driver.ex_list_vlans(location=location,
                                     network_domain=network_domain)
        found_vlans = filter(lambda x: x.name == locator, vlans)

        if not found_vlans:
            raise UnknownVLANError("VLAN '%s' could not be found" % locator)

        vlan_id = found_vlans[0].id

    return driver.ex_get_vlan(vlan_id)


def get_mcp_version(driver, location):
    """
    Get a locations MCP version
    """
    # Get location to determine if MCP 1.0 or 2.0
    location = driver.ex_get_location_by_id(location)
    if 'MCP 2.0' in location.name:
        return '2.0'
    return '1.0'


def is_uuid(u, version=4):
    """
    Test if valid v4 UUID
    """
    try:
        uuid_obj = UUID(u, version=version)
        return str(uuid_obj) == u
    except:
        return False


def expand_ip_block(block):
    """
    Expand public IP block to show all addresses
    """
    addresses = []
    ip_r = block.base_ip.split('.')
    last_quad = int(ip_r[3])
    address_root = "%s.%s.%s." % (ip_r[0], ip_r[1], ip_r[2])
    for i in range(int(block.size)):
        addresses.append(address_root + str(last_quad + i))
    return addresses


def get_public_ip_block(module, driver, network_domain, block_id=False,
                        base_ip=False):
    """
    Get public IP block details
    """
    # Block ID given, try to use it.
    if block_id is not 'False':
        try:
            block = driver.ex_get_public_ip_block(block_id)
        except DimensionDataAPIException as e:
            # 'UNEXPECTED_ERROR' should be removed once upstream bug is fixed.
            # Currently any call to ex_get_public_ip_block where the block does
            # not exist will return UNEXPECTED_ERROR rather than
            # 'RESOURCE_NOT_FOUND'.
            if e.code == "RESOURCE_NOT_FOUND" or e.code == 'UNEXPECTED_ERROR':
                module.exit_json(changed=False, msg="Public IP Block does "
                                 "not exist")
            else:
                module.fail_json(msg="Unexpected error while retrieving "
                                 "block: %s" % e.code)
            module.fail_json(msg="Error retreving Public IP Block " +
                                 "'%s': %s" % (block.id, e.message))
    # Block ID not given, try to use base_ip.
    else:
        blocks = list_public_ip_blocks(module, driver, network_domain)
        if blocks is not False:
            block = filter(lambda x: x.base_ip == base_ip, blocks)[0]
        else:
            module.exit_json(changed=False, msg="IP block starting with "
                             "'%s' does not exist." % base_ip)
    return block


def list_nat_rules(module, driver, network_domain):
    """
    Get list of NAT rules for domain
    """
    try:
        return driver.ex_list_nat_rules(network_domain)
    except DimensionDataAPIException as e:
        module.fail_json(msg="Failed to list NAT rules: %s" % e.message)


def list_public_ip_blocks(module, driver, network_domain):
    """
    Get list of public IP blocks for a domain
    """
    try:
        blocks = driver.ex_list_public_ip_blocks(network_domain)
        return blocks
    except DimensionDataAPIException as e:
        module.fail_json(msg="Error retreving Public IP Blocks: %s" % e)


def get_block_allocation(module, cp_driver, lb_driver, network_domain, block):
    """
    Get public IP block allocation details. Shows all ips in block and if
    they are allocated. Example:

        {'id': 'eb8b16ca-3c91-45fb-b04b-5d7d387a9f4a',
          'addresses': [{'address': '162.2.100.100',
                         'allocated': True
                         },
                         {'address': '162.2.100.101',
                          'allocated': False
                         }
                        ]
        }
    """
    nat_rules = list_nat_rules(module, cp_driver, network_domain)
    balancers = list_balancers(module, lb_driver)
    pub_ip_block = get_public_ip_block(module, cp_driver, network_domain,
                                       block.id, False)
    pub_ips = expand_ip_block(pub_ip_block)
    block_detailed = {'id': block.id, 'addresses': []}
    for ip in pub_ips:
        allocated = False
        nat_match = filter(lambda x: x.external_ip == ip, nat_rules)
        lb_match = filter(lambda x: x.ip == ip, balancers)
        if len(nat_match) > 0 or len(lb_match) > 0:
            allocated = True
        else:
            allocated = False
        block_detailed['addresses'].append({'address': ip,
                                            'allocated': allocated})
    return block_detailed


def list_balancers(module, lb_driver):
    try:
        return lb_driver.list_balancers()
    except DimensionDataAPIException as e:
        module.fail_json(msg="Failed to list Load Balancers: %s" % e.message)


def get_blocks_with_unallocated(module, cp_driver, lb_driver, network_domain):
    """
    Gets ip blocks with one or more unallocated IPs.
    ex:
        {'unallocated_count': <total count of unallocated ips>,
         'ip_blocks': [<list of expanded blocks with details
                       (see get_block_allocation())>],
         'unallocated_addresses': [<list of unallocated ip addresses>]
        }
    """
    total_unallocated_ips = 0
    all_blocks = list_public_ip_blocks(module, cp_driver, network_domain)
    unalloc_blocks = []
    unalloc_addresses = []
    for block in all_blocks:
        d_blocks = get_block_allocation(module, cp_driver, lb_driver,
                                        network_domain, block)
        i = 0
        for addr in d_blocks['addresses']:
            if addr['allocated'] is False:
                if i == 0:
                    unalloc_blocks.append(d_blocks)
                unalloc_addresses.append(addr['address'])
                total_unallocated_ips += 1
            i += 1
    return {'unallocated_count': total_unallocated_ips,
            'ip_blocks': unalloc_blocks,
            'unallocated_addresses': unalloc_addresses}


def get_unallocated_public_ips(module, cp_driver, lb_driver, network_domain,
                               reuse_free, count=0):
    """
    Get and/or provision unallocated public IPs
    """
    free_ips = []
    if reuse_free is True:
        blocks_with_unallocated = get_blocks_with_unallocated(module,
                                                              cp_driver,
                                                              lb_driver,
                                                              network_domain)
        free_ips = blocks_with_unallocated['unallocated_addresses']
    if len(free_ips) < count:
        num_needed = count - len(free_ips)
        for i in range(num_needed):
            block = cp_driver.ex_add_public_ip_block_to_network_domain(
                network_domain)
            b_dict = get_block_allocation(module, cp_driver, lb_driver,
                                          network_domain, block)
            for addr in b_dict['addresses']:
                free_ips.append(addr['address'])
            if len(free_ips) >= count:
                break
        return {'changed': True, 'msg': 'Allocated public IP block(s)',
                'addresses': free_ips[:count]}
    else:
        return {'changed': False, 'msg': 'Found enough unallocated IPs' +
                ' without provisioning.', 'addresses': free_ips}


def is_ipv4_addr(ip):
    """
    Simple way to check if IPv4 address
    """
    parts = ip.split('.')
    try:
        return len(parts) == 4 and all(0 <= int(part) < 256 for part in parts)
    except:
        return False


def get_node_by_name_and_ip(module, lb_driver, name, ip):
    """
    Nodes do not have unique names, we need to match name and IP to be
    sure we get the correct one
    """
    nodes = lb_driver.ex_get_nodes()
    found_nodes = []
    if not is_ipv4_addr(ip):
        module.fail_json(msg="Node '%s' ip is not a valid IPv4 address" % ip)
    found_nodes = filter(lambda x: x.name == name and x.ip == ip, nodes)
    if len(found_nodes) == 0:
        return None
    elif len(found_nodes) == 1:
        return found_nodes[0]
    else:
        module.fail_json(msg="More than one node of name '%s' found." % name)

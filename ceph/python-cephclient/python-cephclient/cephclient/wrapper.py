#
# Copyright (c) 2019 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import six

from cephclient.client import CephClient
from cephclient.exception import CephClientFunctionNotImplemented
from cephclient.exception import CephClientInvalidOsdIdValue
from cephclient.exception import CephClientTypeError


class CephWrapper(CephClient):

    def __init__(self, endpoint=''):
        super(CephWrapper, self).__init__()

    def auth_import(self, body='json', timeout=None):
        raise CephClientFunctionNotImplemented(name='auth_import')

    def _sanitize_osdid_to_str(self, _id):
        if isinstance(_id, six.string_types):
            prefix = 'osd.'
            if not _id.startswith(prefix):
                try:
                    int(_id)
                except ValueError:
                    raise CephClientInvalidOsdIdValue(
                        osdid=_id)
                _id = prefix + _id
        elif isinstance(_id, six.integer_types):
            _id = 'osd.{}'.format(_id)
        else:
            raise CephClientInvalidOsdIdValue(
                osdid=_id)
        return _id

    def _sanitize_osdid_to_int(self, _id):
        if isinstance(_id, six.string_types):
            prefix = 'osd.'
            if _id.startswith(prefix):
                _id = _id[len(prefix):]
            try:
                _id = int(_id)
            except ValueError:
                raise CephClientInvalidOsdIdValue(
                    osdid=_id)
        elif not isinstance(_id, six.integer_types):
            raise CephClientInvalidOsdIdValue(
                osdid=_id)
        return _id

    def osd_create(self, uuid, body='json', timeout=None, params=None):
        """create new osd (with optional UUID and ID)

        Notes:
        1. osd create declares it accepts osd id as string but only works when
           given an integer value; it automatically generates an ID otherwise
           instead of using the one provided by 'osd create id=...'

        2. old cephclient passes osd id through params dictionary
        """
        kwargs = dict(uuid=uuid, body=body, timeout=timeout)
        try:
            kwargs['id'] = self._sanitize_osdid_to_int(params['id'])
        except (KeyError, TypeError):
            pass
        return self._request('osd create', **kwargs)

    def osd_rm(self, ids, body='json', timeout=None):
        """remove osd(s) <id> [<id>...], or use <any|all> to remove all osds """
        if isinstance(ids, list):
            ids = [self._sanitize_osdid_to_str(_id)
                   for _id in ids]
        else:
            ids = self._sanitize_osdid_to_str(ids)
        return super(CephWrapper, self).osd_rm(
            ids=ids, body=body, timeout=timeout)

    def osd_remove(self, ids, body='json', timeout=None):
        return self.osd_rm(ids, body=body, timeout=timeout)

    def osd_down(self, ids, body='json', timeout=None):
        """set osd(s) <id> [<id>...] down, or use <any|all> to set all osds down """
        if isinstance(ids, list):
            ids = [self._sanitize_osdid_to_str(_id)
                   for _id in ids]
        else:
            ids = self._sanitize_osdid_to_str(ids)
        return super(CephWrapper, self).osd_down(
            ids=ids, body=body, timeout=timeout)

    OSD_CRUSH_TREE_CONVERTED_FIELDS = [
        'crush_weight', 'depth', 'id', 'name', 'type', 'type_id']

    def _osd_crush_tree_convert_node(self, node):
        return {k: node[k] for k in self.OSD_CRUSH_TREE_CONVERTED_FIELDS
                if k in node}

    def _osd_crush_tree_populate_tree(self, node, node_map):
        children = node.get('children')
        node = self._osd_crush_tree_convert_node(node)
        if children:
            node['items'] = []
            for _id in children:
                node['items'].append(
                    self._osd_crush_tree_populate_tree(
                        node_map[_id], node_map))
        return node

    def osd_crush_tree(self, shadow=None, body='json', timeout=None):
        """dump crush buckets and items in a tree view """
        response, _body = super(CephWrapper, self).osd_crush_tree(
            shadow=shadow, body=body, timeout=timeout)
        trees = []
        if response.ok and body == 'json' \
           and 'output' in _body:
            node_map = {}
            root_nodes = []
            for node in _body['output']:
                node_map[node['id']] = node
                if node['type'] == 'root':
                    root_nodes.append(node)
            for root in root_nodes:
                trees.append(
                    self._osd_crush_tree_populate_tree(
                        root, node_map))
            _body['output'] = trees
        return response, _body

    def _osd_crush_rule_by_ruleset(self, ruleset, timeout=None):
        response, _body = self.osd_crush_rule_dump(
            body='json', timeout=timeout)
        if not response.ok:
            return response, _body
        name = None
        for rule in _body['output']:
            if rule.get('ruleset') == ruleset:
                name = rule.get('rule_name')
        _body['output'] = dict(rule=name)
        return response, _body

    def _osd_crush_ruleset_by_rule(self, rule, timeout=None):
        response, _body = self.osd_crush_rule_dump(
            name=rule, body='json', timeout=timeout)
        return response, _body

    def osd_pool_create(self, pool, pg_num, pgp_num=None, pool_type=None,
                        erasure_code_profile=None, ruleset=None,
                        expected_num_objects=None, body='json', timeout=None):
        """create pool

        Notes:
        1. map 'ruleset' to 'rule' (assuming 1:1 correspondence)
        """
        response, _body = self._osd_crush_rule_by_ruleset(ruleset)
        if not response.ok:
            return response, _body
        rule = _body['output']['rule']
        return super(CephWrapper, self).osd_pool_create(
            pool, pg_num, pgp_num=pgp_num, pool_type=pool_type,
            erasure_code_profile=erasure_code_profile, rule=rule,
            expected_num_objects=expected_num_objects, body=body,
            timeout=timeout)

    def osd_get_pool_param(self, pool, var, body='json', timeout=None):
        """get pool parameter <var> """
        if var == 'crush_ruleset':
            response, _body = super(CephWrapper, self).osd_pool_get(
                pool, 'crush_rule', body='json', timeout=timeout)
            if response.ok:
                rule = _body['output']['crush_rule']
                del _body['output']['crush_rule']
                response, _body = self._osd_crush_ruleset_by_rule(
                    rule, timeout=timeout)
                if response.ok:
                    _body['output'] = dict(
                        crush_ruleset=_body['output']['ruleset'])
            return response, _body
        else:
            return super(CephWrapper, self).osd_pool_get(
                pool, var, body=body, timeout=timeout)

    def osd_pool_set(self, pool, var, val, force=None,
                     body='json', timeout=None):
        """set pool parameter <var> to <val> """
        return super(CephWrapper, self).osd_pool_set(
            pool=pool, var=var, val=str(val),
            force=force, body=body, timeout=timeout)

    def osd_set_pool_param(self, pool, var, val, force=None,
                           body='json', timeout=None):
        """set pool parameter <var> to <val> """
        if var == 'crush_ruleset':
            var = 'crush_rule'
            response, _body = self._osd_crush_rule_by_ruleset(
                val, timeout=timeout)
            if not response.ok:
                return response, _body
            val = _body['output']['rule']
        return super(CephWrapper, self).osd_pool_set(
            pool, var, str(val), force=None,
            body=body, timeout=timeout)

    def osd_get_pool_quota(self, pool, body='json', timeout=None):
        """obtain object or byte limits for pool """
        return super(CephWrapper, self).osd_pool_get_quota(
            pool, body=body, timeout=timeout)

    def osd_set_pool_quota(self, pool, field, val, body='json', timeout=None):
        """set object or byte limit on pool """
        return super(CephWrapper, self).osd_pool_set_quota(
            pool, field, str(val), body=body, timeout=timeout)

    def osd_pool_set_quota(self, pool, field, val,
                           body='json', timeout=None):
        """set object or byte limit on pool """
        return super(CephWrapper, self).osd_pool_set_quota(
            pool=pool, field=field, val=str(val),
            body=body, timeout=timeout)

    def _auth_convert_caps(self, caps):
        if caps:
            if not isinstance(caps, dict):
                raise CephClientTypeError(
                    name='caps',
                    actual=type(caps),
                    expected=dict)
            _caps = []
            for key, value in list(caps.items()):
                _caps.append(key)
                _caps.append(value)
            caps = _caps
        return caps

    def auth_add(self, entity, caps=None, body='json', timeout=None):
        """add auth info for <entity> from input file, or random key if no input is given, and/or any caps specified in the command """
        caps = self._auth_convert_caps(caps)
        return super(CephWrapper, self).auth_add(
            entity, caps=caps, body=body, timeout=timeout)

    def auth_caps(self, entity, caps, body='json', timeout=None):
        """update caps for <name> from caps specified in the command """
        caps = self._auth_convert_caps(caps)
        return super(CephWrapper, self).auth_caps(
            entity, caps=caps, body=body, timeout=timeout)

    def auth_get_or_create(self, entity, caps=None, body='json', timeout=None):
        """add auth info for <entity> from input file, or random key if no input given, and/or any caps specified in the command """
        caps = self._auth_convert_caps(caps)
        return super(CephWrapper, self).auth_get_or_create(
            entity, caps, body=body, timeout=timeout)

    def auth_get_or_create_key(self, entity, caps=None,
                               body='json', timeout=None):

        """get, or add, key for <name> from system/caps pairs specified in the command.  If key already exists, any given caps must match the existing caps for that key.  """
        caps = self._auth_convert_caps(caps)
        response, _body = super(CephWrapper, self).auth_get_or_create_key(
            entity, caps, body=body, timeout=timeout)
        if response.ok:
            _body['output'] = _body['output']
        return response, _body

    def osd_set_key(self, key, sure=None, body='json', timeout=None):
        """set <key> """
        return self.osd_set(key, sure=sure, body=body, timeout=timeout)

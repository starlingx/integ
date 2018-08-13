#
# Copyright (c) 2016 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#
import oslo_i18n

DOMAIN = 'ceph-manager'

_translators = oslo_i18n.TranslatorFactory(domain=DOMAIN)
_ = _translators.primary

_LI = _translators.log_info
_LW = _translators.log_warning
_LE = _translators.log_error

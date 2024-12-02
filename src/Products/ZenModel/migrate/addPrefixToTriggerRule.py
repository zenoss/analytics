##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################


__doc__='''
Updates all triggers in the system that use details added by Zenpacks. It renames the details in the triggers
so that zep will be able to evaluate them (prepends 'zp_det.' to the detail name and replaces any '.' with '_').
Moreover, a condition to check if the detail exists in the event is added to the triggers that use zp details.
Example:
   original trigger rule: ("hola" in zenoss.gom.source_uuid)
   new trigger rule:      (hasattr(zp_det, "zenoss_gom_source_uuid") and "hola" in zp_det.zenoss_gom_source_uuid)
'''

import Migrate
from Products.Zuul import getFacade

class AddPrefixToTriggerRule(Migrate.Step):
    version = Migrate.Version(5, 0, 70)

    ZP_DETAILS_TRIGGER_PREFIX = "zp_det";

    def _migrate_detail_in_trigger(self, trigger_source, detail, detail_translator):
        """ Searchs for the custom zp detail 'detail' in 'trigger_source', renames the detail to the new format and adds 
            a condition to avoid the trigger failing for events that do not have the detail """
        to_replace = []
        index = trigger_source.find(detail, 0)
        while index != -1:
            start = trigger_source.rfind('(', 0, index) # find the first '(' from index going backwards
            end = trigger_source.find(')', index)       # find the first ')' from index going forward
            if start != -1 and end != -1:
                rule_with_parenthesis = trigger_source[start:end+1]
                rule = rule_with_parenthesis[1:-1]
                new_detail_name = detail_translator.get(detail)
                new_detail_expr = '{0}.{1}'.format(self.ZP_DETAILS_TRIGGER_PREFIX, new_detail_name)
                new_rule = '(hasattr({0}, "{1}") and {2})'.format(self.ZP_DETAILS_TRIGGER_PREFIX, new_detail_name, rule.replace(detail, new_detail_expr))
                to_replace.append((rule_with_parenthesis, new_rule))
            index = trigger_source.find(detail, index+1)

        for rule, new_rule in to_replace:
            trigger_source = trigger_source.replace(rule, new_rule)

        return trigger_source

    def cutover(self, dmd):
        zep_facade = getFacade('zep')
        triggers_facade = getFacade('triggers')

        zp_details = [ det.get('key') for det in zep_facade.getUnmappedDetails() if det.get('key') ]

        zp_detail_translator = {}
        for zp_detail in zp_details:
            zp_detail_translator[zp_detail] = '_'.join(zp_detail.split('.'))

        for trigger in triggers_facade.getTriggers():
            if trigger.get('rule') and trigger.get('rule').get('source'):
                source = trigger.get('rule').get('source')
                for zp_detail in zp_details:
                    if zp_detail in source:
                        new_source = self._migrate_detail_in_trigger(source, zp_detail, zp_detail_translator)
                        trigger['rule']['source'] = new_source
                        triggers_facade.updateTrigger(**trigger)
                        print "Trigger {0} updated.".format(trigger.get('name'))

# Disabling this migrate script, because it requires zeneventserver to be running. ZEN-17256 ZEN-18175
# AddPrefixToTriggerRule()

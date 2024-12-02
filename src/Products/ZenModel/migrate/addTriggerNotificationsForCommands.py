##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate
import logging
from Products.ZenEvents.WhereClause import toPython, PythonConversionException
from Products.ZenModel.migrate.addTriggersAndNotifications import TriggerRuleSourceError, talesifyLegacyFormatString
from Products import Zuul

log = logging.getLogger( 'zen.migrate' )

class AddTriggerNotificationsForCommands(Migrate.Step):
    version = Migrate.Version(4, 0, 0)

    def __init__(self):
        Migrate.Step.__init__(self)
        import addTriggers, addNotificationSubscriptions
        self.dependencies = [ addTriggers.triggers, addNotificationSubscriptions.notificationSubscriptions ]

    def _parseCommand(self, command):
        python_statement = toPython(command.genMeta(), command.where)

        # if the parser failed to parse the where clause, the python statement
        # will be empty.
        if not python_statement:
            raise TriggerRuleSourceError(command.where)

        log.debug('Parsing From: "%s"' % command.where)
        log.debug('        To  : "%s"' % python_statement)
        return python_statement

    def _parseContent(self, content):
        return talesifyLegacyFormatString(content)

    def _createTrigger(self, command):
        log.debug('Creating trigger for: %s' % command.id)

        new_rule_source = self._parseCommand(command)
        
        trigger_id = command.id

        for t in self.existing_triggers:
            if trigger_id == t['name']:
                log.debug('Trigger already exists, not creating.')
                return self.triggers_facade.getTrigger(t['uuid'])

        trigger_uuid = self.triggers_facade.addTrigger(trigger_id)
        trigger = self.triggers_facade.getTrigger(trigger_uuid)
        trigger['enabled'] = command.enabled
        trigger['rule']['source'] = new_rule_source

        self.triggers_facade.updateTrigger(**trigger)

        return trigger

    def _createNotification(self, command, trigger):
        log.debug('Creating notification for: %s (%s)' % (command.id, 'command'))

        notification_id = command.id

        for n in self.existing_notifications:
            if notification_id == n.id:
                log.debug('Notification already exists, not creating.')
                return

        self.triggers_facade.addNotification(notification_id, 'command')

        notification_obj = self.dmd.NotificationSubscriptions.findChild(notification_id)


        notification_obj.enabled = command.enabled
        notification_obj.send_clear = True
        notification_obj.send_initial_occurrence = True
        notification_obj.delay_seconds = command.delay
        notification_obj.repeat_seconds = command.repeatTime

        notification_obj.subscriptions = [trigger['uuid']]

        notification_obj.content['body_content_type'] = 'text'
        notification_obj.content['body_format'] = self._parseContent(command.command)
        notification_obj.content['clear_body_format'] = self._parseContent(command.clearCommand)

        # commands do not have recipients.
        log.debug('Not adding recipients since commands dont have recipients.')

        # old event commands didn't have a concept of active windows
        log.debug('Not trying to migrate windows since legacy event commands did not have them.')

        self.triggers_facade.updateNotificationSubscriptions(notification_obj)

    def cutover(self, dmd):

        self.dmd = dmd
        self.triggers_facade = Zuul.getFacade('triggers', dmd)

        self.existing_triggers = self.triggers_facade.getTriggers()
        self.existing_notifications = self.triggers_facade.getNotifications()

        # action rules are being removed, make sure they haven't been yet.
        commands = dmd.ZenEventManager.commands.objectValues()

        failed = False
        for command in commands:
            if not command.where:
                continue
            try:
                trigger = self._createTrigger(command)
                self._createNotification(command, trigger)
                log.info('Done processing event command: %s.' % command.id)
            except TriggerRuleSourceError as e:
                failed = True
                log.warn('Unable to parse existing event command: %s' % command.id)
            except PythonConversionException as e:
                log.debug("Failed conversion: %s", e)
                log.warn("Unable to convert existing event command: %s" % command.id)
                failed = True

        if failed:
            log.info('If any event commands were unable to be migrated, they '
            'will need to be manually migrated to triggers and notifications. '
            'You can access the old Event Commands through the ZMI.')



addTriggerNotificationsForCommands = AddTriggerNotificationsForCommands()

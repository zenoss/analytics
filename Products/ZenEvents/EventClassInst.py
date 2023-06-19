##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################
from contextlib import contextmanager
from functools import partial

from ZODB.transact import transact

import copy
import re
import sre_constants
import logging
import transaction
import urllib
import time
import pickle
import os
import zope.component
from Products.ZenMessaging.audit import audit

log = logging.getLogger("zen.Events")

from AccessControl.class_init import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions
from Acquisition import aq_chain
from zope.interface import implements

from Products.ZenModel.interfaces import IIndexed
from Products.ZenModel.ZenossSecurity import *
from Products.ZenRelations.RelSchema import *
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenModel.EventView import EventView
from Products.ZenModel.ZenPackable import ZenPackable
from Products.ZenWidgets import messaging
from Products.ZenUtils.guid.interfaces import IGloballyIdentifiable
from Products.ZenUtils.Utils import convToUnits, zdecode, getDisplayName
from Products.ZenUtils.Time import SaveMessage
from Products import Zuul
from Products.Zuul.interfaces import IInfo
from Products.ZenUtils.path import zenPath
from Products.ZenUtils.daemonconfig import IDaemonConfig

from zenoss.protocols.jsonformat import to_dict

MAX_TRANSFORM_TIME = 2.0
MAX_TRANSFORM_FAILS = 'zEventMaxTransformFails'

def manage_addEventClassInst(context, id, REQUEST = None):
    """make a device class"""
    dc = EventClassInst(id)
    context._setObject(id, dc)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url_path() + '/manage_main')

@contextmanager
def transformsavepoint(errorCallback=lambda :None):
    sp = None
    hadError = False
    try:
        txn = transaction.get()
        sp = txn.savepoint()
        yield
    except (Exception, SystemExit) as e:
        sp = None
        hadError = True
        log.info("Transform error %s; aborting transaction", e) 
        transaction.abort()
        errorCallback()
    finally:
        try:
            if sp and sp.valid:
                log.debug("Reverting to savepoint after transform") 
                sp.rollback()
            elif not hadError:
                log.debug("Aborting transaction after transform") 
                transaction.abort()
        except Exception:
            log.exception("Error rolling back transaction after transform")

class EventClassPropertyMixin(object):

    transform = ''
    transformEnabled = True

    # dictionary to store counter of bad_transforms for all EventClasses
    _badtransform = {}

    _properties = (
        {'id':'transform', 'type':'text', 'mode':'w'},
        {'id': 'transformEnabled', 'type': 'bool', 'mode': 'w'},
        )

    def applyValues(self, evt):
        """Modify event with values taken from dict Inst.
        Any non-None property values are applied to the event.
        """
        evt._clearClasses = copy.copy(getattr(self, "zEventClearClasses", []))
        evt._action = getattr(self, "zEventAction", "status")
        sev = getattr(self, "zEventSeverity", -1)
        if sev >= 0:
            if evt.severity > 0:
                evt.severity = sev
        log.debug("Per transform/mapping, using severity %s, action '%s' and clear classes %s",
                  evt.severity, evt._action, evt._clearClasses)
        updates = {}
        for name in 'resolution', 'explanation':
            value = getattr(self, name, None)
            if value is not None and value != '':
                updates[name] = value
        if updates:
            log.debug("Adding fields from transform/mapping: %s", updates)
        evt.updateFromDict(updates)
        return evt

    def formatTransform(self, transformLines, badLineNo=None):
        """
        Convenience function to number the transform info
        """
        if badLineNo is not None:
            transformed_lines = []
            for line_index, line in enumerate(transformLines, start=1):
                if line_index == badLineNo:
                    transformed_lines.append(" * %3s %s" % (line_index, line))
                else:
                    transformed_lines.append("   %3s %s" % (line_index, line))
            return '\n'.join(transformed_lines)
        else:
            return '\n'.join("%3s %s" % enumText
                             for enumText in enumerate(transformLines, start=1))

    def formatTransformForUI(self):
        """
        For the status page so the user can easily read the transform
        without clicking edit.
        """
        lines = self.transform.splitlines()
        return self.formatTransform(lines).replace(" ", "&nbsp;").replace("\n", "<br />").replace("\t", "&nbsp;" * 8)

    def sendTransformException(self, eventclass, evt):
        """
        Try to convert the rather horrible looking traceback that
        is hard to understand into something actionable by the user.
        """
        transformName = '/%s'% '/'.join(eventclass.getPhysicalPath()[4:])
        evt.eventClass = transformName
        self.pickleFailedEvent(evt)
        summary = "Error processing transform/mapping on Event Class %s" % \
            transformName

        import sys
        from traceback import format_exc, extract_tb
        tb = extract_tb(sys.exc_info()[2])
        exceptionText = format_exc(0).splitlines()[1]
        transformLines = eventclass.transform.splitlines()

        # try to extract line number and code from traceback, but set up
        # default values in case this fails - don't want to throw a traceback
        # when cleaning up a traceback
        badLineNo = None
        badLineText = ''
        try:
            if len(tb) == 2:
                # Compiletime error: with exceptionText in the form:
                # '  File "<string>", line 4'
                # We must extract the line number from the exceptionText
                badLineNo = int(exceptionText.rsplit(None,1)[1])
                exceptionText = "compile error on line %d" % badLineNo
            else:
                # Runtime error: the transform code is in the third tuple
                #1 (element 0) transformsavepoint yield
                #2 (element 1) applyTransform exec
                #3 (element 2) transform code
                badLineNo = tb[2][1]
        except Exception:
            pass
        
        badLineText = transformLines[badLineNo-1]
        transformFormatted = self.formatTransform(transformLines, badLineNo)

        message = """%s
Problem on line %s: %s
%s

Transform:
%s
""" % (summary, badLineNo, exceptionText, badLineText,
        transformFormatted)
        log.warn(message)
        # add the event that caused this exception to the transform event
        # so the operator has context for debugging transforms
        sourceEventText = str(evt._zepRawEvent._pb)
        sourceEventDevice = evt.device
        sourceEventComponent = evt.component

        # Now send an event
        zem = self.getDmd().ZenEventManager
        badEvt = dict(
            # Don't send the *same* event class or we trash and
            # and crash endlessly
            eventClass='/App/Zenoss',
            eventKey='transform_failed',
            device=zem.host,
            component=transformName,
            summary=summary,
            severity=4,
            message = "Problem with line %s: %s" % (badLineNo, badLineText),
            transform=transformFormatted,
            exception=exceptionText,
            # Set False if the root ('/') transform failed; avoids looping
            # infinitely on creating transform event failures.
            applyTransforms=False if (transformName == '/') else True,
            sourceEventText=sourceEventText,
            sourceEventDevice=sourceEventDevice,
            sourceEventComponent=sourceEventComponent
        )
        zem.sendEvent(badEvt)

        use_blocking_mechanism = eventclass.getProperty(MAX_TRANSFORM_FAILS) > 0 and eventclass.transformEnabled
        if use_blocking_mechanism:
            disableEvt = self._updateBadTransformCounter(evt, eventclass)
            if disableEvt:
                disable_msg = "Transform for Event Class %s is disabled due to %d attempts to apply it: line %d, %s, " \
                              "exception %s" % (
                    evt.eventClass, eventclass.getProperty(MAX_TRANSFORM_FAILS), badLineNo, badLineText, exceptionText)
                disableTransformEvt = dict(
                    eventClass='/App/Zenoss',
                    eventKey='transform_disabled',
                    device=zem.host,
                    component=evt.eventClass,
                    summary=disable_msg,
                    severity=4,
                    message='Transform can be enabled again in Event Classes settings.'
                )
                zem.sendEvent(disableTransformEvt)
                self.setTransformEnabled(eventclass, False)
                self._resetBadTransformCounter(evt.eventClass)

    def _updateBadTransformCounter(self, evt, eventclass):
        name = evt.eventClass
        if not self._badtransform.get(name):
            self._badtransform[name] = 1
        else:
            self._badtransform[name] += 1
        if self._badtransform[name] >= eventclass.getProperty(MAX_TRANSFORM_FAILS):
            return True
        return False

    def _resetBadTransformCounter(self, eventclass_name):
        self._badtransform[eventclass_name] = 0

    @transact
    def setTransformEnabled(self, eventclass, enabled):
        # Enables or disables transform on the given event class.
        eventclass.transformEnabled = bool(enabled)

    def pickleFailedEvent(self, evt):
        obj = zope.component.getUtility(IDaemonConfig, 'zeneventd_config')
        config = obj.getConfig()
        # By default there are 100 pickle files in failed_transformed_events folder.
        # To change this value set maxpickle value in /opt/zenoss/etc/zeneventd.conf
        max_pickle = config.maxpickle-1
        # By default the path to save pickle files is
        # $ZENHOME/var/zeneventd/failed_transformed_events.
        # To change this value set pickledir value in /opt/zenoss/etc/zeneventd.conf
        pickle_dir = config.pickledir
        if not os.path.exists(pickle_dir):
            os.makedirs(pickle_dir)
        file_list = []
        pickles_count = 0
        for file in os.listdir(pickle_dir):
            filepath = os.path.join(pickle_dir, file)            
            modified = os.stat(filepath).st_mtime
            file_tuple = modified, file
            file_list.append(file_tuple)
        file_list.sort(reverse=True)
        files_to_delete = file_list[max_pickle:]
        for time, file in files_to_delete:
            filepath = os.path.join(pickle_dir, file)
            if os.path.isfile(filepath):
                if pickles_count == 0:
                    log.info("Deleting old pickle files ...")
                try:
                    os.remove(filepath)
                    pickles_count += 1
                except Exception as e:
                    log.exception("Unable to delete %s: %s", filepath, e)
        if pickles_count:
            log.info("Deleted %s old pickle files.", pickles_count)
        filename = pickle_dir + '/%s_%s.pickle' % (evt.device, evt.evid)        
        try:
            with open(filename, 'w') as f:
                evtDict = to_dict(evt._event)
                pickle.dump(evtDict, f)
        except Exception as ex:
            log.exception("Unable to store evt pickle data to %s: %s", filename, ex)

    def applyTransform(self, evt, device, component=None):
        """
        Apply transforms on an event from the top level of the Event Class Tree
        down to the actual Event Rules (EventClassInst)
        """
        transpath = self._eventClassPath()
        variables_and_funcs = {
            'evt':evt, 'device':device, 'dev':device,
            'convToUnits':convToUnits, 'zdecode':zdecode,
            'txnCommit':transaction.commit,  # this function is deprecated in favor of transforms using @transact
            'transact':transact, 'dmd':self.dmd,
            'log':log, 'component':component,
            'getFacade':Zuul.getFacade, 'IInfo':IInfo,
        }
        for eventclass in transpath:
            if not eventclass.transform: continue
            startTime = time.time()
            errorCallback = partial(self.sendTransformException, eventclass, evt)
            with transformsavepoint(errorCallback):
                exec(eventclass.transform, variables_and_funcs)
            endTime = time.time()

            if endTime - startTime > MAX_TRANSFORM_TIME:
                log.warning('Event transform took %.1f seconds (threshold %.1f seconds), event context is %s, transform is: %s', endTime - startTime, MAX_TRANSFORM_TIME, evt, eventclass.transform)
            elif log.isEnabledFor(logging.DEBUG):
                log.debug('Event transform took %.1f seconds (threshold %.1f seconds), event context is %s', endTime - startTime, MAX_TRANSFORM_TIME, evt)

        return variables_and_funcs['evt']


    def inheritedTransforms(self):
        """
        Make a string that brings together all the transforms inherited from the
        base EventClass to self.
        """
        transpath = self._eventClassPath()
        transtext = []
        for obj in transpath:
            if not obj.transform: continue
            if obj.transform == self.transform: break
            transtext.append("""<a href='%s/editEventClassTransform'>%s<a>
                """ % (obj.getPrimaryUrlPath(), obj.getPrimaryDmdId()))
            transtext.append("<pre>%s</pre>" % obj.transform)
        return "\n".join(transtext)


    def testTransformStyle(self):
        """Test our transform by compiling it.
        """
        try:
            if self.transform:
                compile(self.transform, "<string>", "exec")
        except Exception:
            return "color:#FF0000;"


    def _eventClassPath(self):
        """
        Return the path to our current EventClassInst from the top level
        EventClass down. We use this to process and display the heirarchy of
        event transforms.
        """
        transpath = []
        for obj in aq_chain(self):
            # skip over relationships in the aq_chain
            if not isinstance(obj, EventClassPropertyMixin): continue
            if obj.id == 'dmd': break
            transpath.append(obj)
        transpath.reverse()
        return transpath

# Why is this a subclass of EventView?

class EventClassInst(EventClassPropertyMixin, ZenModelRM, EventView,
                     ZenPackable):
    """
    EventClassInst.
    """
    implements(IIndexed, IGloballyIdentifiable)

    event_key = meta_type = "EventClassInst"

    default_catalog = "eventClassSearch"

    actions = ("status", "history", "heartbeat", "drop")

    _properties = EventClassPropertyMixin._properties + (
        {'id':'eventClassKey', 'type':'string', 'mode':'w'},
        {'id':'sequence', 'type':'int', 'mode':'w'},
        {'id':'rule', 'type':'string', 'mode':'w'},
        {'id':'regex', 'type':'string', 'mode':'w'},
        {'id':'example', 'type':'string', 'mode':'w'},
        {'id':'explanation', 'type':'text', 'mode':'w'},
        {'id':'resolution', 'type':'text', 'mode':'w'},
        )


    _relations = ZenPackable._relations + (
        ("eventClass", ToOne(ToManyCont,"Products.ZenEvents.EventClass","instances")),
        )


    # Screen action bindings (and tab definitions)
    factory_type_information = (
        {
            'id'             : 'EventClassInst',
            'meta_type'      : 'EventClassInst',
            'description'    : """Base class for all devices""",
            'icon'           : 'EventClassInst.gif',
            'product'        : 'ZenEvents',
            'factory'        : 'manage_addEventClassInst',
            'immediate_view' : 'eventClassInstStatus',
            'actions'        :
            (
                { 'id'            : 'status'
                , 'name'          : 'Status'
                , 'action'        : 'eventClassInstStatus'
                , 'permissions'   : (Permissions.view, )
                },
                { 'id'            : 'edit'
                , 'name'          : 'Edit'
                , 'action'        : 'eventClassInstEdit'
                , 'permissions'   : ("Manage DMD", )
                },
                { 'id'            : 'sequence'
                , 'name'          : 'Sequence'
                , 'action'        : 'eventClassInstSequence'
                , 'permissions'   : (Permissions.view,)
                },
                { 'id'            : 'config'
                , 'name'          : 'Configuration Properties'
                , 'action'        : 'zPropertyEditNew'
                , 'permissions'   : ("Manage DMD",)
                },
                { 'id'            : 'events'
                , 'name'          : 'Events'
                , 'action'        : 'viewEvents'
                , 'permissions'   : (Permissions.view, )
                },
            )
         },
        )

    security = ClassSecurityInfo()

    def __init__(self, id):
        ZenModelRM.__init__(self, id)
        self.eventClassKey = id
        self.sequence = None
        self.rule = ""
        self.regex = ""
        self.example = ""
        self.explanation = ""
        self.resolution = ""

    def _updateProperty(self, id, value):
        resequence = False
        if id == 'sequence':
            for mapping in self.sameKey():
                if mapping.sequence == value:
                    # We have a sequence conflict. Allow it to proceed, but
                    # resequence afterwards to deal with overlaps and holes.
                    resequence = True
                    break
        super(EventClassInst, self)._updateProperty(id, value)
        if resequence:
            for i, mapping in enumerate(self.sameKey()):
                mapping.sequence = i

    def getStatus(self, **kwargs):
        """Return the status number for this device of class statClass.
        """
        return EventView.getStatus(self, self.getEventClass())

    def getEventClass(self):
        """Return the full EventClass of this EventClassInst."""
        return self.getOrganizerName()

    def getEventClassHref(self):
        """Return href of our class.
        """
        return self.eventClass().getPrimaryUrlPath()


    def getDmdKey(self):
        """Return the dmd key of this mapping ie: /App/Start/zentinel
        """
        return self.getOrganizerName() + "/" + self.id


    def applyExtraction(self, evt):
        """
        Apply the event dict regex to extract additional values from the event.
        """
        if self.regex:
            m = re.search(self.regex, evt.message)
            if m: evt.updateFromDict(m.groupdict())
        return evt


    def applyValues(self, evt):
        """Modify event with values taken from dict Inst.
        Any non-None property values are applied to the event.
        """
        evt.eventClass = self.getEventClass()
        evt.eventClassMapping = '%s/%s' % (self.getEventClass(), self.id)
        return EventClassPropertyMixin.applyValues(self, evt)

    def ruleOrRegex(self, limit=None):
        """Return the rule if it exists else return the regex.
        limit limits the number of characters returned.
        """
        value = self.rule if self.rule else self.regex
        if not value and self.example:
            value = self.example
        if limit: value = value[:limit]
        return value


    def match(self, evt, device):
        """
        Match an event message against our regex.

        @parameter evt: event to match in our mapping
        @type evt: dictionary
        @parameter device: device
        @type device: DMD object
        @return: boolean
        @rtype: boolean
        """
        value = False
        log.debug("match on:%s", self.getPrimaryDmdId())
        if self.rule:
            try:
                log.debug("eval rule:%s", self.rule)
                value = eval(self.rule, {'evt':evt, 'dev':device, 'device': device})
            except Exception as e:
                logging.warn("EventClassInst: %s rule failure: %s",
                            self.getDmdKey(), e)
        else:
            try:
                log.debug("regex='%s' message='%s'", self.regex, evt.message)
                value = re.search(self.regex, evt.message, re.I)
            except sre_constants.error: pass
        return value


    def testRegexStyle(self):
        """Test our regex using the example event string.
        """
        if self.example:
            try:
                value = re.search(self.regex, self.example, re.I)
                if not value: return "color:#FF0000;"
            except sre_constants.error:
                return "color:#FF0000;"


    def testRuleStyle(self):
        """Test our rule by compiling it.
        """
        try:
            if self.rule:
                compile(self.rule, "<string>", "eval")
        except Exception:
            return "color:#FF0000;"


    def sameKey(self):
        """Return a list of all mappings with the same eventClassKey.
        """
        return [ i for i in self.eventClass().find(self.eventClassKey) \
            if i.eventClassKey == self.eventClassKey ]


    security.declareProtected('Manage DMD', 'manage_resequence')
    def manage_resequence(self, seqmap, seqid, REQUEST=None):
        """
        Reorder the sequence of eventClassMappings with the same key.
        """
        for num, path in zip(seqmap, seqid):
            self.unrestrictedTraverse(urllib.unquote(path)).sequence = int(num)
        # second pass take out any holes
        for i, map in enumerate(self.sameKey()):
            map.sequence = i
        if REQUEST:
            audit('UI.EventClassMapping.Resequence', self.id, sequence=seqmap)
            return self.callZenScreen(REQUEST)


    security.declareProtected('Manage DMD', 'manage_editEventClassInst')
    def manage_editEventClassInst(self, name='', eventClassKey='',
                                regex='', rule='', example='',
                                transform='',
                                explanation='', resolution='', REQUEST=None):
        """Edit an EventClassInst from a web page."""

        #save arguments for audit logging
        values = locals()

        oldValues = {
            'name':getDisplayName(self),
            'eventClassKey':self.eventClassKey,
            'regex':self.regex,
            'rule':self.rule,
            'example':self.example,
            'transform':self.transform,
            'explanation':self.explanation,
            'resolution':self.resolution,
        }
        
        redirect = self.rename(name)
        if eventClassKey and self.eventClassKey != eventClassKey:
            self.unindex_object()
            self.sequence = self.eventClass().nextSequenceNumber(eventClassKey)
            self.eventClassKey = eventClassKey
            self.index_object()
        self.regex = regex
        self.rule = rule
        self.example = example
        self.transform = transform
        self.explanation = explanation
        self.resolution = resolution
        if REQUEST:
            audit('UI.EventClassMapping.Edit', self, data_=values, oldData_=oldValues, skipFields_=['self','REQUEST'])
            messaging.IMessageSender(self).sendToBrowser(
                'Saved', SaveMessage())
            return self.callZenScreen(REQUEST, redirect)


InitializeClass(EventClassInst)

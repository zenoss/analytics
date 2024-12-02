class ExamplePreEventPlugin(object):
    def apply(self, eventProxy, dmd):
        event = eventProxy._zepRawEvent.event

        # Do something to the event. Any changes made to the event object will
        # be saved to it. You should not return anything from this method.
        event.summary = 'ExamplePreEventPlugin changed the summary'


class ExamplePostEventPlugin(object):
    def apply(self, eventProxy, dmd):
        event = eventProxy._zepRawEvent.event

        # Do something to the event. Any changes made to the event object will
        # be saved to it. You should not return anything from this method.
        event.summary = 'ExamplePostEventPlugin changed the summary'

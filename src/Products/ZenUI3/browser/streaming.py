##############################################################################
#
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import cgi
import logging
import traceback

from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from Products.ZenUtils.Utils import is_browser_connection_open

log = logging.getLogger("zen.streaming")

LINE = """
<div class="streaming-line %(lineclass)s">%(data)s</div>
"""


class StreamClosed(Exception):
    """
    The browser has closed the connection.
    """


class StreamingView(BrowserView):

    tpl = ViewPageTemplateFile("streaming.pt")

    def __init__(self, context, request):
        super(StreamingView, self).__init__(context, request)
        self._stream = self.request.response
        self._lineno = 0

    def __call__(self):
        # tells nginx that we want to stream this text
        self._stream.setHeader("X-Accel-Buffering", "no")
        self._stream.setHeader("Cache-Control", "no-transform")
        header, footer = str(self.tpl()).split("*****CONTENT_TOKEN*****")
        self._stream.write(header)
        try:
            try:
                self.stream()
            except StreamClosed:
                return
            except Exception:
                self.write("Exception while performing command: <br />")
                self.write("<pre>%s</pre>" % (traceback.format_exc()))
        finally:
            self._stream.write(footer)
            self._stream.flush()
            self.request.close()

    def write(self, data=""):
        data = cgi.escape(data)
        log.info("streaming data %s", data)
        if not is_browser_connection_open(self.request):
            raise StreamClosed("The browser has closed the connection.")
        html = LINE % {
            "lineclass": self._lineno % 2 and "odd" or "even",
            "data": data,
        }
        self._stream.write(html)
        self._lineno += 1
        # fill up the buffer so it is more stream-y
        self._stream.write(" " * 1024)


class TestStream(StreamingView):
    def stream(self):
        import time

        for i in range(100):
            self.write(i)
            time.sleep(0.5)

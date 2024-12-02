##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import print_function

import subprocess
import sys
import urllib2

from email.mime.application import MIMEApplication
from email.MIMEMultipart import MIMEMultipart
from HTMLParser import HTMLParser
from urlparse import urlparse, urlunparse, parse_qsl, urlsplit, urlunsplit

from Products.ZenUtils import Utils
from Products.ZenUtils.ZenScriptBase import ZenScriptBase

gValidReportFileTypes = ["PDF", "PNG", "JPG", "GIF"]


def sibling(url, path):
    parts = list(urlparse(url))
    parts[2] = "/".join(parts[2].split("/")[:-1] + [path])
    return urlunparse(parts[0:3] + ["", "", ""])


class Page(HTMLParser):
    """Turn an html page into a mime-encoded multi-part email.
    Turn the <title> into the subject and keep only the text of the
    content pane.  Url references are turned into absolute references,
    and images are sent with the page."""

    def __init__(self, user, passwd):
        HTMLParser.__init__(self)
        self.user = user
        self.passwd = passwd

    def generateScreenShot(
        self, url, reportFileName, ignoreSslErrors, enableDebug
    ):
        command = [
            "/opt/zenoss/bin/phantomjs",
            "/opt/zenoss/bin/rasterize.js",
            url,
            self.user,
            self.passwd,
            reportFileName,
        ]
        if ignoreSslErrors:
            # insert after "/opt/zenoss/bin/phantomjs"
            command.insert(1, "--ignore-ssl-errors=yes")
            command.insert(2, "--ssl-protocol=any")
        if enableDebug:
            # insert after "/opt/zenoss/bin/phantomjs"
            command.insert(1, "--debug=true")

        print("Running: %s" % " ".join(command))
        phanomjsProcess = subprocess.Popen(command)  # noqa: S603
        phanomjsProcessRC = phanomjsProcess.wait()
        if phanomjsProcessRC:
            sys.stderr.write(
                " ##### ERROR: phantomjs process return code: %s \n"
                % phanomjsProcessRC
            )
            sys.exit(phanomjsProcessRC)
        else:
            print("file created: %s" % reportFileName)

    def mail(self, reportFileName):
        msg = MIMEMultipart("related")
        msg.preamble = "This is a multi-part message in MIME format"

        # Attaching PDF screenshot
        part = MIMEApplication(open(reportFileName, "rb").read())
        part.add_header(
            "Content-Disposition",
            "attachment",
            filename=reportFileName.split("/")[-1],
        )
        msg.attach(part)

        return msg


class ReportMail(ZenScriptBase):
    def run(self):
        "Fetch a report by URL and post as a mime encoded email"
        self.connect()
        o = self.options
        if not o.passwd and not o.url:
            sys.stderr.write("No zenoss password or url provided\n")
            sys.exit(1)
        try:
            user = self.dmd.ZenUsers._getOb(o.user)
        except AttributeError:
            sys.stderr.write("Unknown user %s\n" % o.user)
            sys.exit(1)

        if not o.addresses and user.email:
            o.addresses = [user.email]
        if not o.addresses:
            sys.stderr.write("No address for user %s\n" % o.user)
            sys.exit(1)
        page = Page(o.user, o.passwd)
        url = self.mangleUrl(o.url)
        ignoreSslErrors = o.ignoreSslErrors
        enableDebug = o.enableDebug
        reportFileType = self.determineFileFormat(o.reportFileType)
        reportFileName = "{}.{}".format(o.outputFilePath, reportFileType)
        page.generateScreenShot(
            url, reportFileName, ignoreSslErrors, enableDebug
        )
        msg = page.mail(reportFileName)

        # we aren't actually parsing any HTML so rely on the last "segment"
        # of the URL for the subject if one is not provided
        title = urllib2.unquote(url.split("/")[-1].split("?")[0])
        if o.subject:
            msg["Subject"] = o.subject
        elif title:
            msg["Subject"] = title
        else:
            msg["Subject"] = "Zenoss Report"
        msg["From"] = o.fromAddress
        msg["To"] = ", ".join(o.addresses)

        result, errorMsg = Utils.sendEmail(
            msg,
            self.dmd.smtpHost,
            self.dmd.smtpPort,
            self.dmd.smtpUseTLS,
            self.dmd.smtpUser,
            self.dmd.smtpPass,
        )

        if result:
            print("sent email: %s to:%s" % (msg.as_string(), o.addresses))
        else:
            sys.stderr.write(
                "failed to send email to %s: %s %s\n"
                % (o.addresses, msg.as_string(), errorMsg)
            )
            sys.exit(1)

        sys.exit(0)

    def determineFileFormat(self, reportFileType):
        if reportFileType in gValidReportFileTypes:
            return reportFileType.lower()

        sys.stderr.write(
            "Invalid file type: %s (creating a %s)\n"
            % (reportFileType, gValidReportFileTypes[0])
        )
        return gValidReportFileTypes[0].lower()  # create a pdf

    def mangleUrl(self, url):
        # remove path if exists
        if url.find("/zport/dmd/reports#reporttree:") != -1:
            urlSplit = url.split("/zport/dmd/reports#reporttree:")
            url = urlSplit[0] + urlSplit[1].replace(".", "/")
        parsed = urlsplit(url)
        q_params = dict(parse_qsl(parsed.query))
        # remove a cache buster query param
        q_params.pop("_dc", None)
        q_params["adapt"] = "false"
        url = urlunsplit(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                "&".join(["=".join(entry) for entry in q_params.items()]),
                parsed.fragment,
            )
        )

        return url

    def buildOptions(self):
        ZenScriptBase.buildOptions(self)
        self.parser.add_option(
            "--url",
            "-u",
            dest="url",
            default=None,
            help="URL of report to send",
        )
        self.parser.add_option(
            "--reportFileType",
            "-r",
            dest="reportFileType",
            default="PDF",
            help="report file type (%s)" % "|".join(gValidReportFileTypes),
        )
        self.parser.add_option(
            "--outputFilePath",
            "-o",
            dest="outputFilePath",
            default="/tmp/report_screenshot",  # noqa: S108
            help="Path for generated report. For example, "
            "/tmp/report_screenshot",
        )
        self.parser.add_option(
            "--user",
            "-U",
            dest="user",
            default="admin",
            help="User to log into Zenoss",
        )
        self.parser.add_option(
            "--passwd", "-p", dest="passwd", help="Password to log into Zenoss"
        )
        self.parser.add_option(
            "--address",
            "-a",
            dest="addresses",
            default=[],
            action="append",
            help="Email address destination "
            "(may be given more than once).  Default value"
            "comes from the user's profile.",
        )
        self.parser.add_option(
            "--subject",
            "-s",
            dest="subject",
            default="",
            help="Subject line for email message."
            "Default value is the title of the html page.",
        )
        self.parser.add_option(
            "--from",
            "-f",
            dest="fromAddress",
            default="zenoss@localhost",
            help="Origination address",
        )
        self.parser.add_option(
            "--debug",
            "-d",
            dest="enableDebug",
            action="store_true",
            help="Enable debug mode",
        )
        self.parser.add_option(
            "--ignore-ssl-errors",
            "-i",
            dest="ignoreSslErrors",
            action="store_true",
            help="Ignore SSL errors",
        )


def main():
    ReportMail().run()

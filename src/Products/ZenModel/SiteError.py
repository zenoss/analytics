##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


__doc__="""SiteError

SiteError consolidates code used to handle and report site errors.
"""
import smtplib
import re
import cgi # for cgi.escape()

class SiteError:

    SMTP_HOST = 'mail.zenoss.com'
    ERRORS_ADDRESS = 'errors@zenoss.com'

    def cleanUrl(cls, errorUrl):
        ''' Strip protocol and domain from the url
        '''
        stripDomain = False
        if errorUrl.startswith('http://'):
            errorUrl = errorUrl[len('http://'):]
            stripDomain = True
        elif errorUrl.startswith('https://'):
            errorUrl = errorUrl[len('https://'):]
            stripDomain = True
        if stripDomain and '/' in errorUrl:
            errorUrl = errorUrl[errorUrl.find('/'):]
        return errorUrl
    cleanUrl = classmethod(cleanUrl)


    def createEmailHeader(cls, fromAddress, toAddress, subject):
        ''' Create the snmp header for an error email
        '''
        header = 'To: %s\nFrom: %s\nSubject: %s\n' % (
                    toAddress, fromAddress, subject)
        return header
    createEmailHeader = classmethod(createEmailHeader)


    def createReport(cls, errorType, errorValue, errorTrace, errorUrl,
                        versionShort,
                        inHtml=True, contactName=None, contactEmail=None, 
                        comments=None):
        ''' Produce a summary of the given error details suitable for use
        in an error email (inHtml=false) or on a page (inHtml=true)
        '''
        def StripTags(s):
            ''' Strip html tags from string
            '''
            return re.sub('<[^>]*>', '', s)

        # If not inHtml then strip html tags from the errorTrace
        if inHtml:
            linebreak = '<br />\n'
            contactName = cgi.escape(contactName)
            contactEmail = cgi.escape(contactEmail)
            comments = cgi.escape(comments)
        else:
            linebreak = '\n'
            errorType = StripTags(errorType)
            errorValue = StripTags(errorValue)
            errorTrace = StripTags(errorTrace)
            errorTrace = re.sub('\r\n\r\n', '\r\n', errorTrace)
        msg = linebreak.join(['Type: %s' % errorType,
                                'Value: %s' % errorValue,
                                'URL: %s' % cls.cleanUrl(errorUrl),
                                'Version: %s' % versionShort,
                                '%s' % errorTrace,
                                'Contact name: %s' % (contactName or ''),
                                'Email address: %s' % (contactEmail or ''),
                                'Comments: %s' % (comments or '')])
        return msg
    createReport = classmethod(createReport)


    def sendErrorEmail(self, errorType, errorValue, errorTrace, errorUrl,
                        versionShort,
                        contactName=None, contactEmail=None, comments=None,
                        smtphost=None, smtpport=25, usetls=False, usr='', 
                        pwd=''):
        ''' Attempt to send an email to the zenoss errors email address
        with details of this error.
        Returns true if mail was sent, false otherwise.
        '''
        import socket
        fqdn = socket.getfqdn()
        fromAddress = 'errors@%s' % fqdn
        cleanUrl = self.cleanUrl(errorUrl)
        subject = '%s: %s (%s)' % (errorType, errorValue[:15], cleanUrl)
        header = self.createEmailHeader(
                    fromAddress, self.ERRORS_ADDRESS, subject)
        body = self.createReport(errorType, errorValue, errorTrace, cleanUrl,
                                versionShort,
                                0, contactName, contactEmail, comments)
        mailSent = False

        # Log in to the server using user's smtp or fall back to mail.zenoss.com
        if not smtphost:
            smtphost = self.SMTP_HOST
        server = smtplib.SMTP(smtphost, smtpport)
        if usetls:
            server.ehlo()
            server.starttls()
            server.ehlo()
        if usr: server.login(usr, pwd)
        try:
            server.sendmail(fromAddress, self.ERRORS_ADDRESS, 
                            '%s\n\n%s' % (header, body))
            mailSent = True
        finally:
            try: server.quit()
            except Exception: pass
        return mailSent
    sendErrorEmail = classmethod(sendErrorEmail)

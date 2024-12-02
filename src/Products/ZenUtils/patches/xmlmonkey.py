##################################################################
# This is a monkey patch which fixes xml vulnerabilities         #
# https://docs.python.org/2/library/xml.html#xml-vulnerabilities #
# https://jira.zenoss.com/browse/ZEN-15414                       #
################################################################ #

try:
    from defusedxml import xmlrpc
    xmlrpc.monkey_patch()
except ImportError:
    pass

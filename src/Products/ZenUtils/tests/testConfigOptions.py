##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import sys
import logging
import tempfile
import unittest
import logging
from optparse import OptionParser, SUPPRESS_HELP, NO_DEFAULT, OptionValueError
from Products.ZenUtils.CmdBase import CmdBase
from Products.ZenTestCase.BaseTestCase import BaseTestCase
from StringIO import StringIO

"""
Cases for config source:
    defaults
    config file
    command line
"""
class MockCmdBase(CmdBase):
    default_options = {
        'var_logseverity':'ERROR',
        'var_str':'default_string',
        'var_int':200,
    }        
    def buildOptions(self):
        CmdBase.buildOptions(self)
        
        self.parser.add_option(
            '--var-logseverity',
            dest='var_logseverity',
            help='var_logseverity',
            default=self.default_options['var_logseverity'],
            type='loglevel',
        )

        self.parser.add_option(
            '--var-str',
            dest='var_str',
            help='var_str',
            default=self.default_options['var_str'],
            type='str',
        )

        self.parser.add_option(
            '--var-int',
            dest='var_int',
            help='var_int',
            default=self.default_options['var_int'],
            type='int',
        )
        
class TestConfigOptions(BaseTestCase):
    """
    Test loading config options for CmdBase from conf files, command line args,
    and defaults defined in OptParse options.
    """
    
    # Test three different types of config options. Testing strings for basic
    # functionality. Testing ints ensures that OptParse interprets it's 'type'
    # parameter correctly even when given a string (OptParse actually coerces).
    # Testing logseverity because it is a complex custom type and new.
    example_cmds = {
        'var-str':'cmd_string',
        'var-int':100001,
        'var-logseverity':'CRITical',
    }
    example_conf = {
        'var-str':'conf_string',
        'var-int':9444449,
        'var-logseverity':'10', # debug level
    }
    
    def __init__(self, *args, **kwargs):
        super(TestConfigOptions, self).__init__(*args, **kwargs)
        self.original_args = list(sys.argv)
    
    def _get_args(self, d):
        argv = list(self.original_args)
        for k, v in d.items():
            argv.append('--%s' % k)
            argv.append(str(v))
        return argv
                
    def afterSetUp(self):
        super(TestConfigOptions, self).afterSetUp()
        
        # test command line args
        args = self._get_args(self.example_cmds)
        self.cmd_cmdbase = MockCmdBase(args=args)
        
        
        # test conf files
        conf_file = tempfile.NamedTemporaryFile()
        with conf_file as f:
            f.writelines(['%s %s\n' % (k, v) for k, v in self.example_conf.items()])
            f.flush()
            
            # pass the filename as a parameter. all daemons are called with bash
            # scripts that pass '--configfile' as a parameter.
            configfile_conf = {'configfile':f.name}
            args = self._get_args(configfile_conf)
            self.conf_cmdbase = MockCmdBase(args=args)
        
        # test defaults
        args = self._get_args({})
        self.default_cmdbase = MockCmdBase(args=args)
        
        
        # test combination of everything
        # remove the 'var_int' param so that a default can be provided.
        partial_conf = dict(self.example_conf)
        del  partial_conf['var-int']
        
        conf_file = tempfile.NamedTemporaryFile()
        with conf_file as f:
            f.writelines(['%s %s\n' % (k, v) for k, v in partial_conf.items()])
            f.flush()
            
            # let var_str be passed in
            # let var_logseverity be from config file
            # let var_int be from defaults
            args = {
                'var-str':self.example_cmds['var-str'],
                'configfile': f.name
            }
            args = self._get_args(args)
            self.combined_cmdbase = MockCmdBase(args=args)
            
    def testCmdConfigOptions(self):
        src = self.example_cmds
        opts = self.cmd_cmdbase.options
        
        self.assertTrue(hasattr(opts, 'var_str'))
        self.assertEquals(src['var-str'], opts.var_str)
        
        self.assertTrue(hasattr(opts, 'var_int'))
        self.assertEquals(src['var-int'], opts.var_int)
        
        self.assertTrue(hasattr(opts, 'var_logseverity'))
        self.assertEquals(logging.CRITICAL, opts.var_logseverity)
    
    def testFileConfigOptions(self):
        src = self.example_conf
        opts = self.conf_cmdbase.options

        self.assertTrue(hasattr(opts, 'var_str'))
        self.assertEquals(src['var-str'], opts.var_str)
        
        self.assertTrue(hasattr(opts, 'var_int'))
        self.assertEquals(src['var-int'], opts.var_int)
        
        self.assertTrue(hasattr(opts, 'var_logseverity'))
        self.assertEquals(logging.DEBUG, opts.var_logseverity)
    
    def testDefaultConfigOptions(self):
        src = self.default_cmdbase.default_options
        opts = self.default_cmdbase.options
        
        self.assertTrue(hasattr(opts, 'var_str'))
        self.assertEquals(src['var_str'], opts.var_str)
        
        self.assertTrue(hasattr(opts, 'var_int'))
        self.assertEquals(src['var_int'], opts.var_int)
        
        self.assertTrue(hasattr(opts, 'var_logseverity'))
        self.assertEquals(logging.ERROR, opts.var_logseverity)
    
    def testCombinedConfigOptions(self):
        """
        Test parameters collected from all sources: command line, conf file, defaults.
        # let var_str be passed in
        # let var_logseverity be from config file
        # let var_int be from defaults
        """
        opts = self.combined_cmdbase.options
        
        cmd_str = self.example_cmds['var-str']
        conf_logseverity = logging.DEBUG
        default_int = self.default_cmdbase.default_options['var_int']
        
        self.assertTrue(hasattr(opts, 'var_str'))
        self.assertEquals(cmd_str, opts.var_str)
        
        self.assertTrue(hasattr(opts, 'var_logseverity'))
        self.assertEquals(conf_logseverity, opts.var_logseverity)
        
        self.assertTrue(hasattr(opts, 'var_int'))
        self.assertEquals(default_int, opts.var_int)
        
def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestConfigOptions))
    return suite

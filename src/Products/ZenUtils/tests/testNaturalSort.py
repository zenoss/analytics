#!/usr/bin/env python

from Products.ZenUtils.NaturalSort import natural_compare
from Products.ZenTestCase.BaseTestCase import BaseTestCase

class SortTestCase(BaseTestCase):
    def cases( self, *candidates):
        for candidate in candidates:
            self.sortedEquals( *candidate)

    def sortedEquals(self, candidate, expected, message=None):
        sorted_candidated = sorted( candidate, cmp=natural_compare)
        self.assertEquals( sorted_candidated, expected, message)

class TestDifferentValueTypes(SortTestCase):
    def test(self):
        self.cases( 
            ( ['a',1], [1, 'a'], 'number always comes first'),
            ( ['1',1], ['1', 1], 'number vs. numberic string should remain unchanged'),
            ( ['1',1], ['1', 1], 'passing numeric string vs number')
        )
class TestVersionNumberStrings(SortTestCase):
    def test(self):
        self.cases(
            ( ['1.0.2','1.0.1','1.0.0','1.0.9'], ['1.0.0','1.0.1','1.0.2','1.0.9'], 'close version numbers'),
            ( ['1.0.03','1.0.003','1.0.002','1.0.0001'], ['1.0.0001','1.0.002','1.0.003','1.0.03'], 'multi-digit branch release'),
            ( ['1.1beta','1.1.2alpha3','1.0.2alpha3','1.0.2alpha1','1.0.1alpha4','2.1.2','2.1.1'],
              ['1.0.1alpha4','1.0.2alpha1','1.0.2alpha3','1.1.2alpha3','1.1beta','2.1.1','2.1.2'], 'close version numbers'),
            ( ['myrelease-1.1.3','myrelease-1.2.3','myrelease-1.1.4','myrelease-1.1.1','myrelease-1.0.5'],
              ['myrelease-1.0.5','myrelease-1.1.1','myrelease-1.1.3','myrelease-1.1.4','myrelease-1.2.3'], 'string first'),
        )

class TestNumerics(SortTestCase):
    def test(self):
        self.cases(
            ( ['10',9,2,'1','4'], ['1',2,'4',9,'10'], 'string vs number'),
            ( ['0001','002','001'], ['0001','001','002'], '0 left-padded numbers'),
            ( [2,1,'1','0001','002','02','001'], ['0001','001','002','02',1,'1',2], '0 left-padded numbers and regular numbers'),
            ( ['10.0401',10.022,10.042,'10.021999'], ['10.021999',10.022,'10.0401',10.042], 'decimal string vs decimal, different precision'),
            ( ['10.04',10.02,10.03,'10.01'], ['10.01',10.02,10.03,'10.04'], 'decimal string vs decimal, same precision'),
            ( ['10.04f','10.039F','10.038d','10.037D'], ['10.037D','10.038d','10.039F','10.04f'], 'float/decimal with \'F\' or \'D\' notation'),
            ( ['10.004Z','10.039T','10.038ooo','10.037g'], ['10.004Z','10.037g','10.038ooo','10.039T'], 'not foat/decimal notation'),
            ( ['1.528535047e5','1.528535047e7','1.528535047e3'], ['1.528535047e3','1.528535047e5','1.528535047e7'], 'scientific notation'),
            ( ['-1','-2','4','-3','0','-5'], ['-5','-3','-2','-1','0','4'], 'negative numbers as strings'),
            ( [-1,'-2',4,-3,'0','-5'], ['-5',-3,'-2',-1,'0',4], 'negative numbers as strings - mixed input type, string + numeric'),
            ( [-2.01,-2.1,4.144,4.1,-2.001,-5], [-5,-2.1,-2.01,-2.001,4.1,4.144], 'negative floats - all numeric'),
        )

class TestIPAddresses(SortTestCase):
    def test(self):
        self.cases((
            [ '192.168.0.100', '192.168.0.1', '192.168.1.1', '192.168.0.250', '192.168.1.123', '10.0.0.2', '10.0.0.1' ],
            [ '10.0.0.1', '10.0.0.2', '192.168.0.1', '192.168.0.100', '192.168.0.250', '192.168.1.1', '192.168.1.123' ]
        ))

class TestFileNames(SortTestCase):
    def test(self):
        self.cases(
            ( ['img12.png','img10.png','img2.png','img1.png'],
              ['img1.png','img2.png','img10.png','img12.png'],
              'simple image filenames'),
            ( ['car.mov','01alpha.sgi','001alpha.sgi','my.string_41299.tif','organic2.0001.sgi'],
              ['001alpha.sgi','01alpha.sgi','car.mov','my.string_41299.tif','organic2.0001.sgi'],
              'complex filenames'),
            ( [
                './system/kernel/js/01_ui.core.js',
                './system/kernel/js/00_jquery-1.3.2.js',
                './system/kernel/js/02_my.desktop.js'
              ],[
                './system/kernel/js/00_jquery-1.3.2.js',
                './system/kernel/js/01_ui.core.js',
                './system/kernel/js/02_my.desktop.js'
              ], 'unix filenames'),
        )

class TestSpacesAsFirstCharacter(SortTestCase):
    def test(self):
        self.cases(
            (['alpha',' 1',' 3',' 2',0], [0,' 1',' 2',' 3','alpha'])
        )

class TestEmptyStringsAndSpaceCharacter(SortTestCase):
    def test(self):
        self.cases(
            ( ['10023','999','',2,5.663,5.6629], [2,5.6629,5.663,'999','10023','']),
            ( [0,'0',''], [0,'0',''])
        )

class TestHex(SortTestCase):
    def test(self):
        self.cases(
            ( [ '0xA','0x9','0x99' ], [ '0x9','0xA','0x99' ],'real hex numbers'),
            ( [ '0xZZ','0xVVV','0xVEV','0xUU' ], [ '0xUU','0xVEV','0xVVV','0xZZ' ],'fake hex numbers'),
        )

class TestUnicode(SortTestCase):
    def test(self):
        self.cases(
            ([ '\u0044', '\u0055', '\u0054', '\u0043'],[ '\u0043', '\u0044', '\u0054', '\u0055' ],'basic latin')
        )

class TestContributedTestCases(SortTestCase):
    def test(self):
        self.cases(
            ([
                'T78','U17','U10','U12',
                'U14','745','U7','01',
                '485','S16','S2','S22',
                '1081','S25','1055',
                '779','776','771','44',
                '4','87','1091','42',
                '480','952','951','756',
                '1000','824','770','666',
                '633','619','1','991',
                '77H','PIER-7','47',
                '29','9','77L','433'
                ], [
                '01', '1', '4','9','29',
                '42','44','47','77H',
                '77L','87','433','480',
                '485','619','633','666',
                '745','756','770','771',
                '776','779','824','951',
                '952','991','1000','1055',
                '1081','1091', 'PIER-7',
                'S2','S16','S22','S25',
                'T78','U7','U10','U12',
                'U14','U17'
                ], 'contributed by Bob Zeiner'),
            (
                [
                'FSI stop, Position: 5',
                'Mail Group stop, Position: 5',
                'Mail Group stop, Position: 5',
                'FSI stop, Position: 6',
                'FSI stop, Position: 6',
                'Newsstand stop, Position: 4',
                'Newsstand stop, Position: 4',
                'FSI stop, Position: 5'
                ],[
                'FSI stop, Position: 5',
                'FSI stop, Position: 5',
                'FSI stop, Position: 6',
                'FSI stop, Position: 6',
                'Mail Group stop, Position: 5',
                'Mail Group stop, Position: 5',
                'Newsstand stop, Position: 4',
                'Newsstand stop, Position: 4'
                ],'contributed by Scott'),
            ( [2, 10, 1, 'azd', None, 'asd'], [1, 2, 10, 'asd', 'azd', None], 'issue #2 - undefined support - jarvinen pekka'),
            ( [None, None, None, 1, None], [1, None, None, None, None], 'issue #2 - undefined support - jarvinen pekka'),
            ( ['-1', '-2', '4', '-3', '0', '-5'], ['-5', '-3', '-2', '-1', '0', '4'], 'issue #3 - invalid numeric string sorting - guilermo.dev'),
            #naturalSort.insensitive = true;
            #wrapTest(
            #    ['9','11','22','99','A','aaaa','bbbb','Aaaa','aAaa','aa','AA','Aa','aA','BB','bB','aaA','AaA','aaa'],
            #    ['9', '11', '22', '99', 'A', 'aa', 'AA', 'Aa', 'aA', 'aaA', 'AaA', 'aaa', 'aaaa', 'Aaaa', 'aAaa', 'BB', 'bB', 'bbbb'],
            #    'issue #5 - invalid sort order - Howie Schecter');
            #naturalSort.insensitive = false;
            #wrapTest(
            #    ['9','11','22','99','A','aaaa','bbbb','Aaaa','aAaa','aa','AA','Aa','aA','BB','bB','aaA','AaA','aaa'],
            #    ['9', '11', '22', '99', 'A', 'AA', 'Aa', 'AaA', 'Aaaa', 'BB', 'aA', 'aAaa', 'aa', 'aaA', 'aaa', 'aaaa', 'bB', 'bbbb'],
            #    'issue #5 - invalid sort order - Howie Schecter');
        )

class TestZenossExamples(SortTestCase): 
    def test(self):
        self.cases( (
            ['Gi1/1', 'Gi1/10', 'Gi1/11', 'Gi1/2', 'Gi1/20', 'Gi1/3'],
            ['Gi1/1', 'Gi1/2', 'Gi1/3', 'Gi1/10','Gi1/11', 'Gi1/20'], 'Cisco'
        ) )

def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestDifferentValueTypes))
    suite.addTest(makeSuite(TestVersionNumberStrings))
    suite.addTest(makeSuite(TestIPAddresses))
    suite.addTest(makeSuite(TestNumerics))
    suite.addTest(makeSuite(TestFileNames))
    suite.addTest(makeSuite(TestSpacesAsFirstCharacter))
    suite.addTest(makeSuite(TestEmptyStringsAndSpaceCharacter))
    suite.addTest(makeSuite(TestUnicode))
    suite.addTest(makeSuite(TestHex))
    suite.addTest(makeSuite(TestContributedTestCases))
    suite.addTest(makeSuite(TestZenossExamples))
    return suite

#/usr/bin/env python3

"""Unit testing suite for RedCLAP library.
"""

import shutil
import unittest
import warnings

import redclap as clap


#   enable debugging output which is basically huge number of print() calls
DEBUG = False


class FormatterTests(unittest.TestCase):
    def testSplittingEqualSignedOptions(self):
        argv = ['--foo=bar', '--', '--baz=bax']
        f = clap.formatter.Formatter(argv)
        f._splitequal()
        if DEBUG: print('\'{0}\' -> \'{1}\''.format(' '.join(argv), ' '.join(f.formatted)))
        self.assertEqual(list(f), ['--foo', 'bar', '--', '--baz=bax'])

    def testSplittingConnectedShortOptions(self):
        argv = ['-abc', '--', '-def']
        f = clap.formatter.Formatter(argv)
        f._splitshorts()
        if DEBUG: print('\'{0}\' -> \'{1}\''.format(' '.join(argv), ' '.join(f.formatted)))
        self.assertEqual(list(f), ['-a', '-b', '-c', '--', '-def'])

    def testGeneralFormating(self):
        argv = ['-abc', 'eggs', '--bar', '--ham', 'good', '--food=spam', '--', '--bax=bay']
        f = clap.formatter.Formatter(argv)
        f.format()
        if DEBUG: print('\'{0}\' -> \'{1}\''.format(' '.join(argv), ' '.join(f.formatted)))
        self.assertEqual(list(f), ['-a', '-b', '-c', 'eggs', '--bar', '--ham', 'good', '--food', 'spam', '--', '--bax=bay'])


class OptionTests(unittest.TestCase):
    def testOnlyShortName(self):
        o = clap.option.Option(short='f')
        self.assertEqual(o['short'], '-f')
        self.assertEqual(o['long'], '')
        self.assertEqual(str(o), '-f')

    def testOnlyLongName(self):
        o = clap.option.Option(long='foo')
        self.assertEqual(o['short'], '')
        self.assertEqual(o['long'], '--foo')
        self.assertEqual(str(o), '--foo')

    def testInvalidLongName(self):
        tests = ['a', 'A', '0', '-']
        for o in tests:
            if DEBUG: print(o)
            self.assertRaises(TypeError, clap.option.Option, long=o)

    def testBothNames(self):
        o = clap.option.Option(short='f', long='foo')
        self.assertEqual(o['short'], '-f')
        self.assertEqual(o['long'], '--foo')
        self.assertEqual(str(o), '--foo')

    def testNoName(self):
        self.assertRaises(TypeError, clap.option.Option)

    def testParams(self):
        o = clap.option.Option(short='f', arguments=[int])
        self.assertEqual([int], o.params())
        p = clap.option.Option(short='f')
        self.assertEqual([], p.params())

    def testMatching(self):
        o = clap.option.Option(short='f', long='foo')
        self.assertEqual(True, o.match('-f'))
        self.assertEqual(True, o.match('--foo'))

    def testAliases(self):
        o = clap.option.Option(short='f', long='foo')
        self.assertEqual('--foo', o.alias('-f'))
        self.assertEqual('-f', o.alias('--foo'))
        self.assertRaises(NameError, o.alias, '--bar')


class ModeTests(unittest.TestCase):
    def testAddingLocalOptions(self):
        mode = clap.mode.RedMode()
        mode.addLocalOption(clap.option.Option(short='a', long='all'))
        self.assertTrue(mode.accepts('-a'))
        self.assertTrue(mode.accepts('--all'))
        self.assertEqual('-a', mode.alias('--all'))
        self.assertEqual('--all', mode.alias('-a'))

    def testAddingModes(self):
        mode = clap.mode.RedMode()
        mode.addMode('foo', clap.mode.RedMode())
        mode.addMode('bar', clap.mode.RedMode())
        self.assertTrue(mode.hasmode('foo'))
        self.assertTrue(mode.hasmode('bar'))

    def testAddingGlobalOptions(self):
        mode = clap.mode.RedMode()
        mode.addMode('foo', clap.mode.RedMode())
        mode.addMode('bar', clap.mode.RedMode())
        mode.addGlobalOption(clap.option.Option(short='v', long='verbose')).propagate()
        self.assertTrue(mode.accepts('--verbose'))
        self.assertTrue(mode.getmode('foo').accepts('--verbose'))
        self.assertTrue(mode.getmode('bar').accepts('--verbose'))


class RedParserTests(unittest.TestCase):
    def testFeedingArgsToParser(self):
        mode = clap.mode.RedMode()
        parser = clap.parser.Parser(mode)
        args = ['-a', '--foo', 'bar']
        parser.feed(args)
        self.assertEqual(args, parser.getargs())

    def testParsingBareOption(self):
        mode = clap.mode.RedMode()
        mode.addLocalOption(clap.option.Option(short='v', long='verbose'))
        parser = clap.parser.Parser(mode).feed(['--verbose']).parse()
        self.assertTrue('--verbose' in parser)
        self.assertTrue('-v' in parser)
        self.assertEqual(None, parser.get('--verbose'))
        self.assertEqual(None, parser.get('-v'))

    def testParsingBareOptions(self):
        mode = clap.mode.RedMode()
        mode.addLocalOption(clap.option.Option(short='v', long='verbose'))
        mode.addLocalOption(clap.option.Option(short='d', long='debug'))
        parser = clap.parser.Parser(mode).feed(['--verbose', '--debug']).parse()
        self.assertTrue('--verbose' in parser)
        self.assertTrue('-v' in parser)
        self.assertTrue('--debug' in parser)
        self.assertTrue('-d' in parser)
        self.assertEqual(None, parser.get('--verbose'))
        self.assertEqual(None, parser.get('-v'))
        self.assertEqual(None, parser.get('--debug'))
        self.assertEqual(None, parser.get('-d'))

    def testParsingOptionWithOneArgument(self):
        mode = clap.mode.RedMode()
        mode.addLocalOption(clap.option.Option(short='f', long='foo', arguments=['str']))
        parser = clap.parser.Parser(mode).feed(['--foo', 'spam']).parse()
        self.assertTrue('--foo' in parser)
        self.assertEqual(('spam',), parser.get('--foo'))
        self.assertEqual(('spam',), parser.get('-f'))

    def testParsingOptionWithMultipleArguments(self):
        mode = clap.mode.RedMode()
        mode.addLocalOption(clap.option.Option(short='f', long='foo', arguments=['str', 'str']))
        parser = clap.parser.Parser(mode).feed(['--foo', 'spam', 'eggs']).parse()
        self.assertTrue('--foo' in parser)
        self.assertEqual(('spam', 'eggs'), parser.get('--foo'))
        self.assertEqual(('spam', 'eggs'), parser.get('-f'))

    def testParsingStopsOnFirstNonOption(self):
        mode = clap.mode.RedMode()
        mode.addLocalOption(clap.option.Option(short='f', long='foo', arguments=['str', 'str']))
        parser = clap.parser.Parser(mode).feed(['spam', '--foo']).parse()
        self.assertTrue('--foo' not in parser)
        self.assertEqual(['spam', '--foo'], parser.getoperands())

    def testParsingStopsOnBreaker(self):
        mode = clap.mode.RedMode()
        mode.addLocalOption(clap.option.Option(short='f', long='foo', arguments=['str', 'str']))
        parser = clap.parser.Parser(mode).feed(['--', '--foo']).parse()
        self.assertTrue('--foo' not in parser)
        self.assertEqual(['--foo'], parser.getoperands())

    def testParsingShortOptions(self):
        args = ['-a', '-b', '-c', 'd', 'e', 'f']
        mode = clap.mode.RedMode()
        mode.addLocalOption(clap.option.Option(short='a'))
        mode.addLocalOption(clap.option.Option(short='b'))
        mode.addLocalOption(clap.option.Option(short='c'))
        parser = clap.parser.Parser(mode).feed(args).parse()
        self.assertEqual(None, parser.get('-a'))
        self.assertEqual(None, parser.get('-b'))
        self.assertEqual(None, parser.get('-c'))
        self.assertEqual(['d', 'e', 'f'], parser.getoperands())

    def testShortOptionsWithArguments(self):
        args = ['-s', 'eggs', '-i', '42', '-f', '4.2', '--', 'foo']
        mode = clap.mode.RedMode()
        mode.addLocalOption(clap.option.Option(short='s', arguments=[str]))
        mode.addLocalOption(clap.option.Option(short='i', arguments=[int]))
        mode.addLocalOption(clap.option.Option(short='f', arguments=[float]))
        parser = clap.parser.Parser(mode).feed(args).parse()
        self.assertEqual('eggs', parser.get('-s', tuplise=False))
        self.assertEqual(42, parser.get('-i', tuplise=False))
        self.assertEqual(4.2, parser.get('-f', tuplise=False))
        self.assertEqual(['foo'], parser.getoperands())


class RedCheckerTests(unittest.TestCase):
    def testUnrecognizedOptions(self):
        argv = ['--foo', '--bar', '--baz']
        mode = clap.mode.RedMode()
        mode.addLocalOption(clap.option.Option(long='foo'))
        mode.addLocalOption(clap.option.Option(long='bar'))
        parser = clap.parser.Parser(mode).feed(argv)
        checker = clap.checker.RedChecker(parser)
        self.assertRaises(clap.errors.UnrecognizedOptionError, checker._checkunrecognized)

    def testArgumentNotGivenAtTheEnd(self):
        argv = ['--bar', '--foo']
        mode = clap.mode.RedMode()
        mode.addLocalOption(clap.option.Option(long='foo', arguments=['str']))
        mode.addLocalOption(clap.option.Option(long='bar'))
        parser = clap.parser.Parser(mode).feed(argv)
        checker = clap.checker.RedChecker(parser)
        self.assertRaises(clap.errors.MissingArgumentError, checker._checkarguments)

    def testArgumentNotGivenAtTheEndBecauseOfBreaker(self):
        argv = ['--bar', '--foo', '--', 'baz']
        mode = clap.mode.RedMode()
        mode.addLocalOption(clap.option.Option(long='foo', arguments=['str']))
        mode.addLocalOption(clap.option.Option(long='bar'))
        parser = clap.parser.Parser(mode).feed(argv)
        checker = clap.checker.RedChecker(parser)
        self.assertRaises(clap.errors.MissingArgumentError, checker._checkarguments)

    @unittest.skip('due to library being redesigned')
    def testInvalidArgumentType(self):
        argv = ['--bar', '--foo', 'baz']
        parser = clap.base.Base(argv)
        parser.add(long='foo', arguments=[int])
        parser.add(long='bar')
        checker = clap.checker.Checker(parser)
        self.assertRaises(clap.errors.InvalidArgumentTypeError, checker._checkarguments)

    @unittest.skip('due to library being redesigned')
    def testInvalidArgumentTypeWhenMultipleArgumentsAreRequested(self):
        argv = ['--point', '0', 'y']
        parser = clap.base.Base(argv)
        parser.add(long='point', arguments=[int, int])
        checker = clap.checker.Checker(parser)
        self.assertRaises(clap.errors.InvalidArgumentTypeError, checker._checkarguments)

    @unittest.skip('due to library being redesigned')
    def testAnotherOptionGivenAsArgument(self):
        argv = ['--foo', '--bar']
        parser = clap.base.Base(argv)
        parser.add(long='foo', arguments=[int])
        parser.add(long='bar')
        checker = clap.checker.Checker(parser)
        self.assertRaises(clap.errors.MissingArgumentError, checker._checkarguments)

    @unittest.skip('due to library being redesigned')
    def testRequiredOptionNotFound(self):
        argv = ['--bar']
        parser = clap.base.Base(argv)
        parser.add(long='foo', required=True)
        parser.add(long='bar')
        checker = clap.checker.Checker(parser)
        self.assertRaises(clap.errors.RequiredOptionNotFoundError, checker._checkrequired)

    @unittest.skip('due to library being redesigned')
    def testRequiredOptionNotFoundBecauseOfBreaker(self):
        argv = ['--bar', '--', '--foo']
        parser = clap.base.Base(argv)
        parser.add(long='foo', required=True)
        parser.add(long='bar')
        checker = clap.checker.Checker(parser)
        if DEBUG: print(parser._getinput())
        self.assertRaises(clap.errors.RequiredOptionNotFoundError, checker._checkrequired)

    @unittest.skip('due to library being redesigned')
    def testRequiredNotWithAnotherOption(self):
        argv = ['--bar']
        parser = clap.base.Base(argv)
        parser.add(long='foo', required=True, not_with=['--bar'])
        parser.add(short='b', long='bar')
        checker = clap.checker.Checker(parser)
        checker._checkrequired()

    @unittest.skip('due to library being redesigned')
    def testRequiredNotWithAnotherOptionNotFoundBecauseOfBreaker(self):
        argv = ['--baz', '--', '-b']
        parser = clap.base.Base(argv)
        parser.add(long='foo', required=True, not_with=['--bar'])
        parser.add(short='b', long='bar')
        parser.add(long='baz')
        checker = clap.checker.Checker(parser)
        if DEBUG: print(parser._getinput())
        self.assertRaises(clap.errors.RequiredOptionNotFoundError, checker._checkrequired)

    @unittest.skip('due to library being redesigned')
    def testOptionRequiredByAnotherOption(self):
        argv = ['--foo', '--bar', '--baz']
        parser = clap.base.Base(argv)
        parser.add(long='foo', requires=['--bar', '--baz'])
        parser.add(long='bar')
        parser.add(long='baz')
        checker = clap.checker.Checker(parser)
        if DEBUG: print(parser._getinput())
        checker._checkrequires()

    @unittest.skip('due to library being redesigned')
    def testOptionRequiredByAnotherOptionNotFound(self):
        argv = ['--foo', '--bar']
        parser = clap.base.Base(argv)
        parser.add(long='foo', requires=['--bar', '--baz'])
        parser.add(long='bar')
        parser.add(long='baz')
        checker = clap.checker.Checker(parser)
        if DEBUG: print(parser._getinput())
        self.assertRaises(clap.errors.RequiredOptionNotFoundError, checker._checkrequires)

    @unittest.skip('due to library being redesigned')
    def testOptionRequiredByAnotherOptionNotFoundBecauseOfBreaker(self):
        argv = ['--foo', '--bar', '--', '--baz']
        parser = clap.base.Base(argv)
        parser.add(long='foo', requires=['--bar', '--baz'])
        parser.add(long='bar')
        parser.add(long='baz')
        checker = clap.checker.Checker(parser)
        if DEBUG: print(parser._getinput())
        self.assertRaises(clap.errors.RequiredOptionNotFoundError, checker._checkrequires)

    @unittest.skip('due to library being redesigned')
    def testOptionWantedByAnotherOption(self):
        argv_both = ['--bar', '--foo', '--baz']
        argv_only_bar = ['--foo', '--bar', '42']
        argv_only_baz = ['--baz', '--foo']
        parser = clap.base.Base()
        parser.add(long='foo', wants=['--bar', '--baz'])
        parser.add(long='bar', arguments=[int])
        parser.add(long='baz')
        for argv in [argv_both, argv_only_bar, argv_only_baz]:
            parser.feed(argv)
            checker = clap.checker.Checker(parser)
            if DEBUG: print(parser._getinput())
            checker._checkwants()

    @unittest.skip('due to library being redesigned')
    def testOptionNeededByAnotherOptionNotFound(self):
        argv = ['--foo']
        parser = clap.base.Base()
        parser.add(long='foo', wants=['--bar', '--baz'])
        parser.add(long='bar', arguments=[int])
        parser.add(long='baz')
        parser.feed(argv)
        checker = clap.checker.Checker(parser)
        if DEBUG: print(parser._getinput())
        self.assertRaises(clap.errors.WantedOptionNotFoundError, checker._checkwants)

    @unittest.skip('due to library being redesigned')
    def testOptionNeededByAnotherOptionNotFoundBecauseOfBreaker(self):
        argv = ['--foo', '--', '--bar']
        parser = clap.base.Base()
        parser.add(long='foo', wants=['--bar', '--baz'])
        parser.add(long='bar', arguments=[int])
        parser.add(long='baz')
        parser.feed(argv)
        checker = clap.checker.Checker(parser)
        if DEBUG: print(parser._getinput())
        self.assertRaises(clap.errors.WantedOptionNotFoundError, checker._checkwants)

    @unittest.skip('due to library being redesigned')
    def testConflicts(self):
        argv = ['--foo', '--bar']
        parser = clap.base.Base(argv=argv)
        parser.add(long='foo', conflicts=['--bar'])
        parser.add(long='bar')
        checker = clap.checker.Checker(parser)
        if DEBUG: print(parser._getinput())
        self.assertRaises(clap.errors.ConflictingOptionsError, checker._checkconflicts)

    @unittest.skip('due to library being redesigned')
    def testConflictsNotRaisedBecauseOfBreaker(self):
        argv = ['--foo', '--', '--bar']
        parser = clap.base.Base()
        parser.add(long='foo', conflicts=['--bar'])
        parser.add(long='bar')
        parser.feed(argv)
        checker = clap.checker.Checker(parser)
        if DEBUG: print(parser._getinput())
        checker._checkconflicts()


@unittest.skip('due to library being redesigned')
class BaseTests(unittest.TestCase):
    def testAddingNewOption(self):
        base = clap.base.Base([])
        base.add(short='f', long='foo', arguments=[str],
                 required=True, not_with=['-s'],
                 requires=['--bar'], wants=['--baz', '--bax'],
                 conflicts=['--bay'])
        option0 = clap.option.Option(short='f', long='foo',
                                     arguments=[str], required=True, not_with=['-s'],
                                     requires=['--bar'], wants=['--baz', '--bax'],
                                     conflicts=['--bay'])
        option1 = clap.option.Option(short='b', long='bar',
                                     arguments=[int],
                                     wants=['--baz', '--bax'])
        self.assertIn(option0, base._options)
        self.assertNotIn(option1, base._options)

    def testRemovingOption(self):
        base = clap.base.Base([])
        base.add(short='f', long='foo', arguments=[str],
                 required=True, not_with=['-s'],
                 requires=['--bar'], wants=['--baz', '--bax'],
                 conflicts=['--bay'])
        option0 = clap.option.Option(short='f', long='foo',
                                     arguments=[str], required=True, not_with=['-s'],
                                     requires=['--bar'], wants=['--baz', '--bax'],
                                     conflicts=['--bay'])
        option1 = clap.option.Option(short='b', long='bar',
                                     arguments=[int],
                                     wants=['--baz', '--bax'])
        base.add(short='b', long='bar', arguments=[int], wants=['--baz', '--bax'])
        self.assertIn(option0, base._options)
        self.assertIn(option1, base._options)
        base.remove(short='b')
        self.assertIn(option0, base._options)
        self.assertNotIn(option1, base._options)

    def testGettingEmptyInput(self):
        argvs = [   ['--', '--foo', '--bar', 'baz', 'bax'],
                    ['bax', '--foo', '--bar', 'baz'],
                    ['bax', 'foo', 'bar', 'baz'],
                    ]
        base = clap.base.Base()
        base.add(long='foo')
        base.add(long='bar', arguments=[str])
        for argv in argvs:
            base.feed(argv)
            self.assertEqual([], base._getinput())

    def testGettingInput(self):
        argv = ['--foo', '--bar', 'baz', 'bax']
        base = clap.base.Base(argv)
        base.add(long='foo')
        base.add(long='bar', arguments=[str])
        self.assertEqual(['--foo', '--bar', 'baz'], base._getinput())

    def testGettingInputWhenOptionsRequestMultipleArguments(self):
        argv = ['--foo', '--point', '0', '0', '--bar', 'baz']
        base = clap.base.Base(argv)
        base.add(long='foo')
        base.add(long='bar')
        base.add(long='point', arguments=[int, int])
        self.assertEqual(['--foo', '--point', '0', '0', '--bar'], base._getinput())

    def testGettingInputWithBreakerPresent(self):
        argv = ['--foo', '--', '--bar', 'baz', 'bax']
        base = clap.base.Base(argv)
        base.add(long='foo')
        base.add(long='bar', arguments=[str])
        self.assertEqual(['--foo'], base._getinput())

    def testCheckingIfOptionIsInInputUsingString(self):
        argv = ['--foo', '--bar', 'baz']
        base = clap.base.Base(argv)
        base.add(short='f', long='foo')
        base.add(short='b', long='bar', arguments=[str])
        self.assertEqual(True, base._ininput(string='--foo'))
        self.assertEqual(True, base._ininput(string='-b'))

    def testCheckingIfOptionIsInInputUsingOptionObject(self):
        argv = ['-f', '--bar', 'baz']
        base = clap.base.Base(argv)
        foo = clap.option.Option(short='f', long='foo')
        bar = clap.option.Option(short='b', long='bar', arguments=[str])
        base._append(foo)
        base._append(bar)
        self.assertEqual(True, base._ininput(option=foo))
        self.assertEqual(True, base._ininput(option=bar))

    def testCheckingIfOptionIsInInputWithBreaker(self):
        argv = ['--foo', '--', '--bar', 'baz']
        base = clap.base.Base(argv)
        base.add(long='foo')
        base.add(long='bar', arguments=[str])
        self.assertEqual(True, base._ininput(string='--foo'))
        self.assertEqual(False, base._ininput(string='--bar'))

    def testOptionRecognition(self):
        tests = [('-a', True),
                 ('--foo', True),
                 ('--foo=bar', True),
                 ('-abc', True),
                 ('a', False),
                 ('foo', False),
                 ('--a', False),
                 ('-a=foo', False),
                 ('--', False),
                 ('-', False),
                 ]
        for opt, result in tests:
            if DEBUG: print(opt, result)
            self.assertEqual(clap.shared.lookslikeopt(opt), result)


@unittest.skip('due to library being redesigned')
class BuilderTests(unittest.TestCase):
    def testTypeRecognitionOption(self):
        data = {'short': 'p',
                'arguments': [int, int]
                }
        self.assertEqual(True, clap.builder.isoption(data))

    def testTypeRecognitionParser(self):
        data = [ {'short': 'p',
                 'arguments': [int, int]
                 }
                 ]
        self.assertEqual(True, clap.builder.isparser(data))

    def testTypeRecognitionNestedParser(self):
        data = {
                'foo': [
                    {
                        'short': 'p',
                        'arguments': [int, int]
                    }
                    ],
                '__global__': [
                        {
                            'short': 'o',
                            'long': 'output',
                            'arguments': [str]
                        }
                    ]
                }
        self.assertEqual(True, clap.builder.isparser(data))

    def testBuildingSingleParserDefinedAsNestedWithAllOptionsGlobal(self):
        parser = clap.parser.Parser()
        parser.addOption(short='s', long='string', arguments=[str])
        parser.addOption(short='i', long='integer', arguments=[int])
        parser.addOption(short='f', long='float', arguments=[float])
        built = clap.builder.Builder(path='./testfiles/single_parser_defined_as_nested_with_all_opts_global.json').build()
        self.assertEqual(parser.finalize(), built.finalize())

    def testBuildingSingleParserDefinedAsListOfOptions(self):
        parser = clap.parser.Parser()
        parser.addOption(short='s', long='string', arguments=[str])
        parser.addOption(short='i', long='integer', arguments=[int])
        parser.addOption(short='f', long='float', arguments=[float])
        built = clap.builder.Builder(path='./testfiles/single_parser_defined_as_list_of_options.json').build()
        self.assertEqual(parser.finalize().getopts(), built.finalize().getopts())

    def testBuildingMultipleModeParser(self):
        parser = clap.parser.Parser()
        parser.addMode('foo', clap.parser.Parser().addOption(short='f', long='foo'))
        parser.addMode('bar', clap.parser.Parser().addOption(short='b', long='bar'))
        parser.addOption(short='B', long='baz')
        built = clap.builder.Builder(path='./testfiles/multiple_modes_parser.json').build()
        self.assertEqual(sorted(parser.finalize()._modes.keys()), sorted(built.finalize()._modes.keys()))


if __name__ == '__main__':
    unittest.main()
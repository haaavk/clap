#!/usr/bin/env python3


from clap import base, option, errors


"""This module contains Checker() object which is used internaly, by
Parser() to check correctness of input.
"""


class Checker(base.Base):
    """This object is used for checking correctness of input.
    """
    def __init__(self, parser):
        self.argv = parser.argv
        self.options = parser.options

    def _checkunrecognized(self):
        """Checks if input list contains any unrecognized options.
        """
        for i in self._getinput():
            if i == '--': break
            if base.lookslikeopt(i) and not self.accepts(i): raise errors.UnrecognizedOptionError(i)

    def _checkarguments(self):
        """Checks if arguments given to options which require them are valid.
        Raises `MissingArgumentError` when option which requires an argument is last item
        in input list.
        Raises `TypeError` when option is given argument of invalid type.
        Raises `MissingArgumentError` when option which requires an argument is followed by
        another option accepted by this instance of parser.
        **Notice:** if you want to pass option-like argument wrap it in `"` or `'` and
        escape first hyphen or double-escape first hyphen.
        Last check is done only when `deep` argument is True.
        """
        input = self._getinput()
        for i, opt in enumerate(input):
            if i == '--': break
            if base.lookslikeopt(opt) and self.type(opt):
                if i+1 == len(input): raise errors.MissingArgumentError(opt)
                arg = input[i+1]
                try: self.type(opt)(arg)
                except ValueError as e: raise errors.InvalidArgumentTypeError('{0}: {1}'.format(opt, e))
                if base.lookslikeopt(arg) and self.accepts(arg): raise errors.MissingArgumentError(opt)

    def _checkrequired(self):
        """Checks if all required options are present in input list.
        """
        for option in self.options:
            check = option['required']
            for n in option['not_with']:
                if not check: break
                check = not self._ininput(n)
            if not check: continue
            if not self._ininput(str(option)): raise errors.RequiredOptionNotFoundError(option)

    def _checkrequires(self):
        """Check if all options required by other options are present.
        """
        for o in self.options:
            option = str(o)
            if not self._ininput(option): continue
            for n in o['requires']:
                if not self._ininput(option):
                    if option in self._getinput(): needs = option
                    else: needs = self.alias(option)
                    raise errors.RequiredOptionNotFoundError('{0} -> {1}'.format(needs, n))

    def _checkneeds(self):
        """Check needed options.
        """
        for i in self.options:
            option = str(i)
            if not self._ininput(option): continue
            fail = True
            for n in i['needs']:
                if self._ininput(option):
                    fail = False
                    break
            if fail and i['needs']:
                needs = self._variantin(option)
                raise errors.NeededOptionNotFoundError('{0} -> {1}'.format(needs, ', '.join(i['needs'])))

    def _checkconflicts(self):
        """Check for conflicting options.
        """
        for i in self.options:
            option = str(i)
            if i['conflicts'] and self._ininput(option):
                conflicted = self._variantin(option)
                for c in i['conflicts']:
                    conflicting = self._variantin(c)
                    if conflicting: raise errors.ConflictingOptionsError('{0} | {1}'.format(conflicted, conflicting))


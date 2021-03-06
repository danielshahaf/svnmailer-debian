# -*- coding: utf-8 -*-
# pylint: disable-msg = W0613, W0704
#
# Copyright 2004-2006 André Malo or his licensors, as applicable
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Base notifier class

@var EMPTY_TABLE: provides an empty translation table
@type EMPTY_TABLE: C{str}

@var CTRL_CHARS: provides a list of control chars (< ascii 32)
@type CTRL_CHARS: C{str}
"""
__author__    = "André Malo"
__docformat__ = "epytext en"
__all__       = ['BaseNotifier']

# global imports
from svnmailer import util

import string
EMPTY_TABLE = string.maketrans('', '')
CTRL_CHARS = ''.join([
    chr(num) for num in range(32)
    if chr(num) not in "\r\n\t\f"
])
del string


def addFunc(change):
    """ diffable add """
    return change.wasAdded() and not change.wasCopied() and not \
        change.isDirectory()

def delFunc(change):
    """ diffable del """
    return change.wasDeleted() and not change.isDirectory()

def copyFunc(change):
    """ diffable copy """
    return change.wasCopied() and change.hasContentChanges()

def modFunc(change):
    """ diffable modify """
    return change.wasModified() and change.hasContentChanges()

def propFunc(change):
    """ diffable propchange """
    return change.hasPropertyChanges()

def noneFunc(change):
    """ not diffable """
    return False


class BaseNotifier(object):
    """ Base class for notifiers

        Custom notifiers must implement this interface
        (that is just the run method, however).

        Additionally it contains some useful utility methods,
        which can be used.

        @ivar _settings: The settings to use
        @type _settings: C{svnmailer.settings.Settings}

        @ivar _groupset: The groupset to process
        @type _groupset: C{list}

        @ivar _penc_cache: The (path, rev) -> property encoding cache
        @type _penc_cache: C{dict}

        @cvar _diffable_tests: Map C{generate_diffs} list entrys to change
            methods
        @type _diffable_tests: C{tuple}

        @cvar ADD: "add" token
        @type ADD: C{unicode}

        @cvar DELETE: "delete" token
        @type DELETE: C{unicode}

        @cvar COPY: "copy" token
        @type COPY: C{unicode}

        @cvar MODIFY: "modify" token
        @type MODIFY: C{unicode}

        @cvar PROPCHANGE: "propchange" token
        @type PROPCHANGE: C{unicode}

        @cvar NONE: "none" token
        @type NONE: C{unicode}

        @cvar ENC_CONFIG: magic value, meaning that the content encoding should
            be retrieved from the config
        @type ENC_CONFIG: C{str}

        @cvar ENC_PROPERTY: The property name, where encodings could be stored
        @type ENC_PROPERTY: C{str}
    """
    ADD    = u"add"
    DELETE = u"delete"
    COPY   = u"copy"
    MODIFY = u"modify"
    PROPCHANGE = u"propchange"
    NONE   = u"none"

    ENC_CONFIG = "retrieve encoding from config"
    ENC_DEFAULT = "show default encoding"
    ENC_PROPERTY = "svnmailer:content-charset"

    _diffable_tests = (
        (ADD,        addFunc),
        (DELETE,     delFunc),
        (COPY,       copyFunc),
        (MODIFY,     modFunc),
        (PROPCHANGE, propFunc),
        (NONE,       noneFunc),
    )


    def __init__(self, settings, groupset):
        """ Initialization """
        self._settings = settings
        self._groupset = groupset
        self._penc_cache = {}


    def run(self):
        """ Runs the notifier """
        raise NotImplementedError()


    def getAuthor(self):
        """ Returns the author of the revision

            @return: The author or C{None} if there's no author
            @rtype: C{str}
        """
        author = self._settings.runtime.author
        if not author:
            author = self._settings.runtime._repos.getRevisionAuthor(
                self._settings.runtime.revision
            )

        return author


    def getTime(self):
        """ Returns the time of the revision in seconds since epoch

            @return: The time
            @rtype: C{int}
        """
        return self._settings.runtime._repos.getRevisionTime(
            self._settings.runtime.revision
        )


    def getLog(self):
        """ Returns the log entry of the revision

            @return: The log entry
            @rtype: C{str}
        """
        return self._settings.runtime._repos.getRevisionLog(
            self._settings.runtime.revision
        ) or ''


    def getUrl(self, config):
        """ Returns the revision URL

            @return: The URL or C{None}
            @rtype: C{str}
        """
        from svnmailer import browser
        generator = browser.getBrowserUrlGenerator(config)
        if generator:
            return generator.getRevisionUrl(self._settings.runtime.revision)

        return None


    def getDiffer(self, command = None):
        """ Returns the initialized differ

            @param command: The diff command to use (if any)
            @type command: C{tuple} or C{None}

            @return: The differ type
            @rtype: C{svnmailer.differ.*}
        """
        from svnmailer import differ

        if command:
            return differ.ExternalDiffer(command, self.getTempDir())
        else:
            return differ.InternalDiffer()


    def getTempFile(self):
        """ Returns an open temporary file container object

            @return: The filename and an descriptor
            @rtype: C{svnmailer.util.TempFile}
        """
        return util.TempFile(tempdir = self.getTempDir(), text = False)


    def getTempDir(self):
        """ Returns the temporary directory

            @return: The directory or C{None}
            @rtype: C{unicode} or {str}
        """
        if not self._settings.general.tempdir:
            return None

        return self._settings.general.tempdir


    def getDiffTokens(self, config):
        """ Returns valid diff tokens and tests

            @param config: group config
            @type config: C{svnmailer.settings.GroupSettingsContainer}

            @return: The diff tokens and diffable tests
                The first element of the tuple contains a list
                of diff tokens, the second element the diff tests
            @rtype: C{tuple}
        """
        diff_tokens = config.generate_diffs
        if not diff_tokens:
            diff_tokens = diff_tokens is not None and ['none'] or []

        # unknown tokens from the config are just ignored
        # if the result is empty, we assume either an
        # empty generate_diffs option or a nasty typo
        # However, in that case we active all possible tokens
        diff_test_list = [(token.lower(), test)
            for token, test in self._diffable_tests
            if token.lower() in diff_tokens
        ] or self._diffable_tests

        diff_tokens = []
        diff_tests = []
        for token, test in diff_test_list:
            if token != self.NONE:
                diff_tokens.append(token)
                diff_tests.append(test)

        return (diff_tokens, diff_tests)


    def dumpContent(self, change, enc = 'utf-8', default = False):
        """ Dump the two revisions of a particular change

            (This dumps the files, not the properties)

            @param change: The particular change to process
            @type change: C{svnmailer.subversion.VersionedPathDescriptor}

            @param enc: The file data encoding (The data will be recoded
                to UTF-8; but by default it isn't recoded, because utf-8
                is assumed)
            @type enc: C{str}

            @param default: Return the default encoding (iso-8859-1) if the
                determined is C{None}
            @type default: C{bool}

            @return: Two file container objects plus their recoding state
                (file1, file2, rec1, rec2), where rec? is either the
                accompanying original encoding or C{None}
            @rtype: C{tuple}
        """
        from svnmailer import stream

        rec1 = rec2 = None
        if enc not in (self.ENC_CONFIG, self.ENC_DEFAULT):
            rec1 = rec2 = enc1 = enc2 = enc
        else:
            if enc == self.ENC_CONFIG:
                enc1, enc2 = self.getContentEncodings(change)
                rec1, rec2 = (enc1, enc2)
                enc1 = enc1 or 'iso-8859-1'
                enc2 = enc2 or 'iso-8859-1'
                if rec1 and not rec2:
                    rec2 = enc2
                elif rec2 and not rec1:
                    rec1 = enc1
            elif enc == self.ENC_DEFAULT:
                enc1 = enc2 = 'iso-8859-1'

            if default:
                rec1 = rec1 or enc1
                rec2 = rec2 or enc2

        file1 = self.getTempFile()
        if not change.wasAdded() or change.wasCopied():
            fp = (enc1 and enc1.lower() != 'utf-8') and \
                stream.UnicodeStream(file1.fp, enc1) or file1.fp
            self._settings.runtime._repos.dumpPathContent(
                fp, change.getBasePath(), change.getBaseRevision()
            )
        file1.close()

        file2 = self.getTempFile()
        if not change.wasDeleted():
            fp = (enc2 and enc2.lower() != 'utf-8') and \
                stream.UnicodeStream(file2.fp, enc2) or file2.fp
            self._settings.runtime._repos.dumpPathContent(
                fp, change.path, change.revision
            )
        file2.close()

        return (file1, file2, rec1, rec2)


    def getContentEncodings(self, change, default = None):
        """ Returns the encodings of the change content (base and current rev)

            @param change: The change to process
            @type change: C{svnmailer.subversion.VersionedPathDescriptor}

            @param default: The default encoding, if nothing is specified
            @type default: C{str}

            @return: The two encodings
            @rtype: C{tuple} of C{str}
        """
        enc1 = enc2 = default
        if not change.wasAdded() or change.wasCopied():
            try:
                enc1 = self._getContentEncoding(
                    change.getBasePath(), change.getBaseRevision()
                )
            except LookupError:
                # fall back
                pass

        if change.wasDeleted():
            enc2 = enc1
        else:
            try:
                enc2 = self._getContentEncoding(
                    change.path, change.revision
                )
            except LookupError:
                # fall back
                pass

        if change.wasAdded() and not change.wasCopied():
            enc1 = enc2

        return (enc1, enc2)


    def _getContentEncoding(self, path, revision):
        """ Returns the encoding for the specified path and revision

            @param path: The path
            @type path: C{str}

            @param revision: The revision number
            @type revision: C{int}

            @return: The encoding
            @rtype: C{str}

            @exception LookupError: The specified encoding
                is not implemented or no encoding was specified
        """
        # first try the svn:mime-type
        enc = self.getEncodingFromMimeType(path, revision)
        if enc:
            enc = enc.strip()

        # try svnmailer:content-charset on the file itself
        if not enc:
            enc = self.getContentEncodingProperty(path, revision)
            if enc:
                enc = enc.strip()

        # nope... traverse the path
        if not enc:
            globs = []
            for dirpath in util.getParentDirList(path):
                globlist = self.getContentEncodingProperty(dirpath, revision)
                if globlist:
                    globs.extend([(glob.strip(), supp_enc.strip())
                        for glob, supp_enc in [
                            glob.split('=', 1)
                            for glob in globlist.splitlines(False)
                            if glob and not glob.lstrip()[:1] == '#'
                                and '=' in glob
                        ] if glob.strip() and supp_enc.strip()
                    ])

            if path[:1] != '/':
                path = "/%s" % path
            enc = util.getGlobValue(globs, path)

        if enc:
            # try a lookup, it raises a LookupError in case of question
            import codecs
            codecs.lookup(enc)
            return enc

        raise LookupError("No Encoding configured")


    def getEncodingFromMimeType(self, path, revision):
        """ Returns the encoding extracted from svn:mime-type

            @param path: The path
            @type path: C{str}

            @param revision: The revision number
            @type revision: C{int}

            @return: The encoding or C{None}
            @rtype: C{str}
        """
        result = None
        repos = self._settings.runtime._repos
        mtype = repos.getPathMimeType(path, revision)

        if mtype:
            parsed = util.parseContentType(mtype)
            enc = parsed and parsed[1].get('charset')
            if enc and len(enc) == 1:
                result = enc[0]

        return result


    def getContentEncodingProperty(self, path, revision):
        """ Returns the content encoding property for a path/rev

            @param path: The path
            @type path: C{str}

            @param revision: The revision number
            @type revision: C{int}

            @return: The encoding or C{None}
            @rtype: C{str}
        """
        try:
            result = self._penc_cache[(path, revision)]
        except KeyError:
            repos = self._settings.runtime._repos
            result = repos.getPathProperty(self.ENC_PROPERTY, path, revision)
            if result is not None:
                try:
                    result = result.decode('utf-8')
                except UnicodeError:
                    # ugh.
                    result = result.decode('iso-8859-1')
                result = result.encode('utf-8')

            self._penc_cache[(path, revision)] = result

        return result


    def getContentDiffUrl(self, config, change):
        """ Returns the content diff url for a particular change

            @param config: group config
            @type config: C{svnmailer.settings.GroupSettingsContainer}

            @param change: The particular change to process
            @type change: C{svnmailer.subversion.VersionedPathDescriptor}

            @return: The URL or C{None} if there's no base URL configured
            @rtype: C{str}
        """
        from svnmailer import browser

        generator = browser.getBrowserUrlGenerator(config)
        if generator:
            return generator.getContentDiffUrl(change)


    def isUTF8Property(self, name):
        """ Returns if the supplied property name represents an UTF-8 property

            @param name: The property name
            @type name: C{str}

            @return: The decision
            @rtype: C{bool}
        """
        from svnmailer import subversion
        return subversion.isUnicodeProperty(name)


    def isBinaryProperty(self, values):
        """ Returns if the supplied property seems to be binary

            Note that is a very rudimentary check, just to not
            pollute diff output with garbage

            @param values: The value tuple
            @type values: C{tuple}

            @return: binary property?
            @rtype: C{bool}
        """
        for value in values:
            if value is None:
                continue

            # look for control characters
            if value != value.translate(EMPTY_TABLE, CTRL_CHARS):
                return True

            # look for a newline
            if len(value) > 255 and "\n" not in value[:255]:
                return True

        # ok, could be text
        return False


    def isOneLineProperty(self, name, value):
        """ Returns if the supplied property value takes just one line

            @param value: The property value
            @type value: C{str}

            @param name: Property name
            @type name: C{str}

            @return: one line property?
            @rtype: C{bool}
        """
        # TODO: make one-line-property line length configurable?
        return bool(len(name + value) <= 75 and value.find("\n") == -1)


    def getContentDiffAction(self, change):
        """ Returns the content diff action for a particular change

            @param change: The particular change to process
            @type change: C{svnmailer.subversion.VersionedPathDescriptor}

            @return: The diff token or C{None} if there nothing
            @rtype: C{unicode}
        """
        if change.wasDeleted():
            return self.DELETE
        else:
            if change.wasCopied():
                return self.COPY
            elif change.wasAdded():
                return self.ADD
            elif change.hasContentChanges():
                return self.MODIFY

        return None


    def getPropertyDiffAction(self, values):
        """ Returns the property diff action for a particular change

            @param values: The two values of the property
            @type values: C{tuple}

            @return: The diff token
            @rtype: C{unicode}
        """
        if values[0] is None:
            return self.ADD
        elif values[1] is None:
            return self.DELETE

        return self.MODIFY

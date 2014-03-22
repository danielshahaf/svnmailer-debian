#!/usr/bin/env python2.3
# -*- coding: utf-8 -*-


def check_versions():
    import sys

    major, minor = sys.version_info[0:2]
    if major < 2 or minor < 3:
        raise AssertionError(
            "Python 2.3 or later required, but sys.version_info = %r" %
            (sys.version_info, )
        )

    try:
        import svn
    except:
        print >> sys.stderr, \
            "WARNING: Subversion/Python bindings could not be imported"


def setup():
    import sys
    from distutils import core

    addargs = {}
    if sys.platform != 'win32':
        addargs['data_files'] = [("man/man1", ["docs/svn-mailer.1"])]

    core.setup(
        name = "svnmailer",
        version = "1.0.9",
        description = "Feature rich subversion commit notification tool",
        author = "André Malo",
        author_email = "nd@perlig.de",
        url = "http://opensource.perlig.de/svnmailer/",
        license = "Apache License 2.0",

        package_dir = {'': 'src/lib'},
        packages = ['svnmailer', 'svnmailer.notifier'],
        scripts = ['src/svn-mailer'],
        **addargs
    )


########### main ############
check_versions()
setup()

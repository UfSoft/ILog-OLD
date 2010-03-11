#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2009 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from setuptools import setup
import ilog

setup(name=ilog.__package__,
      version=ilog.__version__,
      author=ilog.__author__,
      author_email=ilog.__email__,
      url=ilog.__url__,
      download_url='http://python.org/pypi/%s' % ilog.__package__,
      description=ilog.__summary__,
      long_description=ilog.__description__,
      license=ilog.__license__,
      platforms="UNIX/Linux Dependent.",
      keywords = "IRC Logging",
      packages=['ilog'],
      install_requires = ['pytz', 'Babel', 'werkzeug', 'SQLAlchemy'],
      package_data={
          'ilog': ['static/**/*', 'templates/**/*.html']
      },
      message_extractors = {'ilog': [
          ('**.py', 'python', None),
          ('**/templates/**.html', 'jinja2', None),
          ('shared/**', 'ignore', None)]
      },
      entry_points = """
      [distutils.commands]
      compile = babel.messages.frontend:compile_catalog
      extract = babel.messages.frontend:extract_messages
         init = babel.messages.frontend:init_catalog
       update = babel.messages.frontend:update_catalog
      """,

      classifiers=[
          'Development Status :: 5 - Alpha',
          'Environment :: Web Environment',
          'Intended Audience :: System Administrators',
          'License :: OSI Approved :: BSD License',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Topic :: Utilities',
          'Topic :: Internet :: WWW/HTTP',
          'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
      ]
)

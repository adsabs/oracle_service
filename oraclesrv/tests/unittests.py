#!/usr/bin/env python

import unittest
import sys

if __name__ == '__main__':

    suite = unittest.TestLoader().discover('tests')
    results = unittest.TextTestRunner(verbosity=3).run(suite)
    if results.errors or results.failures:
      sys.exit(1)

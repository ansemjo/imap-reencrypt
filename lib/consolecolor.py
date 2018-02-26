# Copyright 2018 Anton Semjonov
# SPDX-License-Identiter: MIT

import contextlib

@contextlib.contextmanager
def color(colordef):
  print(f'\033[{colordef}m', end='')
  yield
  print(f'\033[0m', end='')

class COLOR:
  RED     = '31'
  GREEN   = '32'
  YELLOW  = '33'
  BLUE    = '34'
  PURPLE  = '35'
  TEAL    = '36'

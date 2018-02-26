# Copyright 2018 Anton Semjonov
# SPDX-License-Identiter: MIT

import configparser

def get_configuration(filepath, account=None):

  # initialize and read configuration file
  parser = configparser.ConfigParser()
  parser.read(filepath)

  # return configuration for account
  if account != None:
    return parser[account]
  else:
    return parser[parser.defaults()['account']]

def get_imap_configuration(filepath, account=None):

  # get configuration from above
  c = get_configuration(filepath, account)

  # return a list
  return (c['server'], c['username'], c['password'])

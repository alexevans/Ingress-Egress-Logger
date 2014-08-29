#!/usr/bin/env python

# SPSU AUV Team Ingress-Egress-Logger
# Copyright (C) 2014  SPSU AUV Team
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

from __future__ import print_function
import numpy as np
import ConfigParser
import datetime as datetime
import sys
import re
import subprocess


passcount = 4
mail_header = "From: \"SPSU AUV Door PC\" <no-reply@spsu.edu>\nTo: \"Taylor Martin\" <taylormartin357@gmail.com>\nSubject: Parking Passes\n"

#                              Member Name         Time Ingressed            Parking Pass num   got pass time               Future Use - RFID?
mydf = np.zeros( (0,), dtype=[('name',np.str_,16),('time',datetime.datetime),('pass',np.int_),('passtime',datetime.datetime),('id',np.str_,12)] )

def findUser(name):
  global mydf
  if np.any(mydf['name'] == name):
    return np.where(mydf['name']==name)[0][0]
  else:
   return -1

def importUser(name, id, overwriteID=False):
  global mydf
  if np.any(mydf['name'] == name):
    if not overwriteID:
      print('ERROR: '+name+' exists.', file=sys.stderr)
    else:
      i=findUser(name)
      if not mydf['id'][i]==id:
        print('WARN:  Overwriting '+name+'\'s id.', file=sys.stderr)
      mydf['id'][i]=id
    return
  newUser = np.zeros( (1,), dtype=[('name',np.str_,16),('time',datetime.datetime),('pass',np.int_),('passtime',datetime.datetime),('id',np.str_,12)] )
  newUser['name'][0]=name
  newUser['id'][0]=id
  newUser['pass'][0]=-1
  mydf=np.append(mydf, newUser)

def reloadUsers():
  cnames=ConfigParser.RawConfigParser()
  cnames.read('names.ini')
  for entry in cnames.sections():
    importUser(entry, cnames.get(entry,'id'), overwriteID=True)

def lerror(str):
  print('\a\a\a\033[;31m'+str+'\033[0m')

def lprint(str):
  print('\033[;36m'+str+'\033[0m')

def login(name):
  i=findUser(name)
  if i == -1:
    lerror("Could not find member: "+name)
    lerror("Please have an admin add you")
    return
  if mydf['time'][i] == 0:
    mydf['time'][i]=datetime.datetime.now()
    lprint(name+' signed-in')
  else:
    lerror("You are already signed in")

def logout(data):
  name = data.partition(' ')[0]
  work = data.partition(' ')[2]
  i=findUser(name)
  if i == -1:
    lerror("Could not find member: "+name)
    lerror("Please have an admin add you")
    return
  if mydf['time'][i] == 0:
    lerror("You are already signed out")
  else:
    stop=datetime.datetime.now()
    f = open(str(stop.year)+'-'+str(stop.month)+'-'+name+'.time', 'a')
    start=mydf['time'][i]
    diff=stop-start
    f.write(str(start)+'; '+work.translate(None, ';')+'; '+str(diff)+'; \n')
    f.close()
    mydf['time'][i] = 0
    lprint(name+' worked on '+work)

def listin():
  if not np.any(mydf['time'] <> 0):
    lprint("Lab is empty.")
  else:
    for i in list(np.where(mydf['time'] <> 0)[0]):
      lprint(mydf['name'][i])
  if not np.any(mydf['pass'] <> -1):
    lprint('All passes are signed-in')
  else:
    lprint("\n\rPARKING PASSES\n\r--------------")
    for i in list(np.where(mydf['pass'] <> -1)[0]):
      lprint(str(mydf['pass'][i])+' '+mydf['name'][i]+' '+str(datetime.datetime.now()-mydf['passtime'][i]))

def help():
  print("\033[0;33m")
  print("Sign In: i name")
  print("Sign Out: o name work_peformed")
  print("List Users In: l")
  print("Get Parking Pass: p g last_digit name")
  print("Return Parking Pass: p r last_digit name")
  print("\033[0m")

def passes(data):
  global mydf
  global passcount
  code = data.partition(' ')[0]
  digit = data.partition(' ')[2].partition(' ')[0]
  name = data.partition(' ')[2].partition(' ')[2]
  i=findUser(name)
  if i == -1:
    lerror("Could not find member: "+name)
    lerror("Please have an admin add you")
    return
  if code[0] == 'g':
    if mydf['pass'][i] <> -1:
      lerror("You have already checked-out pass number "+str(mydf['pass'][i]))
      return
    if np.any(mydf['pass'] == int(digit)):
      lerror("Parking pass number "+digit+" is already out")
      return
    mydf['pass'][i]=int(digit)
    mydf['passtime'][i]=datetime.datetime.now()
    f = open('passes.log', 'a')
    lprint(name+' checked-out pass number '+digit+' at '+str(mydf['passtime'][i]))
    f.write(name+' checked-out pass number '+digit+' at '+str(mydf['passtime'][i])+'\n')
    f.close()
    passcount = passcount - 1
    if passcount is 1:
      try:
        subprocess.check_output("echo \""+mail_header+"One Pass Left\" | ssmtp -t", shell=True)
      except:
        lerror('mail not send')
    elif passcount is 0:
      try:
        subprocess.check_output("echo \""+mail_header+"All Passes Gone\" | ssmtp -t", shell=True)
      except:
        lerror('mail not send')
  elif code[0] == 'r':
    if not np.any(mydf['pass'] == int(digit)):
      lerror("Pass humber "+digit+" is already checked-in")
      return
    p=np.where(mydf['pass']==int(digit))[0][0]
    mydf['pass'][p]=-1
    if name == mydf['name'][p]:
      f = open('passes.log', 'a')
      lprint(name+' checked-in pass number '+digit)
      f.write(name+' checked-in pass number '+digit+'\n')
      f.close()
    else:
      f = open('passes.log', 'a')
      lerror(name+' checked-in pass number '+digit+' for '+mydf['name'][p])
      f.write(name+' checked-in pass number '+digit+' for '+mydf['name'][p]+'\n')
      f.close()
    passcount = passcount + 1
    if passcount is 1:
      try:
        subprocess.check_output("echo \""+mail_header+"One Pass Left\" | ssmtp -t", shell=True)
      except:
        lerror('mail not send')
    elif passcount > 1:
      try:
        subprocess.check_output("echo \""+mail_header+"Multiple Passes Left\" | ssmtp -t", shell=True)
      except:
        lerror('mail not send')


def a_function():
  help()
  inp=raw_input("\033[;32mReady: \033[0m")
  inp=inp.lstrip()
  inp=re.sub(' +',' ',inp)
  code = inp.partition(' ')[0][0]
  if code == 'i':
    login(inp.partition(' ')[2])
  elif code == 'o':
    logout(inp.partition(' ')[2])
  elif code == 'l':
    listin()
  elif code == 'p':
    passes(inp.partition(' ')[2])
  elif inp == 'reload':
    reloadUsers()
    lprint("Reloaded Users")
  #elif inp == 'quit': return True
  return False

def main():
  reloadUsers()
  print("\033[2J")# Clear Screen
  quit=False
  while not quit:
    try:
      quit=a_function()
    except:
      lerror("ERROR")# I am lazy - Taylor
      # No, but really it did say 'Invalid Command' because somewhere in a_function() if the command
      # was malformed an exception would be thrown, there was a lot of them. Later I realized that I
      # may have missed somthing else in another function, like the ones with file operations, so an
      # all-catching except block was easier. That being said, in the time it took me to write this,
      # I probablly could have wrote a try block in each function so that if there were an error, we
      # would know where it came from. See how this comment block is justified, that was on purpose.

if __name__ == '__main__':
  main()


#!/usr/bin/env python

# Copyright (c) 2014, Christoph Stahl
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
# 
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# 
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import fnmatch
import os

def calcRectInRect(innerRect, outerRect):
  """Return innerRect translated relative to outerRect"""
  (ix, iy, iw, ih) = innerRect
  (ox, oy, ow, oh) = outerRect
  return (ox + ix, oy + iy, iw, ih)
  

def middleOfRect(rect):
  """Returns int middle point of rectangle""" 
  (x, y, w, h) = rect
 
  return (x + int(w/2.0), y + int(h/2.0))
  

def filefilter(filename):
  """Filter list of files for .jpg and return those"""
  return fnmatch.fnmatch(filename, '*.JPG') or fnmatch.fnmatch(filename, '*.jpg') or fnmatch.fnmatch(filename, '*.jpeg') 
  

def checkFolder(path):
  """Returns absolute version of path and checks that folder is existent"""
  if path is None:
    return None
  path = os.path.expanduser(path)
  path = os.path.abspath(path)
  if os.path.isdir(path):
    return path
  else:
    return None
    
    
def checkFile(path):
  """Returns absolute version of path and checks that directory of file exists"""
  if path is None:
    return None
  path = os.path.expanduser(path)
  path = os.path.abspath(path)
  dir = os.path.dirname(path)
  if os.path.isdir(dir) and not os.path.isdir(path):
    return path
  else:
    return None
  
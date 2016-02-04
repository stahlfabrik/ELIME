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

import os
import cv
from datetime import datetime, timedelta, date
import logging

# Pillow
from PIL import Image, ImageDraw, ImageFont, ExifTags

# This following import was found on
# http://docs.opencv.org/modules/contrib/doc/facerec/facerec_tutorial.html
# Thanks, Philipp Wagner for sharing!
import AlignFaceImage

def loadAndTransposePILImage(inputImageFileName):
  """Load PIL Image and return rotated Image if exif data has rotation"""
  pilImage = Image.open(inputImageFileName)

  #inspired by
  #http://stackoverflow.com/questions/4228530/pil-thumbnail-is-rotating-my-image/11543365#11543365

  if hasattr(pilImage, '_getexif'): # only present in JPEGs
    for orientation in ExifTags.TAGS.keys(): 
      if ExifTags.TAGS[orientation]=='Orientation':
        break
       
    e = pilImage._getexif()       # returns None if no EXIF data
    if e is not None:
      exif=dict(e.items())
      orientation = exif[orientation] 

      if orientation == 3:   pilImage = pilImage.transpose(Image.ROTATE_180)
      elif orientation == 6: pilImage = pilImage.transpose(Image.ROTATE_270)
      elif orientation == 8: pilImage = pilImage.transpose(Image.ROTATE_90)

  return pilImage
  

def convertPIL2CV(PILImage):
  """Concert PIL Image to openCV Image and return it"""
  # inspired by
  # http://opencv.willowgarage.com/wiki/PythonInterface			
  cvImage = cv.CreateImageHeader(PILImage.size, cv.IPL_DEPTH_8U, 3)
  cv.SetData(cvImage, PILImage.tobytes(), PILImage.size[0]*3)
  cv.CvtColor(cvImage, cvImage, cv.CV_RGB2BGR)

  return cvImage


def getCreationDateTimeOfPicture(path, customDateFormat=''):
  """Get Creation date and time of imagefile. Parse filename or (better) use exif data if possible, else return modify time"""
  
  fileNameDateTime = None
  
  if len(customDateFormat):
    #parse datetime from filename
    fileNameDateTime = datetime.strptime(os.path.basename(path), customDateFormat)
    
  #check for exif date in file
  pilImage = Image.open(path)
  
  exifDateTime = None
  if hasattr(pilImage, '_getexif'):
   
    exifData = pilImage._getexif()
    
    if exifData is not None:
      for k,v in ExifTags.TAGS.iteritems(): 
        if v == 'DateTimeOriginal':
          break
      
      if k in exifData:    
        exifDateTimeString = exifData[k]

        #2012:02:03 17:14:43
        #YYYY:MM:DD HH:MM:SS
  
        exifFormat = "%Y:%m:%d %H:%M:%S"
        exifDateTime = datetime.strptime(exifDateTimeString, exifFormat)
  
  #get modified time as fallback
  mDateTime = datetime.fromtimestamp(os.path.getmtime(path))

  if exifDateTime is not None:
    return exifDateTime

  if fileNameDateTime is not None:
    return fileNameDateTime

  return mDateTime
  

def renderPhoto(srcPath, dbPhoto, font=None, format='%x', 
                offset_pct=(0.43,0.425), dest_sz=(1920,1080), brightness=1.0, 
                posDebug=False):
  """Render db photo to desired values adding text as well and return PIL image"""
  logger = logging.getLogger('ELIME.renderPhoto')
  
  if not os.path.isdir(srcPath):
    logger.error("Given source path is not valid %s", srcPath)
    return None
  
  filePath = os.path.join(srcPath, dbPhoto[1])
  
  pilImage = loadAndTransposePILImage(filePath)
  
  if posDebug:
    draw = ImageDraw.Draw(pilImage)
    draw.line([(dbPhoto[3], dbPhoto[4] - 1), (dbPhoto[3], dbPhoto[4] + 1)], fill="white")
    draw.line([(dbPhoto[3] - 1, dbPhoto[4]), (dbPhoto[3] + 1, dbPhoto[4])], fill="white")
    
    draw.line([(dbPhoto[5], dbPhoto[6] - 1), (dbPhoto[5], dbPhoto[6] + 1)], fill="white")
    draw.line([(dbPhoto[5] - 1, dbPhoto[6]), (dbPhoto[5] + 1, dbPhoto[6])], fill="white")
    del draw
  pilImage = AlignFaceImage.CropFace(pilImage, (dbPhoto[3],dbPhoto[4]), (dbPhoto[5],dbPhoto[6]), offset_pct, dest_sz)

  if not brightness == 1.0:
    pilImage = pilImage.point(lambda x: x * brightness)
        
  width, height = pilImage.size
    
  if font:
    text = dbPhoto[2].strftime(format)
    (twidth, theight) = font.getsize(text)
    draw = ImageDraw.Draw(pilImage)
    draw.text((10, height - (10 + theight)), text, font=font)
    del draw
  
  return pilImage

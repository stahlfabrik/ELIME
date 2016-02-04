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

import cv2.cv as cv
import math
import logging
import os
import sys

# ELIME Project
import HelperFunctions
import UiFunctions


MINFACEPERCENTAGE = 0.1
PATHTOCASCADES = '/usr/local/opt/opencv/share/OpenCV/haarcascades/'


def detectFacesInImage(cvImage, detectionDebug=False): 
  logger = logging.getLogger('ELIME.OpenCVFunctions.detectFacesInImage')
  width, height = cv.GetSize(cvImage)
  
  minDimension = min(width, height)
  
#   scale_factor = 1.1
#   min_neighbors = 3
#   flags = 0
#   min_size = (20,20)
  
  arguments = [(1.1, 3, 0, (20, 20)),
              (1.1, 3, 0, (int(1.0 * minDimension), int(1.0 * minDimension))),
              (1.1, 3, 0, (int(0.7 * minDimension), int(0.7 * minDimension))),
              (1.1, 3, 0, (int(0.4 * minDimension), int(0.4 * minDimension))),
              (1.1, 3, 0, (int(0.1 * minDimension), int(0.1 * minDimension))),
              (1.1, 3, 0, (int(0.01 * minDimension), int(0.01 * minDimension)))]
              
  path = os.path.join(PATHTOCASCADES, 'haarcascade_frontalface_default.xml')
  path = HelperFunctions.checkFile(path)
 
  if path is None:
    logger.critical("Path to opencv haarcascades is wrong: %s", PATHTOCASCADES)
    sys.exit(1)

  print path    
  faceCascade = cv.Load(path)
  
  storage = cv.CreateMemStorage()
  
  returnFaces = set()
  
  for (scale_factor, min_neighbors, flags, min_size) in arguments:
    
    detectedFaces = cv.HaarDetectObjects(cvImage, faceCascade, storage, scale_factor, min_neighbors, flags, min_size)
    debugString = '{0:d} faces found, args: {1} {2} {3} {4}'.format(len(detectedFaces), str(scale_factor), str(min_neighbors), str(flags), str(min_size))
    logger.debug(debugString)
    for face,n in detectedFaces:
      returnFaces.add(face)
    
    if detectionDebug:
      debugFaces = []
      for face,n in detectedFaces:
        debugFaces.append((face, cv.RGB(0, 0, 255)))
      UiFunctions.displayColoredRects(cvImage, debugString, debugFaces)
      
  logger.debug("returning Faces: %s", returnFaces)     
  return returnFaces
  
   
def detectEyesInRectInImage(cvImage, rect, detectionDebug=False):

  logger = logging.getLogger('ELIME.OpenCVFunctions.detectEyesInRectInImage')
  
  EYESWANTED = 2
  
#   (scale_factor, min_neighbors, flags, min_size)
  arguments = [(1.1, 3, 0, (20,20)),
               (1.01, 3, 0, (10,10)),
               (1.05, 3, 0, (15,15)),
               (1.025, 3, 0, (10,10)),
               (1.075, 3, 0, (10,10)),
               (1.125, 3, 0, (10,10)),
               (1.15, 3, 0, (15,15)),
               (1.1, 2, 0, (30, 30))]
  
  if rect:
    (x, y, w, h) = rect
    cv.SetImageROI(cvImage, (x, y, w, int(h * 0.6)))
  
  haarcascades = ['haarcascade_eye_tree_eyeglasses.xml', 'haarcascade_eye.xml']

  storage = cv.CreateMemStorage()

  returnedEyes = []

  for cascade in haarcascades:
    
    path = os.path.join(PATHTOCASCADES, cascade)
    path = HelperFunctions.checkFile(path)
 
    if len(returnedEyes) == 2:
      break
    
    if path is None:
      logger.critical("Path to haarcascade is wrong: %s", os.path.join(PATHTOCASCADES, cascade))
      sys.exit(1)
      
    eyeCascade = cv.Load(path)
    
    for (scale_factor, min_neighbors, flags, min_size) in arguments:
      
      detectedEyes = cv.HaarDetectObjects(cvImage, eyeCascade, storage, scale_factor, min_neighbors, flags, min_size)
      
      debugString = '{0:d} eyes found, args: {1} {2} {3} {4} {5}'.format(len(detectedEyes), cascade, str(scale_factor), str(min_neighbors), str(flags), str(min_size))
      
      if detectionDebug:
        debugEyes = []
        for eye,n in detectedEyes:
          debugEyes.append((eye, cv.RGB(255, 255, 0)))
        UiFunctions.displayColoredRects(cvImage, debugString, debugEyes)
      
      logger.debug(debugString)

      if len(detectedEyes) == 0:
        logger.debug("0 eyes found. Continue.")
        continue
      
      if len(detectedEyes) == 2:
        logger.debug("2 eyes found. Break")
        returnedEyes = detectedEyes
        break
    
      if len(returnedEyes) == 0 or math.fabs(len(detectedEyes) - EYESWANTED) < math.fabs(len(returnedEyes) - EYESWANTED):
        logger.debug("%d eyes found. Better than: %d", len(detectedEyes), len(returnedEyes))
        returnedEyes = detectedEyes
    
  cv.ResetImageROI(cvImage)

  logger.debug("Returning Eyes: %s", returnedEyes)     
  return returnedEyes

 
def eyeRectsInImage(cvImage, fileName='', detectionDebug=False):
  logger = logging.getLogger('ELIME.OpenCVFunctions.eyeRectsInImage')
  listOfEyeRects = []
  
  logger.info("Start detecting faces.")
  
  faces = detectFacesInImage(cvImage, detectionDebug)
  
  biggestFace = None
  
  logger.info("%d faces found.", len(faces))
    
  for faceRect in faces:
    if not biggestFace:
      biggestFace = faceRect
    else:
      (x, y, w, h) = faceRect
      (bx, by, bw, bh) = biggestFace
      if w * h > bw * bh:
        biggestFace = faceRect
  
  if biggestFace is not None:
    logger.debug("biggest face is %s", biggestFace)
    (bx, by, bw, bh) = biggestFace
    width, height = cv.GetSize(cvImage)
    imArea = width * height
    bfArea = bw * bh
  
    division = bfArea / float(imArea)
  
    if division > MINFACEPERCENTAGE:
      logger.info("%f biggest face size of image size - bigger than threshhold %f. Using face region for eye search.", division, MINFACEPERCENTAGE)
      eyes = detectEyesInRectInImage(cvImage, biggestFace, detectionDebug)
  
      for (eyeRect, n) in eyes:
        listOfEyeRects.append(HelperFunctions.calcRectInRect(eyeRect, biggestFace))
        
    else:
      logger.info("%f biggest face size of image size - smaller than threshhold %f. Search everywhere in image for eyes.", division, MINFACEPERCENTAGE)
      eyes = detectEyesInRectInImage(cvImage, None, detectionDebug)
      for (eyeRect, n) in eyes:
        listOfEyeRects.append(eyeRect)
        
  else:
    logger.info("No face found. Search everywhere in image for eyes.")
    eyes = detectEyesInRectInImage(cvImage, None, detectionDebug)
    for (eyeRect, n) in eyes:
      listOfEyeRects.append(eyeRect)
  
  # return new sorted list
  listOfEyeRects = sorted(listOfEyeRects, key=lambda rect: HelperFunctions.middleOfRect(rect)[0])

  if detectionDebug:
    facecolor = cv.RGB(0, 0, 255)
    biggestfacecolor = cv.RGB(122, 0, 255)
    eyecolor = cv.RGB(255, 255, 0)
    
    rectsAndColor = []
    
    for face in faces:
      rectsAndColor.append((face, facecolor))
    rectsAndColor.append((biggestFace, biggestfacecolor))
    for eye in listOfEyeRects:
      rectsAndColor.append((eye, eyecolor))
    windowName = "finally {0:d} faces {1:d} eyes in {2}".format(len(faces), len(listOfEyeRects), fileName)
    UiFunctions.displayColoredRects(cvImage, windowName, rectsAndColor)
    
  logger.debug("Returning Eyes: %s", listOfEyeRects) 
  return listOfEyeRects



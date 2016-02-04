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

import sys
import cv
import logging

# ELIME Project
import HelperFunctions


def onMouseAllEyes(event,x,y,i,(fileName, cvImage, eyeCoordinates, selectedEye)):
  """Mouse callback for manually adjust all eyes"""
  
  if not hasattr(onMouseAllEyes, "leftPressed"):
    onMouseAllEyes.leftPressed = False
  
  if not hasattr(onMouseAllEyes, "rightPressed"):
    onMouseAllEyes.rightPressed = False
  
  if event == 1:
    onMouseAllEyes.leftPressed = True
  elif event == 2:
    onMouseAllEyes.rightPressed = True
  elif event == 4:
    onMouseAllEyes.leftPressed = False
  elif event == 5:
    onMouseAllEyes.rightPressed = False
    
  if onMouseAllEyes.leftPressed or onMouseAllEyes.rightPressed:
    if len(eyeCoordinates) > 2:
      print "More then two eyes. Delete some eyes before using mouse control."
      return
    
    if len(selectedEye):
      selectedEye[0] = i - 1
    else:
      selectedEye.append(i - 1)
        
    if onMouseAllEyes.leftPressed:
      # left click -> left eye        
      if len(eyeCoordinates) == 0:
        #create new left eye
        eyeCoordinates.append((x, y))
      if len(eyeCoordinates) >= 1:
        #set new position of left eye
        eyeCoordinates[0] = (x, y)

    if onMouseAllEyes.rightPressed:
      # right click -> right eye or create second eye if there is no left eye
      if len(eyeCoordinates) == 0 or len(eyeCoordinates) == 1:
        #create new left or right eye
        eyeCoordinates.append((x, y))
        if len(eyeCoordinates) == 1:
          # there was no left eye -> correct now selected eye
          selectedEye[0] = 1
      if len(eyeCoordinates) == 2:
        #set new position of right eye
        eyeCoordinates[1] = (x, y)

    highEye = None
    if len(eyeCoordinates):
      highEye = eyeCoordinates[selectedEye[0]]
    eyeCoordinates.sort(key=lambda pos: pos[0])
    
    if highEye is not None:
       selectedEye[0] = eyeCoordinates.index(highEye)
    showEyesInImageFile(fileName, eyeCoordinates, cvImage, selectedEye)
    

def showEyesInImageFile(fileName, eyeCoordinates, cvImage, selectedEye = []):
  """Take opencvimage and eye positions and draw colored rectangles around eyes and present in window"""
  copyImage = cv.CloneImage(cvImage)

  if len(selectedEye):
    highlightIndex = selectedEye[0]
  else:
    highlightIndex = None
  
  isize = cv.GetSize(cvImage)
  radius = int(max(10, 0.05 * max(isize[0], isize[1])))
  
  for eye in eyeCoordinates:
      (x, y) = eye
      
      #in the end:
      #natural right eye - index 0 - green
      #natural left eye - index 1 - red
      
      color = cv.RGB(255, 0, 255) # bad magenta :-P
      
      index = eyeCoordinates.index(eye)
      if index == highlightIndex:
        color = cv.RGB(255, 200, 255) #highlight magenta
      
      if index == 0:
        color = cv.RGB(0, 255, 0)
        if highlightIndex == 0:
          color = cv.RGB(200, 255, 200)
      
      if index == 1:
        color = cv.RGB(255, 0, 0)
        if highlightIndex == 1:
          color = cv.RGB(255, 200, 200)
                     
      cv.Circle(copyImage, (x, y), radius, color, 2)
      cv.Line(copyImage, (x - 1, y), (x + 1, y), color, 1)
      cv.Line(copyImage, (x, y - 1), (x, y + 1), color, 1)  
  cv.ShowImage(fileName, copyImage)
   

def manuallyAdjustEyePositions(cvImage, fileName, eyeCoordinates):
  """UI for moving eyes in full image, returns new eye positions"""
  
  eyeCoordinates = sorted(eyeCoordinates, key=lambda pos: pos[0])

  key = 0
  selectedEye = []
  exit = False
  
  speed = 1
  
  cv.NamedWindow(fileName, cv.CV_WINDOW_AUTOSIZE)
  cv.SetMouseCallback(fileName, onMouseAllEyes, param=(fileName, cvImage, eyeCoordinates, selectedEye))
  
  while not exit:
    highEye = None
    
    if len(selectedEye):
      highEye = eyeCoordinates[selectedEye[0]]
    eyeCoordinates.sort(key=lambda pos: pos[0])
    
    if highEye is not None:
       selectedEye[0] = eyeCoordinates.index(highEye)
        
    showEyesInImageFile(fileName, eyeCoordinates, cvImage, selectedEye)
    key = cv.WaitKey()
        
    if key == 63232: # up arrow
      if len(selectedEye) and selectedEye[0] < len(eyeCoordinates):
        eyeCoordinates[selectedEye[0]] = (eyeCoordinates[selectedEye[0]][0], eyeCoordinates[selectedEye[0]][1] - speed)
    elif key == 63233: # down arrow
      if len(selectedEye) and selectedEye[0] < len(eyeCoordinates):
        eyeCoordinates[selectedEye[0]] = (eyeCoordinates[selectedEye[0]][0], eyeCoordinates[selectedEye[0]][1] + speed)
    elif key == 63234: # left arrow
      if len(selectedEye) and selectedEye[0] < len(eyeCoordinates):
        eyeCoordinates[selectedEye[0]] = (eyeCoordinates[selectedEye[0]][0] - speed, eyeCoordinates[selectedEye[0]][1])
    elif key == 63235: # right arrow
      if len(selectedEye) and selectedEye[0] < len(eyeCoordinates):
        eyeCoordinates[selectedEye[0]] = (eyeCoordinates[selectedEye[0]][0] + speed, eyeCoordinates[selectedEye[0]][1])
  
    elif key == 9: # 'TAB' - toggle selected eye 
      if len(eyeCoordinates) > 0:
        if len(selectedEye) == 0:
          selectedEye.append(0)
        elif (selectedEye[0] + 1) % len(eyeCoordinates) == 0:
          selectedEye.pop()
        else:
          selectedEye[0] = selectedEye[0] + 1
      else:
        selectedEye = []
      
      if len(selectedEye) == 0:
        print "No eye selected"
      else:
        print "Selected Eye Index:", selectedEye[0]
    
    elif key == ord('c'): # create new eye
      if len(eyeCoordinates) < 2:
        width, height = cv.GetSize(cvImage)
        
        y = int(height * 0.35)
        
        if len(eyeCoordinates) == 1:
          mx, my = eyeCoordinates[0]
          
          x = int(width - mx)
          y = my
          
          if mx < width / 2:
            # left eye is already here
            insertIndex = 1
          else:  
            # right eye is already here
            insertIndex = 0
        else:
          x = int((width / 2.0) - (0.1 * width))
          insertIndex = 0
        
        eyeCoordinates.insert(insertIndex, (x, y))
        if len(selectedEye):
          selectedEye[0] = insertIndex
        else:
          selectedEye.append(insertIndex)
        
    elif key == ord('n') or key == 32: # or 'SPACE' - next picture
      if len(eyeCoordinates) == 2:
        exit = True
      else:
        print "You need exactly two eyes to continue"
        
    elif key == 27: # 'ESC' - deselect eye
      selectedEye = []
      
    elif key == ord('d') or key == ord('x'): # delete selected eye
      if len(selectedEye) and selectedEye[0] < len(eyeCoordinates):
        eyeCoordinates.pop(selectedEye[0])
        selectedEye.pop()
        
    elif key == ord('q'): # quit
      sys.exit(0)
      
    elif key == ord('f'): # "fastness", speed
      speed = (speed + 10) % 30
       
    else:
      print key

  cv.DestroyWindow(fileName)
  eyeCoordinates = sorted(eyeCoordinates, key=lambda pos: pos[0])
        
  return eyeCoordinates


def onMouseDetailEye(event,x,y,i,(windowName, cvImage, eyeIndex, eyePos, zoomSize)):
  
  if event == 4:
    
    zx = int(x / float(zoomSize) * manuallyDetailAdjustEyePosition.eyeSize)
    zy = int(y / float(zoomSize) * manuallyDetailAdjustEyePosition.eyeSize)
  
    eyePos[0] = int(zx + eyePos[0] - (manuallyDetailAdjustEyePosition.eyeSize / 2.0))
    eyePos[1] = int(zy + eyePos[1] - (manuallyDetailAdjustEyePosition.eyeSize / 2.0))
    
    showDetailEyeInImageFile(windowName, eyePos[0], eyePos[1], manuallyDetailAdjustEyePosition.eyeSize, cvImage, eyeIndex, zoomSize, manuallyDetailAdjustEyePosition.crosshairStyle)


def showDetailEyeInImageFile(windowName, eyecenterX, eyecenterY, eyeSize, cvImage, eyeIndex, zoomSize, crosshairstyle=0):

  copyImage = cv.CloneImage(cvImage)
  
  #natural right eye - index 0 - green
  #natural left eye - index 1 - red
  
  if eyeIndex == 0:
    color = cv.RGB(125, 255, 125)  
  else:
    color = cv.RGB(255, 125, 125)
  
  if crosshairstyle == 0:
    cv.Line(copyImage, (eyecenterX - 1, eyecenterY), (eyecenterX + 1, eyecenterY), color, 1)
    cv.Line(copyImage, (eyecenterX, eyecenterY - 1), (eyecenterX, eyecenterY + 1), color, 1)
  
  elif crosshairstyle == 1:
    cv.Line(copyImage, (eyecenterX, eyecenterY), (eyecenterX, eyecenterY), color, 1)
    
  elif crosshairstyle == 2:
    cv.Line(copyImage, (eyecenterX - int(eyeSize / 3.0), eyecenterY), (eyecenterX + int(eyeSize / 3.0), eyecenterY), color, 1)
    cv.Line(copyImage, (eyecenterX, eyecenterY - int(eyeSize / 3.0)), (eyecenterX, eyecenterY + int(eyeSize / 3.0)), color, 1)
    
  elif crosshairstyle == 3:
    cv.Line(copyImage, (eyecenterX, eyecenterY), (eyecenterX, eyecenterY), color, 1)
    cv.Circle(copyImage, (eyecenterX, eyecenterY), int(eyeSize * 0.05), color, 1)
  
  elif crosshairstyle == 4:
    cv.Line(copyImage, (eyecenterX, eyecenterY), (eyecenterX, eyecenterY), color, 1)
    cv.Circle(copyImage, (eyecenterX, eyecenterY), int(eyeSize * 0.1), color, 1)
  
  elif crosshairstyle == 5:
    cv.Line(copyImage, (eyecenterX, eyecenterY), (eyecenterX, eyecenterY), color, 1)
    cv.Circle(copyImage, (eyecenterX, eyecenterY), int(eyeSize * 0.15), color, 1)
  
  elif crosshairstyle == 6:
    cv.Line(copyImage, (eyecenterX, eyecenterY), (eyecenterX, eyecenterY), color, 1)
    cv.Circle(copyImage, (eyecenterX, eyecenterY), int(eyeSize * 0.2), color, 1)
  
  elif crosshairstyle == 7:
    cv.Line(copyImage, (eyecenterX, eyecenterY), (eyecenterX, eyecenterY), color, 1)
    cv.Circle(copyImage, (eyecenterX, eyecenterY), int(eyeSize * 0.25), color, 1)
  
  elif crosshairstyle == 8:
    cv.Line(copyImage, (eyecenterX - int(eyeSize / 3.0), eyecenterY), (eyecenterX + int(eyeSize / 3.0), eyecenterY), color, 1)
    cv.Line(copyImage, (eyecenterX, eyecenterY - int(eyeSize / 3.0)), (eyecenterX, eyecenterY + int(eyeSize / 3.0)), color, 1)
    cv.Circle(copyImage, (eyecenterX, eyecenterY), int(eyeSize * 0.05), color, 1)
    
  elif crosshairstyle == 9:
    cv.Line(copyImage, (eyecenterX - int(eyeSize / 3.0), eyecenterY), (eyecenterX + int(eyeSize / 3.0), eyecenterY), color, 1)
    cv.Line(copyImage, (eyecenterX, eyecenterY - int(eyeSize / 3.0)), (eyecenterX, eyecenterY + int(eyeSize / 3.0)), color, 1)
    cv.Circle(copyImage, (eyecenterX, eyecenterY), int(eyeSize * 0.1), color, 1)
    
  elif crosshairstyle == 10:
    cv.Line(copyImage, (eyecenterX - int(eyeSize / 3.0), eyecenterY), (eyecenterX + int(eyeSize / 3.0), eyecenterY), color, 1)
    cv.Line(copyImage, (eyecenterX, eyecenterY - int(eyeSize / 3.0)), (eyecenterX, eyecenterY + int(eyeSize / 3.0)), color, 1)
    cv.Circle(copyImage, (eyecenterX, eyecenterY), int(eyeSize * 0.15), color, 1)
  
  elif crosshairstyle == 11:
    cv.Line(copyImage, (eyecenterX - int(eyeSize / 3.0), eyecenterY), (eyecenterX + int(eyeSize / 3.0), eyecenterY), color, 1)
    cv.Line(copyImage, (eyecenterX, eyecenterY - int(eyeSize / 3.0)), (eyecenterX, eyecenterY + int(eyeSize / 3.0)), color, 1)
    cv.Circle(copyImage, (eyecenterX, eyecenterY), int(eyeSize * 0.2), color, 1)
    
  elif crosshairstyle == 12:
    cv.Line(copyImage, (eyecenterX - int(eyeSize / 3.0), eyecenterY), (eyecenterX + int(eyeSize / 3.0), eyecenterY), color, 1)
    cv.Line(copyImage, (eyecenterX, eyecenterY - int(eyeSize / 3.0)), (eyecenterX, eyecenterY + int(eyeSize / 3.0)), color, 1)
    cv.Circle(copyImage, (eyecenterX, eyecenterY), int(eyeSize * 0.25), color, 1)
    
  elif crosshairstyle == 13:
    cv.Line(copyImage, (eyecenterX - int(eyeSize / 3.0), eyecenterY), (eyecenterX + int(eyeSize / 3.0), eyecenterY), color, 1)
    cv.Line(copyImage, (eyecenterX, eyecenterY - int(eyeSize / 3.0)), (eyecenterX, eyecenterY + int(eyeSize / 3.0)), color, 1)
    cv.Circle(copyImage, (eyecenterX, eyecenterY), int(eyeSize * 0.3), color, 1)
    
  elif crosshairstyle == 14:
    cv.Line(copyImage, (eyecenterX - int(eyeSize / 3.0), eyecenterY), (eyecenterX + int(eyeSize / 3.0), eyecenterY), color, 1)
    cv.Line(copyImage, (eyecenterX, eyecenterY - int(eyeSize / 3.0)), (eyecenterX, eyecenterY + int(eyeSize / 3.0)), color, 1)
    cv.Circle(copyImage, (eyecenterX, eyecenterY), int(eyeSize * 0.35), color, 1)
    
  elif crosshairstyle == 15:
    pass
     
  croppedImage = cv.CreateImage((eyeSize, eyeSize), cvImage.depth, cvImage.nChannels)
  src_region = cv.GetSubRect(copyImage, (int(eyecenterX - eyeSize/2.0), int(eyecenterY - eyeSize/2.0), eyeSize, eyeSize))
  cv.Copy(src_region, croppedImage)
  
  zommedImage = cv.CreateImage((zoomSize, zoomSize), cvImage.depth, cvImage.nChannels)
  cv.Resize(croppedImage, zommedImage)
   
  cv.ShowImage(windowName, zommedImage) 
  
 
def manuallyDetailAdjustEyePosition(inputImageFileName, eyeIndex, cvImage, eyecenterX, eyecenterY, zoomSize):
  if not hasattr(manuallyDetailAdjustEyePosition, "crosshairStyle"):
    manuallyDetailAdjustEyePosition.crosshairStyle = 0
  if not hasattr(manuallyDetailAdjustEyePosition, "eyeSize"):
    isize = cv.GetSize(cvImage)
    esize = int(max(20, 0.10 * max(isize[0], isize[1])))
    manuallyDetailAdjustEyePosition.eyeSize = esize
    
  if eyeIndex == 0:
    windowName =  inputImageFileName + " (left Eye)"
  else:
    windowName =  inputImageFileName + " (right Eye)"
  
  speed = 1
  exit = False
  
  width, height = cv.GetSize(cvImage)
  
  eyePos = [eyecenterX, eyecenterY]
    
  cv.NamedWindow(windowName, cv.CV_WINDOW_AUTOSIZE)
  cv.SetMouseCallback(windowName, onMouseDetailEye, param=(windowName, cvImage, eyeIndex, eyePos, zoomSize))
  
  while not exit:
    showDetailEyeInImageFile(windowName, eyePos[0], eyePos[1], manuallyDetailAdjustEyePosition.eyeSize, cvImage, eyeIndex, zoomSize, manuallyDetailAdjustEyePosition.crosshairStyle)
    key = cv.WaitKey()
        
    if key == 63232: # up arrow
      if eyePos[1] - int(manuallyDetailAdjustEyePosition.eyeSize/2.0) >= speed:
        eyePos[1] = eyePos[1] - speed
    elif key == 63233: # down arrow
      if eyePos[1] + int(manuallyDetailAdjustEyePosition.eyeSize/2.0) <= height - speed:
        eyePos[1] = eyePos[1] + speed
    elif key == 63234: # left arrow
      if eyePos[0] - int(manuallyDetailAdjustEyePosition.eyeSize/2.0) >= speed:
        eyePos[0] = eyePos[0] - speed
    elif key == 63235: # right arrow
      if eyePos[0] + int(manuallyDetailAdjustEyePosition.eyeSize/2.0) <= width - speed:
        eyePos[0] = eyePos[0] + speed
      
    elif key == ord('n') or key == 32 or key == 9: # or 'SPACE' or 'TAB' - next picture
      exit = True
        
    elif key == ord('q'): # 'q' quit
      sys.exit(0)
      
    elif key == ord('f'): # 'f' speed
      speed = (speed + 5) % 10
  
    elif key == ord('s'): # change crosshair style
      NUMBEROFSTYLESAVAILABLE = 16
      manuallyDetailAdjustEyePosition.crosshairStyle = (manuallyDetailAdjustEyePosition.crosshairStyle + 1) % NUMBEROFSTYLESAVAILABLE
      
    elif key == ord('+'):
      if manuallyDetailAdjustEyePosition.eyeSize > 5:
        manuallyDetailAdjustEyePosition.eyeSize = manuallyDetailAdjustEyePosition.eyeSize - 5
    
    elif key == ord('-'):
      if eyePos[0] - int(manuallyDetailAdjustEyePosition.eyeSize/2.0) > 5 and \
         eyePos[0] + int(manuallyDetailAdjustEyePosition.eyeSize/2.0) < width - 5 and \
         eyePos[1] - int(manuallyDetailAdjustEyePosition.eyeSize/2.0) > 5 and \
         eyePos[1] + int(manuallyDetailAdjustEyePosition.eyeSize/2.0) < height - 5:
        
        manuallyDetailAdjustEyePosition.eyeSize = manuallyDetailAdjustEyePosition.eyeSize + 5
      
    else:
      print key
  
  cv.DestroyWindow(windowName)
  return (eyePos[0], eyePos[1]) 
  
  
def displayColoredRects(cvImage, fileName, rectsAndColor):
  """Draws supplied colored rectangles on supplied cvImage"""
  cv.NamedWindow(fileName, cv.CV_WINDOW_AUTOSIZE)

  copyImage = cv.CloneImage(cvImage)

  for rect, color in rectsAndColor:
    (x, y, w, h) = rect
    cv.Rectangle(copyImage, (x, y) , (x + w, y + h), color, 2)
  
  cv.ShowImage(fileName, copyImage)
  key = cv.WaitKey()
  cv.DestroyWindow(fileName)
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

"""
Everyday, look into my eyes! - ELIME 
------------------------------------

ELIME helps you create astonishing video from your everyday self portrait 
project's photos. It locates your eyes in the photos and stabilizes the photos 
around them. There are only a few steps necessary:
  - pre - Rename camera pictures into sortable names, by using their creation
          date. This is kind of optional. But I do it to normalize the somehow random 
          file names of digital cameras into sortable filenames that contain the date and
          time of picture creation. It will also copy the images to the working directory.
          Maybe you want to have a folder action triggering on a "drop" folder and call 
          pre automatically for you.
  - add - Detect eyes in your photos, manually adjust and save their positions
          to database
  - render - Based on eye positions, create JPGs from your pictures, scaled, 
             rotated and moved to perfect position

You can also do:
  - tidy - After you chose to delete a photo from your project's working directory, tidy 
           the database.
  - check - Use 'check' to go over eye positions of all or certain photos. 

"""
# python standard
import textwrap
import argparse
import ConfigParser
import os
import sys
import sqlite3
from datetime import datetime, timedelta, date
import shutil
import locale
import logging, logging.handlers

#Pillow
from PIL import Image, ImageDraw, ImageFont, ExifTags

#OpenCV
import cv

# ELIME Project
import DatabaseFunctions
import ImageFunctions
import OpenCvFunctions
import UiFunctions
import HelperFunctions


def setupLogging(logLevel=logging.DEBUG, logLevelConsole=logging.DEBUG, logLevelFile=logging.DEBUG, 
                 consoleString='%(levelname)s - %(message)s', 
                 fileString='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
                 logFile=None, maxBytes=666 * 1024, backupCount=5):
  """Sets up logging for ELIME Project"""
  
  logger = logging.getLogger('ELIME')
  logger.setLevel(logLevel)
  
  ch = logging.StreamHandler()
  ch.setLevel(logLevelConsole)

  cformatter = logging.Formatter(consoleString)

  ch.setFormatter(cformatter)

  logger.addHandler(ch)
  
  logger.debug('Setup of console logger done')
  
  if not (logFile is None):
    fh = logging.handlers.RotatingFileHandler(logFile, maxBytes=maxBytes, backupCount=backupCount)
    fh.setLevel(logLevelFile)
    
    fformatter = logging.Formatter(fileString)
    fh.setFormatter(fformatter)
    
    logger.addHandler(fh)
    logger.debug('Setup of file logger (to %s) done', logFile)
  else:
    logger.debug('No logging to logfile - no path specified!')


#
#
# The program's main functions
# 
#


def preProcessImageFiles(sourcePath, destinationPath=None, prefix=None, delete=False, customDateFormat=''):
  """Move image files from sourcePath to DestinationPath (permanent photo storage), renaming them with creation date"""
  logger = logging.getLogger('ELIME.pre')

  if not sourcePath:
    logger.error('sourcePath not valid')
    return
    
  if destinationPath is None:
    #copy and rename in place
    logger.warning('No destination path given. Using source path %s', sourcePath)
    destinationPath = sourcePath
    
  sourceFiles = []
  
  # get all files in sourcepath
  if os.path.isdir(sourcePath):
    sourceFiles = [ f for f in os.listdir(sourcePath) if os.path.isfile(os.path.join(sourcePath,f)) ]
  
  # filter only wanted files (jpgs)
  sourcePhotos = filter(HelperFunctions.filefilter, sourceFiles)
  
  count = len(sourcePhotos)
  if count:
    logger.info('Preprocessing %d photos from source %s to destination %s', count, sourcePath, destinationPath)
  else:
    logger.info('No photos to preprocess at %s', sourcePath)
    
  # rename files - as copy
  for photo in sourcePhotos:
    completeSourcePath = os.path.join(sourcePath, photo)
    
    photoDateTime = ImageFunctions.getCreationDateTimeOfPicture(completeSourcePath, customDateFormat)
    timestr = photoDateTime.strftime("%Y-%m-%d_%H-%M-%S")
    
    # create destination filename
    if prefix is None:
      destPath = os.path.join(destinationPath, timestr + os.path.splitext(photo)[1])
    else:
      destPath = os.path.join(destinationPath, prefix + '_' + timestr + os.path.splitext(photo)[1])
    
    logger.info("Copying: %s -> %s", completeSourcePath, destPath)
    
    # copy the file to destination
    if not os.path.isfile(destPath):
      shutil.copy2(completeSourcePath, destPath)
    else:
      logger.warning("File %s is already existing. Did not copy!", destPath)
      continue
    
    # delete source file if wanted (e.g. move and not copy)  
    if delete:
      logger.info("Deleting source file %s", completeSourcePath)
      os.remove(completeSourcePath)
  
  if count:      
    logger.info('Done preprocessing %d photos from source %s to destination %s!', count, sourcePath, destinationPath)

  
  
def addMissingEyeData(srcPath, dbPath, maxDimension=1024, detectionDebug=False, zoomSize=640, customDateFormat=''):
  """Add eye postions of photos not yet in database to database"""
  logger = logging.getLogger('ELIME.addToDB')
   
  if dbPath is None:
    logger.error("dbPath is invalid")
    return     
  
  if not os.path.exists(dbPath):
    logger.info("No Database file at %s ,yet.", dbPath)
  
  if srcPath is None:
    logger.error("srcPath is not valid")
    return
  
  logger.debug("Preparing database tables...")
  
  # create database if it does not exist yet
  DatabaseFunctions.prepareDataBaseTable(dbPath)
  
  # connect to database file
  conn = sqlite3.connect(dbPath, detect_types=sqlite3.PARSE_DECLTYPES)
  c = conn.cursor()
  
  # get all jpgs in source directory
  srcFiles = [ f for f in os.listdir(srcPath) if os.path.isfile(os.path.join(srcPath,f)) ]
  srcPhotos = filter(HelperFunctions.filefilter, srcFiles)
  
  numPhotos = len(srcPhotos)
  if numPhotos == 0:
    logger.warning("No photos found in source path %s", srcpath)
    return

  # get the number of pictures already in the database
  numAllDBPhotos = DatabaseFunctions.numberOfPhotosInDB(c)
  
  # simple consistency check on database: are there at least as many pictures in db as in
  # source path?
  if numPhotos < numAllDBPhotos:
    logger.warning("There are just %d photos in source path %s, but %d photos in database %s", numPhotos, srcPAth, numAllDBPhotos, dbPath)
    logger.warning("Please run a database tidy before, if you know what you are doing!")
    return
  
  # step through all pictures in sourcepath  
  for inputImageFileName in srcPhotos:
      
    logger.debug("Image name: %s", inputImageFileName)
    
    inputImageFilePath = os.path.join(srcPath, inputImageFileName)
    
    # get picture's creation date and time
    photoDateTime = ImageFunctions.getCreationDateTimeOfPicture(inputImageFilePath, customDateFormat)
    
    # check if photo is already and database
    c.execute('''SELECT * FROM eyesInPhotos WHERE photoFileName=?''',(inputImageFileName,))
    dbPhotos = c.fetchall()

    numDBPhotos = len(dbPhotos)

    if numDBPhotos == 0 or (numDBPhotos == 1 and ((dbPhotos[0][3] is None) or (dbPhotos[0][4] is None) or (dbPhotos[0][5] is None) or (dbPhotos[0][6] is None))):
      if numDBPhotos == 0:
        # the picture with this filename is not in database yet
        logger.info("Photo %s not in database yet", inputImageFileName)
      if numDBPhotos == 1:
        # there is one picture with the filename but data is incomplete
        logger.info("Eye info for photo %s in db incomplete (%d,%d), (%d,%d)", inputImageFileName, dbPhotos[0][3], dbPhotos[0][4], dbPhotos[0][5], dbPhotos[0][6])
      
      # find eye positions and add everything to database
      
      # create a opencv image from PIL image
      pilImage = ImageFunctions.loadAndTransposePILImage(inputImageFilePath)
      cvImage = ImageFunctions.convertPIL2CV(pilImage)

      # get the image size
      size = cv.GetSize(cvImage)
  
      # create scaling factor for too large images
      maxDimension = float(maxDimension)
      
      scale = 1.0
      if size[0] > maxDimension or size[1] > maxDimension:
        scale = max(size[0]/maxDimension, size[1]/maxDimension)

      logger.debug("Image scale factor is %f", scale)
      
      newSize = ( int(size[0] / scale), int (size[1] / scale) )

      # create a scaled down version of the original picture 
      scaledImage = cv.CreateImage(newSize, cvImage.depth, cvImage.nChannels)
      cv.Resize(cvImage, scaledImage)
      
      # find eye coordinates in scaled picture automatically
      scaledEyeRects = OpenCvFunctions.eyeRectsInImage(scaledImage, inputImageFileName, detectionDebug)
      logger.debug("Scaled eye rectangles detected %s", scaledEyeRects)
      
      scaledEyeCoordinates = []
      for scaledEyeRect in scaledEyeRects:
        scaledEyeCoordinates.append(HelperFunctions.middleOfRect(scaledEyeRect))
      
      logger.debug("Scaled eye positions detected %s", scaledEyeCoordinates)

      # manually adjust eye positions in scaled image
      scaledEyeCoordinates = UiFunctions.manuallyAdjustEyePositions(scaledImage, inputImageFileName, scaledEyeCoordinates)
      logger.debug("Scaled eye positions manually corrected %s", scaledEyeCoordinates)

      eyeCoordinates = []
      
      # scale back eye position to original sized image
      for eyeIndex, scaledEyePos in enumerate(scaledEyeCoordinates):
        (sx, sy) = scaledEyePos
        (eyecenterX, eyecenterY) = (int(sx * scale), int(sy * scale))
        logger.debug("True eye position of eye %d before manual correction %s", eyeIndex, (eyecenterX, eyecenterY))
        (x, y) = UiFunctions.manuallyDetailAdjustEyePosition(inputImageFileName, eyeIndex, cvImage, eyecenterX, eyecenterY, zoomSize)
        logger.debug("True eye position of eye %d after manual correction %s", eyeIndex, (x, y))
        eyeCoordinates.append((x, y))
        
      # save everything to database
      middleLeftEye = eyeCoordinates[0]
      middleRightEye = eyeCoordinates[1]
    
      if len(dbPhotos) == 0:
        # create new entry in db
        logger.debug("Executing: 'INSERT INTO eyesInPhotos (photoFileName, date, lEyeX, lEyeY, rEyeX, rEyeY) VALUES (%s, %s, %d, %d, %d, %d)'", 
          inputImageFileName, 
          photoDateTime, 
          middleLeftEye[0], 
          middleLeftEye[1], 
          middleRightEye[0], 
          middleRightEye[1])
          
        c.execute('INSERT INTO eyesInPhotos (photoFileName, date, lEyeX, lEyeY, rEyeX, rEyeY) VALUES (?, ?, ?, ?, ?, ?)', 
          (inputImageFileName, 
          photoDateTime, 
          middleLeftEye[0], 
          middleLeftEye[1], 
          middleRightEye[0], 
          middleRightEye[1]))
          
      else:
        # update entry in database			
        logger.debug("Executing: 'UPDATE eyesInPhotos SET lEyeX=%d, lEyeY=%d, rEyeX=%d, rEyeY=%d WHERE photoFileName=%s'",
          middleLeftEye[0], 
          middleLeftEye[1], 
          middleRightEye[0], 
          middleRightEye[1],
          inputImageFileNam)
        
        c.execute('UPDATE eyesInPhotos SET lEyeX=?, lEyeY=?, rEyeX=?, rEyeY=? WHERE photoFileName=?', 
          (middleLeftEye[0], 
          middleLeftEye[1], 
          middleRightEye[0], 
          middleRightEye[1],
          inputImageFileName))  
      
      conn.commit()
    
    # we found the image in the database with complete data or there are more than 1 image
    else:
      if numDBPhotos > 1:
        logger.critical("Database in bad shape. Found %d occurences of photo named %s", numDBPhotos, inputImageFileName)
        conn.close() 
        sys.exit(1)
      else:
        logger.info("Photo %s already in db", inputImageFileName)
        
  newNumAllDBPhotos = DatabaseFunctions.numberOfPhotosInDB(c)
        
  logger.info("Added %d photos with eyeinfo to database %s",  newNumAllDBPhotos - numAllDBPhotos, dbPath)
  conn.close()    


def checkEyeData(srcPath, dbPath, beginWith=[], maxDimension = 1024, zoomSize=640, detailOnly=True):
  """Check and correct eye positions in database on all or selected image files"""
  logger = logging.getLogger('ELIME.checkEyeDataOfPhotos')
  
  logger.info("Checking eyepositions stored in db")
  
  if dbPath is None:
    logger.error("dbPath is invalid")
    return  
  
  if srcPath is None:
    logger.error("srcPath is invalid")
    return
  
  # connect to databse
  conn = sqlite3.connect(dbPath, detect_types=sqlite3.PARSE_DECLTYPES)
  c = conn.cursor() 
  
  # get list of files to check eye positions
  # assume we get it alphabetically ordered
  # begin with photo named in variable beginWith or take all
  filenames = []
  
  processing = True
  
  filenames = [ f for f in os.listdir(srcPath) if os.path.isfile(os.path.join(srcPath,f)) ]
  
  if len(beginWith) == 0:
    logger.debug("No filename to begin with specified. Will check all.")
  else:
    logger.debug("Starting with photo named %s", beginWith[0])
    processing = False
  
  # filter for jpgs   
  filenames = filter(HelperFunctions.filefilter, filenames)
  
  for filename in filenames:
    # start processing with given filename, if any
    if not processing:
      if filename == beginWith[0]:
        processing = True
      else:
        continue
          
    logger.debug("Image name: %s", filename)
    
    inputImageFilePath = os.path.join(srcPath, filename)
    
    # get pictures stored info from database
    c.execute('''SELECT * FROM eyesInPhotos WHERE photoFileName=?''',(filename,))
    dbPhotos = c.fetchall()

    numDBPhotos = len(dbPhotos)

    if numDBPhotos == 0:
      logger.error("Photo named %s not in database! Do nothing. You should add it!", filename)
      continue
      
    if numDBPhotos == 1:
      lEyeX = int(dbPhotos[0][3])
      lEyeY = int(dbPhotos[0][4])
      rEyeX = int(dbPhotos[0][5])
      rEyeY = int(dbPhotos[0][6])
      
      logger.debug("Eye position in db: lEyeX=%d, lEyeY=%d, rEyeX=%d, rEyeY=%d", lEyeX, lEyeY, rEyeX, rEyeY) 
      
      # load image to opencv image
      pilImage = ImageFunctions.loadAndTransposePILImage(inputImageFilePath)
      cvImage = ImageFunctions.convertPIL2CV(pilImage)

      # scale it down
      size = cv.GetSize(cvImage)
      
      maxDimension = float(maxDimension)
      
      scale = 1.0
      if size[0] > maxDimension or size[1] > maxDimension:
        scale = max(size[0]/maxDimension, size[1]/maxDimension)

      newSize = ( int(size[0] / scale), int (size[1] / scale) )

      scaledImage = cv.CreateImage(newSize, cvImage.depth, cvImage.nChannels)
      cv.Resize(cvImage, scaledImage)
      
      # calculate scaled eye coordinates      
      scaledEyeCoordinates = [(int(lEyeX / scale), int(lEyeY / scale)),
                              (int(rEyeX / scale), int(rEyeY / scale))]
      
      eyeCoordinates = [(lEyeX, lEyeY), (rEyeX, rEyeY)]
      
      # if we show not only show the zoomed detail one eye view but the whole picture
      if not detailOnly:
        # coarse eye positions in total face/image view
        newScaledEyeCoordinates = UiFunctions.manuallyAdjustEyePositions(scaledImage, filename, scaledEyeCoordinates)  
      
        if scaledEyeCoordinates == newScaledEyeCoordinates:
          logger.debug("No new coarse eye positions, taking positions from database for fine control")      
        else:
          logger.debug("New eye positions in coarse image set, taking these for fine control")
          eyeCoordinates = []  
          for scaledEyePos in newScaledEyeCoordinates:  
            (sx, sy) = scaledEyePos
            eyeCoordinates.append((int(sx * scale), int(sy * scale)))
      
      newEyeCoordinates = []
      
      # detail set eye position, one per eye
      for eyeIndex, eyeCoordinate in enumerate(eyeCoordinates):
        logger.debug("Eye position of eye %d before manual correction %s", eyeIndex, (eyeCoordinate[0], eyeCoordinate[1]))
        
        (x, y) = UiFunctions.manuallyDetailAdjustEyePosition(filename, eyeIndex, cvImage, eyeCoordinate[0], eyeCoordinate[1], zoomSize)
        
        logger.debug("True eye position of eye %d after manual correction %s", eyeIndex, (x, y))
        newEyeCoordinates.append((x, y))

      middleLeftEye = newEyeCoordinates[0]
      middleRightEye = newEyeCoordinates[1]
        
      # and update the database
      logger.info("Executing: 'UPDATE eyesInPhotos SET lEyeX=%d, lEyeY=%d, rEyeX=%d, rEyeY=%d WHERE photoFileName=%s'",
        middleLeftEye[0], 
        middleLeftEye[1], 
        middleRightEye[0], 
        middleRightEye[1],
        filename)
      
      c.execute('UPDATE eyesInPhotos SET lEyeX=?, lEyeY=?, rEyeX=?, rEyeY=? WHERE photoFileName=?', 
        (middleLeftEye[0], 
        middleLeftEye[1], 
        middleRightEye[0], 
        middleRightEye[1],
        filename))  
    
      conn.commit()

    if numDBPhotos > 1:
      logger.critical("Database in bad shape. Found %d occurences of photo named %s", numDBPhotos, filename)
      conn.close() 
      sys.exit(1)
  
  logger.info("Checking Eyepositions finished.")   
  conn.close() 


def tidyDB(srcPath, dbPath):
  """Delete photos from database that are missing in permanent photo storage"""
  logger = logging.getLogger('ELIME.tidyDB')
  
  if dbPath is None:
    logger.error("dbPath is not valid")
    return
    
  if srcPath is None:
    logger.error("srcPath is invalid")
    return
  
  # connect to the database  
  conn = sqlite3.connect(dbPath, detect_types=sqlite3.PARSE_DECLTYPES)
  c = conn.cursor() 
  
  
  numDBPhotos = DatabaseFunctions.numberOfPhotosInDB(c)
  
  if numDBPhotos == 0:
    logger.error("The Database at %s is empty already", dbPath)
    return
   
  logger.info("Start tidying database %s. There are %d photos in DB before tidying.", dbPath, numDBPhotos)
  
  # now find all db photos that cannot be found on disk aka srcPath anymore 
  c.execute('''SELECT * FROM eyesInPhotos ORDER BY date''')
  dbPhotos = c.fetchall()
  
  photosToDelete = []
  
  for photo in dbPhotos:
    path = os.path.join(srcPath, photo[1])
    if os.path.exists(path):
      logger.debug("Photo %s found on disk", photo[1])
    else:
      logger.debug("Photo %s not found on disk. Add to delete list.", photo[1])
      photosToDelete.append(photo[1])

  numDelete = len(photosToDelete)
  
  if numDelete > 0:
    print "Do you want to delete these", numDelete, "photos?"
    for name in photosToDelete:
      print name
    
    decision = raw_input('Do you want to remove these photos from database? [delete/no]:')
    if decision == 'delete':
      for name in photosToDelete:
        c.execute('''DELETE FROM eyesInPhotos WHERE photoFileName=?''', (name,))
        logger.debug("Executing: 'DELETE FROM eyesInPhotos WHERE photoFileName=%s'", name)
        conn.commit()
    else:
      print "Deletion aborted."
      
  else:
    print "All photos in DB", dbPath ,"were found in srcPath", srcPath
      
  numDBPhotos = DatabaseFunctions.numberOfPhotosInDB(c)    
  logger.info("Finished tidying database %s. There are %d photos in DB now.", dbPath, numDBPhotos)
  
  conn.close()
  
  
def renderPhotos(srcPath, dstPath, dbPath, mode='fill', offset_pct=(0.43,0.425),
                 dest_sz=(1920,1080), ttfontpath="./HelveticaNeueLight.ttf", 
                 fontSize=64, format='%x', localestr="de_DE", show=False, 
                 posDebug=False):
  """Render all photos from database to disk with correct eye positions"""
  #use "fondu" to get ttf on mac os x
  logger = logging.getLogger('ELIME.renderPhotos')
  
  
  if dbPath is None:
    logger.error("dbPath is not valid")
    return
    
  if srcPath is None:
    logger.error("srcPath is not valid")
    return
  
  if dstPath is None:
    logger.error("dstPath is not valid")
    return
    
  if srcPath == dstPath:
    logger.error("srcPath and dstPath MUST be different for security reasons;-)")
    return
  
  # set up locale
  locale.setlocale(locale.LC_TIME, localestr)
  
  # load truetype font for date imprint
  ttfont = None 
  
  if ttfontpath is not None:
    ttfontpath = os.path.abspath(ttfontpath)
    if os.path.isfile(ttfontpath):
      logger.info("Fontrendering active using font path %s", ttfontpath)
      ttfont = ImageFont.truetype(ttfontpath, fontSize)
    else:
      logger.error("Fontpath %s is not a file", ttfontpath)
      return None
      
  # connect to database
  conn = sqlite3.connect(dbPath, detect_types=sqlite3.PARSE_DECLTYPES)
  c = conn.cursor() 
  
  # get photos ordered by date
  c.execute('''SELECT * FROM eyesInPhotos ORDER BY date''')
  dbPhotos = c.fetchall()
  
  for photo in dbPhotos:
    if not os.path.exists(os.path.join(srcPath, photo[1])):
      logger.error("Photo %s does not exist in srcPath %s! Check path, do tidydb, then try again!", photo[1], srcPath)
      sys.exit(1)
  
  # get time span of pictures in database      
  firstDatetime = dbPhotos[0][2].date()
  lastDatetime = dbPhotos[-1][2].date()
  
  logger.info("First photo %s in database taken on %s", dbPhotos[0][1], firstDatetime)
  logger.info("Last photo %s in database taken on %s", dbPhotos[-1][1], lastDatetime)

  # in fill mode, there will be created a frame for every day in the time span interval
  # if there is a picture in the database for each day or not
  # it is assumed that there is only one picture per date.
  if mode == 'fill':
    
    numdays = (lastDatetime - firstDatetime).days
    logger.info("Will generate %d frames", numdays)
    
    dates = [firstDatetime + timedelta(days=i) for i in range(0, numdays + 1)]
  
    brightness = 1.0
    
    lastPhoto = None
    for aDate in dates:
      for photo in dbPhotos:
        if photo[2].date() == aDate:
          lastPhoto = photo
          brightness = 1.0
          break
      else:
        logger.debug("No photo for date %s in database", aDate)
        brightness *= 0.90
        lastPhoto = (lastPhoto[0], lastPhoto[1], datetime(aDate.year, aDate.month, aDate.day), lastPhoto[3], lastPhoto[4], lastPhoto[5], lastPhoto[6])

      logger.info("Rendering Image %s, date %s", lastPhoto[1], lastPhoto[2].strftime(format))
      
      pilImage = ImageFunctions.renderPhoto(srcPath, lastPhoto, ttfont, format, offset_pct, dest_sz, brightness, posDebug)
      
      if show:
        cvImage = ImageFunctions.convertPIL2CV(pilImage)
        cv.NamedWindow(lastPhoto[1]+ " " + aDate.strftime(format), cv.CV_WINDOW_AUTOSIZE)
        cv.ShowImage(lastPhoto[1]+ " " + aDate.strftime(format), cvImage) 
        key = cv.WaitKey()
        
        if key == 113: # 'q' quit
          sys.exit(0)  
        
        cv.DestroyWindow(lastPhoto[1]+ " " + aDate.strftime(format))
      
      pilImage.save(os.path.join(dstPath, 'rendered_' + lastPhoto[2].strftime("%Y_%m_%d") + '.jpg'), quality=95)
  
  # in all mode render every picture in database, skip dates with no pics
  if mode == 'all':
    for photo in dbPhotos:
      logger.info("Rendering Image %s, date %s", photo[1], photo[2].strftime(format))
    
      pilImage = ImageFunctions.renderPhoto(srcPath, photo, ttfont, format, offset_pct, dest_sz, 1.0, posDebug)      
      
      if show:
        cvImage = ImageFunctions.convertPIL2CV(pilImage)
        cv.NamedWindow(photo[1]+ " " + photo[2].strftime(format), cv.CV_WINDOW_AUTOSIZE)
        cv.ShowImage(photo[1]+ " " + photo[2].strftime(format), cvImage) 
        key = cv.WaitKey()
        
        if key == 113: # 'q' quit
          sys.exit(0)  
        
        cv.DestroyWindow(photo[1]+ " " + photo[2].strftime(format))
          
      pilImage.save(os.path.join(dstPath, 'rendered_' + photo[2].strftime("%Y_%m_%d") + '.jpg'), quality=95)
    
  conn.close()       
      
  # ffmpeg -f image2 -r 5 -pattern_type glob -i 'render*.jpg' -c:v libx264 -r 30 out.mp4    
  
  
def main():

  configTemplate = """  [ELIME]
  # dbFile - The file path to where your eye position database will be 
  #  stored
  dbFile = ~/Documents/ELIME Project/Database/eyepositions.db

  # sourceFolder - The folder where ELIME's pre(process) command will find
  #  your unrenamed digital cameras photos
  sourceFolder = ~/Documents/ELIME Project/Drop Regular Files/

  # prefix - The prefix ELIME's pre(process) command will prepend to your
  #  photo's creation date to create the new filename
  prefix = christoph

  # delete - If ELIME should move (and not copy) your photos while renaming
  #  from sourceFolder to photoFolder
  delete = true

  # photoFolder - The folder where all your (preprocessed) daily photos
  #  savely and permanently are stored. The names of the photos in that 
  #  folder get stored in the eye position database.
  photoFolder = ~/Documents/ELIME Project/Photo Storage/

  # targetFolder - The folder where the rendered (scaled and roated) images
  #  that make up the frames of your project's video get saved. Must be 
  #  different from photoFolder for "security reasons" (tm)
  targetFolder = ~/Documents/ELIME Project/temp/

  # maxSize - The maximum x or y of the image's dimensions on which ELIME 
  #  will automatically detect eye positions and show in window. Do not go
  #  over 1024! The final size of the rendered images is completey 
  #  independent from this!
  maxSize = 1024
  
  # posDebug - Draws a colored pixel at the the eyes' positions in the rendered
  #  output images.
  posDebug = false
  
  # detectionDebug - Shows all detected eyes and faces before manual fine 
  #  control.
  detectionDebug = false
  
  # openCVHaarcascadesFolder - Path to where your opencv installation's 
  #  haarcascades reside.
  openCVHaarcascadesFolder = /usr/local/opt/opencv/share/OpenCV/haarcascades/
  """

  defaultConfigPath = os.path.expanduser('~/.ELIME.cfg')

  defaultValues = {'delete': 'false', 'maxSize': '1024', 'prefix': 'elime', 
                   'posDebug': 'false', 'detectionDebug': 'false', 
                   'openCVHaarcascadesFolder': '/usr/local/opt/opencv/share/OpenCV/haarcascades/'}

  conf_parser = argparse.ArgumentParser(add_help=False)
  conf_parser.add_argument("-c", "--conf", help="Use config file not located in '~/.ELIME.cfg' (which is the default path for ELIME's config file)", metavar="FILE")
  conf_parser.add_argument("-cc", "--createConf", action='store_true', help="Create new config file from config file template")
  args, remainingArgv = conf_parser.parse_known_args()

  if args.conf:
    defaultConfigPath = args.confFile

  if args.createConf:
    if os.path.exists(defaultConfigPath):
      print "File exists:", defaultConfigPath, "will not overwrite! Exit."
      sys.exit(1)
    with open(defaultConfigPath, 'wb') as configfile:
      configfile.write(textwrap.dedent(configTemplate))
      
    print "Created config file template at", defaultConfigPath, "Go now and customize it! ELIME's waiting here."
    sys.exit(0)

  if os.path.exists(defaultConfigPath):
    config = ConfigParser.SafeConfigParser(defaults=defaultValues, allow_no_value=True)
    config.read([defaultConfigPath])
  
    if not config.has_section('ELIME'):
      print "The config file at", defaultConfigPath, "is not a valid ELIME config file. No 'ELIME' section found. Exit."
      sys.exit(1)
    
    # print config.items('ELIME')
  
    if config.has_option('ELIME', 'dbFile'):
      defaultValues['dbFile'] = config.get('ELIME', 'dbFile')
  
    if config.has_option('ELIME', 'sourceFolder'):
      defaultValues['sourceFolder'] = config.get('ELIME', 'sourceFolder')
    
    if config.has_option('ELIME', 'prefix'):
      defaultValues['prefix'] = config.get('ELIME', 'prefix')
    
    if config.has_option('ELIME', 'delete'):
      defaultValues['delete'] = config.getboolean('ELIME', 'delete')

    if config.has_option('ELIME', 'photoFolder'):
      defaultValues['photoFolder'] = config.get('ELIME', 'photoFolder')
        
    if config.has_option('ELIME', 'targetFolder'):
      defaultValues['targetFolder'] = config.get('ELIME', 'targetFolder')
    
    if config.has_option('ELIME', 'maxSize'):
      defaultValues['maxSize'] = config.getint('ELIME', 'maxSize') 
      
    if config.has_option('ELIME', 'posDebug'):
      defaultValues['posDebug'] = config.getboolean('ELIME', 'posDebug')
      
    if config.has_option('ELIME', 'detectionDebug'):
      defaultValues['detectionDebug'] = config.getboolean('ELIME', 'detectionDebug')
    
    if config.has_option('ELIME', 'openCVHaarcascadesFolder'):
      defaultValues['openCVHaarcascadesFolder'] = config.get('ELIME', 'openCVHaarcascadesFolder')
    
    
  #print defaultValues  

  if not isinstance(defaultValues['delete'], bool):
    defaultValues['delete'] = defaultValues['delete'] in ['true', 'True']
    
  if not isinstance(defaultValues['posDebug'], bool):
    defaultValues['posDebug'] = defaultValues['posDebug'] in ['true', 'True']
    
  if not isinstance(defaultValues['detectionDebug'], bool):
    defaultValues['detectionDebug'] = defaultValues['detectionDebug'] in ['true', 'True']

  if not isinstance(defaultValues['maxSize'], int):
    defaultValues['maxSize'] = int(defaultValues['maxSize'])
  
  # print defaultValues

  parser = argparse.ArgumentParser(parents=[conf_parser], description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, epilog = "Everyday, look into my eyes!")
  parser.set_defaults(**defaultValues)

  # main parser
  parser.add_argument('--logFile', help='To enable log to file specify path of logfile')

  subparsers = parser.add_subparsers(dest='subparser_name')

  # create the parser for the "pre" command
  parser_pre = subparsers.add_parser('pre', help='Tries to determines your photos creation date and renames and moves your photos to the permanent photo folder.')
  parser_pre.add_argument('-sF', '--sourceFolder', help="The folder where ELIME's pre(process) command will find your unrenamed digital cameras photos")
  parser_pre.add_argument('-pF', '--photoFolder', help='The folder where all your (preprocessed) daily photos savely and permanently are stored. The names of the photos in that folder get stored in the eye position database.')
  parser_pre.add_argument('-p', '--prefix', help="The prefix ELIME's pre(process) command will prepend to your photo's creation date to create the new filename")
  parser_pre.add_argument('-d', '--delete', action='store_true', help='If ELIME should move (and not copy) your photos while renaming from sourceFolder to photoFolder')
  parser_pre.add_argument('-mS', '--maxSize', type=int, help="The maximum x or y of the image's dimensions on which ELIME will automatically detect eye positions and show in window. Do not go over 1024! The final size of the rendered images is completey independent from this!")
  parser_pre.set_defaults(func=preProcessImageFiles)
  # the lines in the subparsers like the next line was not needed before. Just a quick hack. Might be not the optimal solution for why it suddenly does not work anymore without.
  parser_pre.set_defaults(**defaultValues)

  # create the parser for the "add" command
  parser_add = subparsers.add_parser('add', help='"Automagically" detects your eyes in your photos from the photoFolder, lets you do fine adjustments and saves eye locations to database file.')
  parser_add.add_argument('-pF', '--photoFolder', help='The folder where all your (preprocessed) daily photos savely and permanently are stored. The names of the photos in that folder get stored in the eye position database.')
  parser_add.add_argument('-dF', '--dbFile', help='The file path to where your eye position database will be stored')
  parser_add.add_argument('-mS', '--maxSize', type=int, help="The maximum x or y of the image's dimensions on which ELIME will automatically detect eye positions and show in window. Do not go over 1024! The final size of the rendered images is completey independent from this!")
  parser_add.add_argument('--detectionDebug', action='store_true', help="Shows all detected eyes and faces before manual fine control.")
  parser_add.add_argument('-oF', '--openCVHaarcascadesFolder', help="Path to where your opencv installation's haarcascades reside.")
  parser_add.set_defaults(func=addMissingEyeData)
  parser_add.set_defaults(**defaultValues)

  # create the parser for the "check" command  
  parser_check = subparsers.add_parser('check', help='If you want to correct saved eye positions in database, here you can.')
  parser_check.add_argument('-pF', '--photoFolder', help='The folder where all your (preprocessed) daily photos savely and permanently are stored. The names of the photos in that folder get stored in the eye position database.')
  parser_check.add_argument('-dF', '--dbFile', help='The file path to where your eye position database are be stored')
  parser_check.add_argument('-mS', '--maxSize', type=int, help="The maximum x or y of the image's dimensions on which ELIME will automatically detect eye positions and show in window. Do not go over 1024! The final size of the rendered images is completey independent from this!")
  parser_check.add_argument('beginWith', nargs='*', help='Filename to begin with checking.')
  parser_check.set_defaults(func=checkEyeData)  
  parser_check.set_defaults(**defaultValues)
    
  # create the parser for the "tidy" command
  parser_tidy = subparsers.add_parser('tidy', help='Did you delete photos from your photoFolder? Run tidy to tidy the eyeposition database from deleted pictures.')
  parser_tidy.add_argument('-pF', '--photoFolder', help='The folder where all your (preprocessed) daily photos savely and permanently are stored. The names of the photos in that folder get stored in the eye position database.')
  parser_tidy.add_argument('-dF', '--dbFile', help='The file path to where your eye position database are be stored')
  parser_tidy.set_defaults(func=tidyDB)
  parser_tidy.set_defaults(**defaultValues)  
  
  # create the parser for the "render" command
  parser_render = subparsers.add_parser('render', help='Render your photos - scaled, moved and roated based on your eye positions stored in database into JPGs for further processing.')
  parser_render.add_argument('-pF', '--photoFolder', help='The folder where all your (preprocessed) daily photos savely and permanently are stored. The names of the photos in that folder get stored in the eye position database.')
  parser_render.add_argument('-dF', '--dbFile', help='The file path to where your eye position database are be stored')
  parser_render.add_argument('-tF', '--targetFolder', help="The folder where the rendered (scaled and roated) images that make up the frames of your project's video get saved. Must be different from photoFolder for 'security reasons' (tm)")
  parser_render.add_argument('--posDebug', action='store_true', help="Draws a colored pixel at the the eyes' positions in the rendered output images")
  parser_render.set_defaults(func=renderPhotos)
  parser_render.set_defaults(**defaultValues)
  
  #print parser_pre.get_default("sourceFolder")
  
  #print remainingArgv
  args = parser.parse_args(remainingArgv)
	
  #print args
	
  args.logFile = HelperFunctions.checkFile(args.logFile)
  
  setupLogging(logFile=args.logFile)
  
  if args.func == preProcessImageFiles:
    args.sourceFolder = HelperFunctions.checkFolder(args.sourceFolder)
    args.photoFolder = HelperFunctions.checkFolder(args.photoFolder)
    args.func(args.sourceFolder, args.photoFolder, args.prefix, args.delete)
  
  if args.func == addMissingEyeData:
    args.openCVHaarcascadesFolder = HelperFunctions.checkFolder(args.openCVHaarcascadesFolder)
    OpenCvFunctions.PATHTOCASCADES = args.openCVHaarcascadesFolder
    
    args.photoFolder = HelperFunctions.checkFolder(args.photoFolder)
    args.dbFile = HelperFunctions.checkFile(args.dbFile)

    args.func(args.photoFolder, args.dbFile, args.maxSize, 
              detectionDebug=args.detectionDebug)
    
  if args.func == checkEyeData:
    args.photoFolder = HelperFunctions.checkFolder(args.photoFolder)
    args.dbFile = HelperFunctions.checkFile(args.dbFile)

    args.func(args.photoFolder, args.dbFile, args.beginWith, args.maxSize)
    
  if args.func == tidyDB:
    args.photoFolder = HelperFunctions.checkFolder(args.photoFolder)
    args.dbFile = HelperFunctions.checkFile(args.dbFile)

    args.func(args.photoFolder, args.dbFile)
  
  if args.func == renderPhotos:
    args.photoFolder = HelperFunctions.checkFolder(args.photoFolder)
    args.dbFile = HelperFunctions.checkFile(args.dbFile)
    args.targetFolder = HelperFunctions.checkFolder(args.targetFolder)

    args.func(args.photoFolder, args.targetFolder, args.dbFile, 
              posDebug=args.posDebug)
      
  sys.exit(0)
 
if __name__ == "__main__":
  main ()
  

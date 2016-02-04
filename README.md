ELIME - Everyday Look Into My Eyes
==============

Overview
--------------

ELIME is a useful little python program that helps you create amazing videos of your 
everyday selfie photo project. It finds the position of your eyes in the photos 
automatically and will let you set pixel perfect anchor points for adjusting the photos to 
the position of your eyes. When you render the photos to video you get exact same position
in every frame thus achieving a great and steady flow of images for your viewing pleasure.

The eye positions are detected automatically using complex computer vision algorithms
from the great openCV project. Only minor manual corrections to each found position are 
necessary to achieve the best effect. The processing of each image, automatically and 
manually, only takes a view moments. The position of the eyes, along with the photo's name
and date of creation get saved in a sqlite database.

When the eyes' position in every photo have been stored, ELIME renders the aligned images
out for e.g. further processing by ffmpeg.


Installation
--------------

You basically need python 2.7.x, opencv and PIL to get ready to use ELIME.

On Mac OS X I use homebrew to install a current python. 
 *brew install python*

Install opencv like this:
 *pip install numpy* 
 *brew tap homebrew/science*
 *brew install opencv*

Last time I checked, PIL was removed from homebrew and from pip. So install Pillow instead
 
 *brew install libtiff libjpeg webp little-cms2*
 *pip install Pillow*
 
 How to use it
 --------------
 
 The first time you use ELIME, run ELIME.py with the --cc option to create a config file
 in your home directory (~/.ELIME.cfg).
 
 Edit this file to tell ELIME where to find your photos, where to put them after renaming,
 where to put its database file, where to put rendered (temporary) images and so on.
 
 When you are done configuring ELIME. There are those typical steps you invoke:
 
  - pre - Rename camera pictures into sortable names, by using their creation
          date. This is kind of optional. But I do it to normalize the somehow random 
          file names of digital cameras into sortable filenames that contain the date and
          time of picture creation. It will also copy the images to the working directory.
          Maybe you want to have a folder action triggering on a "drop" folder and call 
          pre automatically for you.
  - add - Detect eyes in your photos, manually adjust and add their positions to database
  - render - Based on eye positions, create JPGs from your pictures, scaled, 
             rotated and moved to perfect position

You can also do:
  - tidy - After you chose to delete a photo from your project's working directory, tidy 
           the database.
  - check - Use 'check' to go over eye positions of all or certain photos.

IMPORTANT NOTICE
---------------
Due to changes in the current version of opencv in homebrew on Mac OS X
ELIME sadly cannot be used here. A rewrite to use the new cv2 python API seems the only
way to solve this. Maybe installation of an older opencv is also an OK workaround.
 

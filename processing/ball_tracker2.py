"""
2020 Frc Infinite Recharge
Ball Intake Detection
uses contour lines, rough area calculations
width/height ratios, and radius of contours found
in masked image to find ball
"""

import cv2
from processing import colors
from processing import cvfilters
from processing import shape_util

MIN_AREA = 5
BALL_RADIUS = 3.5

debug = False

def process(img, camera, frame_cnt, color_profile):
  global rgb_window_active, hsv_window_active

  FRAME_WIDTH = camera.FRAME_WIDTH
  FRAME_HEIGHT = camera.FRAME_HEIGHT
  red = color_profile.red
  green = color_profile.green
  blue = color_profile.blue
  hue = color_profile.hsv_hue
  sat = color_profile.hsv_sat
  val = color_profile.hsv_val

  tracking_data = []
  original_img = img

  img = cv2.GaussianBlur(img, (13, 13), 0)
  #cv2.imshow('img', img)
  hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
  mask_hsv = cv2.inRange(hsv, (hue.min, sat.min, val.min),  (hue.max, sat.max, val.max))
  mask_rgb = cv2.inRange(img, (red.min, green.min, blue.min), (red.max, green.max, blue.max))
  img = cvfilters.apply_mask(img, mask_hsv)
  img = cvfilters.apply_mask(img, mask_rgb)
  img = cv2.erode(img, None, iterations=2)
  img = cv2.dilate(img, None, iterations=2)
  img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

  if debug:
    cv2.imshow('ball tracker img', img)

  contours, hierarchy = cv2.findContours(img,
                                              cv2.RETR_EXTERNAL,
                                              cv2.CHAIN_APPROX_SIMPLE)

  contour_list = []

  # algorithm for detecting rectangular object (loading bay)
  for (index, contour) in enumerate(contours):

    peri = cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, 0.04 * peri, True)
    area = cv2.contourArea(approx)
    # limit the number of contours to process
    #

    #print('%s area:%s' %(index, area) )
    if area > MIN_AREA:
      x, y, w, h = cv2.boundingRect(approx)
      center_mass_x = x + w / 2
      center_mass_y = y + h / 2
      ((x,y), radius) = cv2.minEnclosingCircle(contour)
      contour_list.append(contour)
            
      #
      # tests for if its width is around its height which should be true

      # print('x: %s y:%s ratio:%s' % (w, h, w/h))

      if True :
        #convert distance to inches
        distance = shape_util.distance_in_inches(w)
        angle = shape_util.get_angle(camera, center_mass_x, center_mass_y)
        font = cv2.FONT_HERSHEY_DUPLEX

        #if(BALL_RADIUS * 0.9 <= radius <= BALL_RADIUS * 1.10):
        # cv2.circle(original_img, (int(x), int(y)), int(radius), colors.GREEN, 2)
        # print 'x:%s, y:%s angle:%s ' % ( center_mass_x, center_mass_y, angle )


        data = dict(shape='BALL',
            radius=radius,
            dist=distance,
            angle=angle,
            xpos=center_mass_x,
            ypos=center_mass_y)

        tracking_data.append(data)

        # #labels image
        # radius_text = 'radius:%s' % (radius)
        # coordinate_text = 'x:%s y:%s ' % (center_mass_x, center_mass_y)
        # area_text = 'area:%s width:%s height:%s' % (area, w, h)
        # angle_text = 'angle:%.2f  distance:%.2f' % (angle, distance)

        # cv2.putText(original_img, coordinate_text, (int(x), int(y) - 35), font, .4, colors.WHITE, 1, cv2.LINE_AA)
        # cv2.putText(original_img, area_text, (int(x), int(y) - 20), font, .4, colors.WHITE, 1, cv2.LINE_AA)
        # cv2.putText(original_img, angle_text, (int(x), int(y) - 5), font, .4, colors.WHITE, 1, cv2.LINE_AA)
        # cv2.putText(original_img, radius_text, (int(x), int(y) - 50), font, .4, colors.WHITE, 1, cv2.LINE_AA)

        # cv2.line(original_img, (FRAME_WIDTH // 2, FRAME_HEIGHT), (int(center_mass_x), int(center_mass_y)), colors.GREEN, 2)
        # cv2.drawContours(original_img, contours, index, colors.GREEN, 2)

      elif debug:

        cv2.drawContours(original_img, contours, index, colors.random(), 2)
        #cv2.rectangle(original_img, (x, y), (x + w, y + h), colors.WHITE, 2)

        # print the rectangle that did not match

      #
      # print 'square: %s,%s' % (w,h)
      # print w/h, h/w
  # top_center = (FRAME_WIDTH // 2, FRAME_HEIGHT)
  # bottom_center = (FRAME_WIDTH // 2, 0)
  # cv2.line(original_img, top_center, bottom_center, colors.WHITE, 4)

  return tracking_data

def combine(img, tracking_data, ml_data, leeway):
  height, width, _ = img.shape

  valid_tracking_data = []

  alpha = 0.3

  out_img = img.copy()
  overlay = img.copy()

  for region in ml_data:
    if region['class_id'] == 3:
      b_box = region['bounding_box']
      klass = region['class_id']
      score = region['score']

      top = int(b_box[0] * height)
      left = int(b_box[1] * width)
      bottom = int(b_box[2] * height)
      right =  int(b_box[3] * width)
    
      cv2.rectangle(overlay, (left, top), (right, bottom), colors.GREEN, -1)

      for target in tracking_data:
        x_center = int(target['xpos'])
        y_center = int(target['ypos'])
        xpos_in_bounds = left - leeway < x_center and right + leeway > x_center
        ypos_in_bounds = top - leeway < y_center and bottom + leeway > y_center

        # print('left: ' + str(left) + '     right: ' + str(right) + '     acc: ' + str(target['xpos']))
        # print('top: ' + str(top) + '     bottom: ' + str(bottom) + '     acc: ' + str(target['ypos']))

        if xpos_in_bounds and ypos_in_bounds and score > 0.0:
          valid_tracking_data.append(target)
          
  
  cv2.addWeighted(overlay, alpha, out_img, 1 - alpha, 0, out_img)

  for target in valid_tracking_data:
    cv2.circle(out_img, (int(target['xpos']), int(target['ypos'])), int(target['radius']), colors.BLUE, 2)
    cv2.circle(out_img, (int(target['xpos']), int(target['ypos'])), 4, colors.BLUE, -1)

  return out_img, valid_tracking_data


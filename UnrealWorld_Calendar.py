# -*- coding: utf-8 -*-
import pygame
import sys
import os
import re
import json
import time
import csv
import GameDateTime as gdt
from pathlib import Path
import numpy as np
from collections import defaultdict

# Todo:
# Add custom marker for quests


pygame.init()

DEBUG = False

print_once = True

SCREEN_WIDTH = 1600
SCREEN_HEIGHT = 900

class URL_Calendar():
  # --- Constants ---
  def __init__(self):
    self.last_x = 0
    self.last_y = 0
    self.at_home = False
    self.event_markers = {}
    self.todays_events = {}
    self.weekly_events = {}
    self.tally_stats = {}
    self.temp_village_content = []
    self.fuzzy_village_content = []
    self.logfile_changed_ts = None
    self.current_timestamp = None
    self.new_state = None
    self.progress = None
    self.has_dog = False
    self.in_settlement = False
    self.current_settlement_key = None
    self.village_goods = {}
    self.food_storage = {}
    self.blacksmith = {}
    self.revisited_tile = -1
    self.fow = set()
    self.zoom_level = 4
    self.map_x = 10
    self.map_y = 0
    self.map_width = 550
    self.map_height = 460
    self.map_surface = None
    self.fog_surface = None
    self.map_rect = None
    self.world_anchor = (0,0)
    self.highlight = None
    self.time_enter_rect = 0
    self.tooltip = None
    self.no_tiles = True
    self.menu_open = False
    self.menu_pos = (-1, -1)
    self.tooltip_pos = (-1, -1)
    self.menu_date = None
    self.map_tiles = [2730, 2048]
    self.tiles_sizes = [[0,0],[1.125,1.25], [2.25,2.5],[4.5,5],[9,10],[18,20]]
    self.months = ['Center',
                   'Pearl',
                   'Soil',
                   'Swidden',
                   'Seedtime',
                   'Fallow',
                   'Hay',
                   'Harvest',
                   'Fall',
                   'Dirt',
                   'Dead',
                   'Winter',
                   'Center']
    self.months_until_weeks = [3, 7, 11, 15, 20, 24, 29, 33, 37, 41, 46, 50, 52]
    self.drying_months1 = [1,4]
    self.drying_months2 = [10, 13]
    self.birch_bark_months = [4, 6]
    self.nettle_harvest_months = [7,8]
    self.lower_screen = 0
    self.menu_items = ['Set reminder for:', 'Axe', 'Knife','Needle', 'Arrowheads', 'Spear', 'Quest']
    # Setup screen
    self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption('Unreal World Calendar')

    # Fonts
    self.FONT = pygame.font.SysFont('Arial', 12)
    self.BOLD_FONT = pygame.font.SysFont('Arial', 14, bold=True)
    self.BIG_FONT = pygame.font.SysFont('Arial', 18)
    self.TITLE_FONT = pygame.font.SysFont('Arial', 22, bold=True)
    self.font_wk_cal = pygame.font.SysFont('Segoe UI', 11, bold=True)
    self.font_bold_wk_cal = pygame.font.SysFont('Segoe UI', 12, bold=True)

    self.SCHEDULE_WIDTH = 400
    self.CHORES_WIDTH = 150
    self.calendar_year_y = 20

  # Assign season by day index
  def Get_Season(self, day_number):
    week = (day_number - 1) // 7 + 1
    day_of_week = (day_number - 1) % 7 + 1
    if week < 12 or (week == 12 and day_of_week == 1):
      return 'winter'
    elif week < 20 or (week == 20 and day_of_week <= 5):
      return 'spring'
    elif week < 29 or (week == 29 and day_of_week <= 4):
      return 'summer'
    elif week < 42 or (week == 42 and day_of_week <= 3):
      return 'fall'
    else:
      return 'winter'

  def Load_Json(self, path):
      if not os.path.exists(path):
          return {}
      with open(path, 'r') as f:
          return json.load(f)

  def Save_Json(self, path, data):
      with open(path, 'w') as f:
          json.dump(data, f, indent=2)

  def WorldCoord2ImgPixel(self, x_world, y_world, zoom):
    pixel_x = x_world * self.tiles_sizes[zoom][0]
    pixel_y = y_world * self.tiles_sizes[zoom][1]

    return (pixel_x, pixel_y)

  def WorldCoord2Chunk(self, world_x, world_y, zoom):
    chunk_x = world_x * self.tiles_sizes[zoom][0] / 512
    chunk_y = world_y * self.tiles_sizes[zoom][1] / 512

    return chunk_x, chunk_y

  def Chunk2WorldCoord(self, chunk_x, chunk_y, zoom):
    world_x = chunk_x * 512 / self.tiles_sizes[zoom][0]
    world_y = chunk_y * 512 / self.tiles_sizes[zoom][1]

    return world_x, world_y

  def Chunk2ImgPixel(self, chunk_x, chunk_y, zoom):
    pixel_x = chunk_x*512
    pixel_y = chunk_y*512

    return pixel_x, pixel_y

  def CreateMap(self):
    coordinates = (self.last_x, self.last_y)
    tile_w = self.tiles_sizes[self.zoom_level][0]
    tile_h = self.tiles_sizes[self.zoom_level][1]
    chunk_x_frac, chunk_y_frac = self.WorldCoord2Chunk(coordinates[0], coordinates[1], self.zoom_level)

    chunk_anchor = (0,0)
    self.world_anchor = (0,0)

    chunk_x = int(chunk_x_frac)
    chunk_y = int(chunk_y_frac)

    x_perc = chunk_x_frac - chunk_x
    y_perc = chunk_y_frac - chunk_y
    if DEBUG:
      print ('tile-%d-%d-%d.png'%(chunk_x,chunk_y, self.zoom_level))

    neighbor = []
    if x_perc <= 0.5:
      x_neighbor = chunk_x-1
    else:
      x_neighbor = chunk_x+1
    if y_perc <= 0.5:
      y_neighbor = chunk_y-1
    else:
      y_neighbor = chunk_y+1

    tile_files = {}
    tile_files['topleft']  = 'tile-%d-%d-%d.png'%(min(chunk_x, x_neighbor),min(chunk_y, y_neighbor),self.zoom_level)
    tile_files['topright'] = 'tile-%d-%d-%d.png'%(max(chunk_x, x_neighbor),min(chunk_y, y_neighbor),self.zoom_level)
    tile_files['botleft']  = 'tile-%d-%d-%d.png'%(min(chunk_x, x_neighbor),max(chunk_y, y_neighbor),self.zoom_level)
    tile_files['botright'] = 'tile-%d-%d-%d.png'%(max(chunk_x, x_neighbor),max(chunk_y, y_neighbor),self.zoom_level)

    chunk_anchor = [min(chunk_x, x_neighbor), min(chunk_y, y_neighbor)]
    wa_x, wa_y = self.Chunk2WorldCoord(chunk_anchor[0], chunk_anchor[1], self.zoom_level)
    self.world_anchor = ((wa_x), (wa_y))

    img_w, img_h = (2*512, 2*512)
    chunk_surfaces = {}
    for key, filename in tile_files.items():
      try:
        chunk_surfaces[key] = pygame.image.load(TILES_PATH+filename).convert_alpha()
      except:
        self.no_tiles = True
    if (len(chunk_surfaces) == 4):
      self.no_tiles = False

    if (self.no_tiles == False):
      self.map_surface = pygame.Surface((img_w, img_h), pygame.SRCALPHA)
      fog = np.full((img_h, img_w), 225, dtype=np.uint8)

      fog_radius = int(12 * tile_w)
      fog_radius_sq = fog_radius * fog_radius

      gradient_px = int(3 * tile_w)

      inner_radius = fog_radius - gradient_px
      inner_sq = inner_radius * inner_radius
      outer_sq = fog_radius_sq

      for x, y in self.fow:
        x_coord = int(x)
        y_coord = int(y)
        
        local_x_coord = x_coord-self.world_anchor[0]
        local_y_coord = y_coord-self.world_anchor[1]

        if ((local_x_coord >= 0) and (local_x_coord < 2*512/tile_w)):
          if ((local_y_coord >= 0) and (local_y_coord < 2*512/tile_h)):
            cx = int(local_x_coord * tile_w)
            cy = int(local_y_coord * tile_h)

            x0 = max(0, cx - fog_radius)
            x1 = min(img_w, cx + fog_radius + 1)
            y0 = max(0, cy - fog_radius)
            y1 = min(img_h, cy + fog_radius + 1)

            yy, xx = np.ogrid[y0:y1, x0:x1]

            #mask = (xx - cx) ** 2 + (yy - cy) ** 2 <= fog_radius_sq
            #fog[y0:y1, x0:x1][mask] = 0
            dist_sq = (xx - cx) ** 2 + (yy - cy) ** 2

            # fully visible
            inside = dist_sq <= inner_sq
            fog_slice = fog[y0:y1, x0:x1]
            fog_slice[inside] = np.minimum(fog_slice[inside], 0)

            # gradient ring
            ring = (dist_sq > inner_sq) & (dist_sq <= outer_sq)

            # distance-based alpha interpolation
            dist = np.sqrt(dist_sq[ring])

            alpha = ( (dist - inner_radius) / (fog_radius - inner_radius) ) * 225

            fog_slice[ring] = np.minimum( fog_slice[ring], alpha.astype(np.uint8))

      self.fog_surface = pygame.Surface((img_w, img_h), pygame.SRCALPHA)

      self.fog_surface.fill((0, 0, 0, 255))  # fully hidden

      alpha_array = pygame.surfarray.pixels_alpha(self.fog_surface)
      alpha_array[:] = fog.T
      del alpha_array

      # -------------------------------------------------
      # Camera state
      # -------------------------------------------------
      coordinates_image = (tile_w*(coordinates[0] - self.world_anchor[0]), tile_h*(coordinates[1]- self.world_anchor[1]))

      camera_x = coordinates_image[0] - self.map_width // 2
      camera_y = coordinates_image[1] - self.map_height // 2

      camera_x = max(0, min(camera_x, img_w - self.map_width))
      camera_y = max(0, min(camera_y, img_h - self.map_height))

      # -------------------------------------------------
      # Create camera rectangle
      # -------------------------------------------------
      self.map_rect = pygame.Rect(
          int(camera_x),
          int(camera_y),
          self.map_width,
          self.map_height
      )

      # Clamp rectangle safely
      self.map_rect.clamp_ip(pygame.Rect(0, 0, img_w, img_h))
      self.map_surface.blit(chunk_surfaces['topleft'], (0, 0))
      self.map_surface.blit(chunk_surfaces['topright'], (512, 0))
      self.map_surface.blit(chunk_surfaces['botleft'], (0, 512))
      self.map_surface.blit(chunk_surfaces['botright'], (512, 512))

      # draw player position
      pygame.draw.circle( self.map_surface,
                            (255,0,0),
                            (coordinates_image[0]+0.5*tile_w,coordinates_image[1]+.5*tile_h),
                            max(3, tile_h/2-3))

      # print ('pixels: ',coordinates_image)
      # Draw settlements
      settlements = self.new_state.get('settlements',{})
      for key in settlements:
        key_split = key.split(':')

        marker_loc = (tile_w * (int(key_split[0]) - self.world_anchor[0]),
                      tile_h *(int(key_split[1]) - self.world_anchor[1]))

        center = (marker_loc[0]+0.5*tile_w,marker_loc[1]+0.5*tile_h)
        width = max(tile_w, 10)
        height = max(tile_h, 10)
        rect = (center[0] - (0.5*width),center[1] - (0.5*height), width, width)
        pygame.draw.rect(self.map_surface,
                        (255,255,0),
                        rect,
                        2)

      # Draw home
      markers = self.new_state.get('markers',{})
      for key in markers:
        name = markers[key]
        key_split = key.split(':')
        if name.lower() == 'home':
          marker_loc = (tile_w * (int(key_split[0]) - self.world_anchor[0]),
                        tile_h * (int(key_split[1]) - self.world_anchor[1]))

          center = (marker_loc[0]+0.5*tile_w,marker_loc[1]+0.5*tile_h)
          width = max(tile_w, 10)
          height = max(tile_h, 10)
          rect = (center[0] - (0.5*width),center[1] - (0.5*height), width, width)
          pygame.draw.rect(
              self.map_surface,
              (255,0,0),
              rect,
              3)
          pygame.draw.line(
              self.map_surface,
              (255,0,0),
              (rect[0], rect[1]),
              (rect[0]+0.5*width,rect[1]-0.5*height ),
              3)
          pygame.draw.line(
              self.map_surface,
              (255,0,0),
              (rect[0]+width, rect[1]),
              (rect[0]+0.5*width,rect[1]-0.5*height ),
              3)
        else:
          marker_loc = (tile_w * (int(key_split[0]) - self.world_anchor[0]),
                        tile_h * (int(key_split[1]) - self.world_anchor[1]))
          center = (marker_loc[0]+0.5*tile_w,marker_loc[1]+0.5*tile_h)
          width = max(tile_w, 10)
          height = max(tile_h, 10)
          rect = (center[0] - (0.5*width),center[1] - (0.5*height), width, width)
          pygame.draw.line( self.map_surface,
                            (255,0,0),
                            (rect[0], rect[1]),
                            (rect[0]+width, rect[1]+height ),
                            2)
          pygame.draw.line( self.map_surface,
                            (255,0,0),
                            (rect[0], rect[1]+height),
                            (rect[0]+width, rect[1] ),
                            2)

  def File_Has_Changed(self):
    if not self.logfile_changed_ts:
      self.logfile_changed_ts = os.path.getmtime(LOG_FILE)
      return True
    else:
      ts = os.path.getmtime(LOG_FILE)
      if (ts != self.logfile_changed_ts):
        self.logfile_changed_ts = ts
        return True
    return False

  def Check_Key_Is_Near(self, key, my_list, name = None, dist=2):
    x = int(key.split(':')[0])
    y = int(key.split(':')[1])

    if name is None:
      dist += 1
    for i in range(-dist, dist+1):
      for k in range(-dist, dist+1):
        search_key = f'{x+i}:{y+k}'
        if (search_key in my_list):
          list_item = my_list[search_key]
          if (isinstance(list_item, list)):
            list_item=list_item[0]
          if (name is None or name == list_item.lower()):
            return search_key
    return None

  def Parse_Log(self):
    self.state = self.Load_Json(STATE_FILE)
    self.progress = self.Load_Json(PROGRESS_FILE)
    self.reminders = self.Load_Json(REMINDERS_FILE)
    x = 0
    y = 0
    if 'last_ts' not in self.progress:
      if DEBUG:
        print('New file being created')
      self.progress['last_ts'] = '0000'
    else:
      self.current_timestamp = gdt.GameDateTime(self.progress['last_ts'])
    if 'repeats' not in self.progress:
      self.progress['repeats'] = 0
    if 'chores' in self.progress:
      if ('Feed Animals' in self.progress['chores']):
        self.has_dog = self.progress['chores']['Feed Animals']['needed']
    if 'temp settlement' in self.progress:
      self.temp_village_content = self.progress['temp settlement']['content']
      self.current_settlement_key = self.progress['temp settlement']['key']
    if 'last coordinate' in self.progress:
      self.last_coord_str = self.progress['last coordinate']
    if (DEBUG):
      print(self.progress)
      if self.current_timestamp:
        self.current_timestamp.Print()

    trees_felled = self.state.get('trees felled', 0)
    fires_made = self.state.get('fires made', 0)
    sacrifices = self.state.get('sacrifices', 0)
    kills = self.state.get('kills', {})
    food_items = self.state.get('food items', {})
    self.food_storage = self.state.get('stored food', {})
    tanning = self.state.get('tanning processes', [])
    cooking = self.state.get('cooking processes', [])
    textile = self.state.get('textile processes', [])
    fishing = self.state.get('fishing processes', [])
    self.blacksmith = self.reminders.get('blacksmith processes', [])
    settlements = self.state.get('settlements',{})
    markers = self.state.get('markers',{})
    self.village_goods = self.state.get('village goods',{})
    names = self.state.get('Names',[])
    tanning_outcomes = self.state.get('tanning outcomes', {})
    building_counts = self.state.get('buildings', {})
    
    if (self.current_settlement_key):
      key2 = self.Check_Key_Is_Near(self.current_settlement_key, markers, 'home')
      self.current_settlement_key = key2
      self.at_home = True

    self.fow = set()
    fog_values_loaded = 0
    if Path(FOW_FILE).exists():
      with open(FOW_FILE) as cf:
        reader = csv.reader(cf)
        #next(reader)

        for x_, y_ in reader:
          self.fow.add((int(x_), int(y_)))
          fog_values_loaded += 1
    if DEBUG:
      print (fog_values_loaded, 'fog values loaded')
    prev_fow_size = len(self.fow)

    with open(LOG_FILE, 'r', encoding='utf-8', errors='replace') as f:  # Adding 'errors='replace''
      lines = f.readlines()

    repeating_timestamps = 0
    i = 0
    last_ts = 0
    while i < len(lines):
      line = lines[i]
      m = re.match(r'\((\w+)\):([0-9a-z]{4}):\[(.)\]\{([0-9A-F]+)\}\s+\| (.*)', line)

      if not m:
        i += 1
        if (DEBUG):
          print('Line not parsed: ', line)
        continue

      color, ts, msg_type, place, msg = m.groups()
      x = int(place[0:4], 16)
      y = int(place[4:8], 16)

      if ts == last_ts:
        repeating_timestamps += 1
      else:
        repeating_timestamps = 0

      last_ts = ts
      gt = gdt.GameDateTime(ts)
      gt_last_progress = gdt.GameDateTime(self.progress['last_ts'])
      
      if (gt < gt_last_progress):
        i += 1
        continue
      else:
        if ((gt==gt_last_progress) and (repeating_timestamps <= self.progress['repeats'])):
          i += 1
          continue

      new_ts = gt.Copy()

      if (not self.current_timestamp) or (new_ts.day != self.current_timestamp.day):
        self.new_day = True
        self.progress['chores'] = {'Make Fire':{'needed':False, 'done':False},
                                  'Sacrifice':    {'needed':True, 'done':False},
                                  'Feed Animals': {'needed':self.has_dog, 'done':False},
                                  'Herblore':     {'needed':True, 'done':False},
                                  'Weatherlore':  {'needed':True, 'done':False}
                                  }

      self.current_timestamp = new_ts.Copy()
      #self.current_timestamp.Print()
      if 'I shall name you...' in msg:
        self.has_dog = True
        for j in range(4):
          if 'barks.' in lines[i+j]:
            name = lines[i+j].split(' | ')[1].split(' barks.')[0]
            names.append(name)
            break
      trees_felled= self.Look_For_Tally_Items('The tree falls down.',       msg, trees_felled)
      sacrifices  = self.Look_For_Tally_Items('sacrifice',                  msg, sacrifices)
      fires_made  = self.Look_For_Tally_Items('You managed to make a fire', msg, fires_made)


      self.Look_For_Chores(['sacrifice'], lines,i, msg, self.progress['chores']['Sacrifice'])
      self.Look_For_Chores(['You managed to make a fire','smoked','(being prepared)'], lines,i, msg, self.progress['chores']['Make Fire'], multiline = True, backwards=True, search_area=25)
      self.Look_For_Chores(['Using: WEATHERLORE'], lines,i, msg, self.progress['chores']['Weatherlore'])
      self.Look_For_Chores(['You do not recognize what','You have learned something new about','You do know that'], lines,i, msg, self.progress['chores']['Herblore'],operator_and = False)
      self.Look_For_Chores(['Eat now','gives you a happy look.'], lines,i, msg, self.progress['chores']['Feed Animals'], multiline = True)

      if ('Entering settled area ...' in msg):
        key = f'{x}:{y}'
        key2 = self.Check_Key_Is_Near(key, markers, 'home')
        self.current_settlement_key = key2
        if (key2):
        #if (key in markers):
          if markers[key2].lower() == 'home':
            pass

        self.in_settlement = True
        self.temp_village_content = []
        self.fuzzy_village_content=[]
        key2 = self.Check_Key_Is_Near(key, settlements)
        if (key2 == None):
          settlements[key] = ["settlement"]
      elif ('You have come at your settlement and enter the familiar and cosy courtyard.' in msg):
        self.in_settlement = True
        self.temp_village_content = []
        self.fuzzy_village_content=[]
        key = f'{x}:{y}'
        key2 = self.Check_Key_Is_Near(key, markers, 'home')
        self.current_settlement_key = key2
        self.at_home = True

      elif ('You are entering ' in msg):
        s = msg[msg.find('You are entering'):]
        s = s.replace('You are entering ','').replace('a ','').replace('an ','').replace('...','').replace('\ufffd','ae').replace('\u00e4','?') # replace question mark with ?

        key = f'{x}:{y}'
        if (self.in_settlement):
          key2 = self.Check_Key_Is_Near(key, settlements)
          if key2:
            key = key2
            if settlements[key][0] != s:
              settlements[key][0] = s
        # self.current_settlement_key = key
        # if key not in settlements:
        #   settlements[key] = s
        # self.temp_village_content = []
      elif ('withdraws' in msg):
        if self.in_settlement:
          key = f'{x}:{y}'
          key2 = self.Check_Key_Is_Near(key, settlements)
          if key2:
            key = key2
          if key in settlements:
            if (settlements[key][0] == "settlement"):
              s = msg.replace('The ','').replace('tribesman ','').replace('Old ','').replace('boy ','').replace('Maiden ','').replace('woodsman ','').replace('man ','').replace('hunter ','').replace(' withdraws from your way.','').replace('...','').replace('\ufffd','\u00e4') # replace question mark with ?
              if s not in names:
                settlements[key][0] = s + ' ' + settlements[key][0]
              else:
                pass
      elif ('Zooming in ...' in msg):
        key = f'{x}:{y}'
        key2 = self.Check_Key_Is_Near(key, markers, 'home')
        if key2:
          self.at_home = True
      elif ('Zooming out ...' in msg):
        if (self.in_settlement or self.at_home):
          if (self.in_settlement):
            self.in_settlement = False
            if not self.current_settlement_key:
              key = f'{x}:{y}'
              key2 = self.Check_Key_Is_Near(key, settlements)
              if (key2 == None):
                self.current_settlement_key = key
              else:
                self.current_settlement_key = key2
          if (self.at_home):
            self.Tally_Village_Goods('home')
          else:
            self.Tally_Village_Goods(self.current_settlement_key)

        self.current_settlement_key = None
        self.at_home = False
        self.revisited_tile = -1
      elif ('You see a marked location' in msg):
        text = msg.split('\"')
        key = f'{x}:{y}'
        markers[key] = text[1]
      elif ('-- ' in msg): # this is a note
        key = f'{x}:{y}'
        note = msg.split('-- ')[1]
        if (self.in_settlement):
          key2 = self.Check_Key_Is_Near(key, settlements)
          if key2:
            key = key2
          settlements[key].append(note)
      elif (msg == 'Ok. You finish the current building job.'):
        # look back to find last building name
        for j in range(1, 50):
          prev_line = lines[max(1,i-j)]
          if 'BUILDING OPTIONS:' in prev_line:
            name = prev_line.split('BUILDING OPTIONS:')[-1].strip().lower()
            break
          elif 'You continue working on the' in prev_line:
            name = prev_line.split('You continue working on the')[-1].strip().lower()
            break
        else:
          name = 'unknown'
        for keyword in ['fence', 'corner', 'wall', 'door', 'shutter', 'cellar', 'fireplace', 'wooden building', 'shelter']:
          if keyword in name.lower():
            building_counts[keyword] = building_counts.get(keyword, 0) + 1
      elif ('sighs once, then stays laying dead still' in msg):
        m = re.search(r'the (.*?) sighs once', msg)
        if m:
          name = m.group(1).strip().lower().replace(' calf', '')
          if ' ' in name:
            name = name.split(' ')[1]
          kills[name] = kills.get(name, 0) + 1
      elif ('You got' in msg and 'meat' in msg):
        m = re.search(r'You got (\d+) edible cuts of (.*?) meat', msg)
        if m:
          count, name = m.groups()
          name = name.lower()
          if ' ' in name:
            name = name.split(' ')[1]+' cuts'
          name +=' cuts'
          food_items[name] = food_items.get(name, 0) + int(count)
      elif ('you finished preparing' in msg and 'flatbread' in msg):
        m = re.search(r'you finished preparing (\d+) (.*?) flatbread', msg)
        if m:
          count, name = m.groups()
          name = name.lower()
          if ' ' in name:
            name = name.split(' ')[1]
          name += ' flatbreads'
          food_items[name] = food_items.get(name, 0) + int(count)
      elif ('finish the tanning process and obtained a' in msg):
        m = re.search(r'obtained a (.*?) (.*?) (leather|fur)', msg)
        if m:
          quality, ttype, material = m.groups()
          ttype = ttype.replace(' forest', '')
          if ' ' in ttype:
            ttype = ttype.split(' ')[1]
          key = f'{ttype}:{material}:{quality}'
          tanning_outcomes[key] = tanning_outcomes.get(key, 0) + 1
      # Processes
      elif ('tanning the skin' in msg):
        self.Parse_Short_Process(msg, tanning)
      elif ('Ok, you leave' in msg and 'to cook and prepare' in msg):
        cooking_type = ''
        if 'dried' in msg:
          cooking_type = 'Drying Food'
        elif 'smoked' in msg:
          cooking_type = 'Smoking'
        elif 'roasted' in msg:
          cooking_type = 'Roasting'
          i += 1
        amount_type = msg.split('leave')[-1].split('to cook')[0].strip()
        self.Parse_Long_Process(lines, i, msg, cooking, cooking_type, amount_type)
      elif ('You finalize cleaning the skin and set it properly in place for curing.' in msg):
        self.Parse_Long_Process(lines, i, msg, tanning, 'Tanning')
      elif ('You leave the nettles to soak in the water, after which they are properly retted.' in msg):
        self.Parse_Long_Process(lines, i, msg, textile, 'Retting')
      elif ('tendons are now left to dry, after which you can proceed to separate the sinew fibre.' in msg):
        self.Parse_Long_Process(lines, i, msg, textile, 'Drying Tendons')
      elif ('The retted nettles are now set in loose bundles to dry out fully, after which you can proceed to extract the fibre.' in msg):
        self.Parse_Long_Process(lines, i, msg, textile, 'Drying Nettles')
      elif ('Return here after few days to retrieve the net and see if there' in msg):
        self.Parse_Long_Process(lines, i, msg, fishing, 'Fishing')
      elif (self.in_settlement or self.at_home):
        if ('Things that are here:' in msg or 'There are several objects here:' in msg):
          self.Parse_Items_On_Ground(lines, i)
        if ('You see ' in msg and ' here.' in msg):
          self.Parse_One_Item(lines[i])
        elif ('You pick up' in msg):
          self.Pick_Up_Items_On_Ground(msg)
        elif ('You drop' in msg):
          self.Drop_Items_On_Ground(msg)
      
      self.fow.add((x,y))

      i += 1
      last_ts = ts

    self.progress['last_ts'] = ts
    self.progress['repeats'] = repeating_timestamps
    self.progress['last coordinate'] = f'{x}:{y}'
    self.progress['temp settlement']={}
    self.progress['temp settlement']['content'] = self.temp_village_content
    self.progress['temp settlement']['key'] = self.current_settlement_key

    # save new state
    tanning_outcomes = dict(sorted(tanning_outcomes.items()))
    kills = dict(sorted(kills.items()))
    food_items = dict(sorted(food_items.items()))
    self.new_state = {
        'trees felled': trees_felled,
        'fires made': fires_made,
        'sacrifices': sacrifices,
        'kills': kills,
        'food items': food_items,
        'stored food': self.food_storage,
        'settlements': settlements,
        'markers':markers,
        'tanning processes': tanning,
        'cooking processes': cooking,
        'textile processes': textile,
        'fishing processes': fishing,
        'tanning outcomes': tanning_outcomes,
        'buildings': building_counts,
        'village goods':self.village_goods,
        'Names': names
    }
    self.Save_Json(STATE_FILE, self.new_state)
    self.Save_Json(PROGRESS_FILE, self.progress)

    if (x != self.last_x) or (y != self.last_y):
      print('Map coordinate: ',x,y, place)
      self.last_x = x
      self.last_y = y
    
    if (len(self.fow) > prev_fow_size):
      with open(FOW_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        for x_, y_ in sorted(self.fow):
            writer.writerow([x_, y_])

    self.CreateMap()

  def Add_Event(self, day, marker):
    if (day in self.event_markers):
      if not marker in self.event_markers[day]: # dont repeat markers
        self.event_markers[day].append(marker)
    else:
      self.event_markers[day] = [marker] # first marker

  def Fill_Events(self):
    self.event_markers = {}
    self.todays_events = {}
    self.weekly_events = defaultdict(list)
    #self.current_timestamp['day']=21 # debug specific dates
    #self.current_timestamp['month']=8 # debug specific dates

    if 'cooking processes' in self.new_state:
      for o in self.new_state['cooking processes']:
        cooking_end_date = gdt.GameDateTime(o['end'])
        cooking_start_date = gdt.GameDateTime(o['start'])
        if (cooking_end_date.year == self.current_timestamp.year):
          if o['type'] == 'Drying Food':
            self.Add_Event(cooking_end_date.calendar_day, 'D')
          elif o['type'] == 'Smoking':
            self.Add_Event(cooking_end_date.calendar_day, 'S')
            if (cooking_end_date.week >= self.current_timestamp.week):
              s = 1
              e = 8
              if (cooking_start_date.week == self.current_timestamp.week):
                s = cooking_start_date.weekday
              if (cooking_end_date.week == self.current_timestamp.week):
                e = cooking_end_date.weekday+1
              for d in range(s, e):
                self.weekly_events[(d, 5)].append('Make Fire')
              if (self.current_timestamp.weekday >= s and self.current_timestamp.weekday <= e):
                self.progress['chores']['Make Fire']['needed'] = True
        if (cooking_end_date.week == self.current_timestamp.week):
          d_w = cooking_end_date.weekday
          if o['type'] == 'Drying Food':
            self.weekly_events[(d_w, cooking_end_date.hour)].append('Drying')
          elif o['type'] == 'Smoking':
            self.weekly_events[(d_w, cooking_end_date.hour)].append('Smoking')

        if (cooking_end_date.day == self.current_timestamp.day):
          self.todays_events[cooking_end_date.hour] = o['amount']

    if 'tanning processes' in self.new_state:
      for t in self.new_state['tanning processes']:
        tanning_end_date = gdt.GameDateTime(t['end'])
        cal_day = tanning_end_date.calendar_day
        if (tanning_end_date.year == self.current_timestamp.year):
          self.Add_Event(cal_day, 'T')
        
        if (cal_day == self.current_timestamp.calendar_day):
          self.todays_events[tanning_end_date.hour] = 'tanning'

        if (tanning_end_date.week == self.current_timestamp.week):
          d_w = tanning_end_date.weekday
          self.weekly_events[(d_w, tanning_end_date.hour)].append('Tanning')

    if 'textile processes' in self.new_state:
      for t in self.new_state['textile processes']:
        end_date = gdt.GameDateTime(t['end'])
        cal_day = end_date.calendar_day
        if (end_date.year == self.current_timestamp.year):
          if (t['type'] == 'Retting'):
            self.Add_Event(cal_day, 'R')
          elif (t['type'] == 'Drying Nettles'):
            self.Add_Event(cal_day, 'd')
          elif (t['type'] == 'Drying Tendons'):
            self.Add_Event(cal_day, 't')
        if (cal_day == self.current_timestamp.calendar_day):
          self.todays_events[end_date.hour] = t['type']
        if (end_date.week == self.current_timestamp.week):
          d_w = end_date.weekday
          self.weekly_events[(d_w, end_date.hour)].append(t['type'])
    
    if 'fishing processes' in self.new_state:
      for t in self.new_state['fishing processes']:
        end_date = gdt.GameDateTime(t['end'])
        cal_day = end_date.calendar_day
        if (end_date.year == self.current_timestamp.year):
          if (t['type'] == 'Fishing'):
            self.Add_Event(cal_day, 'F')
        if (cal_day == self.current_timestamp.calendar_day):
          self.todays_events[end_date.hour] = t['type']
        if (end_date.week == self.current_timestamp.week):
          d_w = end_date.weekday
          self.weekly_events[(d_w, end_date.hour)].append(t['type'])

    if 'blacksmith processes' in self.reminders:
      for b in self.reminders['blacksmith processes']:
        end_date = gdt.GameDateTime(b['finish'])
        cal_day = end_date.calendar_day
        if (end_date.year == self.current_timestamp.year):
          self.Add_Event(cal_day, 'B')
        if (cal_day == self.current_timestamp.calendar_day):
          self.todays_events[end_date.hour] = b['type']
        if (end_date.week == self.current_timestamp.week):
          d_w = end_date.weekday
          self.weekly_events[(d_w, end_date.hour)].append(b['type'])

  def Look_For_Tally_Items(self, search_string,msg,  tally_var):
    if search_string in msg:
      tally_var += 1
    return tally_var

  def Look_For_Chores(self,search_strings,  lines, i, msg, chore_var, multiline = False, backwards = False, search_area = 5, operator_and = True):
    if (multiline):
      if search_strings[0] in msg:
        count_matches = 1
        for j in range (1,search_area):
          if (backwards):
            line = lines[max(1,i-j)]
          else:
            line = lines[min(i+j,len(lines)-1)]
          for k in range(1,len(search_strings)):
            ss = search_strings[k]
            if ss in line:
              count_matches += 1
          if count_matches == len(search_strings) and operator_and:
            chore_var['done'] = True
            break
          elif count_matches >= 2 and operator_and == False:
            chore_var['done'] = True
            break
    else:
      count_matches = 0
      for ss in search_strings:
        if ss in msg:
          count_matches += 1
      if count_matches == len(search_strings) and operator_and:
        chore_var['done'] = True
      elif count_matches > 0 and operator_and == False:
        chore_var['done'] = True

  def Parse_Long_Process(self, lines, i, msg, item, process_type, amount=None):
    duration = None
    for j in range(i+1, min(i+4, len(lines))):
      if 'should be complete' in lines[j]:
        if 'tomorrow' in lines[j]:
          duration = 1
        else:
          m = re.search(r'after (\d+) days', lines[j])
          if m:
            duration = int(m.group(1))
      elif 'Return here after ' in lines[i]:
        duration = 2
      if duration:
        if self.current_timestamp:
          end_date = self.current_timestamp + duration
          if (amount):
            item.append({
              'type': process_type,
              'amount': amount,
              'start': self.current_timestamp.GetDateTime(),
              'end': end_date.GetDateTime()
            })
          else:
            item.append({
              'type': process_type,
              'start': self.current_timestamp.GetDateTime(),
              'end': end_date.GetDateTime()
            })
          break

  def Parse_Short_Process(self, msg, item):
    if self.current_timestamp:
      start_date = self.current_timestamp.Copy()
      end_date = self.current_timestamp.Copy()
      end_date_text = msg.split('.')[0]
      if ('a few hours' in end_date_text):
        end_date.hour +=2
        if (end_date.hour > 23):
          end_date += 1
          end_date.hour -= 24
      elif 'This step is complete by ' in msg:
        time = msg[msg.find(' by ')+4:msg.find('.')]
        h = end_date.GetTimeOfDayFromString(time)
        if h < start_date.hour:
          end_date += 1
        end_date.hour = h
      item.append({
          'start': start_date.GetDateTime(),
          'end': end_date.GetDateTime(),
          'timeframe': end_date_text
      })

  def Get_Item_Group_From_Unique_Name (self, name):
    return name.replace('spoiled ', '').replace('stale ', '').replace('tasty ', '').replace('bland ', '')

  def Check_Food_Items_Are_Same(self, parse_items, fuzzy = False):
    cuts = {}
    same = False
    for i in range(len(parse_items)):
      name, number = self.Parse_Item_Msg_Line(parse_items[i])
      itemgroup = self.Get_Item_Group_From_Unique_Name(name)
      if itemgroup in cuts:
        cuts[itemgroup] += number
      else:
        cuts[itemgroup] = number
    
    cuts2 = []
    cuts2_fuzzy = []
    for k in range(len(self.temp_village_content)):
      items = self.temp_village_content[k]
      cuts2.append({})
      if k in self.fuzzy_village_content:
        cuts2_fuzzy.append(True)
      else:
        cuts2_fuzzy.append(False)
      for i in range(len(items)):
        name, number = self.Parse_Item_Msg_Line(items[i])
        itemgroup = self.Get_Item_Group_From_Unique_Name(name)
        if itemgroup in cuts2[k]:
          cuts2[k][itemgroup] += number
        else:
          cuts2[k][itemgroup]=number
    index = None
    for i in range(len(cuts2)):
      if (cuts2[i] == cuts):
        same = True
        return i, False

    fuzzy_best_index = None
    best_match = 0
    if index == None:
      for i in range(len(cuts2)):
        #if (cuts2_fuzzy[i]):
        if (True):
          sum_match = 0
          sum_all = 0
          match_perc = 0
          for m in cuts:
            found = False
            for k in cuts2[i]:
              if k == m:
                sum_match += cuts[m]
                sum_all += cuts2[i][k]
                found = True
                continue
            if not found:
              sum_all += cuts[m]
          if (sum_all > 0):
            match_perc = sum_match / sum_all
          if best_match < match_perc:
            best_match = match_perc
            fuzzy_best_index = i
    if best_match > .5:
      if DEBUG:
        print('Fuzzy match: ',best_match)
      return fuzzy_best_index, True
    else:
      return None, False
  
  def CheckBlackListedStrings(self, line, blacklist):
    for item in blacklist:
      if item in line:
        return True

    else:
      return False

  def Parse_One_Item(self, line):
    items = []
    cuts_at_home = False
    #if (line.startswith('(000000)')): # when the color is not black, its not an item on the ground
    if 1:
      match = re.search(r"\[(.*?)\]", line)
      if match:
        hotkey = match.group(1)
        if (hotkey.isupper()): # Uppercase letters indicate things that are not laying on ground, but are rather persons or building types
          return
      if (self.CheckBlackListedStrings(line, ['called',' rock ' ,' log','patch', ' boy', 'growing', ' man', 'wife', 'girl' ])): # dont count your named animal
        #print(line)
        return
      if (self.at_home):
        if ('cut' not in line) and ('flatbread' not in line):
          return
        elif ('(being prepared)' in line):
          return
        else:
          cuts_at_home = True
      item = line.split(' here.')[0]
      if ('You see a ' in item):
        item = item.split('You see a ')[1].strip()
      elif ('You see an ' in item):
        item = item.split('You see an ')[1].strip()
      else: 
        item = item.split('You see ')[1].strip()
      items.append(item)
    if items:
      if (cuts_at_home):
        index, fuzzy_matched = self.Check_Food_Items_Are_Same(items, False)
        if (index is not None):
          self.revisited_tile = index
        else:
          self.temp_village_content.append(items)
      else:
        if items in self.temp_village_content:
          # don't count the same tiles multiple times
          # still an issue when pushing items, but we usually dont push food, so I will ignore it for now
          self.revisited_tile = self.temp_village_content.index(items)
        else:
          self.temp_village_content.append(items)

  def Parse_Items_On_Ground(self, lines, i):
    items = []
    cuts_at_home = False
    fuzzy = False
    for j in range(i+1, min(i+100, len(lines))):
      line = lines[j]
      
      if (line.startswith('(000000)')): # when the color is not black, its not an item on the ground
        match = re.search(r"\[(.*?)\]", line)
        if match:
          hotkey = match.group(1)
          if (hotkey.isupper()): # Uppercase letters indicate things that are not laying on ground, but are rather persons or building types
            break
        if ('called' in line): # dont count your named animal
          continue
        if (self.at_home):
          if ('cut' not in line) and ('flatbread' not in line):
            continue
          elif ('(being prepared)' in line):
            continue
          else:
            cuts_at_home = True
        items.append(line.split('| ')[1].strip())
      elif ('...and ' in line):
        fuzzy = True
        break
      elif ('You ' in line):
        break
      elif ('Things that ' in line):
        break
    if items:
      if (cuts_at_home):
        index, fuzzy_matched = self.Check_Food_Items_Are_Same(items, fuzzy)
        if (index is not None):
          self.revisited_tile = index
          if (fuzzy):
            self.fuzzy_village_content.append(index)
          self.temp_village_content[index]=items
        else:
          self.temp_village_content.append(items)
          if (fuzzy):
            self.fuzzy_village_content.append(len(self.temp_village_content)-1)
      else:
        if items in self.temp_village_content:
          # don't count the same tiles multiple times
          # still an issue when pushing items, but we usually dont push food, so I will ignore it for now
          self.revisited_tile = self.temp_village_content.index(items)
        else:
          self.temp_village_content.append(items)

  def Parse_Item_Msg_Line(self, line):
    number = 0
    name = line
    tokens = line.split(' ')
    try:
      number = int(tokens[0])
      name = line.replace(tokens[0]+' ', '')
      if name.endswith('s'):
        name = name[:-1]
    except:
      number = 1

    return name, number

  def Pick_Up_Items_On_Ground(self, line):
    items = []
    if ('cut' in line) or ('flatbread' in line):
      item = line = line.replace('You pick up the ', '')[:-1]
      item, number = self.Parse_Item_Msg_Line(line)
      i = 0
      removed = False
      if (self.temp_village_content):
        for content in self.temp_village_content[self.revisited_tile]:
          if (item in content):
            tokens = content.split(' ')
            num_items_present=0
            try:
              num_items_present = int(tokens[0])
            except:
              num_items_present = 1
            if (num_items_present >= number):
              num_items_new = num_items_present-number
              if (num_items_new == 0):
                self.temp_village_content[self.revisited_tile].remove(content)
              elif (num_items_new == 1):
                if content.endswith('s'):
                  content = content[:-1]
                self.temp_village_content[self.revisited_tile][i] = content.replace('%s'%num_items_present, '1')
              else:
                self.temp_village_content[self.revisited_tile][i] = content.replace('%s'%num_items_present, '%d'%num_items_new)
              removed = True
              break
          i += 1
        if not removed:
          pass
          #print('Something went wrong, could not remove %s from tile: '%(line),self.temp_village_content[self.revisited_tile])
          
    return

  def Drop_Items_On_Ground(self, line):
    if ('cut' in line) or ('flatbread' in line):
      line = line.replace('You drop the ', '')[:-1]
      item, number = self.Parse_Item_Msg_Line(line)
      found = False
      i = 0
      if (self.temp_village_content):
        for content in self.temp_village_content[self.revisited_tile]:
          
          if (item in content):
            found = True
            tokens = content.split(' ')
            num_items_present=0
            try:
              num_items_present = int(tokens[0])
            except:
              num_items_present = 1
          
            num_items_new = num_items_present+number
            
            self.temp_village_content[self.revisited_tile][i] = content.replace('%s'%num_items_present, '%d'%num_items_new)
            break
          i += 1
        if not found:
          if (len(self.temp_village_content) > 0):
            self.temp_village_content[self.revisited_tile].append(line)
          else:
            self.temp_village_content.append([line])

    return

  def Tally_Village_Goods(self, key):
    temp_village_goods = {}
    num_items = 0
    for tile_contents in self.temp_village_content:
      for item in tile_contents:
        count_this = False
        if (key == 'home'):
          if ('cut' in item) or ('flatbread' in item):
            #if ('spoiled' not in item):
            count_this = True
        else:
          count_this = True
        if (count_this):
          item, number = self.Parse_Item_Msg_Line(item)
          # tokens = item.split(' ')
          # try:
          #   number = int(tokens[0])
          #   item = item.replace(tokens[0]+' ', '')
          #   if item.endswith('s'):
          #     item = item[:-1]
          # except:
          #   number = 1
          num_items+=1
          if item in temp_village_goods:
            temp_village_goods[item] += number
          else:
            temp_village_goods[item] = number
    # maybe find a better way to handle visits to villages without looking at all items and not overwrite everything
    if (num_items > 0):
      if (key == 'home'):
        keys_to_remove = []
        for content in temp_village_goods:
          if 'spoiled' in content:
            keys_to_remove.append(content)
        for key in keys_to_remove:
            temp_village_goods.pop(key, None)

        self.food_storage = temp_village_goods
      else:
        self.village_goods[key] = temp_village_goods

    self.temp_village_content = []

  def Format_Hour(self, hour):
    suffix = 'AM' if hour < 12 else 'PM'
    display_hour = hour % 12
    if display_hour == 0:
      display_hour = 12
    return f'{display_hour:2d} {suffix}'

  def GetFoodStorageInWeeks(self):
    weeks = 0
    food_items = 0
    for item in self.food_storage:
      food_items += self.food_storage[item]

    weeks = food_items / 32

    return weeks

  def Draw_Weekly_Calendar(self):
    atX = 10 + display_weeks * week_width - CAL_WIDTH
    atY = self.lower_screen
    calendar_surface = pygame.Surface((CAL_WIDTH, CAL_HEIGHT))
    calendar_surface.fill(BG_COLOR)

    # Day headers
    for i, day in enumerate(DAYS):
      x = MARGIN_X + i * COL_WIDTH
      y = MARGIN_Y
      rect = pygame.Rect(x, y, COL_WIDTH, HEADER_HEIGHT)
      color = CURRENT_DAY_COLOR if i == (self.current_timestamp.weekday-1) else HEADER_BG
      pygame.draw.rect(calendar_surface, color, rect, border_radius=3)

      text = self.font_bold_wk_cal.render(day, True, TEXT_COLOR)
      text_rect = text.get_rect(center=(x + COL_WIDTH // 2, y + HEADER_HEIGHT // 2))
      calendar_surface.blit(text, text_rect)

    # Hour grid
    for j, hour in enumerate(VISIBLE_HOURS):
      y = MARGIN_Y + HEADER_HEIGHT + j * HOUR_HEIGHT

      # Right-aligned time label
      label = self.font_wk_cal.render(self.Format_Hour(hour), True, HOUR_LABEL_COLOR)
      label_rect = label.get_rect(right=MARGIN_X - 5, centery=y)
      calendar_surface.blit(label, label_rect)
      if (hour < 24):
        label = self.font_wk_cal.render(self.current_timestamp.GetTimeOfDayFromHour(hour), True, HOUR_LABEL_COLOR)
        label_rect = label.get_rect(left=MARGIN_X + 7 * COL_WIDTH, centery=y+8)
        calendar_surface.blit(label, label_rect)
      if (j < len(VISIBLE_HOURS)-1):
        for i in range(7):
          x = MARGIN_X + i * COL_WIDTH
          cell_rect = pygame.Rect(x, y, COL_WIDTH, HOUR_HEIGHT)

          is_now = i == (self.current_timestamp.weekday-1) and hour == self.current_timestamp.hour
          if is_now:
            pygame.draw.rect(calendar_surface, CURRENT_HOUR_COLOR, cell_rect)

          pygame.draw.rect(calendar_surface, LINE_COLOR, cell_rect, 1)

          events = self.weekly_events.get((i+1, hour), [])
          if events:
            text_color = EVENT_COLOR_HIGHLIGHTED if is_now else EVENT_COLOR
            for k, event in enumerate(events[:1]):
              text = self.font_wk_cal.render(event, True, text_color)
              calendar_surface.blit(text, (x + 4, y + 0))

    # Grid border
    total_height = (len(VISIBLE_HOURS)-1) * HOUR_HEIGHT
    grid_rect = pygame.Rect(MARGIN_X, MARGIN_Y + HEADER_HEIGHT, COL_WIDTH * 7, total_height)
    pygame.draw.rect(calendar_surface, LINE_COLOR, grid_rect, 2, border_radius=4)

    self.screen.blit(calendar_surface, (atX, atY))

  def Draw_Calendar_Year(self):
    highlight_last = self.highlight
    new_highlight = None
    self.tooltip = None
    self.screen.fill(WHITE)
    index = 0
    start = 10
    self.calendar_year_y = 5
    for week in self.months_until_weeks:
      week_x = 10 + week * week_width
      label = self.FONT.render(self.months[index], True, BLACK)
      pygame.draw.rect(self.screen, BLACK, (start, self.calendar_year_y, week_x-start-1,33),1)
      label_rect = label.get_rect(center=(start+(week_x - start)// 2,self.calendar_year_y+7)) 
      self.screen.blit(label, label_rect)
      start = week_x
      index +=1

    box_y = 0
    drawing_date = self.current_timestamp.Copy()
    drawing_date.day = 1
    drawing_date.month = 1
    drawing_date.hour = 0
    drawing_date.Update()
    # Draw weekly columns
    for week in range(display_weeks):
      week_x = 10 + week * week_width
      self.calendar_year_y = 20+20

      # Label week number (centered)
      label = self.FONT.render(f'{week+1}', True, BLACK)
      label_rect = label.get_rect(center=(week_x + box_width // 2, self.calendar_year_y - 10))
      self.screen.blit(label, label_rect)

      for d in range(7):
        day_number = week * 7 + d + 1
        
        if day_number > drawing_date.GetDaysPerYear():
          break

        box_y = self.calendar_year_y + d * (box_height + 1)
        rect = pygame.Rect(week_x, box_y, box_width, box_height)

        # Fill each box by season
        season = drawing_date.GetSeason()
        pygame.draw.rect(self.screen, SEASON_COLORS[season], rect)
        w = 1
        #current_timestamp['day'] = 20
        #current_timestamp['month'] = 11
        if (drawing_date.day == self.current_timestamp.day and drawing_date.month == self.current_timestamp.month):
          w = 2
        pygame.draw.rect(self.screen, BLACK, rect, w)

        if (self.menu_pos[0] >= week_x) and (self.menu_pos[0] < week_x+box_width):
          if (self.menu_pos[1] >= box_y) and (self.menu_pos[1] < box_y+box_height):
            self.menu_date = drawing_date.Copy()

        # Draw 1-7 day number inside week
        #daystring = '%d %d/%d'%(d+1, drawing_date['day'], drawing_date['month'])
        daystring = '%d'%(d+1)
        txt = self.FONT.render(daystring, True, BLACK)
        self.screen.blit(txt, (rect.x + 2, rect.y + 2))

        # Draw event markers in 2x2 grid if present
        if day_number in self.event_markers:
          markers = self.event_markers[day_number]
          for i, e in enumerate(markers):
            col = i % 2
            row = i // 2
            if i == 4:
              col = 1
              row = -1
            x = rect.x + 2 + col * 14
            y = rect.y + 16 + row * 14
            marker = self.BOLD_FONT.render(e, True, BLACK)
            self.screen.blit(marker, (x, y))
            if (e == 'B'):
              mouse_pos = pygame.mouse.get_pos()
              if (mouse_pos[0] >= week_x) and (mouse_pos[0] < week_x+box_width):
                if (mouse_pos[1] >= box_y) and (mouse_pos[1] < box_y+box_height):

                  if 'blacksmith processes' in self.reminders:
                    for events in self.reminders['blacksmith processes']:
                      blacksmith_date = gdt.GameDateTime(events['finish'])
                      if (blacksmith_date.IsSameDayAs(drawing_date)):
                        
                        if (self.highlight != highlight_last):
                          self.time_enter_rect = pygame.time.get_ticks()
                          self.tooltip = None
                        else:
                          if (pygame.time.get_ticks() - self.time_enter_rect > 1.0):
                            self.tooltip = events['type']
                            self.tooltip_pos = (mouse_pos[0], mouse_pos[1])
                        self.highlight = events['location']
                        new_highlight = self.highlight
                        break
        
        drawing_date += 1
    self.highlight = new_highlight
    row_y = box_y + box_height + 3
    row_height = 18
    # Draw Drying time
    # the months are defined by until which week they last, 
    # so first month lasts from week 1 until including week 3
    # second month lasts from previous spot until including week 7

    starting_month = self.drying_months1[0]-1
    if (starting_month == 0):
      start_week = 0
    else:
      start_week = self.months_until_weeks[starting_month-1]

    end_week = self.months_until_weeks[self.drying_months1[1]-1]
    start_x = 10 + start_week * week_width
    num_weeks = end_week-start_week

    label = self.FONT.render('Meat drying possible', True, BLACK)
    pygame.draw.rect(self.screen, SEASON_COLORS['winter'], (start_x,row_y, num_weeks*week_width-2, row_height))
    pygame.draw.rect(self.screen, BLACK, (start_x,row_y, num_weeks*week_width-2, row_height),1)
    label_rect = label.get_rect(center=(start_x+(num_weeks*week_width)// 2,row_y+8)) 
    self.screen.blit(label, label_rect)

    starting_month = self.drying_months2[0]-1
    if (starting_month == 0):
      start_week = 0
    else:
      start_week = self.months_until_weeks[starting_month-1]

    end_week = self.months_until_weeks[self.drying_months2[1]-1]
    start_x = 10 + start_week * week_width
    num_weeks = end_week-start_week

    label = self.FONT.render('Meat drying possible', True, BLACK)
    pygame.draw.rect(self.screen, SEASON_COLORS['winter'], (start_x,row_y, num_weeks*week_width-2, row_height))
    pygame.draw.rect(self.screen, BLACK, (start_x,row_y, num_weeks*week_width-2, row_height),1)
    label_rect = label.get_rect(center=(start_x+(num_weeks*week_width)// 2,row_y+8)) 
    self.screen.blit(label, label_rect)


    # Draw Birch Bark Time, Nettles Time
    row_y += row_height + 3
    starting_month = self.birch_bark_months[0]-1
    if (starting_month == 0):
      start_week = 0
    else:
      start_week = self.months_until_weeks[starting_month-1]

    end_week = self.months_until_weeks[self.birch_bark_months[1]-1]
    start_x = 10 + start_week * week_width
    num_weeks = end_week-start_week

    label = self.FONT.render('Birch Bark harvestable', True, BLACK)
    pygame.draw.rect(self.screen, SEASON_COLORS['spring'], (start_x,row_y, num_weeks*week_width-2, row_height))
    pygame.draw.rect(self.screen, BLACK, (start_x,row_y, num_weeks*week_width-2, row_height),1)
    label_rect = label.get_rect(center=(start_x+(num_weeks*week_width)// 2,row_y+8)) 
    self.screen.blit(label, label_rect)

    starting_month = self.nettle_harvest_months[0]-1
    if (starting_month == 0):
      start_week = 0
    else:
      start_week = self.months_until_weeks[starting_month-1]

    end_week = self.months_until_weeks[self.nettle_harvest_months[1]-1]
    start_x = 10 + start_week * week_width
    num_weeks = end_week-start_week

    label = self.FONT.render('Nettles harvestable', True, BLACK)
    pygame.draw.rect(self.screen, SEASON_COLORS['summer'], (start_x,row_y, num_weeks*week_width-2, row_height))
    pygame.draw.rect(self.screen, BLACK, (start_x,row_y, num_weeks*week_width-2, row_height),1)
    label_rect = label.get_rect(center=(start_x+(num_weeks*week_width)// 2,row_y+8)) 
    self.screen.blit(label, label_rect)

    self.lower_screen = row_y + row_height + 3

  def Draw_FoodStorage(self):
    pos_x =  10 + display_weeks * week_width - CAL_WIDTH - self.CHORES_WIDTH - 20
    pos_y = self.lower_screen
    storage_title = self.TITLE_FONT.render('Food Storage:', True, BLACK)
    self.screen.blit(storage_title, (pos_x + 10, pos_y))
    weeks = self.GetFoodStorageInWeeks()
    storage_text = self.TITLE_FONT.render('None', True, BLACK)
    if (weeks < 1):
      storage_text = self.BIG_FONT.render('Less than a week', True, BLACK)
    elif (weeks < 3):
      storage_text = self.BIG_FONT.render('%3.1f weeks'%weeks, True, BLACK)
    else:
      storage_text = self.BIG_FONT.render('%d weeks '%round(weeks), True, BLACK)

    self.screen.blit(storage_text, (pos_x + 12, pos_y + 22))

  def Draw_Chores(self):
    # Draw Chores Section
    chores_x = 10 + display_weeks * week_width - CAL_WIDTH - self.CHORES_WIDTH - 20
    chores_y = self.lower_screen + 45
    pygame.draw.rect(self.screen, GRAY, (chores_x, chores_y, self.CHORES_WIDTH, 200))
    pygame.draw.rect(self.screen, BLACK, (chores_x, chores_y, self.CHORES_WIDTH, 200), 2)
    chores_title = self.TITLE_FONT.render('Chores', True, BLACK)
    self.screen.blit(chores_title, (chores_x + 10, chores_y + 10))

    # Draw each chore with a checkbox
    checkbox_size = 20
    for i, chore in enumerate(self.progress['chores']):
      color = DARK_GRAY
      item = self.progress['chores'][chore]
      if item['needed']:
        color = BLACK
      checkbox_x = chores_x + self.CHORES_WIDTH - checkbox_size - 10
      checkbox_y = chores_y + 40 + i * 30
      # Draw checkbox (outline)
      pygame.draw.rect(self.screen, color, (checkbox_x, checkbox_y, checkbox_size, checkbox_size), 2)

      # If chore is done, draw checkmark inside checkbox
      g = 3

      if item['done']:
        pygame.draw.line(self.screen, color, (checkbox_x + g, checkbox_y + g), (checkbox_x + checkbox_size - 2*g+2, checkbox_y + checkbox_size - 2*g+2), 2)
        pygame.draw.line(self.screen, color, (checkbox_x + checkbox_size - 2 * g + 2, checkbox_y + g ), (checkbox_x + g, checkbox_y + checkbox_size - 2*g+2), 2)

      # Draw chore name next to checkbox
      chore_text = self.BIG_FONT.render(chore, True, color)
      self.screen.blit(chore_text, (chores_x + 5, checkbox_y))

  def Draw_Tally(self):
    # Draw Tally Panel below calendar
    #tally_x = 10
    tally_y = self.calendar_year_y + week_height + 40
    chores_x = 10 + display_weeks * week_width - CAL_WIDTH - self.CHORES_WIDTH - 20
    chores_y = self.lower_screen + 200+5
    tally_h = len(self.new_state['kills']) * 25 + 40 
    pygame.draw.rect(self.screen, GRAY, (chores_x, chores_y, self.CHORES_WIDTH, tally_h))
    pygame.draw.rect(self.screen, BLACK, (chores_x, chores_y, self.CHORES_WIDTH, tally_h), 2)
    title = self.TITLE_FONT.render('Kills:', True, BLACK)
    self.screen.blit(title, (chores_x + 10, chores_y + 10))

    for i, (key, val) in enumerate(self.new_state['kills'].items()):
      stat_text = self.BIG_FONT.render(f'{key}s: {val}', True, BLACK)
      self.screen.blit(stat_text, (chores_x + 10, chores_y + 40 + i * 25))

  def Intersect_Ray_Rect(self, origin, direction, rect):
    t_values = []

    if direction.x != 0:
        t1 = (rect.left  - origin.x) / direction.x
        t2 = (rect.right - origin.x) / direction.x
        t_values.extend([t1, t2])

    if direction.y != 0:
        t3 = (rect.top    - origin.y) / direction.y
        t4 = (rect.bottom - origin.y) / direction.y
        t_values.extend([t3, t4])

    hits = []

    for t in t_values:
        if t <= 0:
            continue
        p = origin + direction * t
        #if rect.collidepoint(p):
        if rect.left <= p.x <= rect.right and rect.top <= p.y <= rect.bottom:
            hits.append((t, p))

    if not hits:
        return None

    return min(hits, key=lambda x: x[0])[1]

  def Draw_Map(self):
    self.map_y = self.lower_screen
    this_map_rect = pygame.Rect(self.map_x, self.map_y, self.map_width, self.map_height)
    pygame.draw.rect(self.screen, GRAY, this_map_rect)
    pygame.draw.rect(self.screen, BLACK, this_map_rect, 2)
    if (self.map_surface):
      self.screen.blit(self.map_surface, (self.map_x, self.map_y), self.map_rect)
      if self.highlight:
        tile_w = self.tiles_sizes[self.zoom_level][0]
        tile_h = self.tiles_sizes[self.zoom_level][1]
        x = int(self.highlight.split(':')[0])
        y = int(self.highlight.split(':')[1])
        coordinates_image = (tile_w*(x - self.world_anchor[0]), 
                             tile_h*(y- self.world_anchor[1]))
        coordinates_window = (coordinates_image[0]+0.5*tile_w+self.map_x-self.map_rect[0],coordinates_image[1]+.5*tile_h+self.map_y-self.map_rect[1])
        if (coordinates_window[0] >= self.map_x) and (coordinates_window[0] < self.map_x+self.map_width) and (coordinates_window[1] >= self.map_y) and (coordinates_window[1] < self.map_y+self.map_height):
          pygame.draw.circle( self.screen,
                                (0,255,255),
                                coordinates_window,
                                max(10, tile_h/2+3),
                                2)
      self.screen.blit(self.fog_surface, (self.map_x, self.map_y), self.map_rect)
      if self.highlight:
        tile_w = self.tiles_sizes[self.zoom_level][0]
        tile_h = self.tiles_sizes[self.zoom_level][1]
        x = int(self.highlight.split(':')[0])
        y = int(self.highlight.split(':')[1])
        coordinates_image = (tile_w*(x - self.world_anchor[0]), 
                             tile_h*(y- self.world_anchor[1]))
        coordinates_window = (coordinates_image[0]+0.5*tile_w+self.map_x-self.map_rect[0],coordinates_image[1]+.5*tile_h+self.map_y-self.map_rect[1])
        if (coordinates_window[0] >= self.map_x) and (coordinates_window[0] < self.map_x+self.map_width) and (coordinates_window[1] >= self.map_y) and (coordinates_window[1] < self.map_y+self.map_height):
          pass
        else:
          center = pygame.Vector2(self.map_x+self.map_width/2, self.map_y+self.map_height/2)
          direction = pygame.Vector2(coordinates_window[0],coordinates_window[1]) - center
          if direction.length() == 0:
            pass
          else:

            direction = direction.normalize()
            arrow_pos = self.Intersect_Ray_Rect(center, direction, this_map_rect)
            if arrow_pos is None:
              pass
            else:
              angle = -direction.angle_to(pygame.Vector2(1, 0))
              perp = pygame.Vector2(-direction.y, direction.x)
              size = 15
              tip = arrow_pos# + direction * size
              left = arrow_pos - direction * size + perp * size * 0.4
              right = arrow_pos - direction * size - perp * size * 0.4

              pygame.draw.polygon(self.screen, (0,255, 255), [tip, left, right])

    else:
      if print_once:
        text = self.BIG_FONT.render("No map tiles found in folder: ", True, BLACK)
        self.screen.blit(text, (self.map_x+5, self.map_y))

        text = self.BIG_FONT.render(TILES_PATH, True, BLACK)
        self.screen.blit(text, (self.map_x+5, self.map_y+25))

        text = self.BIG_FONT.render('Use tool urwmap to extract tiles and place in the folder above.', True, BLACK)
        self.screen.blit(text, (self.map_x+5, self.map_y+50))

        text = self.BIG_FONT.render('Download the tool here:', True, BLACK)
        self.screen.blit(text, (self.map_x+5, self.map_y+75))

        text = self.BIG_FONT.render('https://www.tapatalk.com/groups/urwforum/map-viewer-t7712.html', True, BLACK)
        self.screen.blit(text, (self.map_x+5, self.map_y+100))
      
        print('Download urwmap-0.0.3 from here:\nhttps://www.tapatalk.com/groups/urwforum/map-viewer-t7712.html')
        print_once = False

    mouse_pos = pygame.mouse.get_pos()

    if (mouse_pos[0] >= self.map_x) and (mouse_pos[0] < self.map_x+this_map_rect[2]):
      if (mouse_pos[1] >= self.map_y) and (mouse_pos[1] < self.map_y+this_map_rect[3]):
        x_pixel_map = mouse_pos[0] + self.map_rect[0] - self.map_x
        y_pixel_map = mouse_pos[1] + self.map_rect[1] - self.map_y

        tile_w = self.tiles_sizes[self.zoom_level][0]
        tile_h = self.tiles_sizes[self.zoom_level][1]

        x_tile = x_pixel_map / tile_w
        y_tile = y_pixel_map / tile_h

        coord_x = int(x_tile + self.world_anchor[0])
        coord_y = int(y_tile + self.world_anchor[1])

        #text = self.BIG_FONT.render(f'{coord_x}:{coord_y}', True, BLACK)
        #pygame.draw.rect(self.screen, GRAY, (mouse_pos[0]+20, mouse_pos[1]+5, text.get_rect()[2], text.get_rect()[3]))
        #self.screen.blit(text, (mouse_pos[0]+20, mouse_pos[1]+5))

        settlements = self.new_state.get('settlements',{})
        for key in settlements:
          key_split = key.split(':')

          if (abs(coord_x - int(key_split[0])) < 4/self.zoom_level):
            if (abs(coord_y - int(key_split[1])) < 4/self.zoom_level):
              village_goods = self.new_state.get('village goods')
              txtLines = []
              txtWidth = 0
              for s in settlements[key]:
                txtLines.append(self.BIG_FONT.render(s, True, BLACK))
                txtWidth = max(txtWidth, txtLines[-1].get_rect()[2])
              if key in village_goods:
                for k in village_goods[key]:
                  if ((k.find('shingle') == -1) and (k.find('tub') == -1) and (k.find('rock') == -1) and (k.find('stone') == -1)):
                    txtLines.append(self.BIG_FONT.render(f'{k}:{village_goods[key][k]}', True, BLACK))
                    txtWidth = max(txtWidth, txtLines[-1].get_rect()[2])
                textBoxCoord = mouse_pos[1]+5
                if ((mouse_pos[1]+5+len(txtLines)*20) > SCREEN_HEIGHT-25):
                  textBoxCoord = SCREEN_HEIGHT - 25 - (len(txtLines)*20)
                lineNr = 1
                for text in txtLines:
                  pygame.draw.rect(self.screen, GRAY, (mouse_pos[0]+20, textBoxCoord+lineNr*20, txtWidth, text.get_rect()[3]))
                  self.screen.blit(text, (mouse_pos[0]+20, textBoxCoord+lineNr*20))
                  lineNr+=1
        markers = self.new_state.get('markers',{})
        for key in markers:
          key_split = key.split(':')

          if (abs(coord_x - int(key_split[0])) < 4/self.zoom_level):
            if (abs(coord_y - int(key_split[1])) < 4/self.zoom_level):
              text = self.BIG_FONT.render(f'{markers[key]}', True, BLACK)
              txtWidth = text.get_rect()[2]
              pygame.draw.rect(self.screen, GRAY, (mouse_pos[0]+20, mouse_pos[1]+5, txtWidth, text.get_rect()[3]))
              self.screen.blit(text, (mouse_pos[0]+20, mouse_pos[1]+5))

    return

  def Draw_Menu(self):
    MENU_WIDTH = 120
    MENU_HEIGHT = 20
    if (self.menu_open):
      for i in range(len(self.menu_items)):
        pygame.draw.rect(self.screen, GRAY, (self.menu_pos[0], self.menu_pos[1]+i*MENU_HEIGHT, MENU_WIDTH, MENU_HEIGHT))
        menu_text = self.BIG_FONT.render(self.menu_items[i], True, BLACK)
        self.screen.blit(menu_text, (self.menu_pos[0], self.menu_pos[1]+i*MENU_HEIGHT))

  def Draw_Tooltip(self):
    MENU_WIDTH = 50
    MENU_HEIGHT = 20
    if (self.tooltip):
      
      tooltip_text = self.BIG_FONT.render(self.tooltip, True, BLACK)
      pygame.draw.rect(self.screen, GRAY, (self.tooltip_pos[0]+20, self.tooltip_pos[1]+5, tooltip_text.get_rect()[2], MENU_HEIGHT))
      self.screen.blit(tooltip_text, (self.tooltip_pos[0]+20, self.tooltip_pos[1]+5))

  def Draw(self):
    self.Draw_Calendar_Year()
    self.Draw_Weekly_Calendar()
    self.Draw_FoodStorage()
    self.Draw_Chores()
    self.Draw_Tally()
    self.Draw_Map()
    self.Draw_Menu()
    self.Draw_Tooltip()
    pygame.display.flip()

  def ProcessRightMouseButton(self, mouse_pos):
    self.menu_open = not self.menu_open
    if (self.menu_open):
      self.menu_pos = mouse_pos

  def ProcessLeftMouseButton(self, mouse_pos):
    if (self.menu_open):
      MENU_WIDTH = 120
      MENU_HEIGHT = 20
      if (mouse_pos[0] >= self.menu_pos[0]) and (mouse_pos[0] < self.menu_pos[0]+MENU_WIDTH):
        for i in range(len(self.menu_items)):
          if (mouse_pos[1] >= self.menu_pos[1]+i*MENU_HEIGHT) and (mouse_pos[1] < self.menu_pos[1]+i*MENU_HEIGHT+MENU_HEIGHT):
            if i > 0:
              #print('Selected ',menu_items[i], self.menu_date)
              self.blacksmith.append({'type': self.menu_items[i],
                                      'location': f'{self.last_x}:{self.last_y}',
                                      'finish': self.menu_date.GetDateTime()
                                    })
                
              self.reminders = {'blacksmith processes':self.blacksmith}
              self.Save_Json(REMINDERS_FILE, self.reminders)
              self.Fill_Events()

            self.menu_open = False

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GRAY = (220, 220, 220)
MED_GRAY = (180, 180, 180)
DARK_GRAY = (100, 100, 100)
LIGHT_GRAY = (230, 230, 230)
SEASON_COLORS = {
    'spring': (204, 255, 204),
    'summer': (255, 204, 204),
    'fall':   (230, 204, 179),
    'winter': (224, 224, 224),
}

LOG_FILE = 'msglog.txt'
STATE_FILE = 'state.json'
PROGRESS_FILE = 'progress.json'
REMINDERS_FILE = 'reminders.json'
FOW_FILE = 'fog_of_war.csv'
TILES_PATH = 'tiles\\'

# Layout for weekly columns
box_width = 27
box_height = 48
week_width = box_width + 2
week_height = 7 * box_height + 20

# Limit display to 52 weeks
display_weeks = 52

BEFORE = -1
EQUAL = 0
AFTER = 1
NONE = 0
FIRST = 1
SECOND = 2
BOTH = 3

CAL_WIDTH, CAL_HEIGHT = 730, 460

# Colors
BG_COLOR = (245, 241, 235)
LINE_COLOR = (210, 200, 185)
TEXT_COLOR = (40, 40, 30)
HEADER_BG = (220, 214, 202)
HOUR_LABEL_COLOR = (100, 90, 70)
CURRENT_DAY_COLOR = (150, 180, 150)
CURRENT_HOUR_COLOR = (100, 130, 100)
EVENT_COLOR = (60, 60, 60)
EVENT_COLOR_HIGHLIGHTED = (255, 255, 255)

# Layout
DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
VISIBLE_HOURS = list(range(25))
MARGIN_X = 60
MARGIN_Y = 20
HEADER_HEIGHT = 26
HOUR_HEIGHT = (CAL_HEIGHT - MARGIN_Y - HEADER_HEIGHT - 10) // 24
COL_WIDTH = (CAL_WIDTH - MARGIN_X - 10-80) // 7

# --- Main Loop ---
def main():
  game = URL_Calendar()

  while True:
    for event in pygame.event.get():
      if event.type == pygame.QUIT:
        pygame.quit()
        sys.exit()

      elif event.type == pygame.MOUSEBUTTONUP:
        if event.button == 3:
          last_mouse = event.pos
          game.ProcessRightMouseButton(event.pos)

      elif event.type == pygame.MOUSEBUTTONDOWN:
        if event.button == 1:
          last_mouse = event.pos
          game.ProcessLeftMouseButton(event.pos)
        elif event.button == 4:
          if (event.pos[0] >= game.map_x) and (event.pos[0] < game.map_x+game.map_width) and (event.pos[1] >= game.map_y) and (event.pos[1] < game.map_y+game.map_height):
            game.zoom_level = min(5,game.zoom_level + 1)
            game.CreateMap()
        elif event.button == 5:
          if (event.pos[0] >= game.map_x) and (event.pos[0] < game.map_x+game.map_width) and (event.pos[1] >= game.map_y) and (event.pos[1] < game.map_y+game.map_height):
            game.zoom_level = max(1,game.zoom_level - 1)
            game.CreateMap()

    if (game.File_Has_Changed()):
      game.Parse_Log()
      game.Fill_Events()
    game.Draw()
    time.sleep(0.050)

if __name__=="__main__":
  # call the main function
  main()

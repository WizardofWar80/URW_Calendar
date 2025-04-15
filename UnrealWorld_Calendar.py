# -*- coding: utf-8 -*-
import pygame
import sys
import os
import re
import json
import time
from collections import defaultdict

pygame.init()

DEBUG = False

SCREEN_WIDTH = 1600
SCREEN_HEIGHT = 900

class URL_Calendar():
  # --- Constants ---
  def __init__(self):
    self.last_x = 0
    self.last_y = 0
    self.event_markers = {}
    self.todays_events = {}
    self.weekly_events = {}
    self.tally_stats = {}
    self.temp_village_content = []
    self.logfile_changed_ts = None
    self.current_timestamp = None
    self.current_weekday = None
    self.new_state = None
    self.progress = None
    self.has_dog = False
    self.in_settlement = False
    self.current_settlement_key = None
    self.village_goods = {}
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
  def Get_season(self, day_number):
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

  def Parse_timestamp(self, ts):
      if len(ts) != 4:
        print('timstamp has wrong length: \'%s\''%ts)
        return None
      try:
          day = char_to_num[ts[0]]
          month = char_to_num[ts[1]]
          year = char_to_num[ts[2]] + 1200 - 15
          hour = char_to_num[ts[3]]  # not real hours, just relative
          return {'day': day, 'month': month, 'year': year, 'hour': hour}
      except:
          print ('error parsing timestamp: \'%s\''%ts)
          return None

  def CheckDateIsBeforeOrAfter(self, date_to_check, check_against):
    if (date_to_check[2] < check_against[2]):
      # this year is before check year
      return BEFORE
    else:
      if (date_to_check[2] == check_against[2]):
        # same year
        if (date_to_check[1] < check_against[1]):
          # this month is before check month
          return BEFORE
        else:
          if (date_to_check[1] == check_against[1]):
            # same month
            if (date_to_check[0] < check_against[0]):
              # this day is before check day
              return BEFORE
            else:
              if (date_to_check[0] == check_against[0]):
                # same day
                if (date_to_check[3] < check_against[3]):
                  # this hour is before check hour
                  return BEFORE
                else:
                  if (date_to_check[3] == check_against[3]):
                    # same hour
                    return EQUAL
    return AFTER

  def Game_date_to_datetime(self, gd):
    return '%d.%d.%d %d'%(gd['day'], gd['month'], gd['year'], gd['hour'])

  def Add_game_days(self, start, days):
      result = start.copy()
      for _ in range(days):
          result['day'] += 1
          if result['day'] > days_per_month[result['month']]:
              result['day'] = 1
              result['month'] += 1
              if result['month'] > 12:
                  result['month'] = 1
                  result['year'] += 1
      return result

  def To_str_date(self, gd):
    return self.Game_date_to_datetime(gd)

  def Str_date_to_array(self, date_str):
    parts = date_str.replace('.', ' ').split()
    return list(map(int, parts))

  def ConvertToCalendarDay(self, day, month):
    calendar_day = day
    for i in range(1, month):
      calendar_day+=days_per_month[i]
    return calendar_day

  def ConvertFromCalendarDay(self, calendar_day, year, hour = 0):
    day = calendar_day
    month = 1
    for i in range(1,13):
      if (day > days_per_month[i]):
        day -= days_per_month[i]
        month += 1
      else:
        break
    return {'day': day, 'month': month, 'year': year, 'hour': hour}

  def ConvertCalendarDay2WeekDay(self, calendar_day):
    weekday = calendar_day%7
    if weekday == 0:
      weekday = 7
    return weekday

  def Load_json(self, path):
      if not os.path.exists(path):
          return {}
      with open(path, 'r') as f:
          return json.load(f)

  def Save_json(self, path, data):
      with open(path, 'w') as f:
          json.dump(data, f, indent=2)

  def File_has_changed(self):
    if not self.logfile_changed_ts:
      self.logfile_changed_ts = os.path.getmtime(LOG_FILE)
      return True
    else:
      ts = os.path.getmtime(LOG_FILE)
      if (ts != self.logfile_changed_ts):
        self.logfile_changed_ts = ts
        return True
    return False

  def Parse_log(self):
    self.state = self.Load_json(STATE_FILE)
    self.progress = self.Load_json(PROGRESS_FILE)
    x = 0
    y = 0
    if 'last_ts' not in self.progress:
      print('New file being created')
      self.progress['last_ts'] = '0000'
    else:
      self.current_timestamp = self.Parse_timestamp(self.progress['last_ts'])
    if 'repeats' not in self.progress:
      self.progress['repeats'] = 0
    if 'chores' in self.progress:
      if ('Feed Animals' in self.progress['chores']):
        self.has_dog = self.progress['chores']['Feed Animals']['needed']
    if 'temp settlement' in self.progress:
      self.temp_village_content = self.progress['temp settlement']['content']
      self.current_settlement_key = self.progress['temp settlement']['key']
    if (DEBUG):
      print(self.progress)
      print(self.current_timestamp)

    trees_felled = self.state.get('trees_felled', 0)
    fires_made = self.state.get('fires_made', 0)
    sacrifices = self.state.get('sacrifices', 0)
    kills = self.state.get('kills', {})
    meat_cuts = self.state.get('meat_cuts', {})
    tanning = self.state.get('tanning_processes', [])
    cooking = self.state.get('cooking_processes', [])
    textile = self.state.get('textile_processes', [])
    settlements = self.state.get('settlements',{})
    markers = self.state.get('markers',{})
    self.village_goods = self.state.get('village_goods',{})
    tanning_outcomes = self.state.get('tanning_outcomes', {})
    building_counts = self.state.get('buildings', {})

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

      color, ts,msg_type,place, msg = m.groups()
      x = int(place[0:4], 16)
      y = int(place[4:8], 16)
      if ts == last_ts: #progress['last_ts']:
        repeating_timestamps += 1
      else:
        repeating_timestamps = 0
      last_ts = ts
      if (self.CheckDateIsBeforeOrAfter(ts, self.progress['last_ts']) == BEFORE):
        i += 1
        continue
      else:
        if(self.CheckDateIsBeforeOrAfter(ts, self.progress['last_ts']) == EQUAL) and (repeating_timestamps <= self.progress['repeats']):
          i += 1
          continue

      new_ts = self.Parse_timestamp(ts)
      if (not self.current_timestamp) or (new_ts['day'] != self.current_timestamp['day']):
        self.new_day = True
        self.progress['chores'] = {'Make Fire':{'needed':False, 'done':False},
                              'Sacrifice':    {'needed':True, 'done':False},
                              'Feed Animals': {'needed':self.has_dog, 'done':False},
                              'Herblore':     {'needed':True, 'done':False},
                              'Weatherlore':  {'needed':True, 'done':False}
                              }

      self.current_timestamp = new_ts

      if msg == 'ANIMAL COMMANDS: Dog: I shall name you...':
        self.has_dog = True

      trees_felled= self.Look_for_tally_items('The tree falls down.',       msg, trees_felled)
      sacrifices  = self.Look_for_tally_items('sacrifice',                  msg, sacrifices)
      fires_made  = self.Look_for_tally_items('You managed to make a fire', msg, fires_made)


      self.Look_for_chores(['sacrifice'], lines,i, msg, self.progress['chores']['Sacrifice'])
      self.Look_for_chores(['You managed to make a fire','smoked','(being prepared)'], lines,i, msg, self.progress['chores']['Make Fire'], multiline = True, backwards=True, search_area=25)
      self.Look_for_chores(['Using: WEATHERLORE'], lines,i, msg, self.progress['chores']['Weatherlore'])
      self.Look_for_chores(['You do not recognize what','You have learned something new about','You do know that'], lines,i, msg, self.progress['chores']['Herblore'],operator_and = False)
      self.Look_for_chores(['Eat now','gives you a happy look.'], lines,i, msg, self.progress['chores']['Feed Animals'], multiline = True)

      if 'You are entering ' in msg:
        s = msg[msg.find('You are entering'):]
        s = s.replace('You are entering ','').replace('a ','').replace('an ','').replace('...','').replace('\ufffd','\u00e4') # replace question mark with ä

        key = f'{x}:{y}'
        self.current_settlement_key = key
        if key not in settlements:
          settlements[key] = s
        self.temp_village_content = []
        self.in_settlement = True
      elif 'Zooming out ...' in msg:
        if (self.in_settlement):
          self.in_settlement = False
          if not self.current_settlement_key:
            self.current_settlement_key = f'{x}:{y}'
          self.Tally_Village_Goods(self.current_settlement_key)
          self.current_settlement_key = None
      elif 'You see a marked location' in msg:
        text = msg.split('\"')
        key = f'{x}:{y}'
        if key not in markers:
          markers[key] = text[1]
      elif msg == 'Ok. You finish the current building job.':
        # look back to find last building name
        for j in range(1, 20):
          prev_line = lines[max(1,i-j)]
          if 'BUILDING OPTIONS:' in prev_line:
            name = prev_line.split('BUILDING OPTIONS:')[-1].strip().lower()
            break
          elif 'You continue working on the' in prev_line:
            name = prev_line.split('You continue working on the')[-1].strip().lower()
            break
        else:
          name = 'unknown'
        for keyword in ['fence', 'corner', 'wall', 'door', 'shutter', 'cellar', 'fireplace', 'wooden building']:
          if keyword in name.lower():
            building_counts[keyword] = building_counts.get(keyword, 0) + 1
      elif 'sighs once, then stays laying dead still' in msg:
        m = re.search(r'the (.*?) sighs once', msg)
        if m:
          name = m.group(1).strip().lower().replace(' calf', '')
          if ' ' in name:
            name = name.split(' ')[1]
          kills[name] = kills.get(name, 0) + 1
      elif 'You got' in msg and 'meat' in msg:
        m = re.search(r'You got (\d+) edible cuts of (.*?) meat', msg)
        if m:
          count, name = m.groups()
          name = name.lower()
          if ' ' in name:
            name = name.split(' ')[1]
          meat_cuts[name] = meat_cuts.get(name, 0) + int(count)
      elif 'finish the tanning process and obtained a' in msg:
        m = re.search(r'obtained a (.*?) (.*?) (leather|fur)', msg)
        if m:
          quality, ttype, material = m.groups()
          ttype = ttype.replace(' forest', '')
          if ' ' in ttype:
            ttype = ttype.split(' ')[1]
          key = f'{ttype}:{material}:{quality}'
          tanning_outcomes[key] = tanning_outcomes.get(key, 0) + 1
      # Processes
      elif 'tanning the skin' in msg:
        self.Parse_short_process(msg, tanning)
      elif 'Ok, you leave' in msg and 'to cook and prepare' in msg:
        cooking_type = ''
        if 'dried' in msg:
          cooking_type = 'Drying Food'
        elif 'smoked' in msg:
          cooking_type = 'Smoking'
        elif 'roasted' in msg:
          cooking_type = 'Roasting'
          i += 1
        amount_type = msg.split('leave')[-1].split('to cook')[0].strip()
        self.Parse_long_process(lines, i, msg, cooking, cooking_type, amount_type)
      elif 'You leave the nettles to soak in the water, after which they are properly retted.' in msg:
        self.Parse_long_process(lines, i, msg, textile, 'Retting')
      elif 'The retted nettles are now set in loose bundles to dry out fully, after which you can proceed with extracting the fibre.' in msg:
        self.Parse_long_process(lines, i, msg, textile, 'Drying Nettles')
      elif self.in_settlement:
        if 'Things that are here:' in msg or 'There are several objects here:' in msg:
          self.Parse_Items_On_Ground(lines, i)

      i += 1
      last_ts = ts
    self.progress['last_ts'] = ts
    self.progress['repeats'] = repeating_timestamps
    self.progress['temp settlement']={}
    self.progress['temp settlement']['content'] = self.temp_village_content
    self.progress['temp settlement']['key'] = self.current_settlement_key

    # save new state
    tanning_outcomes = dict(sorted(tanning_outcomes.items()))
    kills = dict(sorted(kills.items()))
    meat_cuts = dict(sorted(meat_cuts.items()))
    self.new_state = {
        'trees_felled': trees_felled,
        'fires_made': fires_made,
        'sacrifices': sacrifices,
        'kills': kills,
        'meat_cuts': meat_cuts,
        'settlements': settlements,
        'markers':markers,
        'tanning_processes': tanning,
        'cooking_processes': cooking,
        'textile_processes':textile,
        'tanning_outcomes': tanning_outcomes,
        'buildings': building_counts,
        'village_goods':self.village_goods
    }

    self.Save_json(STATE_FILE, self.new_state)
    self.Save_json(PROGRESS_FILE, self.progress)
    
    if (x != self.last_x) or (y != self.last_y):
      print('Map coordinate: ',x,y)
      self.last_x = x
      self.last_y = y

  def Convert_Weekday_to_Day_Month(self, weekday, week, year, hour):
    year_day = week * 7 + weekday
    month = 1
    for month in range(1,13):
      if (year_day < days_per_month[month]):
        day = year_day+1
        break
      else:
        year_day -= days_per_month[month]

    return {'day': day, 'month': month, 'year': year, 'hour': hour}

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

    calendar_day_today = self.ConvertToCalendarDay(self.current_timestamp['day'], self.current_timestamp['month'])
    self.current_weekday = self.ConvertCalendarDay2WeekDay(calendar_day_today)
    calendar_day_start_of_week = calendar_day_today - self.current_weekday + 1
    date_week_start = self.ConvertFromCalendarDay(calendar_day_start_of_week, self.current_timestamp['year'], 0)
    date_week_end = self.ConvertFromCalendarDay(calendar_day_start_of_week+7, self.current_timestamp['year'], 0)
    this_weeK_array = [date_week_start['day'],date_week_start['month'],date_week_start['year'],0]
    this_weeK_array2 = [date_week_end['day'],date_week_end['month'],date_week_end['year'],0]

    today = [self.current_timestamp['day'],self.current_timestamp['month'],self.current_timestamp['year'],0]
    tomorrow_ = self.Add_game_days(self.current_timestamp, 0)
    tomorrow = [tomorrow_['day'],tomorrow_['month'],tomorrow_['year'],0]
    if 'cooking_processes' in self.new_state:
      this_year = [1,1,self.current_timestamp['year'],0]
      next_year = [1,1,self.current_timestamp['year']+1,0]
      for o in self.new_state['cooking_processes']:
        cooking_end_date = self.Str_date_to_array(o['end'])
        cooking_start_date = self.Str_date_to_array(o['start'])
        cal_day = self.ConvertToCalendarDay(cooking_end_date[0], cooking_end_date[1])
        if (self.CheckDateIsBeforeOrAfter(cooking_end_date, this_year) != BEFORE):
          if (self.CheckDateIsBeforeOrAfter(cooking_end_date, next_year) == BEFORE):
            if o['type'] == 'Drying Food':
              self.Add_Event(cal_day, 'D')
            elif o['type'] == 'Smoking':
              self.Add_Event(cal_day, 'S')
              if (self.CheckDateIsBeforeOrAfter(cooking_start_date, this_weeK_array2) == BEFORE):
                if (self.CheckDateIsBeforeOrAfter(cooking_end_date, this_weeK_array) == AFTER):
                  s = 1
                  e = 8
                  if (self.CheckDateIsBeforeOrAfter(cooking_start_date, this_weeK_array) == AFTER):
                    cooking_start_calenderday = self.ConvertToCalendarDay(cooking_start_date[0], cooking_start_date[1])
                    cooking_start_weekday = self.ConvertCalendarDay2WeekDay(cooking_start_calenderday)
                    s = cooking_start_weekday
                  if (self.CheckDateIsBeforeOrAfter(cooking_end_date, this_weeK_array2) == BEFORE):
                    cooking_end_calenderday = self.ConvertToCalendarDay(cooking_end_date[0], cooking_end_date[1])
                    cooking_end_weekday = self.ConvertCalendarDay2WeekDay(cooking_end_calenderday)
                    e = cooking_end_weekday+1
                  for d in range(s, e):
                    self.weekly_events[(d, 5)].append('Make Fire')
                  if (self.current_weekday >= s and self.current_weekday <= e):
                    self.progress['chores']['Make Fire']['needed'] = True

        if (self.CheckDateIsBeforeOrAfter(cooking_end_date, this_weeK_array) != BEFORE):
          if (self.CheckDateIsBeforeOrAfter(cooking_end_date, this_weeK_array2) == BEFORE):
            d_w = self.ConvertCalendarDay2WeekDay(self.ConvertToCalendarDay(cooking_end_date[0], cooking_end_date[1]))
            if o['type'] == 'Drying Food':
              self.weekly_events[(d_w, cooking_end_date[3])].append('Drying')
            elif o['type'] == 'Smoking':
              self.weekly_events[(d_w, cooking_end_date[3])].append('Smoking')

        if (cal_day == calendar_day_today):
          if (self.CheckDateIsBeforeOrAfter(cooking_end_date, tomorrow) == BEFORE):
            self.todays_events[cooking_end_date[3]] = o['amount']

    if 'tanning_processes' in self.new_state:
      this_year = [1,1,self.current_timestamp['year'],0]
      next_year = [1,1,self.current_timestamp['year']+1,0]
      for t in self.new_state['tanning_processes']:
        tanning_end_date = self.Str_date_to_array(t['end'])
        cal_day = self.ConvertToCalendarDay(tanning_end_date[0], tanning_end_date[1])
        if (self.CheckDateIsBeforeOrAfter(tanning_end_date, this_year) != BEFORE):
          if (self.CheckDateIsBeforeOrAfter(tanning_end_date, next_year) == BEFORE):
            self.Add_Event(cal_day, 'T')
        if (cal_day == calendar_day_today):
          if (self.CheckDateIsBeforeOrAfter(tanning_end_date, tomorrow) == BEFORE):
            self.todays_events[tanning_end_date[3]] = 'tanning'
        if (self.CheckDateIsBeforeOrAfter(tanning_end_date, this_weeK_array) != BEFORE):
          if (self.CheckDateIsBeforeOrAfter(tanning_end_date, this_weeK_array2) == BEFORE):
            d_w = self.ConvertCalendarDay2WeekDay(self.ConvertToCalendarDay(tanning_end_date[0], tanning_end_date[1]))
            self.weekly_events[(d_w, tanning_end_date[3])].append('Tanning')

    if 'textile_processes' in self.new_state:
      this_year = [1,1,self.current_timestamp['year'],0]
      next_year = [1,1,self.current_timestamp['year']+1,0]
      for t in self.new_state['textile_processes']:
        end_date = self.Str_date_to_array(t['end'])
        cal_day = self.ConvertToCalendarDay(end_date[0], end_date[1])
        if (self.CheckDateIsBeforeOrAfter(end_date, this_year) != BEFORE):
          if (self.CheckDateIsBeforeOrAfter(end_date, next_year) == BEFORE):
            if (t['type'] == 'Retting'):
              self.Add_Event(cal_day, 'R')
            elif (t['type'] == 'Drying Nettles'):
              self.Add_Event(cal_day, 'd')
        if (cal_day == calendar_day_today):
          if (self.CheckDateIsBeforeOrAfter(end_date, tomorrow) == BEFORE):
            self.todays_events[end_date[3]] = t['type']
        if (self.CheckDateIsBeforeOrAfter(end_date, this_weeK_array) != BEFORE):
          if (self.CheckDateIsBeforeOrAfter(end_date, this_weeK_array2) == BEFORE):
            d_w = self.ConvertCalendarDay2WeekDay(self.ConvertToCalendarDay(end_date[0], end_date[1]))
            self.weekly_events[(d_w, end_date[3])].append(t['type'])

  def Look_for_tally_items(self, search_string,msg,  tally_var):
    if search_string in msg:
      tally_var += 1
    return tally_var

  def Look_for_chores(self,search_strings,  lines, i, msg, chore_var, multiline = False, backwards = False, search_area = 5, operator_and = True):
    if (multiline):
      if search_strings[0] in msg:
        count_matches = 1
        for j in range (1,search_area):
          if (backwards):
            line = lines[max(1,i-j)]
          else:
            line = lines[min(i+j,len(lines)-1)]
          for i in range(1,len(search_strings)):
            ss = search_strings[i]
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

  def Parse_long_process(self, lines, i, msg, item, process_type, amount=None):
    for j in range(i+1, min(i+4, len(lines))):
      if 'should be complete' in lines[j]:
        m = re.search(r'after (\d+) days', lines[j])
        if m:
          duration = int(m.group(1))
          if self.current_timestamp:
            if (amount):
              item.append({
                'type': process_type,
                'amount': amount,
                'start': self.To_str_date(self.current_timestamp),
                'end': self.To_str_date(self.Add_game_days(self.current_timestamp, duration))
              })
            else:
              item.append({
                'type': process_type,
                'start': self.To_str_date(self.current_timestamp),
                'end': self.To_str_date(self.Add_game_days(self.current_timestamp, duration))
              })
            break

  def Parse_short_process(self, msg, item):
    if self.current_timestamp:
      start_date = self.current_timestamp.copy()
      end_date = self.current_timestamp.copy()
      end_date_text = msg.split('.')[0]
      if ('a few hours' in end_date_text):
        end_date['hour'] +=2
        if (end_date['hour'] > 23):
          end_date = self.Add_game_days(end_date,1)
          end_date['hour'] = end_date['hour']-24
      elif 'This step is complete by ' in msg:
        time = msg[msg.find(' by ')+4:msg.find('.')]
        for h in range(len(string_timeofday)):
          if time.strip() == string_timeofday[h].lower():
            break
        if h < start_date['hour']:
          end_date = self.Add_game_days(end_date,1)
        end_date['hour'] = h
      item.append({
          'start': self.To_str_date(self.current_timestamp),
          'end': self.To_str_date(end_date),
          'timeframe': end_date_text
      })

  def Parse_Items_On_Ground(self, lines, i):
    items = []
    for j in range(i+1, min(i+100, len(lines))):
      line = lines[j]
      if (line.startswith('(000000)')): # when the color is not black, its not an item on the ground
        match = re.search(r"\[(.*?)\]", line)
        if match:
          hotkey = match.group(1)
          if (hotkey.isupper()): # Uppercase letters indicate things that are not laying on ground, but are rather persons or building types
            break
        if ('called' in line): # dont count your named animal
          break
        items.append(line.split('| ')[1].strip())
      else:
        break

    if items in self.temp_village_content:
      # don't count the same tiles multiple times
      # still an issue if you pick something up, it then it counts the rest twice...
      # too lazy to subtract stuff that gets picked up from the tiles contents
      pass
    else:
      self.temp_village_content.append(items)

  def Tally_Village_Goods(self, key):
    temp_village_goods = {}
    num_items = 0
    for tile_contents in self.temp_village_content:
      for item in tile_contents:
        tokens = item.split(' ')
        try:
          number = int(tokens[0])
          item = item.replace(tokens[0]+' ', '')
          if item.endswith('s'):
            item = item[:-1]
        except:
          number = 1
        num_items+=1
        if item in temp_village_goods:
          temp_village_goods[item] += number
        else:
          temp_village_goods[item] = number
    # maybe find a better way to handle visits to villages without looking at all items and not overwrite everything
    if (num_items > 0):
      self.village_goods[key] = temp_village_goods

    self.temp_village_content = []

  def Format_hour(self, hour):
    suffix = 'AM' if hour < 12 else 'PM'
    display_hour = hour % 12
    if display_hour == 0:
      display_hour = 12
    return f'{display_hour:2d} {suffix}'

  def Draw_Weekly_Calendar(self):
    atX = 10 + display_weeks * week_width - CAL_WIDTH
    atY = self.calendar_year_y + week_height + 10
    calendar_surface = pygame.Surface((CAL_WIDTH, CAL_HEIGHT))
    calendar_surface.fill(BG_COLOR)

    # Day headers
    for i, day in enumerate(DAYS):
      x = MARGIN_X + i * COL_WIDTH
      y = MARGIN_Y
      rect = pygame.Rect(x, y, COL_WIDTH, HEADER_HEIGHT)
      color = CURRENT_DAY_COLOR if i == (self.current_weekday-1) else HEADER_BG
      pygame.draw.rect(calendar_surface, color, rect, border_radius=3)

      text = self.font_bold_wk_cal.render(day, True, TEXT_COLOR)
      text_rect = text.get_rect(center=(x + COL_WIDTH // 2, y + HEADER_HEIGHT // 2))
      calendar_surface.blit(text, text_rect)

    # Hour grid
    for j, hour in enumerate(VISIBLE_HOURS):
      y = MARGIN_Y + HEADER_HEIGHT + j * HOUR_HEIGHT

      # Right-aligned time label
      label = self.font_wk_cal.render(self.Format_hour(hour), True, HOUR_LABEL_COLOR)
      label_rect = label.get_rect(right=MARGIN_X - 5, centery=y)
      calendar_surface.blit(label, label_rect)
      if (hour < 24):
        label = self.font_wk_cal.render(string_timeofday[hour], True, HOUR_LABEL_COLOR)
        label_rect = label.get_rect(left=MARGIN_X + 7 * COL_WIDTH, centery=y+8)
        calendar_surface.blit(label, label_rect)
      if (j < len(VISIBLE_HOURS)-1):
        for i in range(7):
          x = MARGIN_X + i * COL_WIDTH
          cell_rect = pygame.Rect(x, y, COL_WIDTH, HOUR_HEIGHT)

          is_now = i == (self.current_weekday-1) and hour == self.current_timestamp['hour']
          if is_now:
            pygame.draw.rect(calendar_surface, CURRENT_HOUR_COLOR, cell_rect)

          pygame.draw.rect(calendar_surface, LINE_COLOR, cell_rect, 1)

          events = self.weekly_events.get((i+1, hour), [])
          if events:
            text_color = EVENT_COLOR_HIGHLIGHTED if is_now else EVENT_COLOR
            for k, event in enumerate(events[:1]):
              text = self.font_wk_cal.render(event, True, text_color)
              calendar_surface.blit(text, (x + 4, y + 2))

    # Grid border
    total_height = (len(VISIBLE_HOURS)-1) * HOUR_HEIGHT
    grid_rect = pygame.Rect(MARGIN_X, MARGIN_Y + HEADER_HEIGHT, COL_WIDTH * 7, total_height)
    pygame.draw.rect(calendar_surface, LINE_COLOR, grid_rect, 2, border_radius=4)

    self.screen.blit(calendar_surface, (atX, atY))

  def Draw_Calendar_Year(self):
    self.screen.fill(WHITE)

    # Draw weekly columns
    for week in range(display_weeks):
      week_x = 10 + week * week_width
      self.calendar_year_y = 20

      # Label week number (centered)
      label = self.FONT.render(f'{week+1}', True, BLACK)
      label_rect = label.get_rect(center=(week_x + box_width // 2, self.calendar_year_y - 10))
      self.screen.blit(label, label_rect)

      for d in range(7):
        day_number = week * 7 + d + 1
        if day_number > total_days:
          break

        box_y = self.calendar_year_y + d * (box_height + 1)
        rect = pygame.Rect(week_x, box_y, box_width, box_height)
              
        # Fill each box by season
        season = self.Get_season(day_number)
        pygame.draw.rect(self.screen, SEASON_COLORS[season], rect)
        w = 1
        drawing_date = self.Convert_Weekday_to_Day_Month(d, week, 1, 1)
        #current_timestamp['day'] = 20
        #current_timestamp['month'] = 11
        if (drawing_date['day'] == self.current_timestamp['day'] and drawing_date['month'] == self.current_timestamp['month']):
          w = 2
        pygame.draw.rect(self.screen, BLACK, rect, w)

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
            x = rect.x + 2 + col * 14
            y = rect.y + 18 + row * 14
            marker = self.BOLD_FONT.render(e, True, BLACK)
            self.screen.blit(marker, (x, y))

  def Draw_Chores(self):
    # Draw Chores Section
    chores_x = 10 + display_weeks * week_width - CAL_WIDTH - self.CHORES_WIDTH - 20
    chores_y = self.calendar_year_y + week_height + 10
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
    tally_x = 10
    tally_y = self.calendar_year_y + week_height + 40
    tally_h = len(self.new_state['kills']) * 25 + 40 
    pygame.draw.rect(self.screen, GRAY, (tally_x, tally_y, 400, tally_h))
    pygame.draw.rect(self.screen, BLACK, (tally_x, tally_y, 400, tally_h), 2)
    title = self.TITLE_FONT.render('Kills:', True, BLACK)
    self.screen.blit(title, (tally_x + 10, tally_y + 10))

    for i, (key, val) in enumerate(self.new_state['kills'].items()):
      stat_text = self.BIG_FONT.render(f'{key}s: {val}', True, BLACK)
      self.screen.blit(stat_text, (tally_x + 10, tally_y + 40 + i * 25))

  def Draw(self):
    self.Draw_Calendar_Year()
    self.Draw_Weekly_Calendar()
    self.Draw_Chores()
    self.Draw_Tally()
    pygame.display.flip()

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

# game calendar info
days_per_month = {i: 30 for i in range(1, 13)}
days_per_month[1] = 32
days_per_month[7] = 32
total_days = sum(days_per_month.values())
total_weeks = (total_days + 6) // 7

# character time encoding: 1-9, a-z
time_chars = '0123456789abcdefghijklmnopqrstuvwxyz'
char_to_num = {c: i for i, c in enumerate(time_chars)}
string_timeofday = ['Midnight', 'After midnight','Small hours','','Early morning','','','Morning','','Late Morning', '', 'Noon', '', 'Early afternoon', 'Afternoon', 'Late afternoon', '', 'Early evening', '', 'Evening', 'Late evening', '', 'Night', 'Late night']

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

CAL_WIDTH, CAL_HEIGHT = 730, 500

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

    if (game.File_has_changed()):
      game.Parse_log()
      game.Fill_Events()
      game.Draw()

if __name__=="__main__":
  # call the main function
  main()

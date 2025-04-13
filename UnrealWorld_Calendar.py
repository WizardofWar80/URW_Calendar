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

# --- Constants ---
SCREEN_WIDTH = 1600
SCREEN_HEIGHT = 900
FPS = 60

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

# Fonts
FONT = pygame.font.SysFont('Arial', 12)
BOLD_FONT = pygame.font.SysFont('Arial', 14, bold=True)
BIG_FONT = pygame.font.SysFont('Arial', 18)
TITLE_FONT = pygame.font.SysFont('Arial', 22, bold=True)
SCHEDULE_WIDTH = 400
CHORES_WIDTH = 150


LOG_FILE = 'msglog.txt'
logfile_changed_ts = None
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
#                   0           1                  2           3   4               5  6  7        8  9               a    b      c   d                 e             f                g
string_timeofday = ['Midnight', 'After midnight','Small hours','','Early morning','','','Morning','','Late Morning', '', 'Noon', '', 'Early afternoon', 'Afternoon', 'Late afternoon', '', 'Early evening', '', 'Evening', 'Late evening', '', 'Night', 'Late night']
#   h              i    j          k              l   m         n             o

last_x = 0
last_y = 0


# Assign season by day index
def get_season(day_number):
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

# Events for days (format: (day_number): ['D', 'T', ...])
event_markers = {}
todays_events = {}
weekly_events = {}

# Sample stats
tally_stats = {
    'Animals Killed': 12,
    'Trees Felled': 8,
    'Fires Made': 15,
    'Furs Made': 3,
    'Leathers Made': 6,
}

# Setup screen
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption('Unreal World Calendar')

# Layout for weekly columns
box_width = 27
box_height = 48
week_width = box_width + 2
week_height = 7 * box_height + 20

# Limit display to 52 weeks
display_weeks = 52

current_timestamp = None
current_weekday = None
new_state = None
progress = None
BEFORE = -1
EQUAL = 0
AFTER = 1

CAL_WIDTH, CAL_HEIGHT = 730, 500
font_wk_cal = pygame.font.SysFont('Segoe UI', 11, bold=True)
font_bold_wk_cal = pygame.font.SysFont('Segoe UI', 12, bold=True)

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

has_dog = False

def parse_timestamp(ts):
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

def CheckDateIsBeforeOrAfter(date_to_check, check_against):
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

def game_date_to_datetime(gd):
  return '%d.%d.%d %d'%(gd['day'], gd['month'], gd['year'], gd['hour'])

def add_game_days(start, days):
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

def to_str_date(gd):
  return game_date_to_datetime(gd)

def str_date_to_array(date_str):
  parts = date_str.replace('.', ' ').split()
  return list(map(int, parts))

def ConvertToCalendarDay(day, month):
  calendar_day = day
  for i in range(1, month):
    calendar_day+=days_per_month[i]
  return calendar_day

def ConvertFromCalendarDay(calendar_day, year, hour = 0):
  day = calendar_day
  month = 1
  for i in range(1,13):
    if (day > days_per_month[i]):
      day -= days_per_month[i]
      month += 1
    else:
      break
  return {'day': day, 'month': month, 'year': year, 'hour': hour}

def ConvertCalendarDay2WeekDay(calendar_day):
  weekday = calendar_day%7
  if weekday == 0:
    weekday = 7
  return weekday

def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, 'r') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def File_has_changed():
  global logfile_changed_ts
  if not logfile_changed_ts:
    logfile_changed_ts = os.path.getmtime(LOG_FILE)
    return True
  else:
    ts = os.path.getmtime(LOG_FILE)
    if (ts != logfile_changed_ts):
      logfile_changed_ts = ts
      return True
  return False

def parse_log():
  global last_x, last_y, current_timestamp, new_state, progress, has_dog
  state = load_json(STATE_FILE)
  progress = load_json(PROGRESS_FILE)
  x = 0
  y = 0
  if 'last_ts' not in progress:
    print('New file being created')
    progress['last_ts'] = '0000'
  else:
    current_timestamp = parse_timestamp(progress['last_ts'])
  if 'repeats' not in progress:
    progress['repeats'] = 0
  if 'chores' in progress:
    if ('Feed Animals' in progress['chores']):
      has_dog = progress['chores']['Feed Animals']['needed']
  if (DEBUG):
    print(progress)
    print(current_timestamp)

  trees_felled = state.get('trees_felled', 0)
  fires_made = state.get('fires_made', 0)
  sacrifices = state.get('sacrifices', 0)
  kills = state.get('kills', {})
  meat_cuts = state.get('meat_cuts', {})
  tanning = state.get('tanning_processes', [])
  cooking = state.get('cooking_processes', [])
  textile = state.get('textile_processes', [])
  settlements = state.get('settlements',{})
  markers = state.get('markers',{})
  tanning_outcomes = state.get('tanning_outcomes', {})
  building_counts = state.get('buildings', {})

  with open(LOG_FILE, 'r', encoding='utf-8', errors='replace') as f:  # Adding 'errors='replace''
    lines = f.readlines()

  last_building_line = ''
  #current_timestamp = None # handled globally now
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
    if (CheckDateIsBeforeOrAfter(ts, progress['last_ts']) == BEFORE):
      i += 1
      continue
    else:
      if(CheckDateIsBeforeOrAfter(ts, progress['last_ts']) == EQUAL) and (repeating_timestamps <= progress['repeats']):
        i += 1
        continue

    new_ts = parse_timestamp(ts)
    if (not current_timestamp) or (new_ts['day'] != current_timestamp['day']):
      new_day = True
      progress['chores'] = {'Make Fire':{'needed':False, 'done':False},
                            'Sacrifice':    {'needed':True, 'done':False},
                            'Feed Animals': {'needed':has_dog, 'done':False},
                            'Herblore':     {'needed':True, 'done':False},
                            'Weatherlore':  {'needed':True, 'done':False}
                            }

    current_timestamp = new_ts
    # Check message patterns
    if msg == 'The tree falls down.':
      trees_felled += 1
    elif msg == 'Using: WEATHERLORE':
      progress['chores']['Weatherlore']['done'] = True
    elif 'You do not recognize what' in msg or 'You have learned something new about' in msg or 'You do know that' in msg:
      progress['chores']['Herblore']['done'] = True
    elif msg == 'You managed to make a fire.':
      fires_made += 1
      for j in range (1,25):
        prev_line = lines[max(1,i-j)]
        if 'smoked' in prev_line and '(being prepared)' in prev_line:
          progress['chores']['Make Fire']['done'] = True
          break
    elif msg == 'ANIMAL COMMANDS: Dog: I shall name you...':
      has_dog = True
    elif msg.find('ANIMAL COMMANDS:') > -1 and msg.find(' Eat now') > -1:
      for j in range(i+1,min(i+5,len(lines))):
        prev_line = lines[j]
        if prev_line.find('gives you a happy look.') > -1:
          progress['chores']['Feed Animals']['done'] = True
          break
        #probably tried to go beyond last line
    elif 'You are entering ' in msg:
      s = msg[msg.find('You are entering'):]
      s = s.replace('You are entering ','').replace('a ','').replace('an ','').replace('...','').replace('\ufffd','\u00e4') # replace question mark with ä

      key = f'{x}:{y}'
      if key not in settlements:
        settlements[key] = s
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
    elif 'sacrifice' in msg:
      progress['chores']['Sacrifice']['done'] = True
      sacrifices += 1
    elif 'tanning the skin' in msg:
      if current_timestamp:
        start_date = current_timestamp.copy()
        end_date = current_timestamp.copy()
        end_date_text = msg.split('[')[-1].split(']')[0]
        if ('a few hours' in end_date_text):
          end_date['hour'] +=2
          if (end_date['hour'] > 23):
            end_date = add_game_days(end_date,1)
            end_date['hour'] = end_date['hour']-24
        elif 'This step is complete by ' in msg:
          time = msg[msg.find(' by ')+4:msg.find('.')]
          for h in range(len(string_timeofday)):
            if time.strip() == string_timeofday[h].lower():
              break
          if h < start_date['hour']:
            end_date = add_game_days(end_date,1)
          end_date['hour'] = h
        tanning.append({
            'start': to_str_date(current_timestamp),
            'end': to_str_date(end_date),
            'timeframe': msg.split('[')[-1].split(']')[0]
        })
    elif 'finish the tanning process and obtained a' in msg:
      m = re.search(r'obtained a (.*?) (.*?) (leather|fur)', msg)
      if m:
        quality, ttype, material = m.groups()
        ttype = ttype.replace(' forest', '')
        if ' ' in ttype:
          ttype = ttype.split(' ')[1]
        key = f'{ttype}:{material}:{quality}'
        tanning_outcomes[key] = tanning_outcomes.get(key, 0) + 1
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
      # look ahead for completion time
      duration = 0
      for j in range(i+1, min(i+4, len(lines))):
        if 'should be complete' in lines[j]:
          msg = lines[j].split('| ')[-1]
          end_date = msg.split('[')[-1].split(']')[0]
          m = re.search(r'after (\d+) days', lines[j])
          if m:
            duration = int(m.group(1))
          #    if m.group(1):
          #        duration = int(m.group(1))
          #    else:
          #        duration = 0.02  # roughly one tick
          break
      if current_timestamp:
        cooking.append({
            'type': cooking_type,
            'amount': amount_type,
            'start': to_str_date(current_timestamp),
            'end': to_str_date(add_game_days(current_timestamp, duration))
        })
    elif 'You leave the nettles to soak in the water, after which they are properly retted.' in msg:
      for j in range(i+1, min(i+4, len(lines))):
        if 'should be complete' in lines[j]:
          end_date = msg.split('[')[-1].split(']')[0]
          m = re.search(r'after (\d+) days', lines[j])
          if m:
            duration = int(m.group(1))
        if current_timestamp:
          textile.append({
            'type': 'Retting',
            'start': to_str_date(current_timestamp),
            'end': to_str_date(add_game_days(current_timestamp, duration))
          })
          break
    elif 'The retted nettles are now set in loose bundles to dry out fully, after which you can proceed with extracting the fibre.' in msg:
      for j in range(i+1, min(i+4, len(lines))):
        if 'should be complete' in lines[j]:
          end_date = msg.split('[')[-1].split(']')[0]
          m = re.search(r'after (\d+) days', lines[j])
          if m:
            duration = int(m.group(1))
        if current_timestamp:
          textile.append({
            'type': 'Drying Nettles',
            'start': to_str_date(current_timestamp),
            'end': to_str_date(add_game_days(current_timestamp, duration))
          })
          break
    i += 1
    last_ts = ts
  progress['last_ts'] = ts
  progress['repeats'] = repeating_timestamps


  # save new state
  tanning_outcomes = dict(sorted(tanning_outcomes.items()))
  kills = dict(sorted(kills.items()))
  meat_cuts = dict(sorted(meat_cuts.items()))
  new_state = {
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
      'buildings': building_counts
  }

  save_json(STATE_FILE, new_state)
  save_json(PROGRESS_FILE, progress)
    
  if (x != last_x) or (y != last_y):
    print('Map coordinate: ',x,y)
    last_x = x
    last_y = y

def Convert_Weekday_to_Day_Month(weekday, week, year, hour):
  year_day = week * 7 + weekday
  month = 1
  for month in range(1,13):
    if (year_day < days_per_month[month]):
      day = year_day+1
      break
    else:
      year_day -= days_per_month[month]

  return {'day': day, 'month': month, 'year': year, 'hour': hour}

def Add_Event(day, marker):
  global event_markers

  if (day in event_markers):
    if not marker in event_markers[day]: # dont repeat markers
      event_markers[day].append(marker)
  else:
    event_markers[day] = [marker] # first marker

def Fill_Events():
  global event_markers, todays_events, weekly_events, current_weekday

  event_markers = {}
  todays_events = {}
  weekly_events = defaultdict(list)
  #current_timestamp['day']=26 # debug specific dates
  #current_timestamp['month']=8 # debug specific dates

  calendar_day_today = ConvertToCalendarDay(current_timestamp['day'], current_timestamp['month'])
  current_weekday = ConvertCalendarDay2WeekDay(calendar_day_today)
  calendar_day_start_of_week = calendar_day_today - current_weekday + 1
  date_week_start = ConvertFromCalendarDay(calendar_day_start_of_week, current_timestamp['year'], 0)
  date_week_end = ConvertFromCalendarDay(calendar_day_start_of_week+7, current_timestamp['year'], 0)
  this_weeK_array = [date_week_start['day'],date_week_start['month'],date_week_start['year'],0]
  this_weeK_array2 = [date_week_end['day'],date_week_end['month'],date_week_end['year'],0]

  today = [current_timestamp['day'],current_timestamp['month'],current_timestamp['year'],0]
  tomorrow_ = add_game_days(current_timestamp, 0)
  tomorrow = [tomorrow_['day'],tomorrow_['month'],tomorrow_['year'],0]
  if 'cooking_processes' in new_state:
    this_year = [1,1,current_timestamp['year'],0]
    next_year = [1,1,current_timestamp['year']+1,0]
    for o in new_state['cooking_processes']:
      cooking_end_date = str_date_to_array(o['end'])
      cooking_start_date = str_date_to_array(o['start'])
      cal_day = ConvertToCalendarDay(cooking_end_date[0], cooking_end_date[1])
      if (CheckDateIsBeforeOrAfter(cooking_end_date, this_year) != BEFORE):
        if (CheckDateIsBeforeOrAfter(cooking_end_date, next_year) == BEFORE):
          if o['type'] == 'Drying Food':
            Add_Event(cal_day, 'D')
          elif o['type'] == 'Smoking':
            Add_Event(cal_day, 'S')
            if (CheckDateIsBeforeOrAfter(cooking_start_date, this_weeK_array2) == BEFORE):
              if (CheckDateIsBeforeOrAfter(cooking_end_date, this_weeK_array) == AFTER):
                s = 1
                e = 8
                if (CheckDateIsBeforeOrAfter(cooking_start_date, this_weeK_array) == AFTER):
                  cooking_start_calenderday = ConvertToCalendarDay(cooking_start_date[0], cooking_start_date[1])
                  cooking_start_weekday = ConvertCalendarDay2WeekDay(cooking_start_calenderday)
                  s = cooking_start_weekday
                if (CheckDateIsBeforeOrAfter(cooking_end_date, this_weeK_array2) == BEFORE):
                  cooking_end_calenderday = ConvertToCalendarDay(cooking_end_date[0], cooking_end_date[1])
                  cooking_end_weekday = ConvertCalendarDay2WeekDay(cooking_end_calenderday)
                  e = cooking_end_weekday+1
                for d in range(s, e):
                  weekly_events[(d, 5)].append('Make Fire')
                if (current_weekday >= s and current_weekday <= e):
                  progress['chores']['Make Fire']['needed'] = True

      if (CheckDateIsBeforeOrAfter(cooking_end_date, this_weeK_array) != BEFORE):
        if (CheckDateIsBeforeOrAfter(cooking_end_date, this_weeK_array2) == BEFORE):
          d_w = ConvertCalendarDay2WeekDay(ConvertToCalendarDay(cooking_end_date[0], cooking_end_date[1]))
          if o['type'] == 'Drying Food':
            weekly_events[(d_w, cooking_end_date[3])].append('Drying')
          elif o['type'] == 'Smoking':
            weekly_events[(d_w, cooking_end_date[3])].append('Smoking')

      if (cal_day == calendar_day_today):
        if (CheckDateIsBeforeOrAfter(cooking_end_date, tomorrow) == BEFORE):
          todays_events[cooking_end_date[3]] = o['amount']

  if 'tanning_processes' in new_state:
    this_year = [1,1,current_timestamp['year'],0]
    next_year = [1,1,current_timestamp['year']+1,0]
    for t in new_state['tanning_processes']:
      tanning_end_date = str_date_to_array(t['end'])
      cal_day = ConvertToCalendarDay(tanning_end_date[0], tanning_end_date[1])
      if (CheckDateIsBeforeOrAfter(tanning_end_date, this_year) != BEFORE):
        if (CheckDateIsBeforeOrAfter(tanning_end_date, next_year) == BEFORE):
          Add_Event(cal_day, 'T')
      if (cal_day == calendar_day_today):
        if (CheckDateIsBeforeOrAfter(tanning_end_date, tomorrow) == BEFORE):
          todays_events[tanning_end_date[3]] = 'tanning'
      if (CheckDateIsBeforeOrAfter(tanning_end_date, this_weeK_array) != BEFORE):
        if (CheckDateIsBeforeOrAfter(tanning_end_date, this_weeK_array2) == BEFORE):
          d_w = ConvertCalendarDay2WeekDay(ConvertToCalendarDay(tanning_end_date[0], tanning_end_date[1]))
          weekly_events[(d_w, tanning_end_date[3])].append('Tanning')

  if 'textile_processes' in new_state:
    this_year = [1,1,current_timestamp['year'],0]
    next_year = [1,1,current_timestamp['year']+1,0]
    for t in new_state['textile_processes']:
      end_date = str_date_to_array(t['end'])
      cal_day = ConvertToCalendarDay(end_date[0], end_date[1])
      if (CheckDateIsBeforeOrAfter(end_date, this_year) != BEFORE):
        if (CheckDateIsBeforeOrAfter(end_date, next_year) == BEFORE):
          if (t['type'] == 'Retting'):
            Add_Event(cal_day, 'R')
          elif (t['type'] == 'Drying Nettles'):
            Add_Event(cal_day, 'd')
      if (cal_day == calendar_day_today):
        if (CheckDateIsBeforeOrAfter(end_date, tomorrow) == BEFORE):
          todays_events[end_date[3]] = t['type']
      if (CheckDateIsBeforeOrAfter(end_date, this_weeK_array) != BEFORE):
        if (CheckDateIsBeforeOrAfter(end_date, this_weeK_array2) == BEFORE):
          d_w = ConvertCalendarDay2WeekDay(ConvertToCalendarDay(end_date[0], end_date[1]))
          weekly_events[(d_w, end_date[3])].append(t['type'])

def format_hour(hour):
  suffix = 'AM' if hour < 12 else 'PM'
  display_hour = hour % 12
  if display_hour == 0:
    display_hour = 12
  return f'{display_hour:2d} {suffix}'

def Draw_Weekly_Calendar(main_surface, atX, atY, cal_events, current_wk_day, current_hr):
  calendar_surface = pygame.Surface((CAL_WIDTH, CAL_HEIGHT))
  calendar_surface.fill(BG_COLOR)

  # Day headers
  for i, day in enumerate(DAYS):
    x = MARGIN_X + i * COL_WIDTH
    y = MARGIN_Y
    rect = pygame.Rect(x, y, COL_WIDTH, HEADER_HEIGHT)
    color = CURRENT_DAY_COLOR if i == (current_wk_day-1) else HEADER_BG
    pygame.draw.rect(calendar_surface, color, rect, border_radius=3)

    text = font_bold_wk_cal.render(day, True, TEXT_COLOR)
    text_rect = text.get_rect(center=(x + COL_WIDTH // 2, y + HEADER_HEIGHT // 2))
    calendar_surface.blit(text, text_rect)

  # Hour grid
  for j, hour in enumerate(VISIBLE_HOURS):
    y = MARGIN_Y + HEADER_HEIGHT + j * HOUR_HEIGHT

    # Right-aligned time label
    label = font_wk_cal.render(format_hour(hour), True, HOUR_LABEL_COLOR)
    label_rect = label.get_rect(right=MARGIN_X - 5, centery=y)
    calendar_surface.blit(label, label_rect)
    if (hour < 24):
      label = font_wk_cal.render(string_timeofday[hour], True, HOUR_LABEL_COLOR)
      label_rect = label.get_rect(left=MARGIN_X + 7 * COL_WIDTH, centery=y+8)
      calendar_surface.blit(label, label_rect)
    if (j < len(VISIBLE_HOURS)-1):
      for i in range(7):
        x = MARGIN_X + i * COL_WIDTH
        cell_rect = pygame.Rect(x, y, COL_WIDTH, HOUR_HEIGHT)

        is_now = i == (current_wk_day-1) and hour == current_hr
        if is_now:
          pygame.draw.rect(calendar_surface, CURRENT_HOUR_COLOR, cell_rect)

        pygame.draw.rect(calendar_surface, LINE_COLOR, cell_rect, 1)

        events = cal_events.get((i+1, hour), [])
        if events:
          text_color = EVENT_COLOR_HIGHLIGHTED if is_now else EVENT_COLOR
          for k, event in enumerate(events[:1]):
            text = font_wk_cal.render(event, True, text_color)
            calendar_surface.blit(text, (x + 4, y + 2))

  # Grid border
  total_height = (len(VISIBLE_HOURS)-1) * HOUR_HEIGHT
  grid_rect = pygame.Rect(MARGIN_X, MARGIN_Y + HEADER_HEIGHT, COL_WIDTH * 7, total_height)
  pygame.draw.rect(calendar_surface, LINE_COLOR, grid_rect, 2, border_radius=4)

  main_surface.blit(calendar_surface, (atX, atY))

# --- Main Loop ---
while True:
  for event in pygame.event.get():
    if event.type == pygame.QUIT:
      pygame.quit()
      sys.exit()

  if (File_has_changed()):
    parse_log()
    Fill_Events()
    screen.fill(WHITE)

    # Draw weekly columns
    for week in range(display_weeks):
      week_x = 10 + week * week_width
      week_y = 20

      # Label week number (centered)
      label = FONT.render(f'{week+1}', True, BLACK)
      label_rect = label.get_rect(center=(week_x + box_width // 2, week_y - 10))
      screen.blit(label, label_rect)

      for d in range(7):
        day_number = week * 7 + d + 1
        if day_number > total_days:
          break

        box_y = week_y + d * (box_height + 1)
        rect = pygame.Rect(week_x, box_y, box_width, box_height)
              
        # Fill each box by season
        season = get_season(day_number)
        pygame.draw.rect(screen, SEASON_COLORS[season], rect)
        w = 1
        drawing_date = Convert_Weekday_to_Day_Month(d, week, 1, 1)
        #current_timestamp['day'] = 20
        #current_timestamp['month'] = 11
        if (drawing_date['day'] == current_timestamp['day'] and drawing_date['month'] == current_timestamp['month']):
          w = 2
        pygame.draw.rect(screen, BLACK, rect, w)

        # Draw 1-7 day number inside week
        #daystring = '%d %d/%d'%(d+1, drawing_date['day'], drawing_date['month'])
        daystring = '%d'%(d+1)
        txt = FONT.render(daystring, True, BLACK)
        screen.blit(txt, (rect.x + 2, rect.y + 2))

        # Draw event markers in 2x2 grid if present
        if day_number in event_markers:
          markers = event_markers[day_number]
          for i, e in enumerate(markers):
            col = i % 2
            row = i // 2
            x = rect.x + 2 + col * 14
            y = rect.y + 18 + row * 14
            marker = BOLD_FONT.render(e, True, BLACK)
            screen.blit(marker, (x, y))


    # Draw Tally Panel below calendar
    tally_x = 10
    tally_y = week_y + week_height + 40
    tally_h = len(new_state['kills']) * 25 + 40 
    pygame.draw.rect(screen, GRAY, (tally_x, tally_y, 400, tally_h))
    pygame.draw.rect(screen, BLACK, (tally_x, tally_y, 400, tally_h), 2)
    title = TITLE_FONT.render('Kills:', True, BLACK)
    screen.blit(title, (tally_x + 10, tally_y + 10))

    for i, (key, val) in enumerate(new_state['kills'].items()):
      stat_text = BIG_FONT.render(f'{key}s: {val}', True, BLACK)
      screen.blit(stat_text, (tally_x + 10, tally_y + 40 + i * 25))

    # Draw Chores Section
    chores_x = 10 + display_weeks * week_width - CAL_WIDTH - CHORES_WIDTH - 20
    chores_y = week_y + week_height + 10
    pygame.draw.rect(screen, GRAY, (chores_x, chores_y, CHORES_WIDTH, 200))
    pygame.draw.rect(screen, BLACK, (chores_x, chores_y, CHORES_WIDTH, 200), 2)
    chores_title = TITLE_FONT.render('Chores', True, BLACK)
    screen.blit(chores_title, (chores_x + 10, chores_y + 10))

    # Draw each chore with a checkbox
    checkbox_size = 20
    for i, chore in enumerate(progress['chores']):
      color = DARK_GRAY
      item = progress['chores'][chore]
      if item['needed']:
        color = BLACK
      checkbox_x = chores_x + CHORES_WIDTH - checkbox_size - 10
      checkbox_y = chores_y + 40 + i * 30
      # Draw checkbox (outline)
      pygame.draw.rect(screen, color, (checkbox_x, checkbox_y, checkbox_size, checkbox_size), 2)

      # If chore is done, draw checkmark inside checkbox
      g = 3

      if item['done']:
        pygame.draw.line(screen, color, (checkbox_x + g, checkbox_y + g), (checkbox_x + checkbox_size - 2*g+2, checkbox_y + checkbox_size - 2*g+2), 2)
        pygame.draw.line(screen, color, (checkbox_x + checkbox_size - 2 * g + 2, checkbox_y + g ), (checkbox_x + g, checkbox_y + checkbox_size - 2*g+2), 2)

      # Draw chore name next to checkbox
      chore_text = BIG_FONT.render(chore, True, color)
      screen.blit(chore_text, (chores_x + 5, checkbox_y))

    schedule_x = 10 + display_weeks * week_width - CAL_WIDTH
    schedule_y = week_y + week_height + 10
    Draw_Weekly_Calendar(screen, schedule_x, schedule_y, weekly_events, current_weekday, current_timestamp['hour'])


    pygame.display.flip()

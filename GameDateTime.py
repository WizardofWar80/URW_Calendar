import time
import copy

def Char2Num(char):
  # character time encoding: 1-9, a-z
  time_chars = '0123456789abcdefghijklmnopqrstuvwxyz'
  char_to_num = {c: i for i, c in enumerate(time_chars)}

  return char_to_num[char]

class GameDateTime():
  def __init__(self, value):
    self.day = 1
    self.month = 1
    self.year = 1
    self.hour = 0
    self.calendar_day = 1
    self.weekday = 1
    self.week = 1
    self.__datetime = ''
    #self.datetime = '%d.%d.%d %d'%(self.day, self.month, self.year, self.hour)
    #self.array = [self.day, self.month, self.year, self.hour]
    self.__string_timeofday = ['Midnight', 'After midnight','Small hours','','Early morning','','','Morning','','Late Morning', '', 'Noon', '', 'Early afternoon', 'Afternoon', 'Late afternoon', '', 'Early evening', '', 'Evening', 'Late evening', '', 'Night', 'Late night']

    self.__days_per_month = {i: 30 for i in range(1, 13)}
    self.__days_per_month[1] = 32
    self.__days_per_month[7] = 32
    self.__total_days = sum(self.__days_per_month.values())
    self.__total_weeks = (self.__total_days + 6) // 7
    
    if isinstance(value, list):
      if (len(value) == 4):
        [self.day, self.month, self.year, self.hour] = value
      else:
        raise TypeError('Length of array needs to be 4, but is %d: '%len(value),value)
    elif isinstance(value, str):
      if len(value) != 4:
        [self.day, self.month, self.year, self.hour] = list(map(int, value.replace('.', ' ').split()))
      else:
        self.day   = Char2Num(value[0])
        self.month = Char2Num(value[1])
        self.year  = Char2Num(value[2]) + 1200 - 15
        self.hour  = Char2Num(value[3])
    else:
      raise TypeError(f"Unsupported type: {type(value).__name__}")
    self.Update()


  def GetTimeOfDayFromString(self,time_string):
    for h in range(len(self.__string_timeofday)):
       if time_string.strip() == self.__string_timeofday[h].lower():
         return h
    else:
      return 0

  def GetTimeOfDayFromHour(self,hour):
    return self.__string_timeofday[hour]

  def GetDaysPerYear(self):
    return self.__total_days

  def Update(self):
    self.CalcCalendarDay()
    self.CalcWeek()
    self.CalcWeekDay()
    self.__datetime = self.GetDateTime()

  def GetDateTime(self):
    return '%d.%d.%d %d'%(self.day, self.month, self.year, self.hour)
  
  def CalcCalendarDay(self):
    self.calendar_day = self.day
    for i in range(1, self.month):
      self.calendar_day+=self.__days_per_month[i]
  
  def CalcWeek(self):
    self.week = (self.calendar_day - 1) // 7 + 1
  
  def CalcWeekDay(self):
    self.weekday = (self.calendar_day - 1) % 7 + 1
    
  def GetSeason(self):
    if self.week < 12 or (self.week == 12 and self.weekday == 1):
      return 'winter'
    elif self.week < 20 or (self.week == 20 and self.weekday <= 5):
      return 'spring'
    elif self.week < 29 or (self.week == 29 and self.weekday <= 4):
      return 'summer'
    elif self.week < 42 or (self.week == 42 and self.weekday <= 3):
      return 'fall'
    else:
      return 'winter'
          
  def DateIsThisWeek(self, today):
    return self.week == today.week
      
  def DateIsThisYear(self, today):
    return self.year == today.year

  def IsSameDayAs(self, other):
    if (    (self.year  != other.year ) 
         or (self.month != other.month)
         or (self.day   != other.day  ) ):
      return True
    else:
      return False

  def Is_Between(self, start_date, end_date, inclusive = 0):
    NONE = 0
    FIRST = 1
    SECOND = 2
    
    after_first = False
    before_last = False
    if (inclusive == NONE) or (inclusive == SECOND):
      if (self > start_date):
        after_first = True
    else:
      if (self >= start_date):
        after_first = True
    if (inclusive == NONE) or (inclusive == FIRST):
      if (self < end_date):
        before_last = True
    else:
      if (self <= end_date):
        before_last = True
    return (after_first and before_last)
    
  # Overload == Operator
  def __eq__(self, other):
    if not isinstance(other, GameDateTime):
      return NotImplemented
    if (self.year == other.year):
      if (self.month == other.month):
        if (self.day == other.day):
          if (self.hour == other.hour):
            return True
    return False
  
  # Overload < Operator
  def __lt__(self, other):
    if not isinstance(other, GameDateTime):
      return NotImplemented
    if (self.year > other.year):
      return False
    elif (self.year < other.year):
      return True
    else:
      if (self.month > other.month):
        return False
      elif (self.month < other.month):
        return True
      else:
        if (self.day > other.day):
          return False
        elif (self.day < other.day):
          return True
        else:
          if (self.hour > other.hour):
            return False
          elif (self.hour < other.hour):
            return True
          else:
            return False
    
  # Overload <= Operator
  def __le__(self, other):
    if not isinstance(other, GameDateTime):
      return NotImplemented
    if (self.year > other.year):
      return False
    elif (self.year < other.year):
      return True
    else:
      if (self.month > other.month):
        return False
      elif (self.month < other.month):
        return True
      else:
        if (self.day > other.day):
          return False
        elif (self.day < other.day):
          return True
        else:
          if (self.hour > other.hour):
            return False
          else:
            return True
    
  # Overload > Operator
  def __gt__(self, other):
    if not isinstance(other, GameDateTime):
      return NotImplemented
    if (self.year < other.year):
      return False
    elif (self.year > other.year):
      return True
    else:
      if (self.month < other.month):
        return False
      elif (self.month > other.month):
        return True
      else:
        if (self.day < other.day):
          return False
        elif (self.day > other.day):
          return True
        else:
          if (self.hour < other.hour):
            return False
          elif (self.hour > other.hour):
            return True
          else:
            return False
    
  # Overload >= Operator
  def __ge__(self, other):
    if not isinstance(other, GameDateTime):
      return NotImplemented
    if (self.year < other.year):
      return False
    elif (self.year > other.year):
      return True
    else:
      if (self.month < other.month):
        return False
      elif (self.month > other.month):
        return True
      else:
        if (self.day < other.day):
          return False
        elif (self.day > other.day):
          return True
        else:
          if (self.hour < other.hour):
            return False
          else:
            return True
    
  # Overload != Operator
  def __ne__(self, other):
    if (    (self.year  != other.year ) 
         or (self.month != other.month)
         or (self.day   != other.day  )
         or (self.hour  != other.hour ) ):
      return True
    else:
      return False
    
  # Overload + Operator
  def __add__(self, days):
    if not isinstance(days, int):
      return NotImplemented
    
    result = copy.copy(self)
    for _ in range(days):
      result.day += 1
      if result.day > self.__days_per_month[result.month]:
        result.day = 1
        result.month += 1
        if result.month > 12:
          result.month = 1
          result.year += 1
    self.Update()
    
    return result
    
  # Overload += Operator
  def __iadd__(self, days):
    if not isinstance(days, int):
        return NotImplemented
    for _ in range(days):
      self.day += 1
      if self.day > self.__days_per_month[self.month]:
        self.day = 1
        self.month += 1
        if self.month > 12:
          self.month = 1
          self.year += 1
    self.Update()
     
    return self

  def Copy(self):
    return copy.copy(self)

  def Print(self):
    print(self.GetDateTime)

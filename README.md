# URW_Calendar
![](https://github.com/WizardofWar80/URW_Calendar/blob/main/screenshot.png)
Helpful calendar for the open world survival game Unreal World by Enormus Elk -> https://www.unrealworld.fi/ 

Prerequisites:<br>
*Python3<br>
*Pygame<br>

This is a companion application to run on a second monitor which provides a helpful overview of events in the world of "Unreal World".
It features a calendar year view, with highlighted seasons, markers of important events like when smoking or drying meat is finished, same for tanning, retting, drying nettles.
There is also a weekly view that has an hourly breakdown of each day of the week.

It also keeps track of chores, such as making a fire when you are smoking meat, practicing herblore or weatherlore, tell your dog to eat every day.

Lastly there is a tally of all your kills.
# Usage:
The script should be placed in the savegame folder that you want to monitor while playing and can be started at any time.

The chore 'Make Fire' is for smoking meat, so it checks if you have meat smoking going on, and then when you make a fire, it looks for you standing on prepared smoking meat to count. It wont just count any random fire you make.<br>
The chore 'Feed Animals' checks if you have named a dog, and if so, the chore becomes active. You need to tell the dog to eat, and it looks for the happy looks message from your dog to count successful feeding.<br>

# Remarks:
The script reads the message log and keeps track of information in a seperate file, because the message log 'forgets' older stuff.

Right now I am playing on version 3.85, so this has not been tested with the newer versions yet.

Please don't judge the software architecture, this is a very quick and dirty version, lots of vibe code happening.

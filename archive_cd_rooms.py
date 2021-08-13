# =============================================================================
# MIT License
# 
# Copyright (c) 2021 luckytyphlosion
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# =============================================================================

import requests
import re
from abc import ABC, abstractmethod
import traceback
import datetime
import bs4
import time

CHADSOFT_STATUS_URL = "https://www.chadsoft.co.uk/online-status/status.txt"
ctww_status_regex = re.compile(r"<h1>CTWW STATUS: ([^<]+)</h1>")
countdown_status_regex = re.compile(r"<h1>COUNTDOWN STATUS: ([^<]+)</h1>")
THERE_ARE_NO_ACTIVE = "There are no active"

tr_class_regex = re.compile(r"^(tr0|tr1)")
tr_id_regex = re.compile(r"^r[0-9]+")
#vs_ctgp_regex = re.compile(r"^vs_[
# soup.find_all("tr", class_=tr_class_regex)[0].next_sibling.next_sibling
WIIMMFI_STATS_MKW_URL = "https://wiimmfi.de/stats/mkw"
WIIMMFI_STATS_MKWX_URL = "https://wiimmfi.de/stats/mkwx"
WIIMMFI_STATS_MKW_ROOM_BASE_URL = "https://wiimmfi.de/stats/mkw/room"
WIIMMFI_STATS_MKWX_ROOM_BASE_URL = "https://wiimmfi.de/stats/mkwx/room"
WIIMMFI_STATS_MKW_ROOM_HISTORY_BASE_URL = "https://wiimmfi.de/stats/mkw/list"
WIIMMFI_STATS_MKWX_ROOM_HISTORY_BASE_URL = "https://wiimmfi.de/stats/mkwx/list"

race_mode_regex = re.compile(r"^race mode")
NO_ROOM_FOUND_TEXT = "<span class=\"warn\">No room found!</span>"

soup = None
mkw_rooms = {}

class GameMode(ABC):
    #__slots__ = ("_online_status_regex",)
    def __init__(self):
        super().__init__()

    @property
    @abstractmethod
    def online_status_regex(self):
        pass

    @abstractmethod
    def is_room_info_game_mode(self, region, room_match):
        pass

    @abstractmethod
    def mkwx_is_game_mode(self, room_type, room_tr):
        pass

class CTWWMode(GameMode):
    def __init__(self):
        super().__init__()

    @property
    def online_status_regex(self):
        return ctww_status_regex

    def is_room_info_game_mode(self, region, room_match):
        return region.text == "CTGP" and room_match.text.startswith("vs_") and 20 <= int(room_match.text[3:]) <= 59

    def mkwx_is_game_mode(self, room_type, room_tr):
        if room_type.text != "Versus Race":
            return False
        
        player_tr = room_tr.find_next_sibling("tr", class_=tr_class_regex)
        player_tds = player_tr.find_all("td", align="center")
        region, room_match, conn_fail, vr, character_vehicle, track, delay, finish_time = player_tds
        return self.is_room_info_game_mode(region, room_match)

class CountdownMode(GameMode):
    def __init__(self):
        super().__init__()

    @property
    def online_status_regex(self):
        return countdown_status_regex

    def is_room_info_game_mode(self, region, room_match):
        return region.text == "CTGP" and room_match.text.startswith("cd")

    def mkwx_is_game_mode(self, room_type, room_tr):
        return "Count Down" in room_type.text

CTWW_MODE = CTWWMode()
COUNTDOWN_MODE = CountdownMode()

class RoomManager:
    __slots__ = ("rooms",)

    def __init__(self):
        self.rooms = {}

    def add_room_from_id_stats_type(self, room_id, stats_type):
        if room_id in self.rooms:
            return

        self.rooms[room_id] = Room(room_id, stats_type)

    def process_rooms(self):
        for room_id, room in self.rooms.copy().items():
            if room.archive_then_delete:
                room.archive_room()
                del self.rooms[room_id]
            elif not room.exists():
                room.set_archive_then_delete()
            else:
                room.archive_room_if_time_passed()

        return len(self.rooms) != 0

    def archive_all_rooms(self):
        for room_id, room in self.rooms.items():
            room.archive_room()

        self.rooms = {}

class StatsType:
    __slots__ = ("room_url", "room_history_url", "name")

    def __init__(self, name, room_url, room_history_url):
        self.name = name
        self.room_url = room_url
        self.room_history_url = room_history_url

mkw_stats = StatsType("mkw", WIIMMFI_STATS_MKW_ROOM_BASE_URL, WIIMMFI_STATS_MKW_ROOM_HISTORY_BASE_URL)
mkwx_stats = StatsType("mkwx", WIIMMFI_STATS_MKWX_ROOM_BASE_URL, WIIMMFI_STATS_MKWX_ROOM_HISTORY_BASE_URL)

class Room:
    __slots__ = ("id", "last_checked", "discovery_time", "stats_type", "archive_then_delete")
    def __init__(self, id, stats_type):
        self.id = id
        self.last_checked = 0
        self.discovery_time = int(time.time())
        self.stats_type = stats_type
        self.archive_then_delete = False

    def exists(self):
        cur_time = int(time.time())
        if self.last_checked + 3600 < cur_time:
            r = requests.get(f"{self.stats_type.room_url}/{self.id}")
            if r.status_code == 200:
                if NO_ROOM_FOUND_TEXT in r.text:
                    return False
                else:
                    self.last_checked = cur_time + 3600
                    return True
            else:
                print(f"returned {r.status_code}: {r.reason}")
                return True
        else:
            return True

    def set_archive_then_delete(self):
        self.archive_then_delete = True
    
    def archive_room_if_time_passed(self):
        # archive every 20 hours if the room is somehow still up
        cur_time = int(time.time())
        if self.discovery_time + 3600*20 < cur_time:
            self.archive_room()
            self.discovery_time = cur_time + 3600*20

    def archive_room(self):
        r = requests.get(f"{self.stats_type.room_history_url}/{self.id}")
        if r.status_code == 200:
            with open(f"countdown_archive/{self.stats_type.name}_{self.id}_{self.discovery_time}.html", "w+") as f:
                f.write(r.text)
        else:
            print(f"returned {r.status_code}: {r.reason}")


def is_room_ctww(region, room_match):
    return region.text == "CTGP" and room_match.text.startswith("vs_") and 20 <= int(room_match.text[3:]) <= 59

def is_room_countdown(region, room_match):
    return region.text == "CTGP" and room_match.text.startswith("cd")

def find_mkwx_rooms(room_manager, chosen_game_mode):
    r = requests.get(WIIMMFI_STATS_MKWX_URL)
    found_room = False
    if r.status_code == 200:
        if r.text == "":
            return
        html_doc = r.text

        soup = bs4.BeautifulSoup(html_doc, "html.parser")
        room_trs = soup.find_all("tr", id=tr_id_regex)
        room_ids = []

        for room_tr in room_trs:
            room_type = room_tr.find("span", attrs={"data-tooltip": race_mode_regex})
            if "Private" not in room_type.text:
                if chosen_game_mode.mkwx_is_game_mode(room_type, room_tr):
                    room_manager.add_room_from_id_stats_type(room_tr["id"], mkwx_stats)
                    found_room = True
    else:
        print(f"returned {r.status_code}: {r.reason}")
        found_room = True

    return found_room

def find_mkw_rooms(room_manager, chosen_game_mode):
    r = requests.get(WIIMMFI_STATS_MKW_URL)
    found_room = False
    if r.status_code == 200:
        if r.text == "":
            return
        html_doc = r.text
    
        soup = bs4.BeautifulSoup(html_doc, "html.parser")
        room_trs = soup.find_all("tr", id=tr_id_regex)
        room_ids = []
    
        for room_tr in room_trs:
            room_type = room_tr.contents[0].contents[0]
            if "Private" not in room_type:
                player_tr = room_tr.find_next_sibling("tr", class_=tr_class_regex)
                player_tds = player_tr.find_all("td", align="center")
                region, room_match, world, conn_fail, vr, br = player_tds

                if chosen_game_mode.is_room_info_game_mode(region, room_match):
                    room_manager.add_room_from_id_stats_type(room_tr["id"], mkw_stats)
                    found_room = True
    else:
        print(f"returned {r.status_code}: {r.reason}")
        found_room = True

    return found_room

def main():
    chosen_game_mode = COUNTDOWN_MODE

    WAITING_FOR_ROOMS = 0
    SEARCHING_FOR_ROOMS = 1
    ARCHIVE_ROOMS = 2

    state = WAITING_FOR_ROOMS
    room_manager = RoomManager()
    exception_sleep_time = 15
    just_archive_rooms = False

    while True:
        try:
            if state == WAITING_FOR_ROOMS:
                r = requests.get(CHADSOFT_STATUS_URL)
                if r.status_code == 200:
                    if r.text != "":
                        response_text = r.text
                        match_obj = chosen_game_mode.online_status_regex.search(response_text)
                        if not match_obj:
                            print("Warning: Could not find online status message.")
                        else:
                            online_status = match_obj.group(1)
                            if not online_status.startswith(THERE_ARE_NO_ACTIVE):
                                state = SEARCHING_FOR_ROOMS
                                now = datetime.datetime.now()
                                print(f"Rooms active, searching on wiimmfi ({now.hour}:{now.minute:02d})")
                                sleep_time = 0
                            else:
                                now = datetime.datetime.now()
                                print(f"No active rooms... ({now.hour}:{now.minute:02d})")
                                sleep_time = 180
                    else:
                        print(f"Chadsoft status returned empty!")
                        sleep_time = 30
                else:
                    print(f"chadsoft returned {r.status_code}: {r.reason}")
                    sleep_time = 180
            elif state == SEARCHING_FOR_ROOMS:
                now = datetime.datetime.now()
                print(f"Searching rooms on wiimmfi... ({now.hour}:{now.minute:02d})")
                found_room = False
                found_room = find_mkw_rooms(room_manager, chosen_game_mode) or found_room
                found_room = find_mkwx_rooms(room_manager, chosen_game_mode) or found_room
                if just_archive_rooms:
                    room_manager.archive_all_rooms()
                    return
                elif not found_room:
                    now = datetime.datetime.now()
                    print(f"No rooms found on wiimmfi, archiving found rooms in 3 minutes! ({now.hour}:{now.minute:02d})")
                    state = ARCHIVE_ROOMS
                elif not room_manager.process_rooms():
                    state = WAITING_FOR_ROOMS
                sleep_time = 180
            elif state == ARCHIVE_ROOMS:
                now = datetime.datetime.now()
                print(f"Archiving found rooms ({now.hour}:{now.minute:02d})")
                room_manager.archive_all_rooms()
                state = WAITING_FOR_ROOMS
                sleep_time = 0

            exception_sleep_time = 15
            time.sleep(sleep_time)
        except Exception as e:
            print(f"Exception occurred: {e}\n{''.join(traceback.format_tb(e.__traceback__))}\nSleeping for {exception_sleep_time} seconds now.")
            time.sleep(exception_sleep_time)
            exception_sleep_time *= 2
            if exception_sleep_time > 1000:
                print("Exception happened too many times! Exiting.")
                return

if __name__ == "__main__":
    main()

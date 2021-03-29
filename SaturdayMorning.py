# SaturdayMorning.py: StepMania simfile injector for Friday Night Funkin'
# Copyright (C) 2021 Telperion (github.com/telperion)

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301
# USA


# No source code for Friday Night Funkin' is included here.
# For more information on its license, please check out their source:
# https://github.com/KadeDev/Kade-Engine


import os
import sys
import json
import shutil
import traceback
from copy import deepcopy

import wx
from wx.lib.agw import genericmessagedialog as GMD

import chart_util



def ExceptMyFate():
    frame = wx.GetApp().GetTopWindow()

    tb = traceback.format_exception(*sys.exc_info())
    exception_str = "".join(tb)
    
    mb = wx.MessageDialog(frame, exception_str, 'I`ve error', wx.ICON_ERROR | wx.CENTRE | wx.STAY_ON_TOP)
    mb.ShowModal()
    mb.Destroy()

def except_decorator(func):
    def wrapper(self, *args, **kwargs):
        try:
            func(self, *args, **kwargs)
        except:
            ExceptMyFate()
    return wrapper

class SaturdayMorning(wx.Frame):
    """
    """

    def __init__(self, *args, **kw):
        super(SaturdayMorning, self).__init__(*args, **kw)

        if getattr(sys, 'frozen', False):
            self.root = os.path.dirname(sys.executable)
        else:
            self.root = os.path.dirname(__file__)

        self.slots = {'Easy': '-easy', 'Normal': '', 'Hard': '-hard'}
        self.data = {}
        self.songlist = []
        self.characters = []
        self.charts = []
        self.name = ''
        self.simfile = None
        self.preload = 'assets/SaturdayMorning_defaults.json'

        self.LoadDefaults()
        try:
            self.LoadSonglist()
        except:
            pass
        self.InitUI()
        self.UpdateUI()
        self.Centre()

    @except_decorator
    def InitUI(self):
        p_all = wx.Panel(self)

        f_yuge = self.GetFont()
        f_yuge.SetWeight(wx.FONTWEIGHT_BOLD)
        f_yuge.SetPointSize(int(f_yuge.GetPointSize() * 1.5))
   
        p_song = wx.Panel(p_all)
        self.l_song_source = wx.StaticText(p_song, label='', style=wx.ALIGN_CENTRE_HORIZONTAL)
        self.l_song_source.SetFont(f_yuge)
        self.l_path_to_exe = wx.StaticText(p_song, label='Path to Funkin.exe:')
        self.t_path_to_exe = wx.TextCtrl(p_song, style=wx.TE_READONLY, size=(480, 24))
        self.b_path_to_exe = wx.Button(p_song)
        self.b_path_to_exe.SetBitmapLabel(wx.ArtProvider.GetBitmap(wx.ART_FOLDER))
        self.l_song_choice = wx.StaticText(p_song, label='Replace which song?')
        self.c_song_choice = wx.ComboBox(p_song, style=wx.CB_DROPDOWN | wx.CB_READONLY | wx.CB_SORT)
        self.Bind(wx.EVT_BUTTON, self.LookupFunkinEXE, self.b_path_to_exe)
        
        p_chart_mapping = wx.Panel(p_all)
        self.l_slot = {}
        self.c_slot_opp = {}
        self.c_slot_plr = {}
        self.l_opp = wx.StaticText(p_chart_mapping, label='Opponent', style=wx.ALIGN_CENTRE_HORIZONTAL)
        self.l_plr = wx.StaticText(p_chart_mapping, label='Player',   style=wx.ALIGN_CENTRE_HORIZONTAL)
        for s in self.slots:
            self.l_slot[s] = wx.StaticText(p_chart_mapping, label=s, style=wx.ALIGN_CENTRE_HORIZONTAL)
            self.c_slot_opp[s] = wx.ComboBox(p_chart_mapping, style=wx.CB_DROPDOWN | wx.CB_READONLY | wx.CB_SORT)
            self.c_slot_plr[s] = wx.ComboBox(p_chart_mapping, style=wx.CB_DROPDOWN | wx.CB_READONLY | wx.CB_SORT)

        p_adjustables = wx.Panel(p_all)
        self.l_offset = wx.StaticText(p_adjustables, label='Additional offset (sec):')
        self.s_offset = wx.SpinCtrlDouble(p_adjustables, min=-1, max=1, initial=0, inc=0.001, style=wx.SP_ARROW_KEYS)
        self.l_speed = wx.StaticText(p_adjustables, label='Speed modifier:')
        self.s_speed = wx.SpinCtrlDouble(p_adjustables, min=0.2, max=4.0, initial=self.data.get('speed', 2.0), inc=0.01, style=wx.SP_ARROW_KEYS)
        
        self.b_go = wx.Button(p_all, label='Go!')
        self.b_go.SetBackgroundColour(wx.Colour(0x00FF00))
        self.b_go.SetFont(f_yuge)
        self.Bind(wx.EVT_BUTTON, self.OnConvert, self.b_go)

        ###

        sz_song = wx.GridBagSizer(6, 6)
        sz_song.Add(self.l_song_source, pos=(0, 0), flag=wx.ALL | wx.EXPAND, span=(1, 3))
        sz_song.Add(self.l_path_to_exe, pos=(1, 0), flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)
        sz_song.Add(self.t_path_to_exe, pos=(1, 1), flag=wx.LEFT | wx.RIGHT | wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        sz_song.Add(self.b_path_to_exe, pos=(1, 2), flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)
        sz_song.Add(self.l_song_choice, pos=(2, 0), flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)
        sz_song.Add(self.c_song_choice, pos=(2, 1), flag=wx.ALL | wx.EXPAND, span=(1, 2))
        sz_song.AddGrowableCol(1)
        p_song.SetSizer(sz_song)

        sz_chart_mapping = wx.GridBagSizer(6, 6)
        sz_chart_mapping.Add(self.l_opp, pos=(0, 1), flag=wx.ALL | wx.EXPAND)
        sz_chart_mapping.Add(self.l_plr, pos=(0, 2), flag=wx.ALL | wx.EXPAND)
        for i, s in enumerate(self.slots):
            sz_chart_mapping.Add(self.l_slot[s], pos=(i+1, 0), flag=wx.ALL | wx.ALIGN_CENTER)
            sz_chart_mapping.Add(self.c_slot_opp[s], pos=(i+1, 1), flag=wx.ALL | wx.EXPAND)
            sz_chart_mapping.Add(self.c_slot_plr[s], pos=(i+1, 2), flag=wx.ALL | wx.EXPAND)
        sz_chart_mapping.AddGrowableCol(1)
        sz_chart_mapping.AddGrowableCol(2)
        p_chart_mapping.SetSizer(sz_chart_mapping)

        sz_adjustables = wx.GridBagSizer(6, 6)
        sz_adjustables.Add(size=(0, 0), pos=(0, 0), flag=wx.ALL | wx.EXPAND)
        sz_adjustables.Add(self.l_offset, pos=(0, 1), flag=wx.LEFT | wx.RIGHT | wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        sz_adjustables.Add(self.s_offset, pos=(0, 2), flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)
        sz_adjustables.Add(size=(0, 0), pos=(0, 3), flag=wx.ALL | wx.EXPAND)
        sz_adjustables.Add(self.l_speed, pos=(0, 4), flag=wx.LEFT | wx.RIGHT | wx.EXPAND | wx.ALIGN_CENTER_VERTICAL)
        sz_adjustables.Add(self.s_speed, pos=(0, 5), flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)
        sz_adjustables.Add(size=(0, 0), pos=(0, 6), flag=wx.ALL | wx.EXPAND)
        sz_adjustables.AddGrowableCol(0)
        sz_adjustables.AddGrowableCol(3)
        sz_adjustables.AddGrowableCol(6)
        p_adjustables.SetSizer(sz_adjustables)

        sz_all = wx.BoxSizer(wx.VERTICAL)
        sz_all.Add(p_song, flag=wx.ALL | wx.EXPAND, border=12)
        sz_all.Add(p_chart_mapping, flag=wx.ALL | wx.EXPAND, border=12)
        sz_all.Add(p_adjustables, flag=wx.ALL | wx.EXPAND, border=12)
        sz_all.Add(self.b_go, 1, flag=wx.ALL | wx.EXPAND, border=12)
        p_all.SetSizer(sz_all)

        sz_top = wx.GridBagSizer(0, 0)
        sz_top.Add(p_all, pos=(0, 0), flag=wx.ALL | wx.EXPAND)
        sz_top.AddGrowableCol(0)
        sz_top.AddGrowableRow(0)
        self.SetSizerAndFit(sz_top)

        self.Bind(wx.EVT_CLOSE, self.OnClose)


    @except_decorator
    def OnClose(self, event):
        self.SaveDefaults()
        event.Skip()


    @except_decorator
    def OnConvert(self, event):
        self.SaveSong()
        self.Close()


    @except_decorator
    def UpdateUI(self):
        self.l_song_source.SetLabel(self.name)
        self.t_path_to_exe.SetLabel(self.data['path'])
        if len(self.songlist) > 0:
            self.c_song_choice.Set(self.songlist)
            self.c_song_choice.SetValue(self.songlist[0])
        if len(self.charts) > 0:
            slots_available = [s for s in self.charts]
            for i, s in enumerate(self.slots):
                i_plr = len(self.slots) - i - 1
                i_plr = max(i_plr, 0)
                i_plr = min(i_plr, len(slots_available)-1)
                self.c_slot_opp[s].Set(slots_available)
                self.c_slot_opp[s].SetValue(slots_available[0])
                self.c_slot_plr[s].Set(slots_available)
                self.c_slot_plr[s].SetValue(slots_available[i_plr])


    @except_decorator
    def LoadSonglist(self):
        p = self.data['path']
        self.songlist = []
        if os.path.exists(p):
            if os.path.exists(os.path.join(p, 'lime.ndll')):
                p_sub = []
                sl_sub = {}

                for d_check in ['data', 'songs']:
                    p_sub = os.path.join(p, 'assets', d_check)
                    p_backup = os.path.join(p, '_backup', d_check)
                    sl_sub[d_check] = [n for n in os.listdir(p_sub) if os.path.isdir(os.path.join(p_sub, n))]
                    if not os.path.isdir(p_backup):
                        shutil.copytree(p_sub, p_backup)

                self.songlist = [n for n in sl_sub['data'] if n in sl_sub['songs']]
            else:
                raise ValueError(f"{os.path.join(p, 'Funkin.exe')} (FNF executable) not found")
        else:
            raise ValueError(f"{p} not found")


    @except_decorator
    def LoadSimfile(self, song_directory):
        if not os.path.isdir(song_directory):
            # Accept drag/drop of a .sm or .ssc as well I guess
            song_directory = os.path.dirname(song_directory)

        if os.path.exists(song_directory):
            self.name = ''
            self.charts = {}

            chart_files = [n for n in os.listdir(song_directory) if os.path.splitext(n)[1] == '.ssc']
            if len(chart_files) == 0:
                chart_files = [n for n in os.listdir(song_directory) if os.path.splitext(n)[1] == '.sm']
            if len(chart_files) == 0:
                raise ValueError(f'No .sm or .ssc files found in "{song_directory}"')

            audio_files = [n for n in os.listdir(song_directory) if os.path.splitext(n)[1] == '.ogg']
            if len(audio_files) == 0:
                raise ValueError(f'No .ogg files found in "{song_directory}"')

            self.simfile = os.path.join(song_directory, chart_files[0])
            any_chart_info = None
            for chart_slot in ['Challenge', 'Hard', 'Medium', 'Easy', 'Beginner']:
                try:
                    parsed_chart, gimmick_data, chart_info = chart_util.ParseChartSM(self.simfile, chart_type='dance-single', chart_slot=chart_slot, shush=True)
                    self.charts[chart_slot] = {
                        'chart': parsed_chart,
                        'gimmick': gimmick_data,
                        'info': chart_info
                    }
                    if any_chart_info is None:
                        any_chart_info = chart_info
                    # print(f'Found a {chart_slot} chart in {chart_files[0]}')
                except:
                    pass
                    # print(f'No {chart_slot} chart in {chart_files[0]}')
            self.name = SaturdayMorning.BuildSongName(any_chart_info)
        else:
            raise ValueError(f'"{song_directory}" not found')

        self.UpdateUI()


    @except_decorator
    def LoadDefaults(self):
        preload_resolved = os.path.join(self.root, self.preload)
        if os.path.exists(preload_resolved):
            with open(preload_resolved, 'r') as fp:
                self.data = json.load(fp)
        if 'path' not in self.data:
            self.data['path'] = r'C:/'
        if 'silence' not in self.data:
            self.data['silence'] = r'assets/silence.ogg'
        if 'speed' not in self.data:
            self.data['speed'] = 2.0

    
    @except_decorator
    def SaveDefaults(self):
        preload_resolved = os.path.join(self.root, self.preload)
        self.data['speed'] = self.s_speed.GetValue()
        with open(preload_resolved, 'w') as fp:
            json.dump(self.data, fp)


    @except_decorator
    def LookupFunkinEXE(self, event):
        fdlg_funkin = wx.FileDialog(
            self,
            message='Select Funkin.exe in the game install that you want to replace songs from',
            defaultDir=self.data['path'],
            defaultFile='*.exe',
            wildcard=".exe",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST            
        )
        if fdlg_funkin.ShowModal() == wx.ID_OK:
            self.data['path'] = os.path.dirname(fdlg_funkin.GetPath())
            self.LoadSonglist()
            self.UpdateUI()
    

    @staticmethod
    def GetTimingEffects(gimmick_data):
        offset = float(gimmick_data['OFFSET'])

        bpm_list = []
        stop_list = []
        warp_list = []
        
        if len(gimmick_data['BPMS'].strip()) > 0:
            bpm_events = gimmick_data['BPMS'].split(',')
            bpm_list = [e.strip().split('=') for e in bpm_events]
        if len(gimmick_data['STOPS'].strip()) > 0:
            stop_events = gimmick_data['STOPS'].split(',')
            stop_list = [e.strip().split('=') for e in stop_events]
        if gimmick_data['WARPS'] is not None:
            if len(gimmick_data['WARPS'].strip()) > 0:
                warp_events = gimmick_data['WARPS'].split(',')
                warp_list = [e.strip().split('=') for e in warp_events]

        bpms = [(float(e[0]), float(e[1])) for e in bpm_list]
        stops = [(float(e[0]), float(e[1])) for e in stop_list]
        warps = [(float(e[0]), float(e[1])) for e in warp_list]

        bpms.sort(key=lambda e: e[0])
        stops.sort(key=lambda e: e[0])
        warps.sort(key=lambda e: e[0])

        bpms.append((1000000.0, bpms[-1][1]))   # Final BPM continues forever

        return {
            'offset': offset,
            'bpms': bpms,
            'stops': stops,
            'warps': warps
        }

    @staticmethod
    def B2T(timing, b, verbose=False, manual_offset=0.0):
        offset = timing['offset']
        bpms   = timing['bpms']
        stops  = timing['stops']

        t = -offset + manual_offset
        for i in range(len(bpms)-1):
            up_to = min(b, bpms[i+1][0])
            dt = (up_to - bpms[i][0]) * 60 / bpms[i][1]
            t += dt
            if verbose:
                print(f"b{bpms[i][0]:3.3f} -> b{up_to:3.3f}: take {dt:3.3f}")
            if bpms[i+1][0] > b:
                break
        for s in stops:
            if s[0] >= b:
                break
            if verbose:
                print(f"b{s[0]:3.3f}: stop {s[1]:3.3f}")
            t += s[1]
        return t

    @staticmethod
    def CalculateTimes(chart_data, gimmick_data, manual_offset=0.0):
        timing = SaturdayMorning.GetTimingEffects(gimmick_data)
        for e in chart_data:
            e['time'] = SaturdayMorning.B2T(timing, e['beat'], manual_offset=manual_offset)

    @staticmethod
    def CalculateHolds(chart_data):
        for i, e in enumerate(chart_data):
            if e['type'] in ['H', 'R']:
                for potential_end in chart_data[i:]:
                    if potential_end['type'] == 'E' and potential_end['lane'] == e['lane']:
                        e['blen'] = potential_end['time'] - e['time']
                        break

    @staticmethod
    def BuildSongName(chart_info):
        name = chart_info['ARTIST']
        if len(chart_info['ARTISTTRANSLIT'].strip()) != 0:
            name += f" ({chart_info['ARTISTTRANSLIT']})"
        name += ' - "'
        name += chart_info['TITLE']
        if len(chart_info['TITLETRANSLIT'].strip()) != 0:
            name += f" ({chart_info['TITLETRANSLIT']})"
        name += '"'
        return name
    

    def ChartsToFNF(self, slot='Normal'):
        manual_offset = self.s_offset.GetValue()

        chart_opp = deepcopy(self.charts[self.c_slot_opp[slot].GetValue()])
        chart_plr = deepcopy(self.charts[self.c_slot_plr[slot].GetValue()])

        beat_max = max(
            [e['beat'] for e in chart_opp['chart']] +
            [e['beat'] for e in chart_plr['chart']]
        )
        frame_notes = [[] for i in range(1 + int(beat_max) // 4)]

        SaturdayMorning.CalculateTimes(chart_opp['chart'], chart_opp['gimmick'], manual_offset)
        SaturdayMorning.CalculateTimes(chart_plr['chart'], chart_plr['gimmick'], manual_offset)
        SaturdayMorning.CalculateHolds(chart_opp['chart'])
        SaturdayMorning.CalculateHolds(chart_plr['chart'])

        # bf in lanes 4-7
        for e in chart_opp['chart']:
            e['lane'] += 4

        full_chart = chart_opp['chart'] + chart_plr['chart']
        full_chart.sort(key=lambda e: e['beat'])

        for e in full_chart:
            if e['type'] in ['E', 'M']:
                continue

            f = int(e['beat'] / 4)
            t     = e['time'] * 1000            # milliseconds
            t_len = e.get('blen', 0) * 1000     # milliseconds

            if e['type'] == 'T':
                frame_notes[f].append([t, e['lane'], 0])
            elif e['type'] in ['H', 'R']:
                frame_notes[f].append([t, e['lane'], t_len])

        # Convert to frame objects
        frames = []
        timing_plr = SaturdayMorning.GetTimingEffects(chart_plr['gimmick'])
        for fi, fn in enumerate(frame_notes):
            t_start = SaturdayMorning.B2T(timing_plr, fi*4, manual_offset=manual_offset)
            t_end = SaturdayMorning.B2T(timing_plr, 4+fi*4, manual_offset=manual_offset)
            if (t_end - t_start) < 0.001 and len(fn) > 0:
                raise ValueError(f'Frame {fi} has {len(fn)} notes but spans {t_end-t_start:3.3f} seconds?')
            measure = {
                'lengthInSteps': 16,
                'bpm': int(240 / (t_end - t_start)),
                'changeBPM': False,
                'mustHitSection': True,
                'sectionNotes': [],
                'typeOfSection': 0
            }
            measure['sectionNotes'] = fn
            frames.append(measure)

        # Let's use the DDR first-measure trick
        full_offset = -timing_plr['offset'] + manual_offset
        if full_offset > 0.001:                 # Add teeny initial measure
            first_measure = {
                'lengthInSteps': 1,
                'bpm': -15 / full_offset,
                'changeBPM': False,
                'mustHitSection': True,
                'sectionNotes': [],
                'typeOfSection': 0
            }
            frames.insert(0, first_measure)
        elif full_offset < 0.001:               # Shrink initial measure slightly
            spm = 240 / frames[0]['bpm']
            spm -= full_offset
            frames[0]['bpm'] = 240 / spm

        # Create full song JSON!
        display_bpm = int(timing_plr['bpms'][0][1])
        song_name = self.c_song_choice.GetValue().replace('-', ' ').title()
        song_dict = {
            'song': {
                'song': song_name,              # injecting rather than adding a new song oops
                'notes': frames,
                'bpm': display_bpm,
                'sections': 0,
                'needsVoices': False,
                'player1': 'bf',
                'player2': 'dad',               # TODO: Match character?
                'sectionLengths': [],
                'speed': self.s_speed.GetValue(),
                'validScore': True
            },
            'bpm': display_bpm,
            'sections': len(frames)
        }

        return song_dict


    @except_decorator
    def SaveSong(self):
        path = self.data['path']
        song = self.c_song_choice.GetValue()
        simpath = os.path.dirname(self.simfile)
        fn_audio = [fn for fn in os.listdir(simpath) if os.path.splitext(fn)[1] == '.ogg']
        fn_audio = os.path.join(simpath, fn_audio[0])

        for s in self.slots:
            song_dict = self.ChartsToFNF(s)
            with open(os.path.join(path, 'assets/data', song, song + self.slots[s] + '.json'), 'w') as fp:
                json.dump(song_dict, fp)
        shutil.copy2(self.simfile, os.path.join(path, 'assets/data', song, song + '-source' + os.path.splitext(self.simfile)[1]))
        shutil.copy2(fn_audio, os.path.join(path, 'assets/songs', song, 'Inst.ogg'))
        shutil.copy2(os.path.join(self.root, self.data['silence']), os.path.join(path, 'assets/songs', song, 'Voices.ogg'))


if __name__ == '__main__':
    song_test = '' #r'C:\Games\StepMania 5.3 Outfox\Songs\Club Fantastic Season 1\BOSSY'
    program_name = sys.argv[0]
    song_choice = (len(sys.argv) > 1) and sys.argv[1] or song_test

    frame = None
    app = wx.App()
    frame = SaturdayMorning(None, title="Saturday Morning Steppin' 0.2 (StepMania -> FNF)")
    frame.LoadSimfile(song_choice)
    frame.Show()
    app.MainLoop()

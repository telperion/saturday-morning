# chart_util.py: Python utility functions for parsing StepMania simfile data
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

import re
import io
import os.path

import simfile

_multitap_ver = 0.9

def QuantizationID(i, sz):
	factorsOf192 = {3: 1, 2: 6}
	for f in factorsOf192.keys():
		for j in range(factorsOf192[f]):
			# print('{}: {} / {}, {}'.format(f, i, sz, j))
			if sz % f == 0:
				if i % f == 0:
					i //= f
					sz //= f
			else:
				break

	if (sz == 1) or (sz == 2):
		return 4
	elif (sz == 3) or (sz == 6):
		return 12
	else:
		return sz


def DiffCharts(a, b):
	aDiff = []
	bDiff = []
	aOfs = 0
	bOfs = 0

	# Assume sorted lists
	for i in range(max(len(a), len(b))):
		ia = i + aOfs
		ib = i + bOfs
		
		if ia >= len(a):
			bDiff += [b[ib]]            
			continue
		if ib >= len(b):
			aDiff += [a[ia]]
			continue

		mismatch = False
		for k in a[ia].keys():
			if k == 'beat':
				if a[ia][k] < b[ib][k]:
					aDiff += [a[ia]]
					bOfs -= 1
					mismatch = True
					break
				if a[ia][k] > b[ib][k]:
					bDiff += [b[ib]]
					aOfs -= 1
					mismatch = True
					break
			else:
				if a[ia][k] != b[ib][k]:
					aDiff += [a[ia]]
					bDiff += [b[ib]]
					mismatch = True
					break                
		if mismatch:
			continue
	
	return (aDiff, bDiff)

def ParseMetadataLine(line):
	m = re.match('\s*#(\w+):(.*);\s*', line)
	if m is not None:
		return m.group(1), m.group(2)
	else:
		return None, None


note_type_dict = {
	'1': 'T',
	'2': 'H',
	'3': 'E',
	'4': 'R',
	'F': 'F',
	'M': 'M',
	'L': 'L'
}

def ParseNotesField(note_data, shush=True):
	parsedChart = []

	currentMeasureNotes = []
	currentMeasureNumber = 0
	currentMeasureLength = 0
	defaultBeatsPerMeasure = 4

	# print(note_data)
	note_data = note_data.rstrip().rstrip(';') + '\n;'
	for line in re.split('\n+', note_data):
		if re.match('\s*[\,\;]\s*', line) is not None:
			# print('End of measure!')
			currentStartBeat = currentMeasureNumber * defaultBeatsPerMeasure
			currentNoteIncrement = 0
			if currentMeasureLength != 0:
				currentNoteIncrement = defaultBeatsPerMeasure / currentMeasureLength

			for singleNote in currentMeasureNotes:
				singleNote['qtzn'] = QuantizationID(singleNote['tick'], currentMeasureLength)
				singleNote['beat'] = singleNote['tick'] * currentNoteIncrement + currentStartBeat
				if not shush:
					print('{} {} {} {}'.format(singleNote['beat'], singleNote['type'], singleNote['lane'], singleNote['qtzn']))
				parsedChart.append(singleNote)

			currentMeasureNotes = []
			currentMeasureNumber += 1
			currentMeasureLength = 0

		noteLine = re.match('\s*([0-9FLM]+)\s*', line)
		if noteLine is not None:
			notes = noteLine.group(1)
			# print('>>> {}'.format(notes))

			for laneIndex in range(len(notes)):
				for nt_from, nt_to in note_type_dict.items():
					if notes[laneIndex] == nt_from:
						currentMeasureNotes.append({'tick': currentMeasureLength, 'type': nt_to, 'lane': laneIndex})
			currentMeasureLength += 1
	
	if not shush:
		print('End of chart! ({} objects)'.format(len(parsedChart)))
	return parsedChart


ECFA_ScoreModifiers = {
	'scorebase': 40,
	'mscale': {
		'speed': 1,      # unused
		'stamina': 1,    # unused
		'tech': 3,
		'movement': 4,
		'rhythms': 6
	},
	'gimmick': [1.02, 1.04, 1.06],
	'bigscale': 10000,
	'exp': 1.75,
	'maxs': 404
}

def ParseTechRadar(techRadarString):
	# ECFA: Parse tech radar string from #CHARTSTYLE into a table.
	# 
	# e.g., #CHARTSTYLE:speed=5,stamina=6,tech=7,movement=10,timing=9,gimmick=low;
	if techRadarString is None:
		return None

	techRadarTable = {}
	techRadarFields = techRadarString.split(',')
	for f in techRadarFields:
		m = re.match("([^=,]+)=([^=,]+)", f)
		if m is None:
			print(f'Perhaps a malformed field in tech radar string? "{techRadarString}"')
			return None

		k = m.group(1).lower()
		v = m.group(2).lower()
		if k == 'gimmick':
			try:
				v = int(v)
			except:
				v = (v == 'cmod') and -1 or \
					(v == 'low' or v == 'light') and 1 or \
					(v == 'mid' or v == 'medium') and 2 or \
					(v == 'high' or v == 'heavy') and 3 or \
					(v == 'none') and 0 or 0 # None

			techRadarTable[k] = v
		else:
			if k == 'timing' and ('rhythms' not in techRadarTable):
				k = 'rhythms'
			techRadarTable[k] = int(v)

	return techRadarTable


def TechRadarFromSteps(chart_data):
	# pass in a steps and get the tech radar table, including the "rating" field
	radar = ParseTechRadar(chart_data.get('CHARTSTYLE', ''))
	if radar is None:
		return None
	radar['rating'] = int(chart_data.meter)
	return radar


def CalculateECFAScore(radar):
	if radar is None:
		return None

	mods = ECFA_ScoreModifiers
	radar['rating'] = min(radar['rating'], 14)
	bmin = min(radar['rating']/10, 1)

	S = (mods['scorebase']*(
		radar['rating']-7) +
		radar['speed'] +
		radar['stamina'] +
		mods['mscale']['tech']*bmin*radar['tech'] +
		mods['mscale']['movement']*bmin*radar['movement'] +
		mods['mscale']['rhythms']*bmin*radar['rhythms']) * \
		(radar['gimmick'] <= 0 and 1 or mods['gimmick'][radar['gimmick']-1])

	return mods['bigscale'] * ((S/mods['maxs']) ** mods['exp'])


def ParseChartSM(chart_filename, chart_type=None, chart_slot=None, chart_name=None, shush=True):
	stem, ext = os.path.splitext(chart_filename)
	if ext == '.sm' or ext == '.ssc':
		song_data = simfile.open(chart_filename)
		chart_options = [c for c in song_data.charts if 
							(chart_slot is None or c.difficulty.lower() == chart_slot.lower()) and
							(chart_type is None or c.stepstype.lower()  == chart_type.lower())]
		if len(chart_options) < 1:
			raise ValueError(f"Couldn't find a {chart_type or '<n/a type>'} {chart_slot or '<n/a slot>'} in {chart_filename}!")
		elif len(chart_options) > 1:
			raise ValueError(f"Found more than one {chart_type or '<n/a type>'} {chart_slot or '<n/a slot>'} in {chart_filename}!")

		chart_data = chart_options.pop()

		title = song_data.title
		title_tl = song_data.titletranslit
		artist = song_data.artist
		artist_tl = song_data.artisttranslit
		diff = int(chart_data.meter)
		if ext == '.sm':
			chart_author = chart_data.description
			chart_style = ""
		else:
			chart_author = chart_data.get('CREDIT', 
						   chart_data.get('DESCRIPTION',
						   chart_data.get('CHARTNAME', "")))
			chart_style = chart_data.get('CHARTSTYLE', "")
		
		chart_info = {
			'TITLE': title,
			'TITLETRANSLIT': title_tl,
			'ARTIST': artist,
			'ARTISTTRANSLIT': artist_tl,
			'METER': diff,
			'CREDIT': chart_author
		}

		gimmick_data = {
			'OFFSET':   song_data.offset,
			'BPMS':     song_data.bpms,
			'STOPS':    song_data.stops,
			'DELAYS':   getattr(song_data, 'delays', ''),
			'WARPS':    getattr(song_data, 'warps', ''),
			'SPEEDS':   getattr(song_data, 'speeds', '0.000=1.000=0.000=0'),
			'SCROLLS':  getattr(song_data, 'scrolls', '0.000=1.000'),
			'FAKES':    getattr(song_data, 'fakes', '')
		}
		
		if ext == '.ssc':
			gimmick_overwrites = [f for f in gimmick_data if f in chart_data]
			if len(gimmick_overwrites) > 0:
				for f in gimmick_data:
					gimmick_data[f] = chart_data[f]
			# gimmick_data['RADAR'] = TechRadarFromSteps(chart_data)
			# gimmick_data['ECFA'] = CalculateECFAScore(gimmick_data['RADAR'])

	parsedChart = ParseNotesField(chart_data.notes, shush=shush)

	return parsedChart, gimmick_data, chart_info



def ParseChartSM_old(chartFilename, chartType='dance-single', chartSlot='Challenge', chartName=None, shush=True):
	parsedChart = []
	songMetadata = {}

	if chartType is None:
		chartType = '.*'
	if chartSlot is None:
		chartSlot = '.*'
	if chartName is None:
		chartName = '.*'

	with io.open(chartFilename, mode='r', encoding='utf-8') as fid:
		metadataPhase = True
		chartSkipPhase = False
		chartIDPhase = False
		chartIDLines = 5
		chartIDPatterns = [\
			'\s*' + chartType + ':\s*', \
			'\s*' + chartName + ':\s*', \
			'\s*' + chartSlot + ':\s*', \
			'\s*\d*:\s*', \
			'\s*[0-9.,]*:\s*',]
		chartIDMatch = [False, False, False, False, False]
		chartParsePhase = False
		desiredChart = False


		chartIDLineIndex = 0

		currentMeasureNotes = []
		currentMeasureNumber = 0
		currentMeasureLength = 0
		defaultBeatsPerMeasure = 4

		for line in fid:
			if (metadataPhase or chartSkipPhase) and (re.match('\s*#NOTES:\s*', line) is not None):
				metadataPhase = False
				chartSkipPhase = False
				chartIDPhase = True
				chartIDLineIndex = 0
				continue

			if metadataPhase:
				f, v = ParseMetadataLine(line)
				if f is not None and v is not None:
					songMetadata[f.lower()] = v

			if chartIDPhase:
				chartIDMatch[chartIDLineIndex] = (re.match(chartIDPatterns[chartIDLineIndex], line) is not None)
				# print('{}: {}'.format(chartIDLineIndex,
				# chartIDMatch[chartIDLineIndex]))

				if chartIDLineIndex == 1:
					# Difficulty snatch
					songMetadata["chart_author"] = line.strip().rstrip(':')
				elif chartIDLineIndex == 3:
					# Difficulty snatch
					songMetadata["difficulty"] = int(line.strip().rstrip(':'))
					
				chartIDLineIndex += 1

				if chartIDLineIndex >= chartIDLines:
					chartIDPhase = False
					if all(chartIDMatch):
						chartParsePhase = True
						desiredChart = True
						print('Found desired chart!')
					else:
						chartSkipPhase = True
						desiredChart = False
						# print('Skipping this chart!')

				continue

			if chartParsePhase:
				if re.match('\s*[\,\;]\s*', line) is not None:
					# print('End of measure!')
					currentStartBeat = currentMeasureNumber * defaultBeatsPerMeasure
					currentNoteIncrement = 0
					if currentMeasureLength != 0:
						currentNoteIncrement = defaultBeatsPerMeasure / currentMeasureLength

					for singleNote in currentMeasureNotes:
						singleNote['qtzn'] = QuantizationID(singleNote['tick'], currentMeasureLength)
						singleNote['beat'] = singleNote['tick'] * currentNoteIncrement + currentStartBeat
						if not shush:
							print('{} {} {} {}'.format(singleNote['beat'], singleNote['type'], singleNote['lane'], singleNote['qtzn']))
						parsedChart.append(singleNote)

					currentMeasureNotes = []
					currentMeasureNumber += 1
					currentMeasureLength = 0

				if re.match('\s*\;\s*', line) is not None:
					print('End of chart! ({} objects)'.format(len(parsedChart)))
					chartParsePhase = False
					chartSkipPhase = False
					if desiredChart:
						return parsedChart, songMetadata

				noteLine = re.match('\s*([0-9FLM]+)\s*', line)
				if noteLine is not None:
					notes = noteLine.group(1)
					# print('>>> {}'.format(notes))

					for laneIndex in range(len(notes)):
						if notes[laneIndex] == '1':
							currentMeasureNotes.append({'tick': currentMeasureLength, 'type': 'T', 'lane': laneIndex})
						elif notes[laneIndex] == '2':
							currentMeasureNotes.append({'tick': currentMeasureLength, 'type': 'H', 'lane': laneIndex})
						elif notes[laneIndex] == '3':
							currentMeasureNotes.append({'tick': currentMeasureLength, 'type': 'E', 'lane': laneIndex})
						elif notes[laneIndex] == '4':
							currentMeasureNotes.append({'tick': currentMeasureLength, 'type': 'R', 'lane': laneIndex})
						elif notes[laneIndex] == 'F':
							currentMeasureNotes.append({'tick': currentMeasureLength, 'type': 'F', 'lane': laneIndex})
						elif notes[laneIndex] == 'M':
							currentMeasureNotes.append({'tick': currentMeasureLength, 'type': 'M', 'lane': laneIndex})
						elif notes[laneIndex] == 'L':
							currentMeasureNotes.append({'tick': currentMeasureLength, 'type': 'L', 'lane': laneIndex})
					currentMeasureLength += 1

	print('Somehow the file finished before the chart did!')
	return parsedChart, songMetadata


def ChannelToLane(chan, bgm):
	noteType = 'T'
	if chan >= 40:
		chan -= 40
		noteType = 'E'

	noteLane = 'X00'

	if chan == 1:
		noteLane = 'B{:02d}'.format(bgm)
	elif chan >= 11 and chan <= 15:
		noteLane = 'A{:02d}'.format(chan - 10)
	elif chan == 16:
		noteLane = 'ATT'
	elif chan == 18 or chan == 19:
		noteLane = 'A{:02d}'.format(chan - 12)
	elif chan >= 21 and chan <= 25:
		noteLane = 'D{:02d}'.format(chan - 20)
	elif chan == 26:
		noteLane = 'DTT'
	elif chan == 28 or chan == 29:
		noteLane = 'A{:02d}'.format(chan - 12)

	return (noteType, noteLane)


def ParseChartBMS(chartFilename):
	parsedChart = []
	ksAvailable = {}
	ksUsed = []

	with io.open(chartFilename, mode='r', encoding='utf-8') as fid:
		metadataPhase = True
		chartSkipPhase = False
		chartIDPhase = False
		chartIDLines = 5

		chartIDMatch = [False, False, False, False, False]
		chartParsePhase = False
		desiredChart = False

		currentMeasure = 0
		currentMeasureStart = 0
		currentMeasureMeter = None          # 4 beats/measure if not specified (#xxx02: replaces this value
							# for the current measure only!)
		currentBGMChannels = 0

		for line in fid:            
			ksLine = re.match('\s*#WAV(\S\S)\s*(\S+)\s*', line)
			if ksLine is not None:
				ksAvailable[ksLine.group(1)] = ksLine.group(2)

			noteLine = re.match('\s*\#(\d\d\d)(\d\d)\:(\S+)\s*', line)
			if noteLine is not None:
				thisMeasure = int(noteLine.group(1))
				thisChannel = int(noteLine.group(2))

				# Assuming all specs for a specific measure are
				# together
				if thisMeasure != currentMeasure:
					currentMeasure = thisMeasure
					currentMeasureStart += currentMeasureMeter and currentMeasureMeter or 4
					currentMeasureMeter = None
					currentBGMChannels = 0

				if thisChannel == 2:
					# Meter setting
					currentMeasureMeter = 4.0 * float(noteLine.group(3))
				elif thisChannel == 3:
					# BPM direct setting (TODO?)
					selectedBPM = None
				elif thisChannel == 8:
					# BPM selection (TODO?)
					selectedBPM = None
				else:
					# Note lane line
					theseNotes = noteLine.group(3)
					thisMeasDiv = len(theseNotes) // 2

					if thisMeasDiv == 0:
						continue
					
					if thisMeasDiv * 2 != len(theseNotes):
						print('Measure {}, channel {} doesn\'t have an even number of characters in it!'.format(thisMeasure, thisChannel))
					else:
						for nsi in range(thisMeasDiv):
							thisNote = theseNotes[2 * nsi:2 * (nsi + 1)]
							(thisType, thisLane) = ChannelToLane(thisChannel, currentBGMChannels)
							if thisNote != '00':
								parsedChart.append({ \
									'tick': nsi, \
									'type': thisType, \
									'lane': thisLane, \
									'qtzn': thisMeasDiv, \
									'beat': currentMeasureStart + ((currentMeasureMeter and currentMeasureMeter or 4.0) * nsi) / thisMeasDiv, \
									'ksnd': thisNote
									})
								if thisNote not in ksUsed:
									ksUsed.append(thisNote)


					if thisChannel == 1:
						# BGM (automatically firing)
						# channel superposition
						currentBGMChannels += 1

	return (parsedChart, ksAvailable, ksUsed)



def PrettifyChartForLuaSM(parsedChart):
	print('local ChartData = {')
	print('\t-- [1]: beat number, zero at start')
	print('\t-- [2]: lane number, one-indexed')
	print('\t-- [3]: note type: Tap, Hold, Roll, End, or Mine')
	print('\t-- [4]: quantization reciprocal')
	print('\t')
	for singleNote in parsedChart:
		print('\t{{{:>11.6f}, {:d}, "{}", {:>3d}}},'.format(singleNote['beat'], singleNote['lane'] + 1, singleNote['type'], singleNote['qtzn']))
	print('}')

def PrettifyChartForLuaBMS(parsedChart):
	print('local ChartData = {')
	print('\t-- [1]: beat number, zero at start')
	print('\t-- [2]: lane number, one-indexed')
	print('\t-- [3]: note type: Tap, Hold, or End')
	print('\t-- [4]: keysound index')
	print('\t')
	for singleNote in sorted(parsedChart, key=lambda item: item['beat']):
		print('\t{{{:>11.6f}, "{}", "{}", "{}"}},'.format(singleNote['beat'], singleNote['lane'], singleNote['type'], singleNote['ksnd']))
	print('}')


def CompareCharts(fn1, fn2):
	ch1 = ParseChartSM(fn1)
	ch2 = ParseChartSM(fn2)
	(diff1, diff2) = DiffCharts(ch1, ch2)
	anyDiffs = (len(diff1) == 0 and len(diff2) == 0)
	if anyDiffs:
		print('### Charts match!')
	else:
		print('!!! Mismatch!')
		PrettifyChartForLuaSM(diff1)
		PrettifyChartForLuaSM(diff2)
	return anyDiffs



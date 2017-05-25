#!/usr/bin/env python
# -*- coding: UTF-8 -*-

# Usual import stuff
from bs4 import BeautifulSoup
from shutil import copyfileobj
from sys import path, version_info
import spotipy
import eyed3
import requests
import pafy
import os
import argparse
import pathlib
#import spotipy.util as util

def getInputLink(links):
	while True:
		try:
			the_chosen_one = int(raw_input('>> Choose your number: '))
			if the_chosen_one >= 1 and the_chosen_one <= len(links):
				return links[the_chosen_one-1]
			elif the_chosen_one == 0:
				return None
			else:
				print('Choose a valid number!')
		except ValueError:
			print('Choose a valid number!')

# Check if input song is Spotify URL or just a song name
def isSpotify(raw_song):
	if (len(raw_song) == 22 and raw_song.replace(" ", "%20") == raw_song) or (raw_song.find('spotify') > -1):
		return True
	else:
		return False

# [Artist] - [Song Name]
def generateSongName(raw_song):
	if isSpotify(raw_song):
		tags = generateMetaTags(raw_song)
		raw_song = tags['artists'][0]['name'] + ' - ' + tags['name']
	return raw_song

def generateMetaTags(raw_song):
	try:
		if isSpotify(raw_song):
			return spotify.track(raw_song)
		else:
			return spotify.search(raw_song, limit=1)['tracks']['items'][0]
	except:
		return None

def generateSearchURL(song):
	URL = "https://www.youtube.com/results?sp=EgIQAQ%253D%253D&q=" + song.replace(" ", "%20") + " -live -mashup -mix -cover"
	print('youtube search: ' + song.replace(" ", "%20"))
	return URL

def generateYouTubeURL(raw_song):
	song = generateSongName(raw_song)
	searchURL = generateSearchURL(song)
	items = requests.get(searchURL).text
	items_parse = BeautifulSoup(items, "html.parser")
	check = 1
	if args.manual:
		links = []
		print(song)
		print('')
		print('0. Skip downloading this song')
		for x in items_parse.find_all('h3', {'class':'yt-lockup-title'}):
			if not x.find('channel') == -1 or not x.find('googleads') == -1:
				print(str(check) + '. ' + x.get_text())
				links.append(x.find('a')['href'])
				check += 1
		print('')
		result = getInputLink(links)
		if result == None:
			return None
	else:
		result = items_parse.find_all(attrs={'class':'yt-uix-tile-link'})[0]['href']
		while not result.find('channel') == -1 or not result.find('googleads') == -1:
			result = items_parse.find_all(attrs={'class':'yt-uix-tile-link'})[check]['href']
			check += 1
	full_link = "youtube.com" + result
	return full_link

def goPafy(raw_song):
	trackURL = generateYouTubeURL(raw_song)
	if trackURL == None:
		return None
	else:
		return pafy.new(trackURL)

def getYouTubeTitle(content, number):
	title = content.title
	if number == None:
		return title
	else:
		return str(number) + '. ' + title

# Generate name for the song to be downloaded
def generateFileName(content):
	return fixEncoding((content.title).replace("\\", "_").replace("/", "_").replace(":", "_").replace("*", "_").replace("?", "_").replace('"', "_").replace("<", "_").replace(">", "_").replace("|", "_").replace(" ", "_"))

def downloadSong(content):
	music_file = generateFileName(content)
	link = content.getbestaudio(preftype="m4a")
	link.download(filepath="Music/" + music_file + ".m4a")

def convertToMP3(music_file):
	if os.name == 'nt':
		os.system('Scripts\\avconv.exe -loglevel 0 -i "' + 'Music/' + music_file + '.m4a" -ab 192k "' + 'Music/' + music_file + '.mp3"')
	else:
		os.system('avconv -loglevel 0 -i "' + 'Music/' + music_file + '.m4a" -ab 192k "' + 'Music/' + music_file + '.mp3"')
	os.remove('Music/' + music_file + '.m4a')

def checkExists(music_file, raw_song, islist):
	if os.path.exists("Music/" + music_file + ".m4a.temp"):
		os.remove("Music/" + music_file + ".m4a.temp")
	if args.no_convert:
		extension = '.m4a'
	else:
		if os.path.exists("Music/" + music_file + ".m4a"):
			os.remove("Music/" + music_file + ".m4a")
		extension = '.mp3'
	if os.path.isfile("Music/" + music_file + extension):
		if extension == '.mp3':
			audiofile = eyed3.load("Music/" + music_file + extension)
			if isSpotify(raw_song) and not audiofile.tag.title == (generateMetaTags(raw_song))['name']:
				os.remove("Music/" + music_file + extension)
				return False
		if islist:
			return True
		else:
			prompt = raw_input('Song with same name has already been downloaded. Re-download? (y/n): ').lower()
			if prompt == "y":
				os.remove("Music/" + music_file + extension)
				return False
			else:
				return True

# Remove song from list.txt once downloaded
def trimSong(file):
	with open(file, 'r') as fin:
		data = fin.read().splitlines(True)
	with open(file, 'w') as fout:
		fout.writelines(data[1:])

def fixSong(music_file, meta_tags):
	audiofile = eyed3.load("Music/" + music_file + '.mp3')
	audiofile.tag.artist = meta_tags['artists'][0]['name']
	audiofile.tag.album_artist = meta_tags['artists'][0]['name']
	audiofile.tag.album = meta_tags['album']['name']
	audiofile.tag.title = meta_tags['name']
	audiofile.tag.track_num = meta_tags['track_number']
	audiofile.tag.disc_num = meta_tags['disc_number']
	audiofile.tag.release_date = spotify.album(meta_tags['album']['id'])['release_date']
	albumart = (requests.get(meta_tags['album']['images'][0]['url'], stream=True)).raw
	with open('last_albumart.jpg', 'wb') as out_file:
		copyfileobj(albumart, out_file)
	albumart = open("last_albumart.jpg", "rb").read()
	audiofile.tag.images.set(3,albumart,"image/jpeg")
	audiofile.tag.save(version=(2,3,0))

# Logic behind preparing the song to download to finishing meta-tags
def grabSingle(raw_song, number=None):
	if number:
		islist = True
	else:
		islist = False
	content = goPafy(raw_song)
	if content == None:
		return
	print(getYouTubeTitle(content, number))
	music_file = generateFileName(content)
	if not checkExists(music_file, raw_song, islist=islist):
		downloadSong(content)
		print('')
		if not args.no_convert:
			print('Converting ' + music_file + '.m4a to mp3')
			convertToMP3(music_file)
			meta_tags = generateMetaTags(raw_song)
			if not meta_tags == None:
				print('Fixing meta-tags')
				fixSong(music_file, meta_tags)

# Fix python2 encoding issues
def fixEncoding(query):
	if version_info > (3,0):
		return query
	else:
		return query.encode('utf-8')

def grabList(file):
	lines = open(file, 'r').read()
	lines = lines.splitlines()
	# Ignore blank lines in list.txt (if any)
	try:
		lines.remove('')
	except ValueError:
		pass
	print('Total songs in list = ' + str(len(lines)) + ' songs')
	print('')
	# Count the number of song being downloaded
	number = 1
	for raw_song in lines:
		try:
			grabSingle(raw_song, number=number)
			trimSong(file)
			number += 1
			print('')
		except KeyboardInterrupt:
			graceQuit()
		except:
			lines.append(raw_song)
			trimSong(file)
			with open(file, 'a') as myfile:
				myfile.write(raw_song)
			print('Failed to download song. Will retry after other songs.')

def graceQuit():
	print('')
	print('')
	print('Exitting..')
	exit()

# Python 3 compatibility
if version_info > (3,0):
	raw_input = input

eyed3.log.setLevel("ERROR")

os.chdir(path[0])

if not os.path.exists("Music"):
	os.makedirs("Music")
open('list.txt', 'a').close()

spotify = spotipy.Spotify()

# Set up arguments
parser = argparse.ArgumentParser()
parser.add_argument("-n", "--no-convert", help="skip the conversion process and meta-tags", action="store_true")
parser.add_argument("-m", "--manual", help="choose the song to download manually", action="store_true")
parser.add_argument("-l", "--list", help="download songs present in list.txt", action="store_true")
args = parser.parse_args()

if args.no_convert:
        print("-n, --no-convert skip the conversion process and meta-tags")
if args.manual:
	print("-m, --manual     choose the song to download manually")
print('')
if args.list:
	grabList(file='list.txt')
	exit()

while True:
	for temp in os.listdir('Music/'):
		if temp.endswith('.m4a.temp'):
			os.remove('Music/' + temp)
	try:
		print('Enter a Spotify URL or Song Name: ')
		command = raw_input('>> ')
		print('')
		grabSingle(raw_song=command)
		print('')
	except KeyboardInterrupt:
		graceQuit()

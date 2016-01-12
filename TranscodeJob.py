import os
import sys
import glob
import subprocess
import json
import time

mypath = sys.argv[1]
mybackup = sys.argv[2]

#Returns a string of the formatted date stamp for logging purposes
def dateStamp():
	return time.strftime("[%x %X]")

#Logs a string to the specified .log file
def log(toLog):
	with open("/jobs/TranscodeJob.log", "a") as myfile:
		myfile.write(dateStamp() + " " + toLog + "\n")

#Returns a video that needs to be transcoded
def findVideo(path):
	allvideos = []
	for filename in glob.iglob(path + "**/*.mkv"):
		allvideos.append(filename)
	for filename in glob.iglob(path + "**/*.mp4"):
		allvideos.append(filename)
	for video in allvideos:
		command = ["avprobe", "-v", "quiet", "-show_format", "-show_streams", "-of", "json", video]
		out = subprocess.Popen(command, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0]
		parsed = json.loads(out)
		fileFormat = parsed['format']['format_name']
		videoCodec = parsed['streams'][0]['codec_name']
		audioCodec = parsed['streams'][1]['codec_name']
		if "mp4" not in fileFormat or videoCodec != "h264" or audioCodec != "aac":
			return video
	return 0

#Transcodes a video using avconv
def transcodeVideo(badVideo):
	mediaFileIn = badVideo
	mediaFileOut = badVideo.rsplit(".", 1)[0] + ".mp4"
	command = "avconv -i " + repr(mediaFileIn) + " -c:v libx264 -b:v 4000k -c:a aac -strict experimental -b:a 600k " + repr(mediaFileOut)
	subprocess.call(command, shell=True)
	return mediaFileOut

#Checks for errors in a video file using avprobe
def verifyVideo(video):
	command = ["avprobe", video]
	out, err = subprocess.Popen(command, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
	if "invalid data" in err.lower():
		return False
	else:
		return True

#Generates a pid to ensure a single instance
pid = str(os.getpid())
pidfile = "/tmp/TranscodeJob.pid"
if os.path.isfile(pidfile):
	log("Aborting, TranscodeJob already running")
	sys.exit()
else:
	file(pidfile, 'w').write(pid)

#Body of the script
log("Starting");
mybadVideo = findVideo(mypath)
if mybadVideo != 0:
	log("Transcoding " + mybadVideo)
	mygoodVideo = transcodeVideo(mybadVideo)
	log("Transcode complete")
	verify = verifyVideo(mygoodVideo)
	if verify:
		log("Valid Transcode, moving old video to backup")
		command = ["mv", mybadVideo, mybackup]
		subprocess.Popen(command, shell=False)
	else:
		log("Invalid Transcode, deleting new video")
		command = ["rm", mygoodVideo]
		subprocess.Popen(command, shell=False)
else:
	log("No transcoding required")
log("Ending")

#Unlinks pid on script termination
os.unlink(pidfile)

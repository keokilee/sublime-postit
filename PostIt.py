import sys
import os
import sublime
import sublime_plugin
import threading
import json

# Set system path to include requests
sys.path.append(os.path.join(os.path.dirname(__file__), 'requests'))

import requests
from requests.exceptions import HTTPError, ConnectionError, Timeout

ERROR_STATUS_MESSAGE = 'PostIt could not upload your file'
ENDPOINT_URL = 'http://localhost:9157'
STATUS_KEY = 'postit'
REQUEST_TIMEOUT = 3

class PostItCommand(sublime_plugin.WindowCommand):
	"""
	Command that posts the file name and contents to an internal URL. Tested on Sublime Text 3, but
	this should work on previous versions.
	"""
	def run(self):
		view = self.window.active_view()
		file_name = view.file_name()

		if file_name is None:
			sublime.error_message("Please save this file before uploading")
			sublime.status_message(ERROR_STATUS_MESSAGE)
			return

		contents = self.grab_view_contents(view)

		thread = PostItWorker(file_name, contents)
		thread.start()

		self._handle_thread(thread)

	def grab_view_contents(self, view):
		"""Grab the contents for the entire view."""
		return view.substr(sublime.Region(0, view.size()))

	def _handle_thread(self, thread, counter=0):
		view = self.window.active_view()

		if thread.is_alive():
			message = "Working "
			dots = (counter % 3) + 1
			message += ''.join(["." for i in range(0, dots)])
			view.set_status(STATUS_KEY, message)
			counter += 1
			sublime.set_timeout(lambda: self._handle_thread(thread, counter), 500)
		else:
			view.erase_status(STATUS_KEY)
			self._process_result(thread.result)

	def _process_result(self, result):
		print("Received result: %s" % result)

		if 'error' in result:
			sublime.error_message(result['error'])
			sublime.status_message(ERROR_STATUS_MESSAGE)
			return

		sublime.status_message("Your file has been sent")


class PostItWorker(threading.Thread):
	"""
	Worker thread to prevent blocking while uploading contents to the internal
	server
	"""
	def __init__(self, file_name, contents, timeout=REQUEST_TIMEOUT):
		self.file_name = file_name
		self.contents = contents
		self.result = None
		self.timeout = timeout

		super(PostItWorker, self).__init__()

	def run(self):
		data = {'filename': self.file_name, 'contents': self.contents}
		
		try:
			req = requests.post(ENDPOINT_URL, data=data, timeout=self.timeout)
			self.result = json.loads(req.text)
			req.raise_for_status() # Trigger exceptions for 400/500 status codes
			return

		except HTTPError as e:
			err = "HTTP Error: %s" % e
		except ConnectionError as e:
			err = "Connection Error: %s" % e
		except Timeout:
			err = "Connection timed out"
		except Exception as e:
			err = "You broke it: %s" % e

		self.result = {'error': err}

"""Telegram bot api wrapper.

https://core.telegram.org/bots/api
"""

import requests
import urllib.parse
#import urllib.request as request
import json
try:
    json.JSONDecodeError
except AttributeError:
    json.JSONDecodeError = ValueError

import logging
logging.getLogger("requests").setLevel(logging.WARNING)

class Error(Exception):
    pass

class NetworkError(Error):
    """Some issue occured while connecting to the api."""
    def __init__(self, e):
        Error.__init__(self)
        self.e = e

class ApiError(Error):
    """Api response indicates error."""
    def __init__(self, res, desc=""):
        Error.__init__(self)
        self.response = res
        self.desc = desc
    def __str__(self):
        return "{0} {1}".format(self.response, self.desc)

class JSONError(ApiError):
    """JSON could not be parsed"""
    def __init__(self, res, text):
        ApiError.__init__(self, res)
        self.text = text

class Telegram:
    """A wrapper for telegram's bot api.

    Attributes:
        offset (int)
        url (str)
    """

    def __init__(self, auth, offset=0):
        """Creates a new bot.

        Offset can be found with findOffset() if unknown

        Args:
            auth (str): Token recieved from @BotFather
            offset (Optional[int]): Initial offset.
                See telegram documentation for more info
        """
        self.offset = offset
        self.url = "https://api.telegram.org/bot{0}/".format(auth)
        self.timeout = 20*60

    def _get(self, url, params=None):
        try:
            res = requests.get(url, params=params, timeout=self.timeout)
        except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
            raise NetworkError(e)

        if res.status_code != 200:
            try:
                data = json.loads(res.text)
                if data['ok']:
                    return res
                else:
                    raise ApiError(res, data['description'])
            except (json.JSONDecodeError, KeyError):
                pass
            raise ApiError(res)

        return res

    def _post(self, url, data, files=None, params=None):
        try:
            res = requests.post(url, data=data, files=files, params=params, timeout=self.timeout)
        except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
            raise NetworkError(e)

        if res.status_code != 200:
            raise ApiError(res)

        return res

    def findOffset(self):
        """Attempts to find offset after most recent message

        Recieves messages stored by the server until it recieves less than 100 (defualt max)
        Currently has issues if the server has a number of messages stored evenly divisble by 100.
        """
        recv = self.getUpdates(offset=self.offset, timeout=0, updateOffset=False)
        count = len(recv['result'])
        while count == 100:
            self.offset = recv['result'][-1]['update_id']
            recv = self.getUpdates(self.offset, timeout=0, updateOffset=False)
            count = len(recv['result'])
        if recv['result']:
            self.offset = recv['result'][-1]['update_id']
            self.offset += 1

    def getMe(self):
        """/getMe

        Returns:
            dict: representation of json returned by /getMe
        """
        res = self._get(self.url+"getMe")
        data = json.loads(res.text)
        return data

    def getUpdates(self, offset=None, timeout=60, updateOffset=True):
        """/getUpdates

        Will update offset to the most recent messages id+1 if offset is not
        provided, updateOffset is True and at least one new update is recieved.

        Args:
            offset (Optional[int]): Internaly maintained offset used if not
                provided.
            timeout (Otional[int]): Defualts to 60.
            updateOffset (Optional[bool]): Defualts to True.

        Returns:
            dict: representation of json returned by /getUpdates
        """
        offsetGiven = offset != None
        if offset == None:
            offset = self.offset
        if timeout != False:
            res = self._get(self.url+"getUpdates?offset={0}&timeout={1}".format(offset, timeout))
        else:
            res = self._get(self.url+"getUpdates?offset={0}".format(offset))

        try:
            data = json.loads(res.text)
        except ValueError:
            raise JSONError(res, res.text)
        if updateOffset and not offsetGiven and data['result']:
            self.offset = data['result'][-1]['update_id'] + 1
        return data

    def sendMessage(self, chat_id, text):
        """/sendMessage

        Args:
            chat_id (int)
            text (str)

        Returns:
            dict: representation of json representing sent message or error
        """
        text = urllib.parse.quote(text, safe=[])
        url = self.url+"sendMessage?chat_id={0}&text={1}".format(chat_id, text)
        res = self._get(url)
        data = json.loads(res.text)
        return data

    def sendDocument(self, chat_id, document):
        """/sendDocument

        Args:
            chat_id (int)
            document (Union[str, TextIOWrapper]):
                Sends file or file at specified location.

        Returns:
            dict: representation of json representing sent document or error
        """
        url = self.url+"sendDocument"
        #payload = {'chat_id':chat_id, 'document':document}
        payload = {'chat_id':chat_id}
        if isinstance(document, str):
            payload['document'] = document
            res = self._post(url, data=payload)
        else:
            files = {'document':document}
            res = self._post(url, data=payload, files=files)
        return res

    def sendChatAction(self, chat_id, action):
        """/sendChatAction

        Args:
            chat_id (int)
            action (str): One of typing, upload_photo, record_video,
                upload_video, record_audio, upload_audio, upload_document or
                find_location
        """
        url = self.url+"sendChatAction?chat_id={0}&action={1}".format(chat_id, action)
        self._get(url)

    def answer_inline_query(self, query_id, results, next_offset="", cache_time=300, is_personal=None):
        """/answerInlineQuery
        
        Args:
            query_id (str)
            results
            cache_time (int)
            is_personal (bool)
            next_offset (str)
        """
        results = urllib.parse.quote(results, safe=[])
        url = self.url+"answerInlineQuery?inline_query_id={0}&results={1}&next_offset={2}&cache_time={3}"
        url = url.format(query_id, results, next_offset, cache_time)
        self._get(url)

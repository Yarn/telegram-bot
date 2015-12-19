import re
import pickle
from bot_handler import TelegramHandler

class Error(Exception):
    pass

class RegexError(Error):
    def __init__(self, message):
        Error.__init__(self)
        self.message = message

class Announce(TelegramHandler):
    """Announces new releases"""

    def __init__(self, bot=None, config=None):
        TelegramHandler.__init__(self, bot, config)
        self.announceListFile = "announce.dat"
        self.announceList = {}
        self._loadAnnounce()
        try:
            self.sources = self.config['admins'] + self.config['sources']
        except KeyError:
            self.sources = ()

    def _setAnnounce(self, chat_id, subs):
        """sets regex to filter chat announce

        does not check regex, regex errors will be caught when announce is sent

        Args:
            chat_id (int)
            subs (Union[str, None]): regex to match against, if None removes from announce
        """
        if subs != None:
            if subs.count("("):
                raise RegexError("( not allowed.")
            elif len(subs) > 100:
                raise RegexError("Too long")
            try:
                re.compile(subs)
            except re.error as e:
                if e.args:
                    raise RegexError(e.args[0])
                else:
                    raise RegexError("Invalid Regex")

            self.announceList[chat_id] = subs
            pickle.dump(self.announceList, open(self.announceListFile, 'wb'))
        else:
            try:
                del self.announceList[chat_id]
            except KeyError:
                pass

    def _getAnnounce(self, chat_id):
        """gets announce for chat_id"""
        return self.announceList[chat_id]

    def _loadAnnounce(self):
        """loads announce list from file"""
        try:
            self.announceList = pickle.load(open(self.announceListFile, 'rb'))
        except (EOFError, IOError):
            pass

    def update(self, update):
        try:
            message = update['message']
            chat_id = message['chat']['id']
            text = message['text']
        except KeyError:
            pass
        else:
            if text.startswith("/announce "):
                cmd = text.split(" ", 1)
                if cmd[1].count("("):
                    self.bot.sendMessage(chat_id, "( not allowed")
                if cmd[1] != "off":
                    #try:
                    #    re.compile(cmd[1])
                    #except re.error:
                    #    self.bot.sendMessage(chat_id, "Invalid regex")
                    #    return
                    try:
                        self._setAnnounce(chat_id, cmd[1])
                    except RegexError as e:
                        self.bot.sendMessage(chat_id, e.message)
                    self.bot.sendMessage(chat_id, cmd[1])
                else:
                    self._setAnnounce(chat_id, None)
            elif text.startswith("/announce"):
                self.bot.sendMessage(chat_id, self._getAnnounce(chat_id))

        try:
            from_id = update['message']['from']['id']
            document = update['message']['document']
            fid = document['file_id']
            fname = document['file_name']
        except KeyError:
            pass
        else:
            if from_id in self.sources:
                for chat_id in self.announceList:
                    subs = self.announceList[chat_id]
                    try:
                        matches = re.search(subs, fname)
                    except re.error:
                        return
                    if matches:
                        self.bot.sendMessage(chat_id, fname)
                        self.bot.sendDocument(chat_id, fid)

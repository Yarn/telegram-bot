from bot_handler import TelegramHandler
import telegram
import logging
import re

logger = logging.getLogger(__name__)
#pylint: disable=W1202

class Error(Exception):
    pass

class RegexError(Error):
    def __init__(self, message):
        Error.__init__(self)
        self.message = message

class FileList(TelegramHandler):
    def __init__(self, bot=None, config=None):
        TelegramHandler.__init__(self, bot, config)
        
        try:
            self.sources = config['sources']
        except KeyError:
            self.sources = ()
        self.filelistfile = "files.txt"
        self.filelist = {}
        self._loadFileList()
        
    def _loadFileList(self):
        """loads file list from file"""
        with open(self.filelistfile, 'r') as f:
            for line in f:
                fid, fname = line.rstrip().split(" ", 1)
                self.filelist[fname] = fid
                
    def _addFile(self, fid, fname):
        """Adds file to file list

        Args:
            fid (int): file id
            fname (str): file name
        """
        with open(self.filelistfile, 'a') as f:
            f.write(fid + " " +  fname + "\n")
        self.filelist[fname] = fid
        
    def _findFileRe(self, exp):
        """Finds file in file list whose name contains a match to exp

        Args:
            exp (_sre.SRE_Pattern): Compiled regular expression to match.

        Returns:
            (int, Union[str, None]):
                (file id, file name) if file is founding matching exp
                otherwise (0, None)
        """

        try:
            results = self._findFilesRe(exp, maxresults=1)
        except RegexError:
            return (0, None)
        if results:
            return results[0]
        return (0, None)

    def _findFilesRe(self, exp, maxresults=10, fullmatch=False):
        """Finds a list of files whose name contains a match to exp.

        Args:
            exp (Union[str, _sre.SRE_Pattern]):
                Compiled regular expression to match or regex.
            maxresults (int): Maximum number of results to return. Default: 10
            fullmatch (bool): Requires filename to match all of exp. Default: False

        Returns:
            list[(int, str)]:
                list of (file id, file name)

        Raises:
            RegexError: If exp is an invalid regex.
        """

        if isinstance(exp, str):
            if exp.count("("):
                #bot.sendMessage(chat_id, "( not allowed")
                raise RegexError("( not allowed.")
            elif len(exp) > 30:
                #bot.sendMessage(chat_id, "regex too long")
                raise RegexError("Regex too long.")
            else:
                try:
                    exp = re.compile(exp, re.IGNORECASE)
                except re.error:
                    #bot.sendMessage(chat_id, "u wot m8?")
                    raise RegexError("Could not compile regex.")
                #else:

        results = []
        for fname in self.filelist:
            if fullmatch:
                match = exp.fullmatch(fname)
            else:
                match = exp.search(fname)
            if match:
                fid = self.filelist[fname]
                results.append((fid, fname))
                if len(results) >= maxresults:
                    break
        return results
        
    def update(self, update):
        bot = self.bot
        try:
            from_id = update['message']['from']['id']
            chat_id = update['message']['chat']['id']
            text = update['message']['text']
        except KeyError:
            pass
        else:
            if text.startswith("/get "):
                cmd = text.split(" ", 1)
                fid, fname = self._findFileRe(cmd[1])
                if fid:
                    try:
                        bot.sendMessage(chat_id, fname)
                        bot.sendDocument(chat_id, fid)
                    except telegram.Error:
                        logger.exception("document failed to send")
            elif text.startswith("/search "):
                cmd = text.split(" ", 1)
                try:
                    results = self._findFilesRe(cmd[1])
                except RegexError as e:
                    bot.sendMessage(chat_id, e.message)
                    return
                if results:
                    response = "\n".join([r[1] for r in results])
                    bot.sendMessage(chat_id, response)
                    
        try:
            from_id = update['message']['from']['id']
            chat_id = update['message']['chat']['id']
            document = update['message']['document']
            fid = document['file_id']
            fname = document['file_name']
        except KeyError:
            pass
        else:
            logger.debug("Document: [{0}]{1}".format(fid, fname))
            if from_id in self.sources:
                logger.info("Recieved: {0}".format(fname))
                self._addFile(fid, fname)
                bot.sendMessage(chat_id, fname)

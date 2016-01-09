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
        
class QueryError(Error):
    def __init__(self):
        Error.__init__(self)

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
        
    def _inlineQuery(self, query_id, query, offset=''):
        bot = self.bot
        results_per_query = 20
        cache_time = 0
        
        if not offset:
            offset = 0
        else:
            try:
                offset = int(offset)
            except ValueError:
                raise QueryError()
        maxresults = (offset+1)*results_per_query
        
        try:
            results = self._findFilesRe(query, maxresults=maxresults)
        except RegexError as e:
            #bot.sendMessage(chat_id, e.message)
            raise
            return
        if results and len(results) > offset*results_per_query:
            results = [r[1] for r in results]
            #results = sorted(results)
            #response = "\n".join(results)
            new_res = []
            for result in results[-results_per_query:]:
                d = {'type':"article", 'id':str(hash(result))[:64]}
                d['title'] = result
                d['message_text'] = "/get {0}".format(re.escape(result)[:30])
                new_res.append(d)
            
            #bot.sendMessage(chat_id, response)
            import json
            res_json = json.dumps(new_res)
            #import pdb;pdb.set_trace()
            bot.answer_inline_query(query_id, res_json, next_offset=offset+1, cache_time=cache_time)
        else:
            bot.answer_inline_query(query_id, "[]", next_offset=offset, cache_time=cache_time)
        
        #print(results)
        #import pdb;pdb.set_trace()
    
    def update(self, update):
        TelegramHandler.update(self, update)
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
                if from_id == chat_id:
                    maxresults = 30
                else:
                    maxresults = 10
                try:
                    results = self._findFilesRe(cmd[1], maxresults=maxresults)
                except RegexError as e:
                    bot.sendMessage(chat_id, e.message)
                    return
                if results:
                    results = [r[1] for r in results]
                    results = sorted(results)
                    response = "\n".join(results)
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
                
        try:
            query = update['inline_query']
            query_id = query['id']
            query_offset = query['offset']
            query_text = query['query']
        except KeyError:
            pass
        else:
            try:
                self._inlineQuery(query_id, query_text, query_offset)
            except Error:
                logger.exception("error while handling inline query {0}".format(query))

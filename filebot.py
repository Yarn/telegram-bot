import re
import telegram
from telegram import Telegram
import bot_handler
from announce import Announce
from filelist import FileList
import logging

logger = logging.getLogger(__name__)

class Error(Exception):
    pass

class FileServeBot():
    def __init__(self, auth, offset=None, sources=(), admins=()):
        """Sets up a bot that provides access to a list of files

        Args:
            auth (str): Token recieved from @BotFather
            offset (Optional[int]): Initial offset to be used
                If not provided offset is found with Telegram.findOffset
            sources (Optional[List]): A list of telegram user ids who can
                provide new files.
            admins (Optional[List]): A list of telegram user ids who can
                use administrative commands such as stopping the bot.
        """
        self.auth = auth
        self.bot = Telegram(self.auth)
        bot = self.bot
        self.sources = sources
        self.admins = admins
        self.offset = offset
        
        self.config = {'sources':tuple(sources), 'admins':tuple(admins)}
        self.handlers = [Announce(bot=bot, config=self.config)]
        self.handlers += [bot_handler.IPHandler(bot=bot, config=self.config)]
        self.handlers += [FileList(bot, self.config)]
        for handler in self.handlers:
            handler.postInit()

    def start(self):
        """pls"""
        sources = list(self.sources) + list(self.admins)
        bot = self.bot
        
        try:
            logger.debug(bot.getMe())
        except telegram.Error:
            logger.exception("getMe() failed")
        
        if self.offset == None:
            try:
                bot.findOffset()#offset now set to most recent message's id+1
            except telegram.Error:
                logger.critical("Could not get offset.")
                raise
        else:
            bot.offset = self.offset
        logger.info("Initial offset set to {0}".format(bot.offset))
        logger.debug("armed")

        done = False
        failed = False
        while not done:
            if failed:
                time.sleep(4)
                failed = False
            try:
                recv = bot.getUpdates()
            except telegram.Error:
                logger.exception("getUpdates() failed")
                failed=True
                continue
                
            try:
                result = recv['result']
            except KeyError:
                logger.error("No result key in response.")
                continue
            
            for update in result:
                #offset = update['update_id']+1
                for handler in self.handlers:
                    try:
                        handler.update(update)
                    except telegram.Error:
                        logger.exception("Telegram error from handler " + str(handler.__name__))

                logger.debug("\n")
                logger.debug(update)
                try:
                    from_id = update['message']['from']['id']
                    chat_id = update['message']['chat']['id']
                    text = update['message']['text']
                    #message_id = update['message']['message_id']
                except KeyError:
                    pass
                else:
                    logger.info("{0}: {1}".format(str(from_id), text))
                    if text == "/q" and from_id in self.admins:
                        done = True
                    elif text == "/type":
                        bot.sendChatAction(chat_id, "typing")
                    elif text.startswith("/echo "):
                        bot.sendMessage(chat_id, text.split(" ")[1])
                    else:
                        pass

def main(offset=None):
    """
    config
    auth token for bot
    comma seperated list of ids for admins
    comma seperated list of ids for sources
    use empty lines if not providing sources or admins
    """
    with open("config.txt", 'r') as f:
        auth = f.readline().strip()
        admins = (n.strip() for n in f.readline().split(","))
        admins = [int(n) for n in admins if n]
        sources = (n.strip() for n in f.readline().split(","))
        sources = [int(n) for n in sources if n]
        
    bot = FileServeBot(auth, offset=offset, admins=admins, sources=sources)
    bot.start()

if __name__ == "__main__":
    #FORMAT = "%(message)s"
    #FORMAT = "%(asctime)s %(message)s"
    #FORMAT = "%(asctime)s %(levelname)s %(message)s"
    FORMAT = "%(asctime)s %(filename)s %(lineno)s %(funcName)s %(levelname)s %(message)s"
    logging.basicConfig(format=FORMAT, level="DEBUG")
   # import argparse
    import time

    debug = True
    if debug:
        main()
    else:
        while True:
            try:
                main()
            except KeyboardInterrupt:
                break
            except:#pylint: disable=all
                logger.exception("Error in main")
                try:
                    time.sleep(5)
                except:
                    logger.exception("Error while waiting for restart.")

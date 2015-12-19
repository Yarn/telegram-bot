import requests
import logging

logger = logging.getLogger(__name__)

class TelegramHandler:
    def postInit(self):
        pass

    def __init__(self, bot=None, config=None):
        self.bot = bot
        if config != None:
            self.config = config
        else:
            self.config = {}

    def update(self, update):
        """called when update is recieved"""
        pass

class IPHandler(TelegramHandler):
    def __init__(self, bot=None, config=None):
        TelegramHandler.__init__(self, bot, config)
        self.uri = "http://icanhazip.com/"
        
        try:
            self.auth = self.config['admins']
        except KeyError:
            self.auth = ()
            
    def update(self, update):
        try:
            message = update['message']
            chat_id = message['chat']['id']
            from_id = message['from']['id']
            text = message['text']
        except KeyError:
            pass
        else:
            if chat_id==from_id and text=="/ip" and from_id in self.auth:
                try:
                    ip = requests.get(self.uri).text
                except:
                    logger.exception("exception while getting IP")
                self.bot.sendMessage(from_id, ip)
        
        

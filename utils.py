import logging

class Utils:

    @staticmethod
    def log(string):
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
        logger = logging.getLogger()
        logger.info(string)
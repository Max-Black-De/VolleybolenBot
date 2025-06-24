import logging

# Логирование
def setup_logging():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s', level=logging.INFO)
    logger = logging.getLogger(__name__)
    return logger
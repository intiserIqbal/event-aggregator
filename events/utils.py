import logging

logger = logging.getLogger(__name__)

def log_error(error, context=None):
    logger.error(f"Error: {str(error)}", extra={'context': context})

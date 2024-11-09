import logging
import os 
class CustomLogger:
    def __init__(self, service_name, user_id):
        self.service_name = service_name
        self.user_id = user_id
        self.logger = logging.getLogger(service_name)
        self.logger.setLevel(logging.DEBUG)
        # Ensure the log directory exists
        log_dir = os.getenv('LOG_DIR', '/app/logs') # get dir from env
        os.makedirs(log_dir, exist_ok=True)
        
        # Create file handler
        file_handler = logging.FileHandler(f'{log_dir}/{service_name}.log')
        file_handler.setLevel(logging.DEBUG)

        # Create formatter
        formatter = logging.Formatter('%(message)s')

        # Set formatter to handler
        file_handler.setFormatter(formatter)

        # Add the file handler to the logger
        self.logger.addHandler(file_handler)

    def info(self, message):
        self.logger.info(message)

    def error(self, message):
        self.logger.error(message)

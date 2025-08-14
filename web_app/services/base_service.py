"""
Base service class providing common functionality for all services
"""
from web_app.shared.logging_config import get_project_logger


class BaseService:
    """Base class for all services providing common functionality"""
    
    def __init__(self, db_session=None):
        self.logger = get_project_logger(self.__class__.__module__)
        self.db_session = db_session
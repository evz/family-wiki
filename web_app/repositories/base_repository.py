"""
Base repository classes to eliminate duplication and standardize patterns
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Generic, TypeVar, Union

from sqlalchemy.exc import SQLAlchemyError

from web_app.database import db
from web_app.shared.logging_config import get_project_logger

# Generic type for model classes
ModelType = TypeVar('ModelType')


class BaseRepository(ABC):
    """
    Base repository class providing common functionality for all repositories
    
    Features:
    - Standard error handling with rollback
    - Consistent logging setup
    - Transaction management (flush() standardization)
    - Safe operation wrapper
    """
    
    def __init__(self, db_session=None):
        """Initialize base repository with database session and logger"""
        self.db_session = db_session or db.session
        self.logger = get_project_logger(self.__class__.__name__)
    
    def safe_operation(self, operation: Callable[[], Any], operation_name: str = "operation") -> Any:
        """
        Execute database operation with standard error handling
        
        Args:
            operation: Function to execute (should return result)
            operation_name: Description for logging purposes
            
        Returns:
            Result of the operation
            
        Raises:
            Exception: Re-raises original exception after logging and rollback
        """
        try:
            result = operation()
            self.db_session.flush()  # Standard pattern: flush instead of commit
            self.logger.debug(f"Repository {operation_name} completed successfully")
            return result
        except SQLAlchemyError as e:
            self.db_session.rollback()
            self.logger.error(f"Database error in {operation_name}: {e}")
            raise
        except Exception as e:
            self.db_session.rollback()
            self.logger.error(f"Repository {operation_name} failed: {e}")
            raise
    
    def safe_query(self, query_func: Callable[[], Any], operation_name: str = "query") -> Any:
        """
        Execute read-only query with error handling (no flush needed)
        
        Args:
            query_func: Function to execute query 
            operation_name: Description for logging purposes
            
        Returns:
            Query result
        """
        try:
            result = query_func()
            self.logger.debug(f"Repository {operation_name} completed successfully")
            return result
        except Exception as e:
            self.logger.error(f"Repository {operation_name} failed: {e}")
            raise


class ModelRepository(BaseRepository, Generic[ModelType]):
    """
    Generic repository for standard CRUD operations on model types
    
    Provides common patterns for:
    - Creating entities
    - Updating entities  
    - Bulk operations
    - Querying with error handling
    """
    
    def __init__(self, model_class: type[ModelType], db_session=None):
        """
        Initialize model repository
        
        Args:
            model_class: SQLAlchemy model class this repository manages
            db_session: Database session (optional)
        """
        super().__init__(db_session)
        self.model_class = model_class
    
    def create(self, **kwargs) -> ModelType: 
        """Create a new model instance"""
        def _create():
            instance = self.model_class(**kwargs)
            self.db_session.add(instance)
            return instance
        
        return self.safe_operation(_create, f"create {self.model_class.__name__}")
    
    def create_from_dict(self, data: dict) -> ModelType:
        """Create a new model instance from dictionary data"""
        return self.create(**data)
    
    def update(self, instance: ModelType, **kwargs) -> ModelType:
        """Update an existing model instance"""
        def _update():
            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            return instance
        
        return self.safe_operation(_update, f"update {self.model_class.__name__}")
    
    def update_from_dict(self, instance: ModelType, data: dict) -> ModelType:
        """Update an existing model instance from dictionary data"""
        return self.update(instance, **data)
    
    def bulk_create(self, data_list: list[dict]) -> list[ModelType]:
        """Create multiple instances from list of dictionaries"""
        def _bulk_create():
            instances = []
            for data in data_list:
                instance = self.model_class(**data)
                self.db_session.add(instance)
                instances.append(instance)
            return instances
        
        return self.safe_operation(_bulk_create, f"bulk_create {len(data_list)} {self.model_class.__name__}")
    
    def get_by_id(self, id_value: Any) -> Union[ModelType, None]:
        """Get instance by ID with error handling"""
        def _get_by_id():
            return self.db_session.get(self.model_class, id_value)
        
        return self.safe_query(_get_by_id, f"get {self.model_class.__name__} by id")
    
    def get_all(self) -> list[ModelType]:
        """Get all instances with error handling"""
        def _get_all():
            return self.db_session.execute(
                db.select(self.model_class)
            ).scalars().all()
        
        return self.safe_query(_get_all, f"get all {self.model_class.__name__}")
    
    def count(self) -> int:
        """Count all instances with error handling"""
        def _count():
            return self.model_class.query.count()
        
        return self.safe_query(_count, f"count {self.model_class.__name__}")
    
    def delete_all(self) -> None:
        """Delete all instances of this model"""
        def _delete_all():
            self.model_class.query.delete()
            self.logger.info(f"Deleted all {self.model_class.__name__} records")
        
        return self.safe_operation(_delete_all, f"delete all {self.model_class.__name__}")


class CacheableMixin:
    """
    Mixin for repositories that need caching functionality
    Useful for frequently accessed entities like Places
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache = {}
    
    def clear_cache(self):
        """Clear the internal cache"""
        self._cache.clear()
        self.logger.debug("Repository cache cleared")
    
    def get_from_cache(self, key: str):
        """Get item from cache"""
        return self._cache.get(key)
    
    def add_to_cache(self, key: str, value: Any):
        """Add item to cache"""
        self._cache[key] = value
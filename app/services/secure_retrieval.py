"""
Secure Retrieval Service with Role-Based Access Control
"""
import logging
from typing import List, Dict, Any, Optional
from app.services.hybrid_rag_service import HybridRAGService

logger = logging.getLogger(__name__)

class SecureRetrievalService:
    """Secure retrieval with role-based access control"""
    
    def __init__(self):
        self.hybrid_rag = HybridRAGService()
        self.role_hierarchy = {
            'student': 1,
            'teacher': 2,
            'admin': 3
        }
    
    async def secure_retrieve(
        self, 
        query: str, 
        user_role: str, 
        user_grade: Optional[int] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents with role-based access control
        """
        # Get all relevant documents
        all_results = await self.hybrid_rag.hybrid_search(query, top_k=100)
        
        # Filter by role and permissions
        authorized_results = []
        unauthorized_count = 0
        
        for doc in all_results:
            if self._is_authorized(doc, user_role, user_grade):
                authorized_results.append(doc)
            else:
                unauthorized_count += 1
        
        if unauthorized_count > 0:
            logger.info(
                f"Filtered {unauthorized_count} unauthorized documents "
                f"for role={user_role}, grade={user_grade}"
            )
        
        return authorized_results[:top_k]
    
    def _is_authorized(
        self, 
        document: Dict, 
        user_role: str, 
        user_grade: Optional[int] = None
    ) -> bool:
        """
        Check if user is authorized to access document
        """
        doc_metadata = document.get('metadata', {})
        
        # Check role requirement
        required_role = doc_metadata.get('required_role', 'student')
        user_role_level = self.role_hierarchy.get(user_role, 0)
        required_role_level = self.role_hierarchy.get(required_role, 0)
        
        if user_role_level < required_role_level:
            logger.debug(
                f"Access denied: user role {user_role} < required {required_role}"
            )
            return False
        
        # Check grade requirement
        if user_grade and 'min_grade' in doc_metadata:
            if user_grade < doc_metadata['min_grade']:
                logger.debug(
                    f"Access denied: user grade {user_grade} < "
                    f"required {doc_metadata['min_grade']}"
                )
                return False
        
        if user_grade and 'max_grade' in doc_metadata:
            if user_grade > doc_metadata['max_grade']:
                logger.debug(
                    f"Access denied: user grade {user_grade} > "
                    f"max {doc_metadata['max_grade']}"
                )
                return False
        
        # Check content type restrictions
        content_type = doc_metadata.get('content_type', 'general')
        
        # Solutions only for teachers
        if content_type == 'solution' and user_role == 'student':
            logger.debug("Access denied: solutions restricted to teachers")
            return False
        
        # Answer keys only for teachers
        if content_type == 'answer_key' and user_role == 'student':
            logger.debug("Access denied: answer keys restricted to teachers")
            return False
        
        # Teacher resources only for teachers
        if content_type == 'teacher_resource' and user_role == 'student':
            logger.debug("Access denied: teacher resources restricted")
            return False
        
        return True
    
    async def log_access_attempt(
        self, 
        user_id: str, 
        user_role: str, 
        document_id: str, 
        authorized: bool
    ):
        """
        Log access attempts for security auditing
        """
        log_entry = {
            "user_id": user_id,
            "user_role": user_role,
            "document_id": document_id,
            "authorized": authorized,
            "timestamp": "utcnow"
        }
        
        if not authorized:
            logger.warning(f"Unauthorized access attempt: {log_entry}")
        else:
            logger.info(f"Authorized access: {log_entry}")
    
    def get_accessible_content_types(self, user_role: str) -> List[str]:
        """
        Get list of content types accessible to user role
        """
        content_types = {
            'student': ['general', 'lesson', 'example', 'practice'],
            'teacher': ['general', 'lesson', 'example', 'practice', 
                       'solution', 'answer_key', 'teacher_resource'],
            'admin': ['general', 'lesson', 'example', 'practice', 
                     'solution', 'answer_key', 'teacher_resource', 'admin']
        }
        
        return content_types.get(user_role, ['general'])

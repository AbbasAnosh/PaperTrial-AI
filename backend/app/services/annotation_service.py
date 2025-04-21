from datetime import datetime
from typing import List, Optional, Dict, Any
from app.models.annotation import (
    Annotation, AnnotationCreate, AnnotationUpdate,
    Comment, CommentCreate, CommentUpdate,
    AnnotationType, AnnotationStatus
)
from app.core.supabase import supabase_client
from app.core.errors import NotFoundError, ValidationError

class AnnotationService:
    """Service for managing annotations and comments"""
    
    def __init__(self):
        self.annotation_table = "annotations"
        self.comment_table = "comments"
    
    async def create_annotation(
        self,
        workspace_id: str,
        user_id: str,
        annotation_data: AnnotationCreate
    ) -> Annotation:
        """Create a new annotation"""
        try:
            annotation = Annotation(
                workspace_id=workspace_id,
                user_id=user_id,
                **annotation_data.dict()
            )
            
            result = await supabase_client.table(self.annotation_table).insert(
                annotation.dict()
            ).execute()
            
            return Annotation(**result.data[0])
        except Exception as e:
            raise ValidationError(f"Error creating annotation: {str(e)}")
    
    async def get_annotation(self, annotation_id: str) -> Annotation:
        """Get annotation by ID"""
        try:
            result = await supabase_client.table(self.annotation_table)\
                .select("*")\
                .eq("id", annotation_id)\
                .execute()
            
            if not result.data:
                raise NotFoundError(f"Annotation {annotation_id} not found")
            
            return Annotation(**result.data[0])
        except Exception as e:
            raise ValidationError(f"Error getting annotation: {str(e)}")
    
    async def update_annotation(
        self,
        annotation_id: str,
        update_data: AnnotationUpdate
    ) -> Annotation:
        """Update annotation"""
        try:
            update_dict = update_data.dict(exclude_unset=True)
            update_dict["updated_at"] = datetime.utcnow()
            
            result = await supabase_client.table(self.annotation_table)\
                .update(update_dict)\
                .eq("id", annotation_id)\
                .execute()
            
            return Annotation(**result.data[0])
        except Exception as e:
            raise ValidationError(f"Error updating annotation: {str(e)}")
    
    async def resolve_annotation(
        self,
        annotation_id: str,
        user_id: str,
        status: AnnotationStatus
    ) -> Annotation:
        """Resolve an annotation"""
        try:
            update_dict = {
                "status": status,
                "resolved_at": datetime.utcnow(),
                "resolved_by": user_id,
                "updated_at": datetime.utcnow()
            }
            
            result = await supabase_client.table(self.annotation_table)\
                .update(update_dict)\
                .eq("id", annotation_id)\
                .execute()
            
            return Annotation(**result.data[0])
        except Exception as e:
            raise ValidationError(f"Error resolving annotation: {str(e)}")
    
    async def get_file_annotations(
        self,
        workspace_id: str,
        file_id: str,
        status: Optional[AnnotationStatus] = None
    ) -> List[Annotation]:
        """Get annotations for a file"""
        try:
            query = supabase_client.table(self.annotation_table)\
                .select("*")\
                .eq("workspace_id", workspace_id)\
                .eq("file_id", file_id)
            
            if status:
                query = query.eq("status", status)
            
            result = await query.execute()
            return [Annotation(**annotation) for annotation in result.data]
        except Exception as e:
            raise ValidationError(f"Error getting file annotations: {str(e)}")
    
    async def create_comment(
        self,
        workspace_id: str,
        user_id: str,
        comment_data: CommentCreate
    ) -> Comment:
        """Create a new comment"""
        try:
            comment = Comment(
                workspace_id=workspace_id,
                user_id=user_id,
                **comment_data.dict()
            )
            
            result = await supabase_client.table(self.comment_table).insert(
                comment.dict()
            ).execute()
            
            return Comment(**result.data[0])
        except Exception as e:
            raise ValidationError(f"Error creating comment: {str(e)}")
    
    async def get_comment(self, comment_id: str) -> Comment:
        """Get comment by ID"""
        try:
            result = await supabase_client.table(self.comment_table)\
                .select("*")\
                .eq("id", comment_id)\
                .execute()
            
            if not result.data:
                raise NotFoundError(f"Comment {comment_id} not found")
            
            return Comment(**result.data[0])
        except Exception as e:
            raise ValidationError(f"Error getting comment: {str(e)}")
    
    async def update_comment(
        self,
        comment_id: str,
        update_data: CommentUpdate
    ) -> Comment:
        """Update comment"""
        try:
            update_dict = update_data.dict(exclude_unset=True)
            update_dict["updated_at"] = datetime.utcnow()
            
            result = await supabase_client.table(self.comment_table)\
                .update(update_dict)\
                .eq("id", comment_id)\
                .execute()
            
            return Comment(**result.data[0])
        except Exception as e:
            raise ValidationError(f"Error updating comment: {str(e)}")
    
    async def resolve_comment(
        self,
        comment_id: str,
        user_id: str
    ) -> Comment:
        """Resolve a comment"""
        try:
            update_dict = {
                "is_resolved": True,
                "resolved_at": datetime.utcnow(),
                "resolved_by": user_id,
                "updated_at": datetime.utcnow()
            }
            
            result = await supabase_client.table(self.comment_table)\
                .update(update_dict)\
                .eq("id", comment_id)\
                .execute()
            
            return Comment(**result.data[0])
        except Exception as e:
            raise ValidationError(f"Error resolving comment: {str(e)}")
    
    async def get_file_comments(
        self,
        workspace_id: str,
        file_id: str,
        include_resolved: bool = False
    ) -> List[Comment]:
        """Get comments for a file"""
        try:
            query = supabase_client.table(self.comment_table)\
                .select("*")\
                .eq("workspace_id", workspace_id)\
                .eq("file_id", file_id)
            
            if not include_resolved:
                query = query.eq("is_resolved", False)
            
            result = await query.execute()
            return [Comment(**comment) for comment in result.data]
        except Exception as e:
            raise ValidationError(f"Error getting file comments: {str(e)}")
    
    async def get_comment_thread(
        self,
        comment_id: str
    ) -> List[Comment]:
        """Get a comment thread (parent and replies)"""
        try:
            # Get parent comment
            parent = await self.get_comment(comment_id)
            
            # Get replies
            result = await supabase_client.table(self.comment_table)\
                .select("*")\
                .eq("parent_id", comment_id)\
                .order("created_at")\
                .execute()
            
            replies = [Comment(**comment) for comment in result.data]
            
            return [parent] + replies
        except Exception as e:
            raise ValidationError(f"Error getting comment thread: {str(e)}") 
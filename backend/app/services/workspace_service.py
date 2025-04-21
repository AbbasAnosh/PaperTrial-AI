from datetime import datetime
from typing import List, Optional, Dict, Any
from app.models.workspace import (
    Workspace, WorkspaceCreate, WorkspaceUpdate,
    WorkspaceMember, WorkspaceInvite, WorkspaceInviteCreate,
    WorkspaceRole
)
from app.core.supabase import supabase_client
from app.core.errors import NotFoundError, ValidationError

class WorkspaceService:
    """Service for managing workspaces and collaboration"""
    
    def __init__(self):
        self.workspace_table = "workspaces"
        self.member_table = "workspace_members"
        self.invite_table = "workspace_invites"
    
    async def create_workspace(
        self,
        user_id: str,
        workspace_data: WorkspaceCreate
    ) -> Workspace:
        """Create a new workspace"""
        try:
            workspace = Workspace(
                created_by=user_id,
                **workspace_data.dict()
            )
            
            result = await supabase_client.table(self.workspace_table).insert(
                workspace.dict()
            ).execute()
            
            # Add creator as owner
            await self.add_member(
                result.data[0]["id"],
                user_id,
                WorkspaceRole.OWNER
            )
            
            return Workspace(**result.data[0])
        except Exception as e:
            raise ValidationError(f"Error creating workspace: {str(e)}")
    
    async def get_workspace(self, workspace_id: str) -> Workspace:
        """Get workspace by ID"""
        try:
            result = await supabase_client.table(self.workspace_table)\
                .select("*")\
                .eq("id", workspace_id)\
                .execute()
            
            if not result.data:
                raise NotFoundError(f"Workspace {workspace_id} not found")
            
            return Workspace(**result.data[0])
        except Exception as e:
            raise ValidationError(f"Error getting workspace: {str(e)}")
    
    async def update_workspace(
        self,
        workspace_id: str,
        update_data: WorkspaceUpdate
    ) -> Workspace:
        """Update workspace"""
        try:
            update_dict = update_data.dict(exclude_unset=True)
            update_dict["updated_at"] = datetime.utcnow()
            
            result = await supabase_client.table(self.workspace_table)\
                .update(update_dict)\
                .eq("id", workspace_id)\
                .execute()
            
            return Workspace(**result.data[0])
        except Exception as e:
            raise ValidationError(f"Error updating workspace: {str(e)}")
    
    async def add_member(
        self,
        workspace_id: str,
        user_id: str,
        role: WorkspaceRole
    ) -> WorkspaceMember:
        """Add a member to the workspace"""
        try:
            member = WorkspaceMember(
                workspace_id=workspace_id,
                user_id=user_id,
                role=role
            )
            
            result = await supabase_client.table(self.member_table).insert(
                member.dict()
            ).execute()
            
            return WorkspaceMember(**result.data[0])
        except Exception as e:
            raise ValidationError(f"Error adding member: {str(e)}")
    
    async def get_member(
        self,
        workspace_id: str,
        user_id: str
    ) -> WorkspaceMember:
        """Get workspace member"""
        try:
            result = await supabase_client.table(self.member_table)\
                .select("*")\
                .eq("workspace_id", workspace_id)\
                .eq("user_id", user_id)\
                .execute()
            
            if not result.data:
                raise NotFoundError(f"Member not found in workspace {workspace_id}")
            
            return WorkspaceMember(**result.data[0])
        except Exception as e:
            raise ValidationError(f"Error getting member: {str(e)}")
    
    async def update_member_role(
        self,
        workspace_id: str,
        user_id: str,
        new_role: WorkspaceRole
    ) -> WorkspaceMember:
        """Update member role"""
        try:
            result = await supabase_client.table(self.member_table)\
                .update({"role": new_role})\
                .eq("workspace_id", workspace_id)\
                .eq("user_id", user_id)\
                .execute()
            
            return WorkspaceMember(**result.data[0])
        except Exception as e:
            raise ValidationError(f"Error updating member role: {str(e)}")
    
    async def remove_member(
        self,
        workspace_id: str,
        user_id: str
    ) -> None:
        """Remove a member from the workspace"""
        try:
            await supabase_client.table(self.member_table)\
                .delete()\
                .eq("workspace_id", workspace_id)\
                .eq("user_id", user_id)\
                .execute()
        except Exception as e:
            raise ValidationError(f"Error removing member: {str(e)}")
    
    async def create_invite(
        self,
        workspace_id: str,
        user_id: str,
        invite_data: WorkspaceInviteCreate
    ) -> WorkspaceInvite:
        """Create a workspace invite"""
        try:
            invite = WorkspaceInvite(
                workspace_id=workspace_id,
                invited_by=user_id,
                **invite_data.dict()
            )
            
            result = await supabase_client.table(self.invite_table).insert(
                invite.dict()
            ).execute()
            
            return WorkspaceInvite(**result.data[0])
        except Exception as e:
            raise ValidationError(f"Error creating invite: {str(e)}")
    
    async def accept_invite(
        self,
        invite_id: str,
        user_id: str
    ) -> WorkspaceMember:
        """Accept a workspace invite"""
        try:
            # Get invite
            result = await supabase_client.table(self.invite_table)\
                .select("*")\
                .eq("id", invite_id)\
                .execute()
            
            if not result.data:
                raise NotFoundError(f"Invite {invite_id} not found")
            
            invite = WorkspaceInvite(**result.data[0])
            
            # Check if invite is valid
            if invite.status != "pending" or invite.expires_at < datetime.utcnow():
                raise ValidationError("Invite is no longer valid")
            
            # Add member
            member = await self.add_member(
                invite.workspace_id,
                user_id,
                invite.role
            )
            
            # Update invite status
            await supabase_client.table(self.invite_table)\
                .update({"status": "accepted"})\
                .eq("id", invite_id)\
                .execute()
            
            return member
        except Exception as e:
            raise ValidationError(f"Error accepting invite: {str(e)}")
    
    async def get_workspace_members(
        self,
        workspace_id: str
    ) -> List[WorkspaceMember]:
        """Get all members of a workspace"""
        try:
            result = await supabase_client.table(self.member_table)\
                .select("*")\
                .eq("workspace_id", workspace_id)\
                .execute()
            
            return [WorkspaceMember(**member) for member in result.data]
        except Exception as e:
            raise ValidationError(f"Error getting workspace members: {str(e)}")
    
    async def get_user_workspaces(
        self,
        user_id: str
    ) -> List[Workspace]:
        """Get all workspaces for a user"""
        try:
            # Get workspace IDs from memberships
            member_result = await supabase_client.table(self.member_table)\
                .select("workspace_id")\
                .eq("user_id", user_id)\
                .execute()
            
            workspace_ids = [member["workspace_id"] for member in member_result.data]
            
            if not workspace_ids:
                return []
            
            # Get workspace details
            workspace_result = await supabase_client.table(self.workspace_table)\
                .select("*")\
                .in_("id", workspace_ids)\
                .execute()
            
            return [Workspace(**workspace) for workspace in workspace_result.data]
        except Exception as e:
            raise ValidationError(f"Error getting user workspaces: {str(e)}")
    
    async def update_member_activity(
        self,
        workspace_id: str,
        user_id: str
    ) -> None:
        """Update member's last active timestamp"""
        try:
            await supabase_client.table(self.member_table)\
                .update({"last_active": datetime.utcnow()})\
                .eq("workspace_id", workspace_id)\
                .eq("user_id", user_id)\
                .execute()
        except Exception as e:
            raise ValidationError(f"Error updating member activity: {str(e)}") 
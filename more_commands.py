from asyncio import tasks
import logging
import discord
from discord.ui import Button, View, Modal, TextInput
from data_manager import get_user_rubles, server_data, save_data, get_user_data, update_rubles
from discord.ext import commands
import random
import asyncio
from typing import Optional
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta
from discord.ui import Select, View
import json
from pathlib import Path
from discord import Embed, Color, Guild, Interaction
from typing import List, Dict, Any


logger = logging.getLogger(__name__)

class ResetCommandError(Exception):
    """Custom exception for reset command-related errors."""
    pass

class ResetView(View):
    def __init__(self, target_user: discord.User, admin_user: discord.User):
        super().__init__(timeout=30)
        self.target_user = target_user
        self.admin_user = admin_user
        
        confirm_button = Button(style=discord.ButtonStyle.danger, label="Yes", custom_id="confirm")
        cancel_button = Button(style=discord.ButtonStyle.secondary, label="No", custom_id="cancel")
        
        confirm_button.callback = self.confirm_callback
        cancel_button.callback = self.cancel_callback
        
        self.add_item(confirm_button)
        self.add_item(cancel_button)

    async def confirm_callback(self, interaction: discord.Interaction):
        # Check if button clicker is the admin who initiated
        if interaction.user.id != self.admin_user.id:
            await interaction.response.send_message("Only the admin who initiated this reset can confirm it.", ephemeral=True)
            return
            
        try:
            server_id = str(interaction.guild_id)
            user_id = str(self.target_user.id)
            
            server_data[server_id][user_id] = {
                "level": 0,
                "exp": 0,
                "currency": 0,
                "background_url": None,
                "daily_msg": 0,
                "weekly_msg": 0,
                "completed_daily": [],
                "completed_weekly": False,
                "last_spin": None
            }
            save_data(server_data)
            
            embed = discord.Embed(
                title="<:PepeHehe:1347125572865626122> User Data Reset",
                description=f"All data for {self.target_user.mention} has been reset.",
                color=discord.Color.from_rgb(139, 0, 0)
            )
            logger.info(f"User {self.target_user.id}'s data has been reset by admin {interaction.user.id}")
            
        except Exception as e:
            logger.error(f"Error during reset confirmation: {e}")
            embed = discord.Embed(
                title="<a:Animated_Cross:1344705833627549748> Error",
                description="An error occurred while resetting user data.",
                color=discord.Color.red()
            )
            
        await interaction.response.edit_message(embed=embed, view=None)

    async def cancel_callback(self, interaction: discord.Interaction):
        # Check if button clicker is the admin who initiated
        if interaction.user.id != self.admin_user.id:
            await interaction.response.send_message("Only the admin who initiated this reset can cancel it.", ephemeral=True)
            return
            
        embed = discord.Embed(
            title="<a:Animated_Cross:1344705833627549748> Reset Cancelled",
            description="The reset operation has been cancelled.",
            color=discord.Color.from_rgb(139, 0, 0)
        )
        await interaction.response.edit_message(embed=embed, view=None)

async def reset_command(ctx, user: discord.User, client):
    """
    Handle the admin reset command with robust error handling.
    
    Args:
        ctx (discord.Context): The context of the command invocation
        user (discord.User): The user whose data will be reset
        client (discord.Client): The Discord bot client
    
    Raises:
        ResetCommandError: For various potential error scenarios
    """
    try:
        if not ctx or not ctx.guild or not ctx.author:
            raise ResetCommandError("Invalid command context")

        # Check for admin permissions
        if not ctx.author.guild_permissions.administrator:
            await ctx.send(embed=discord.Embed(
                title="<a:Animated_Cross:1344705833627549748> Permission Denied",
                description="You need administrator permissions to use this command.",
                color=discord.Color.red()
            ))
            return

        embed = discord.Embed(
            title="⚠️ Reset User Data",
            description=(
                f"Are you sure you want to reset all data for {user.mention}?\n"
                "This action cannot be undone."
            ),
            color=discord.Color.from_rgb(139, 0, 0)
        )
        
        view = ResetView(user, ctx.author)  # Pass the admin user to the view
        await ctx.send(embed=embed, view=view)
        
    except ResetCommandError as reset_error:
        await ctx.send(f"<a:Animated_Cross:1344705833627549748> Reset Error: {reset_error}")
        logger.error(f"Reset command error: {reset_error}")
    except Exception as unexpected_error:
        await ctx.send("An unexpected error occurred. Please try again later.")
        logger.error(f"Unexpected reset error: {unexpected_error}", exc_info=True)
        
#---------------------------------------------------#------------------------------------------------#-------------------------------------------
#MORE COMMANDS FROM HERE:-



class ProfileTransferCommandError(Exception):
    """Custom exception for profile transfer command-related errors."""
    pass

class ProfileTransferView(View):
    def __init__(self, sender: discord.User, receiver: discord.User, admin: discord.User):
        super().__init__(timeout=30)
        self.sender = sender
        self.receiver = receiver
        self.admin = admin
        
        confirm_button = discord.ui.Button(style=discord.ButtonStyle.danger, label="Yes", custom_id="confirm")
        cancel_button = discord.ui.Button(style=discord.ButtonStyle.secondary, label="No", custom_id="cancel")
        
        confirm_button.callback = self.confirm_callback
        cancel_button.callback = self.cancel_callback
        
        self.add_item(confirm_button)
        self.add_item(cancel_button)

    async def confirm_callback(self, interaction: discord.Interaction):
        # Verify admin permissions
        if not interaction.user.guild_permissions.administrator:
            embed = discord.Embed(
                title="<a:Animated_Cross:1344705833627549748> Permission Denied",
                description="You need administrator permissions to confirm this transfer.",
                color=discord.Color.red()
            )
            await interaction.response.edit_message(embed=embed, view=None)
            return

        # Verify it's the same admin who initiated
        if interaction.user.id != self.admin.id:
            embed = discord.Embed(
                title="<a:Animated_Cross:1344705833627549748> Permission Denied", 
                description="Only the admin who initiated this transfer can confirm it.",
                color=discord.Color.red()
            )
            await interaction.response.edit_message(embed=embed, view=None)
            return

        try:
            server_id = str(interaction.guild_id)
            sender_id = str(self.sender.id)
            receiver_id = str(self.receiver.id)
            
            if sender_id not in server_data.get(server_id, {}):
                embed = discord.Embed(
                    title="<a:Animated_Cross:1344705833627549748> Error",
                    description=f"No data found for {self.sender.mention}.",
                    color=discord.Color.red()
                )
                await interaction.response.edit_message(embed=embed, view=None)
                return
            
            if receiver_id in server_data.get(server_id, {}):
                embed = discord.Embed(
                    title="<a:Animated_Cross:1344705833627549748> Error",
                    description=f"{self.receiver.mention} already has existing data. Transfer aborted.",
                    color=discord.Color.red()
                )
                await interaction.response.edit_message(embed=embed, view=None)
                return

            server_data.setdefault(server_id, {})[receiver_id] = server_data[server_id].pop(sender_id)
            save_data(server_data)
            
            embed = discord.Embed(
                title="<:PepeHehe:1347125572865626122> Profile Transfer Successful",
                description=f"All data has been transferred from {self.sender.mention} to {self.receiver.mention}.",
                color=discord.Color.from_rgb(0, 0, 139)
            )
            
            logger.info(f"User data transferred from {sender_id} to {receiver_id} by admin {interaction.user.id}")
            await interaction.response.edit_message(embed=embed, view=None)

        except Exception as e:
            logger.error(f"Error during profile transfer: {e}", exc_info=True)
            embed = discord.Embed(
                title="<a:Animated_Cross:1344705833627549748> Error",
                description="An error occurred while transferring user data.",
                color=discord.Color.red()
            )
            await interaction.response.edit_message(embed=embed, view=None)

    async def cancel_callback(self, interaction: discord.Interaction):
        # Verify admin permissions
        if not interaction.user.guild_permissions.administrator:
            embed = discord.Embed(
                title="<a:Animated_Cross:1344705833627549748> Permission Denied",
                description="You need administrator permissions to cancel this transfer.",
                color=discord.Color.red()
            )
            await interaction.response.edit_message(embed=embed, view=None)
            return

        # Verify it's the same admin who initiated
        if interaction.user.id != self.admin.id:
            embed = discord.Embed(
                title="<a:Animated_Cross:1344705833627549748> Permission Denied",
                description="Only the admin who initiated this transfer can cancel it.",
                color=discord.Color.red()
            )
            await interaction.response.edit_message(embed=embed, view=None)
            return

        embed = discord.Embed(
            title="<a:Animated_Cross:1344705833627549748> Transfer Cancelled",
            description="The profile transfer operation has been cancelled.",
            color=discord.Color.from_rgb(139, 0, 0)
        )
        await interaction.response.edit_message(embed=embed, view=None)

async def profile_transfer_command(ctx, sender: discord.User, receiver: discord.User, client):
    """
    Handle the admin profile transfer command with robust error handling.
    
    Args:
        ctx (discord.Context): The context of the command invocation
        sender (discord.User): The user whose data will be transferred
        receiver (discord.User): The user who will receive the data
        client (discord.Client): The Discord bot client
    
    Raises:
        ProfileTransferCommandError: For various potential error scenarios
    """
    try:
        if not ctx or not ctx.guild or not ctx.author:
            raise ProfileTransferCommandError("Invalid command context")

        if not ctx.author.guild_permissions.administrator:
            await ctx.send(embed=discord.Embed(
                title="<a:Animated_Cross:1344705833627549748> Permission Denied",
                description="You need administrator permissions to use this command.",
                color=discord.Color.red()
            ))
            return

        # Prevent transfer to same user
        if sender.id == receiver.id:
            await ctx.send(embed=discord.Embed(
                title="<a:Animated_Cross:1344705833627549748> Invalid Transfer",
                description="You cannot transfer data to the same user.",
                color=discord.Color.red()
            ))
            return

        embed = discord.Embed(
            title="⚠️ Transfer User Profile",
            description=(
                f"Are you sure you want to transfer all data from {sender.mention} "
                f"to {receiver.mention}?\n"
                "This action cannot be undone."
            ),
            color=discord.Color.from_rgb(139, 0, 0)
        )
        
        view = ProfileTransferView(sender, receiver, ctx.author)  # Pass the admin user to the view
        await ctx.send(embed=embed, view=view)
        
    except ProfileTransferCommandError as transfer_error:
        await ctx.send(f"<a:Animated_Cross:1344705833627549748> Transfer Error: {transfer_error}")
        logger.error(f"Profile transfer command error: {transfer_error}")
    except Exception as unexpected_error:
        await ctx.send("An unexpected error occurred. Please try again later.")
        logger.error(f"Unexpected profile transfer error: {unexpected_error}", exc_info=True)

#--------------------------------------#----------------------------------------#---------------------------------------#------------------



BOT_PERMISSIONS = discord.Permissions(
    manage_roles=True,
    send_messages=True,
    use_external_emojis=True,
    view_channel=True,
    embed_links=True,
    read_messages=True,
    read_message_history=True,
    manage_channels=True  # Added for creating admin channel if needed
)

class RoleApprovalView(discord.ui.View):
    def __init__(self, user: discord.Member, role_name: str, role_color: discord.Color, role_icon: Optional[discord.PartialEmoji] = None):
        super().__init__(timeout=600)  # 10 minute timeout
        self.user = user
        self.role_name = role_name
        self.role_color = role_color
        self.role_icon = role_icon
        self.guild = user.guild  # Store guild from member object
        
    async def send_admin_notification(self, interaction: discord.Interaction):
        """Send role approval request to administrators"""
        try:
            # Find or create admin channel
            admin_channel = await self._get_or_create_admin_channel(interaction)
            if not admin_channel:
                await self._handle_notification_failure(interaction)
                return

            embed = discord.Embed(
                title="🔔 Role Creation Approval Request",
                description=(
                    f"Booster {self.user.mention} wants to create a role:\n"
                    f"**Name:** {self.role_name}\n"
                    f"**Color:** {self.role_color}"
                ),
                color=discord.Color.blue()
            )
            
            admin_view = AdminActionView(self.user, self.role_name, self.role_color, self.role_icon)
            await admin_channel.send(embed=embed, view=admin_view)
            
            await interaction.followup.send(
                embed=discord.Embed(
                    title="<a:animated_tick:1344705804007112724> Request Sent",
                    description="Your role request has been sent for approval.",
                    color=discord.Color.green()
                )
            )
            
        except Exception as e:
            logger.error(f"Error in send_admin_notification: {e}")
            await self._handle_notification_failure(interaction)

    async def _get_or_create_admin_channel(self, interaction: discord.Interaction) -> Optional[discord.TextChannel]:
        """Find existing admin channel or create a new one"""
        # Try to find existing channel
        admin_channel = discord.utils.get(self.guild.channels, name="admin-notifications")
        if admin_channel:
            return admin_channel

        # Create new channel if we have permissions
        try:
            if self.guild.me.guild_permissions.manage_channels:
                admin_roles = [role for role in self.guild.roles if role.permissions.administrator]
                overwrites = {
                    self.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    self.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                }
                for role in admin_roles:
                    overwrites[role] = discord.PermissionOverwrite(read_messages=True)
                
                return await self.guild.create_text_channel(
                    'admin-notifications',
                    overwrites=overwrites,
                    reason="Created for role approval notifications"
                )
        except Exception as e:
            logger.error(f"Failed to create admin channel: {e}")
        return None

    async def _handle_notification_failure(self, interaction: discord.Interaction):
        """Handle cases where notification cannot be sent"""
        await interaction.followup.send(
            embed=discord.Embed(
                title="⚠️ Notification Error",
                description=(
                    "Unable to send notifications to administrators. Please:\n"
                    "1. Create an #admin-notifications channel, or\n"
                    "2. Ensure the bot has proper permissions"
                ),
                color=discord.Color.red()
            )
        )

class AdminActionView(discord.ui.View):
    def __init__(self, user: discord.Member, role_name: str, role_color: discord.Color, role_icon: Optional[discord.PartialEmoji] = None):
        super().__init__(timeout=600)
        self.user = user
        self.role_name = role_name
        self.role_color = role_color
        self.role_icon = role_icon

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle role approval"""
        try:
            # Verify admin permissions
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("You need administrator permissions for this action.", ephemeral=True)
                return

            # Create and assign role
            role = await self._create_role(interaction)
            if not role:
                return

            # Attempt to assign role to user
            success = await self._assign_role(role)
            if not success:
                await interaction.response.send_message("Role created but couldn't be assigned.", ephemeral=True)
                return

            # Update UI and notify user
            await self._handle_success(interaction, role)
            
        except Exception as e:
            logger.error(f"Error in accept_button: {e}")
            await interaction.response.send_message("An error occurred while processing the request.", ephemeral=True)

    async def _create_role(self, interaction: discord.Interaction) -> Optional[discord.Role]:
        """Create the requested role"""
        try:
            role = await interaction.guild.create_role(
                name=self.role_name,
                color=self.role_color,
                reason=f"Custom role for booster {self.user.name}",
                permissions=discord.Permissions.none()
            )
            
            if self.role_icon:
                try:
                    await role.edit(display_icon=self.role_icon)
                except Exception as e:
                    logger.warning(f"Failed to set role icon: {e}")
            
            return role
            
        except discord.Forbidden:
            await interaction.response.send_message("Missing permissions to create roles.", ephemeral=True)
        except Exception as e:
            logger.error(f"Role creation error: {e}")
            await interaction.response.send_message("Failed to create role.", ephemeral=True)
        return None

    async def _assign_role(self, role: discord.Role) -> bool:
        """Assign the role to the user"""
        try:
            await self.user.add_roles(role)
            return True
        except Exception as e:
            logger.error(f"Role assignment error: {e}")
            return False

    async def _handle_success(self, interaction: discord.Interaction, role: discord.Role):
        """Handle successful role creation and assignment"""
        try:
            # Update interaction message
            await interaction.response.edit_message(
                embed=discord.Embed(
                    title="<a:animated_tick:1344705804007112724> Role Request Approved",
                    description=f"Role for {self.user.mention} has been created and assigned.",
                    color=discord.Color.green()
                ),
                view=None
            )
            
            # Try to notify user
            try:
                await self.user.send(
                    embed=discord.Embed(
                        title="<a:animated_tick:1344705804007112724> Role Approved",
                        description=f"Your role {role.mention} has been approved and created!",
                        color=discord.Color.green()
                    )
                )
            except discord.Forbidden:
                logger.warning(f"Cannot send DM to user {self.user.id}")
                
        except Exception as e:
            logger.error(f"Error in _handle_success: {e}")

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red)
    async def deny_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle role denial"""
        try:
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("You need administrator permissions for this action.", ephemeral=True)
                return

            await interaction.response.edit_message(
                embed=discord.Embed(
                    title="<a:Animated_Cross:1344705833627549748> Role Request Denied",
                    description=f"Role request from {self.user.mention} has been denied.",
                    color=discord.Color.red()
                ),
                view=None
            )
            
            try:
                await self.user.send(
                    embed=discord.Embed(
                        title="<a:Animated_Cross:1344705833627549748> Role Denied",
                        description="Your role request has been denied by an administrator.",
                        color=discord.Color.red()
                    )
                )
            except discord.Forbidden:
                logger.warning(f"Cannot send denial DM to user {self.user.id}")
                
        except Exception as e:
            logger.error(f"Error in deny_button: {e}")
            await interaction.response.send_message("An error occurred while processing the denial.", ephemeral=True)

class RoleManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="role")
    @commands.guild_only()
    async def role_command(self, ctx: commands.Context, role_name: str = None, role_color: str = None, 
                          role_icon: Optional[discord.PartialEmoji] = None):
        """Create a custom role (Booster only)"""
        try:
            # Validate basic requirements
            if not await self._validate_requirements(ctx, role_name):
                return

            # Parse color
            try:
                color = discord.Color.from_str(role_color) if role_color else discord.Color.blue()
            except ValueError:
                await ctx.send(
                    embed=discord.Embed(
                        title="ℹ️ Invalid Color",
                        description="Invalid color format. Using default blue color instead.",
                        color=discord.Color.blue()
                    )
                )
                color = discord.Color.blue()

            # Create and send approval request
            approval_view = RoleApprovalView(ctx.author, role_name, color, role_icon)
            
            await ctx.send(
                embed=discord.Embed(
                    title="🎨 Role Creation Request",
                    description="Your role creation request has been sent to administrators for approval.",
                    color=discord.Color.blue()
                )
            )
            
            await approval_view.send_admin_notification(ctx)

        except Exception as e:
            logger.error(f"Unexpected error in role command: {e}")
            await ctx.send(
                embed=discord.Embed(
                    title="⚠️ Error",
                    description="An unexpected error occurred. Please try again later.",
                    color=discord.Color.red()
                )
            )

    async def _validate_requirements(self, ctx: commands.Context, role_name: str) -> bool:
        """Validate command requirements"""
        # Check bot permissions
        missing_perms = self._check_missing_permissions(ctx.guild.me)
        if missing_perms:
            missing_perms_text = "\n".join([f"• {perm}" for perm in missing_perms])
            description = f"Bot is missing permissions:\n{missing_perms_text}"

            embed = discord.Embed(
            title="⚠️ Missing Permissions",
            description=description,
            color=discord.Color.red()
        )

        await ctx.send(embed=embed)
        return False

        # Check role hierarchy
        if ctx.guild.me.top_role.position <= max(r.position for r in ctx.guild.roles):
            await ctx.send(
                embed=discord.Embed(
                    title="⚠️ Role Hierarchy Issue",
                    description=f"Bot's highest role ({ctx.guild.me.top_role.name}) must be higher in the hierarchy.",
                    color=discord.Color.red()
                )
            )
            return False

        # Check if user is a booster
        if not ctx.author.premium_since:
            await ctx.send(
                embed=discord.Embed(
                    title="⚠️ Booster Only",
                    description="This command is only available for server boosters!",
                    color=discord.Color.red()
                )
            )
            return False

        # Validate role name
        if not role_name:
            await ctx.send(
                embed=discord.Embed(
                    title="ℹ️ Missing Role Name",
                    description="Please provide a name for your custom role.",
                    color=discord.Color.blue()
                )
            )
            return False

        return True

    def _check_missing_permissions(self, member: discord.Member) -> list:
        """Check for missing bot permissions"""
        required_perms = {
            'manage_roles': 'Manage Roles',
            'send_messages': 'Send Messages',
            'embed_links': 'Embed Links',
            'use_external_emojis': 'Use External Emojis',
            'manage_channels': 'Manage Channels'
        }
        
        return [name for perm, name in required_perms.items() 
                if not getattr(member.guild_permissions, perm)]


#-----------------------------------------#---------------------------------------#---------------------------------------------


class CardDropView(discord.ui.View):
    def __init__(self, card_data: dict):
        super().__init__(timeout=60)  # 60 second timeout
        self.card_data = card_data
        self.claimed_by = None
        
        # Add claim button
        claim_button = discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label="Claim Card!",
            emoji="⭐",
            custom_id="claim_card"
        )
        claim_button.callback = self.claim_callback
        self.add_item(claim_button)

    async def claim_callback(self, interaction: discord.Interaction):
        if self.claimed_by:
            await interaction.response.send_message(
                "This card has already been claimed!", 
                ephemeral=True
            )
            return

        self.claimed_by = interaction.user
        
        # Create claimed embed
        claimed_embed = discord.Embed(
            title=f"🎉 Card Claimed!",
            description=f"{interaction.user.mention} claimed the {self.card_data['name']}!",
            color=discord.Color.green()
        )
        claimed_embed.set_image(url=self.card_data['image'])
        claimed_embed.add_field(
            name="Rarity", 
            value=self.card_data['rarity']
        )
        if 'description' in self.card_data:
            claimed_embed.add_field(
                name="Description", 
                value=self.card_data['description'], 
                inline=False
            )

        # Disable the claim button
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            embed=claimed_embed,
            view=self
        )

# Define card data
GENSHIN_CARDS = [
    {
        "name": "Raiden Shogun",
        "image": "https://rerollcdn.com/GENSHIN/Characters/Raiden_Shogun.png",
        "rarity": "⭐⭐⭐⭐⭐",
        "description": "The Raiden Shogun is the awesome vessel of Beelzebul, the current Electro Archon of Inazuma."
    },
    {
        "name": "Primordial Jade Winged-Spear",
        "image": "https://rerollcdn.com/GENSHIN/Weapons/Primordial_Jade_Winged-Spear.png",
        "rarity": "⭐⭐⭐⭐⭐",
        "description": "A legendary spear made from pure jade, capable of piercing through dragons' scales."
    },
    {
        "name": "Nahida",
        "image": "https://rerollcdn.com/GENSHIN/Characters/Nahida.png",
        "rarity": "⭐⭐⭐⭐⭐",
        "description": "The current Dendro Archon and vessel of Lesser Lord Kusanali, known for her wisdom."
    },
    {
        "name": "Mistsplitter Reforged",
        "image": "https://rerollcdn.com/GENSHIN/Weapons/Mistsplitter_Reforged.png",
        "rarity": "⭐⭐⭐⭐⭐",
        "description": "A sword that blazes with a fierce violet light. The name 'Reforged' comes from it being recreated."
    },
    {
        "name": "Zhongli",
        "image": "https://rerollcdn.com/GENSHIN/Characters/Zhongli.png",
        "rarity": "⭐⭐⭐⭐⭐",
        "description": "The consultant of the Wangsheng Funeral Parlor, also known as the Geo Archon Morax."
    }
    # Add more cards as needed
]

async def card_drop_command(ctx):
    """
    Handle the admin card drop command with error handling.
    """
    try:
        # Check if user has admin permissions
        if not ctx.author.guild_permissions.administrator:
            await ctx.send(embed=discord.Embed(
                title="<a:Animated_Cross:1344705833627549748> Permission Denied",
                description="You need administrator permissions to use this command.",
                color=discord.Color.red()
            ))
            return

        # Randomly select a card
        card = random.choice(GENSHIN_CARDS)
        
        # Create the initial drop embed
        embed = discord.Embed(
            title="🎴 Rare Card Drop!",
            description="A rare Genshin Impact card has appeared!\nClick the button below to claim it!",
            color=discord.Color.blue()
        )
        embed.add_field(name="Card Name", value=card['name'])
        embed.add_field(name="Rarity", value=card['rarity'])
        embed.set_image(url=card['image'])
        
        # Create and send the view with the embed
        view = CardDropView(card)
        await ctx.send(embed=embed, view=view)
        
        # Wait for the view to timeout
        await view.wait()
        
        # If no one claimed the card
        if not view.claimed_by:
            timeout_embed = discord.Embed(
                title="<a:Animated_Cross:1344705833627549748> Card Expired",
                description="No one claimed the card in time!",
                color=discord.Color.red()
            )
            await ctx.send(embed=timeout_embed)

    except Exception as e:
        error_embed = discord.Embed(
            title="<a:Animated_Cross:1344705833627549748> Error",
            description="An error occurred while dropping the card.",
            color=discord.Color.red()
        )
        await ctx.send(embed=error_embed)
        logger.error(f"Error in card drop command: {e}", exc_info=True)

#--------------------------------------------------#------------------------------------------#--------------------------------------------


class RouletteGame:
    def __init__(self, entry_fee: int = 100):  # Make entry_fee configurable
        self.entry_fee = entry_fee
        self.min_players = 4
        self.players = {}  # Dictionary to store player_id -> user_id mapping
        self.is_active = False
        self.is_starting = False
        self.bonus_pool = 50  # Fixed bonus amount

    def reset(self):
        self.players.clear()
        self.is_active = False
        self.is_starting = False

    def get_prize_pool(self) -> int:
        return (len(self.players) * self.entry_fee) + self.bonus_pool

class GameManager:
    def __init__(self):
        self.current_game = None
        self.previous_game = None

    def create_new_game(self, entry_fee: int = 100) -> RouletteGame:  # Add entry_fee parameter
        if self.current_game and not self.current_game.is_active:
            return self.current_game
        
        if self.current_game:
            self.previous_game = self.current_game
        
        self.current_game = RouletteGame(entry_fee)  # Pass entry_fee to RouletteGame
        return self.current_game

class RouletteView(discord.ui.View):
    def __init__(self, game: RouletteGame, game_manager: GameManager):
        super().__init__(timeout=60)
        self.game = game
        self.game_manager = game_manager

    @discord.ui.button(
        style=discord.ButtonStyle.success,
        label="Join Game",
        emoji="🎯",
        custom_id="join"
    )
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.join_callback(interaction)

    @discord.ui.button(
        style=discord.ButtonStyle.danger,
        label="Leave Game",
        emoji="🚪",
        custom_id="leave"
    )
    async def leave_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.leave_callback(interaction)

    @discord.ui.button(
        style=discord.ButtonStyle.primary,
        label="Start Game",
        emoji="🎲",
        custom_id="start"
    )
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.start_callback(interaction)

    async def join_callback(self, interaction: discord.Interaction):
        if not interaction.guild or not interaction.user:
            await interaction.response.send_message("Error processing request.", ephemeral=True)
            return

        if self.game.is_starting or self.game.is_active:
            await interaction.response.send_message("Cannot join while game is in progress!", ephemeral=True)
            return

        player_id = str(interaction.user.id)
        server_id = str(interaction.guild.id)

        if player_id in self.game.players:
            await interaction.response.send_message("You're already in the game!", ephemeral=True)
            return

        try:
            current_rubles = get_user_rubles(server_id, player_id)

            if current_rubles < self.game.entry_fee:
                await interaction.response.send_message(
                    f"You need {self.game.entry_fee} rubles to join! You have {current_rubles} rubles.",
                    ephemeral=True
                )
                return

            update_rubles(server_id, player_id, -self.game.entry_fee)
            self.game.players[player_id] = interaction.user.id

            await interaction.response.send_message(
                f"You've joined the game! Entry fee of {self.game.entry_fee} rubles has been deducted.",
                ephemeral=True
            )
            await self.update_game_message(interaction)

        except Exception as e:
            print(f"Error in join_callback: {str(e)}")
            await interaction.response.send_message(
                "Error processing request. Please try again.",
                ephemeral=True
            )

    async def leave_callback(self, interaction: discord.Interaction):
        if not interaction.guild or not interaction.user:
            await interaction.response.send_message("Error processing request.", ephemeral=True)
            return

        if self.game.is_starting or self.game.is_active:
            await interaction.response.send_message("Cannot leave while game is in progress!", ephemeral=True)
            return

        player_id = str(interaction.user.id)
        server_id = str(interaction.guild.id)

        if player_id not in self.game.players:
            await interaction.response.send_message("You're not in the game!", ephemeral=True)
            return

        try:
            update_rubles(server_id, player_id, self.game.entry_fee)
            del self.game.players[player_id]

            await interaction.response.send_message(
                f"You've left the game! Entry fee of {self.game.entry_fee} rubles has been refunded.",
                ephemeral=True
            )
            await self.update_game_message(interaction)

        except Exception as e:
            print(f"Error in leave_callback: {str(e)}")
            await interaction.response.send_message(
                "Error processing request. Please try again.",
                ephemeral=True
            )

    async def start_callback(self, interaction: discord.Interaction):
        if len(self.game.players) < self.game.min_players:
            await interaction.response.send_message(
                f"Need at least {self.game.min_players} players to start!",
                ephemeral=True
            )
            return

        if self.game.is_starting or self.game.is_active:
            await interaction.response.send_message(
                "A game is already in progress!",
                ephemeral=True
            )
            return

        try:
            self.game.is_starting = True
            self.game.is_active = True
            
            await interaction.response.send_message("🎲 The game has begun! Loading the revolver...")
            
            for item in self.children:
                item.disabled = True
            await interaction.message.edit(view=self)
            
            await self.run_game(interaction)

        except Exception as e:
            self.game.is_starting = False
            self.game.is_active = False
            print(f"Error in start_callback: {str(e)}")
            await interaction.response.send_message(
                "Error starting the game. Please try again.",
                ephemeral=True
            )

    async def run_game(self, interaction: discord.Interaction):
        if not interaction.guild:
            return

        try:
            players = list(self.game.players.items())
            random.shuffle(players)
            winner_id, winner_user_id = players[-1]

            for player_id, user_id in players[:-1]:
                elimination_embed = discord.Embed(
                    title="💀 BANG!",
                    description=f"<@{user_id}> pulled the trigger...",
                    color=discord.Color.dark_red()
                )
                await interaction.channel.send(embed=elimination_embed)
                await asyncio.sleep(2)

            server_id = str(interaction.guild.id)
            prize_pool = self.game.get_prize_pool()
            update_rubles(server_id, winner_id, prize_pool)

            winner_embed = discord.Embed(
                title="🎉 Survivor!",
                description=f"<@{winner_user_id}> has survived and won {prize_pool} <a:Rubles:1344705820222292011>!",
                color=discord.Color.green()
            )
            winner_embed.add_field(name="Total Players", value=str(len(self.game.players)), inline=True)
            winner_embed.add_field(name="Prize Pool", value=f"{prize_pool} rubles", inline=True)
            winner_embed.add_field(name="House Bonus", value="50 rubles", inline=True)
            
            await interaction.channel.send(embed=winner_embed)

        except Exception as e:
            print(f"Error in run_game: {str(e)}")
            await interaction.channel.send("An error occurred while running the game.")
        
        finally:
            self.game.reset()

    async def update_game_message(self, interaction: discord.Interaction):
        try:
            embed = self.create_game_embed()
            await interaction.message.edit(embed=embed, view=self)
        except Exception as e:
            print(f"Error updating game message: {str(e)}")

    def create_game_embed(self) -> discord.Embed:
        players_list = "\n".join([f"• <@{user_id}>" for user_id in self.game.players.values()])
        if not players_list:
            players_list = "No players yet!"

        previous_game_info = ""
        if self.game_manager.previous_game and self.game_manager.previous_game.is_active:
            previous_game_info = "\n\n**Previous Game In Progress!**\nPlease wait for it to finish."

        return discord.Embed(
            title="🎲 Russian Roulette Game",
            description=(
                f"Entry Fee: {self.game.entry_fee} <a:Rubles:1344705820222292011>\n"
                f"Prize Pool: {self.game.get_prize_pool()} <a:Rubles:1344705820222292011> "
                f"(Includes 50 rubles house bonus!)\n"
                f"Minimum Players: {self.game.min_players}\n\n"
                f"**Current Players ({len(self.game.players)}):**\n{players_list}"
                f"{previous_game_info}"
            ),
            color=0xff0000
        )

#------------------------------------------------#--------------------------------------------------#----------------------------------------------#-----------


MIN_BET = 10
MAX_BET = 1000
MIN_MINES = 1
MAX_MINES = 5
GRID_SIZE = 16

class MinesGame:
    def __init__(self, bet: int, mines: int, server_id: str, user_id: str):
        """Initialize a new Mines game"""
        # Input validation with specific error messages
        if not isinstance(mines, int):
            raise ValueError("Number of mines must be a whole number")
        if not MIN_MINES <= mines <= MAX_MINES:
            raise ValueError(f"Number of mines must be between {MIN_MINES} and {MAX_MINES}")
        if not isinstance(bet, int):
            raise ValueError("Bet must be an integer")
        if bet < MIN_BET:
            raise ValueError(f"Minimum bet is {MIN_BET}")
        if bet > MAX_BET:
            raise ValueError(f"Maximum bet is {MAX_BET}")

        self.bet = bet
        
        try:
            # Check user balance before deducting
            user_balance = get_user_rubles(server_id, user_id)
            if user_balance < self.bet:
                raise ValueError(f"Insufficient balance. You have {user_balance:,} rubles")
        except Exception as e:
            raise ValueError(f"Failed to check balance: {str(e)}")

        self.server_id = server_id
        self.user_id = user_id
        self.mines = mines
        self.grid = [False] * GRID_SIZE
        self.revealed = [False] * GRID_SIZE
        self.is_active = True
        self.is_finished = False
        self.safe_tiles = GRID_SIZE - mines
        
        # Place mines randomly
        self._place_mines()
        
        # Calculate initial multiplier
        self.multiplier = self._calculate_multiplier()
        
        # Deduct initial bet with error handling
        try:
            update_rubles(server_id, user_id, -self.bet)
        except Exception as e:
            self.is_active = False
            raise ValueError(f"Failed to process bet: {str(e)}")

    def _place_mines(self):
        """Place mines randomly on the grid"""
        try:
            mine_positions = random.sample(range(GRID_SIZE), self.mines)
            for pos in mine_positions:
                self.grid[pos] = True
        except Exception as e:
            raise ValueError(f"Failed to place mines: {str(e)}")

    def _calculate_multiplier(self) -> int:
        """Calculate current multiplier based on revealed tiles"""
        revealed_count = sum(self.revealed)
        remaining_safe = self.safe_tiles - revealed_count
        
        if remaining_safe <= 0:
            return self.multiplier if hasattr(self, 'multiplier') else 0
            
        # Base multiplier calculation with 20% house edge
        try:
            base = (GRID_SIZE / (GRID_SIZE - self.mines)) ** revealed_count
            return max(1, int(round(base * 80)))  # 80% for house edge, minimum 1
        except Exception as e:
            raise ValueError(f"Failed to calculate multiplier: {str(e)}")

    def reveal(self, position: int) -> bool | None:
        """Reveal a tile and return the result"""
        try:
            # Validate position and game state
            if (not self.is_active or 
                self.is_finished or 
                position < 0 or 
                position >= GRID_SIZE or 
                self.revealed[position]):
                return None
                
            self.revealed[position] = True
            
            if self.grid[position]:  # Hit mine
                self.is_active = False
                self.is_finished = True
                return False
                
            # Update multiplier after successful reveal
            self.multiplier = self._calculate_multiplier()
            
            # Check if all safe tiles revealed
            if sum(self.revealed) >= self.safe_tiles:
                self.is_active = False
                self.is_finished = True
                
            return True
        except Exception as e:
            raise ValueError(f"Failed to reveal tile: {str(e)}")

class MinesButton(Button):
    def __init__(self, pos: int):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label="🟦",
            row=pos // 4,
            custom_id=f"mine_{pos}"
        )
        self.pos = pos

    async def callback(self, interaction: Interaction):
        try:
            assert self.view is not None
            
            # Fix: Compare string IDs consistently
            if str(interaction.user.id) != str(self.view.game.user_id):
                await interaction.response.send_message(
                    "<a:Animated_Cross:1344705833627549748> This is not your game!", 
                    ephemeral=True
                )
                return
                
            if not self.view.game.is_active:
                await interaction.response.defer()
                return
                
            # Process tile reveal
            result = self.view.game.reveal(self.pos)
            if result is None:
                await interaction.response.defer()
                return
                
            if not result:  # Mine hit
                # Show all mines
                for button in self.view.children[:-1]:  # Exclude cash out button
                    if isinstance(button, MinesButton):
                        if self.view.game.grid[button.pos]:
                            button.style = discord.ButtonStyle.danger
                            button.label = "💣"
                        button.disabled = True
                
                await interaction.response.edit_message(
                    content=f"💥 **BOOM!** Lost {self.view.game.bet:,} <a:Rubles:1344705820222292011>",
                    embed=self.view.create_embed(),
                    view=self.view
                )
                return
                
            # Successful reveal
            self.style = discord.ButtonStyle.success
            self.label = "💎"
            self.disabled = True
            
            if self.view.game.is_finished:  # Won by revealing all safe tiles
                payout = int(round(self.view.game.bet * self.view.game.multiplier / 100))
                try:
                    update_rubles(self.view.game.server_id, self.view.game.user_id, payout)
                    await interaction.response.edit_message(
                        content=f"🏆 **Perfect Game!** Won {payout:,} <a:Rubles:1344705820222292011>",
                        embed=self.view.create_embed(),
                        view=self.view
                    )
                except Exception as e:
                    await interaction.response.edit_message(
                        content="<a:Animated_Cross:1344705833627549748> Error processing payout. Please contact support.",
                        view=self.view
                    )
            else:
                await interaction.response.edit_message(
                    content=f"**Current Multiplier:** {self.view.game.multiplier/100:.2f}x",
                    embed=self.view.create_embed(),
                    view=self.view
                )
        except Exception as e:
            await interaction.response.send_message(
                "<a:Animated_Cross:1344705833627549748> An unexpected error occurred. Please try again.",
                ephemeral=True
            )

class CashOutButton(Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.success,
            label="💰 Cash Out",
            row=4,
            custom_id="cashout"
        )

    async def callback(self, interaction: Interaction):
        try:
            assert self.view is not None
            
            if str(interaction.user.id) != str(self.view.game.user_id):
                await interaction.response.send_message(
                    "<a:Animated_Cross:1344705833627549748> This is not your game!", 
                    ephemeral=True
                )
                return
                
            if not self.view.game.is_active:
                await interaction.response.defer()
                return
                
            # Process cash out
            self.view.game.is_active = False
            self.view.game.is_finished = True
            
            # Calculate and process payout
            payout = int(round(self.view.game.bet * self.view.game.multiplier / 100))
            try:
                update_rubles(self.view.game.server_id, self.view.game.user_id, payout)
                
                # Show mines after cashing out
                for button in self.view.children[:-1]:
                    if isinstance(button, MinesButton):
                        if self.view.game.grid[button.pos]:
                            button.style = discord.ButtonStyle.danger
                            button.label = "💣"
                        button.disabled = True
                
                await interaction.response.edit_message(
                    content=f"💰 **Cashed Out!** Won {payout:,} <a:Rubles:1344705820222292011>",
                    embed=self.view.create_embed(),
                    view=self.view
                )
            except Exception as e:
                await interaction.response.edit_message(
                    content="<a:Animated_Cross:1344705833627549748> Error processing payout. Please contact support.",
                    view=self.view
                )
        except Exception as e:
            await interaction.response.send_message(
                "<a:Animated_Cross:1344705833627549748> An unexpected error occurred. Please try again.",
                ephemeral=True
            )

class MinesView(View):
    def __init__(self, game: MinesGame):
        super().__init__(timeout=60)
        self.game = game
        self.message = None
        
        # Add mine buttons
        for i in range(GRID_SIZE):
            self.add_item(MinesButton(pos=i))
            
        # Add cash out button
        self.add_item(CashOutButton())

    def create_embed(self) -> Embed:
        try:
            revealed_count = sum(self.game.revealed)
            
            embed = Embed(
                title="💣 Mines Game",
                description=(
                    f"**Bet:** {self.game.bet:,} <a:Rubles:1344705820222292011>\n"
                    f"**Mines:** {self.game.mines}\n"
                    f"**Safe Tiles Found:** {revealed_count}/{self.game.safe_tiles}\n"
                    f"**Current Multiplier:** {self.game.multiplier/100:.2f}x"
                ),
                color=Color.green()
            )
            return embed
        except Exception as e:
            raise ValueError(f"Failed to create embed: {str(e)}")

    async def on_timeout(self):
        if self.game.is_active:
            self.game.is_active = False
            self.game.is_finished = True
            
            # Show all mines on timeout
            for button in self.children[:-1]:
                if isinstance(button, MinesButton):
                    if self.game.grid[button.pos]:
                        button.style = discord.ButtonStyle.danger
                        button.label = "💣"
                    button.disabled = True
            
            try:
                await self.message.edit(
                    content="⏰ Game timed out!",
                    view=self
                )
            except Exception:
                pass

async def play_mines(interaction: Interaction, bet: int, mines: int):
    """Start a new game of Mines"""
    try:
        # Create new game with string IDs
        game = MinesGame(
            bet=bet,
            mines=mines,
            server_id=str(interaction.guild_id),
            user_id=str(interaction.user.id)
        )
        
        # Create and send view
        view = MinesView(game)
        await interaction.response.send_message(
            content=f"**Current Multiplier:** {game.multiplier/100:.2f}x",
            embed=view.create_embed(),
            view=view
        )
        view.message = await interaction.original_response()
        
    except ValueError as e:
        await interaction.response.send_message(
            f"<a:Animated_Cross:1344705833627549748> {str(e)}", 
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            "<a:Animated_Cross:1344705833627549748> An unexpected error occurred. Please try again.",
            ephemeral=True
        )

#----------------------------------------#-----------------------------------------------#----------------------------------#--------------------


class StoreSystem:
    def __init__(self, channel: discord.TextChannel):
        self.channel = channel
        self.store: Dict[str, dict] = {}
        self.active_message: Optional[discord.Message] = None
        self.refresh_task = None
        self.store_file = Path('store_data.json')
        self._load_store_data()

    def _load_store_data(self) -> None:
        """Load store data from JSON file."""
        try:
            if self.store_file.exists():
                with open(self.store_file, 'r', encoding='utf-8') as f:  # Added encoding='utf-8'
                    self.store = json.load(f)
        except Exception as e:
            logger.error(f"Error loading store data: {e}")
            self.store = {}

    def _save_store_data(self) -> None:
        """Save store data to JSON file."""
        try:
            with open(self.store_file, 'w', encoding='utf-8') as f:  
                json.dump(self.store, f, indent=4, ensure_ascii=False)  
        except Exception as e:
            logger.error(f"Error saving store data: {e}")

    async def initialize_store(self) -> None:
        """Initialize and display the store in the channel."""
        try:
            loading_embed = discord.Embed(
                title="Loading Store...",
                description="<a:loading_icon:1334757784834674700> Fetching store items...",
                color=0xB22222
            )
            
            self.active_message = await self.channel.send(embed=loading_embed)
            await asyncio.sleep(2)
            
            if not self.store:
                empty_embed = discord.Embed(
                    title="Server Store",
                    description="The store is currently empty.",
                    color=0xD4AF37
                )
                await self.active_message.edit(embed=empty_embed)
                return
            
            await self.update_store_display()
            self.start_refresh_task()
            
        except Exception as e:
            logger.error(f"Error initializing store: {e}")
            error_embed = discord.Embed(
                title="<a:Animated_Cross:1344705833627549748> Error",
                description="An error occurred while initializing the store.",
                color=0xe74c3c
            )
            await self.channel.send(embed=error_embed)

    async def update_store_display(self) -> None:
        """Update the store display message."""
        try:
            store_embed = discord.Embed(
                title="<:store:1344705843181912075> Server Store",
                description="Welcome to our store! All items can be purchased with Rubles <a:Rubles:1344705820222292011>. For more information, pls read <#1329090546140184606>",
                color=0xD4AF37
            )
            
            for name, details in self.store.items():
                display_name = f"~~{name}~~" if details['stock'] == 0 else name
                emoji = details.get('emoji', '')  # Get emoji from details
                field_name = f"{emoji} {display_name}" if emoji else display_name
                
                field_value = (
                    f"<a:Rubles:1344705820222292011> Value: {details['value']}\n"
                    f"<a:stock:1344705842410164276> Stock: {details['stock']}"
                )
                store_embed.add_field(
                    name=field_name,
                    value=field_value,
                    inline=False
                )

            view = self.create_store_view()
            if self.active_message:
                await self.active_message.edit(embed=store_embed, view=view)
        except Exception as e:
            logger.error(f"Error updating store display: {e}")

    def create_store_view(self) -> View:
        """Create the store view with buttons."""
        view = View(timeout=None)
        
        buy_button = Button(
            style=discord.ButtonStyle.green,
            label="Buy Item",
            custom_id="buy_button",
            emoji="<a:buy:1347111730056265729>"
        )
        buy_button.callback = self.handle_buy_button
        
        custom_button = Button(
            style=discord.ButtonStyle.blurple,
            label="Custom Order",
            custom_id="custom_order_button",
            emoji="<a:MoneyMoney:1344705822219046914>"
        )
        custom_button.callback = self.handle_custom_order_button
        
        view.add_item(buy_button)
        view.add_item(custom_button)
        
        return view

    def create_item_select(self, available_items: list) -> Select:
        """Create the item selection dropdown."""
        options = []
        for name in available_items:
            item_details = self.store[name]
            emoji = item_details.get('emoji', '🏷️')  # Use stored emoji or default
            options.append(
                discord.SelectOption(
                    label=name,
                    description=f"Price: {item_details['value']} Rubles",
                    value=name,
                    emoji=emoji
                )
            )
        
        select = Select(
            placeholder="Choose an item to purchase...",
            min_values=1,
            max_values=1,
            options=options
        )
        select.callback = self.handle_item_select
        return select

    async def handle_buy_button(self, interaction: discord.Interaction) -> None:
        """Handle the buy item button click."""
        try:
            available_items = [name for name, details in self.store.items() if details['stock'] > 0]
            
            if not available_items:
                await interaction.response.send_message(
                    "<a:Animated_Cross:1344705833627549748> Sorry, no items are currently in stock!",
                    ephemeral=True
                )
                return

            select_view = View(timeout=300)
            select_view.add_item(self.create_item_select(available_items))
            
            await interaction.response.send_message(
                "Please select the item you want to purchase:",
                view=select_view,
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error handling buy button: {e}")
            await interaction.response.send_message(
                "An error occurred while processing your request.",
                ephemeral=True
            )

    class CustomOrderModal(Modal):
        def __init__(self, parent_store):
            super().__init__(title="Custom Order Details")
            self.parent_store = parent_store
            
            self.item_name = TextInput(
                label="Item Name",
                placeholder="Enter the item you want to order...",
                required=True,
                max_length=100
            )
            self.server = TextInput(
                label="Server",
                placeholder="Enter the server name...",
                required=True,
                max_length=100
            )
            self.uid = TextInput(
                label="UID",
                placeholder="Enter your UID...",
                required=True,
                max_length=40
            )

        async def on_submit(self, interaction: discord.Interaction):
            await self.parent_store.handle_custom_order_submit(interaction, self)

    async def handle_custom_order_button(self, interaction: discord.Interaction) -> None:
       """Handle the custom order button click."""
       try:
           modal = self.CustomOrderModal(self)
           await interaction.response.send_modal(modal)
       except discord.errors.HTTPException as http_err:
           logger.error(f"Error handling custom order button: {http_err}")
           await interaction.response.send_message(
               "An error occurred with the order form. Please try again later.",
               ephemeral=True
           )
       except Exception as e:
           logger.error(f"Error handling custom order button: {e}")
           await interaction.response.send_message(
               "An error occurred while processing your request.",
               ephemeral=True
           )

    async def handle_item_select(self, interaction: discord.Interaction) -> None:
        """Handle item selection from dropdown."""
        try:
            selected_item = interaction.data['values'][0]
            
            if self.store[selected_item]['stock'] <= 0:
                await interaction.response.send_message(
                    "<a:Animated_Cross:1344705833627549748> This item is out of stock!",
                    ephemeral=True
                )
                return
                
            self.store[selected_item]['stock'] -= 1
            self._save_store_data()
            
            await self.create_purchase_ticket(interaction, selected_item)
            await self.update_store_display()
        except Exception as e:
            logger.error(f"Error handling item selection: {e}")
            await interaction.response.send_message(
                "An error occurred while processing your selection.",
                ephemeral=True
            )

    async def create_purchase_ticket(self, interaction: discord.Interaction, item_name: str) -> None:
        """Create a purchase ticket channel."""
        try:
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.guild.me: discord.PermissionOverwrite(read_messages=True),
                interaction.user: discord.PermissionOverwrite(read_messages=True)
            }

            # Add admin permissions
            for role in interaction.guild.roles:
                if role.permissions.administrator:
                    overwrites[role] = discord.PermissionOverwrite(read_messages=True)

            ticket_channel = await interaction.guild.create_text_channel(
                f'purchase-{interaction.user.name}-{interaction.user.discriminator}',
                overwrites=overwrites,
                category=self.channel.category
            )

            await self.send_purchase_ticket_embed(interaction, ticket_channel, item_name)
            await interaction.response.send_message(
                f"<a:animated_tick:1344705804007112724> Purchase ticket created! Please check {ticket_channel.mention}",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error creating purchase ticket: {e}")
            await interaction.response.send_message(
                "An error occurred while creating your purchase ticket.",
                ephemeral=True
            )

    async def send_purchase_ticket_embed(self, interaction: discord.Interaction, ticket_channel: discord.TextChannel, item_name: str) -> None:
        """Send the purchase ticket embed to the ticket channel."""
        try:
            admin_role = discord.utils.get(interaction.guild.roles, name="admin")
            item_details = self.store[item_name]
            emoji = item_details.get('emoji', '')
            
            ticket_embed = discord.Embed(
                title="🛍️ New Purchase Ticket",
                description="Thank you for your purchase! An administrator will assist you shortly.",
                color=0x9B59B6
            )
            
            ticket_embed.add_field(
                name="Buyer Information",
                value=f"**Buyer:** {interaction.user.mention}\n**User ID:** {interaction.user.id}",
                inline=False
            )
            
            item_field_name = f"{emoji} {item_name}" if emoji else item_name
            ticket_embed.add_field(
                name="Item Information",
                value=f"**Item:** {item_field_name}\n**Price:** {item_details['value']} Rubles\n**Remaining Stock:** {item_details['stock']}",
                inline=False
            )
            
            ticket_embed.set_footer(text="Please wait for an administrator to process your purchase.")
            
            if admin_role:
                await ticket_channel.send(f"{admin_role.mention}", embed=ticket_embed)
            else:
                await ticket_channel.send(embed=ticket_embed)
        except Exception as e:
            logger.error(f"Error sending purchase ticket embed: {e}")

    async def handle_custom_order_submit(self, interaction: discord.Interaction, modal) -> None:
        """Handle custom order form submission."""
        try:
            ticket_channel = await interaction.guild.create_text_channel(
                f'custom-order-{interaction.user.name}-{interaction.user.discriminator}',
                category=self.channel.category
            )

            admin_role = discord.utils.get(interaction.guild.roles, name="admin")
            
            ticket_embed = discord.Embed(
                title="📝 New Custom Order Ticket",
                description="A new custom order has been placed! An administrator will assist you shortly.",
                color=0x9B59B6
            )
            
            ticket_embed.add_field(
                name="Buyer Information",
                value=f"**Buyer:** {interaction.user.mention}\n**User ID:** {interaction.user.id}",
                inline=False
            )
            
            ticket_embed.add_field(
                name="Order Details",
                value=f"**Item:** {modal.item_name.value}\n**Server:** {modal.server.value}\n**UID:** {modal.uid.value}",
                inline=False
            )
            
            if admin_role:
                await ticket_channel.send(f"{admin_role.mention}", embed=ticket_embed)
            else:
                await ticket_channel.send(embed=ticket_embed)

            await interaction.response.send_message(
                f"<a:animated_tick:1344705804007112724> Custom order ticket created! Please check {ticket_channel.mention}",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error handling custom order submission: {e}")
            await interaction.response.send_message(
                "An error occurred while processing your custom order.",
                ephemeral=True
            )

    def start_refresh_task(self) -> None:
        """Start the periodic store refresh task."""
        async def refresh_loop():
            while True:
                try:
                    await asyncio.sleep(300)  # 5 minutes
                    await self.update_store_display()
                except Exception as e:
                    logger.error(f"Error in refresh loop: {e}")

        self.refresh_task = asyncio.create_task(refresh_loop())

    def stop_refresh_task(self) -> None:
        """Stop the store refresh task."""
        if self.refresh_task and not self.refresh_task.cancelled():
            self.refresh_task.cancel()

class StoreManager:
    """Manager class for handling multiple stores."""
    def __init__(self):
        self.active_stores: Dict[str, StoreSystem] = {}

    async def create_store(self, channel: discord.TextChannel) -> StoreSystem:
        """Create a new store in the specified channel."""
        store = StoreSystem(channel)
        self.active_stores[str(channel.id)] = store
        await store.initialize_store()
        return store

    def get_store(self, channel_id: str) -> Optional[StoreSystem]:
        """Get store instance for a channel."""
        return self.active_stores.get(channel_id)

    async def remove_store(self, channel_id: str) -> None:
        """Remove a store instance."""
        if store := self.active_stores.get(channel_id):
            store.stop_refresh_task()
            del self.active_stores[channel_id]

# Create global store manager instance
store_manager = StoreManager()


#----------------------------------------------#--------------------------------------



class GlobalResetCommandError(Exception):
    """Custom exception for global reset command-related errors."""
    pass

class GlobalResetView(View):
    def __init__(self, admin_user: discord.User):
        super().__init__(timeout=60)  # 1 minute timeout
        self.admin_user = admin_user
        
        confirm_button = Button(style=discord.ButtonStyle.danger, label="Yes, Reset All Data", custom_id="confirm")
        cancel_button = Button(style=discord.ButtonStyle.secondary, label="Cancel", custom_id="cancel")
        
        confirm_button.callback = self.confirm_callback
        cancel_button.callback = self.cancel_callback
        
        self.add_item(confirm_button)
        self.add_item(cancel_button)

    async def confirm_callback(self, interaction: discord.Interaction):
        # Only allow the admin who initiated to click
        if interaction.user.id != self.admin_user.id:
            embed = discord.Embed(
                title="<a:Animated_Cross:1344705833627549748> Permission Denied",
                description="Only the admin who initiated this reset can interact with these buttons.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Verify admin permissions
        if not interaction.user.guild_permissions.administrator:
            embed = discord.Embed(
                title="<a:Animated_Cross:1344705833627549748> Permission Denied", 
                description="You need administrator permissions to confirm this global reset.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            server_id = str(interaction.guild_id)
            
            # Reset all user data for this server
            server_data[server_id] = {}
            save_data(server_data)
            
            embed = discord.Embed(
                title="<:PepeHehe:1347125572865626122> Global Reset Complete",
                description="All user data has been reset for this server.",
                color=discord.Color.from_rgb(139, 0, 0)
            )
            logger.info(f"Global reset performed by admin {interaction.user.id} in server {server_id}")
            
            await interaction.response.edit_message(embed=embed, view=None)
            
        except Exception as e:
            logger.error(f"Error during global reset confirmation: {e}")
            embed = discord.Embed(
                title="<a:Animated_Cross:1344705833627549748> Error",
                description="An error occurred while performing the global reset.",
                color=discord.Color.red()
            )
            await interaction.response.edit_message(embed=embed, view=None)

    async def cancel_callback(self, interaction: discord.Interaction):
        # Only allow the admin who initiated to click
        if interaction.user.id != self.admin_user.id:
            embed = discord.Embed(
                title="<a:Animated_Cross:1344705833627549748> Permission Denied",
                description="Only the admin who initiated this reset can interact with these buttons.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(
            title="<a:Animated_Cross:1344705833627549748> Global Reset Cancelled",
            description="The global reset operation has been cancelled.",
            color=discord.Color.from_rgb(139, 0, 0)
        )
        await interaction.response.edit_message(embed=embed, view=None)

# Store the last reset time for each server
last_reset_times = {}

async def global_reset_command(ctx, client):
    """
    Handle the admin global reset command with robust error handling and cooldown.
    
    Args:
        ctx (discord.Context): The context of the command invocation
        client (discord.Client): The Discord bot client
    
    Raises:
        GlobalResetCommandError: For various potential error scenarios
    """
    try:
        if not ctx or not ctx.guild or not ctx.author:
            raise GlobalResetCommandError("Invalid command context")

        # Check for admin permissions
        if not ctx.author.guild_permissions.administrator:
            await ctx.send(embed=discord.Embed(
                title="<a:Animated_Cross:1344705833627549748> Permission Denied",
                description="You need administrator permissions to use this command.",
                color=discord.Color.red()
            ))
            return

        # Check cooldown
        server_id = str(ctx.guild.id)
        current_time = datetime.now()
        if server_id in last_reset_times:
            time_diff = current_time - last_reset_times[server_id]
            if time_diff < timedelta(days=1):
                remaining_time = timedelta(days=1) - time_diff
                hours = remaining_time.seconds // 3600
                minutes = (remaining_time.seconds % 3600) // 60
                await ctx.send(embed=discord.Embed(
                    title="⏳ Command on Cooldown",
                    description=f"This command can only be used once per day.\nPlease wait {hours} hours and {minutes} minutes.",
                    color=discord.Color.orange()
                ))
                return

        embed = discord.Embed(
            title="⚠️ Global Reset Warning",
            description=(
                "**Are you absolutely sure you want to reset ALL user data for this server?**\n\n"
                "This action:\n"
                "• Will delete ALL user data\n"
                "• Cannot be undone\n"
                "• Has a 24-hour cooldown\n\n"
                "Please confirm this action carefully!"
            ),
            color=discord.Color.from_rgb(139, 0, 0)
        )
        
        view = GlobalResetView(ctx.author)
        message = await ctx.send(embed=embed, view=view)
        
        last_reset_times[server_id] = current_time
        
    except GlobalResetCommandError as reset_error:
        await ctx.send(f"<a:Animated_Cross:1344705833627549748> Global Reset Error: {reset_error}")
        logger.error(f"Global reset command error: {reset_error}")
    except Exception as unexpected_error:
        await ctx.send("An unexpected error occurred. Please try again later.")
        logger.error(f"Unexpected global reset error: {unexpected_error}", exc_info=True)


#!/usr/bin/env python3
"""
Scripty CLI - Interactive command-line interface for Scripty AI.
"""

import asyncio
import json
import os
import sys
import re
import threading
import time
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

import httpx
import sseclient
from prompt_toolkit import prompt
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.shortcuts import clear
PROMPT_TOOLKIT_AVAILABLE = True
print("Prompt toolkit available")

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from prompt_toolkit.shortcuts import PromptSession

async def safe_prompt(prompt_text: str, completer=None):
    """Safe prompt function that handles event loop issues."""
    if PROMPT_TOOLKIT_AVAILABLE and completer:
        try:
            # Use prompt_toolkit's async API
            session = PromptSession(completer=completer)
            return await session.prompt_async(prompt_text)
        except Exception as e:
            # Fall back to basic input if there's any issue
            print(f"prompt_toolkit failed: {e}, falling back to basic input")
    
    # Fallback: Use asyncio to run input in a thread to avoid blocking
    import asyncio
    
    def sync_input_with_completion():
        try:
            import readline
            
            if completer:
                # Set up basic completion for slash commands
                def complete_function(text, state):
                    options = []
                    
                    # Get current word (last word in text)
                    words = text.split()
                    current_word = words[-1] if words and not text.endswith(' ') else ""
                    
                    if current_word.startswith('/'):
                        commands = ["/new", "/state", "/help", "/delete", "/upload", "/files", "/delete-file", "/exit"]
                        options = [cmd for cmd in commands if cmd.startswith(current_word)]
                    elif current_word.startswith('@'):
                        # Remote file completion - fallback to cached files if available
                        if hasattr(completer, '_remote_files_cache'):
                            file_prefix = current_word[1:]  # Remove @ prefix
                            for file_path in completer._remote_files_cache:
                                filename = os.path.basename(file_path)
                                if filename.startswith(file_prefix):
                                    options.append(f"@{filename}")
                    elif current_word and not current_word.startswith('/'):
                        # Local file completion (bash-like)
                        import glob
                        try:
                            if '/' in current_word:
                                # Handle paths with directories
                                file_pattern = current_word + '*'
                            else:
                                # Just filename
                                file_pattern = current_word + '*'
                            
                            for match in glob.glob(file_pattern):
                                if os.path.isdir(match):
                                    options.append(match + "/")
                                else:
                                    options.append(match)
                        except:
                            options = []
                    
                    if state < len(options):
                        return options[state]
                    return None
                
                readline.set_completer(complete_function)
                readline.parse_and_bind("tab: complete")
        except ImportError:
            # readline not available, just use basic input
            print("Readline not available, using basic input")
            pass
        
        return input(prompt_text)
    
    # Run input in a thread to avoid blocking the async event loop
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, sync_input_with_completion)


@dataclass
class Conversation:
    """Conversation data structure."""
    id: str
    user_prompt: str
    previous_response_id: Optional[str] = None
    current_script_id: Optional[str] = None
    last_agent_name: Optional[str] = None    


class ScriptyCompleter(Completer):
    """Custom completer for Scripty CLI commands and file paths."""
    
    def __init__(self, workspace_path: str = ".", cli_instance=None):
        self.workspace_path = workspace_path
        self.cli_instance = cli_instance
        self.commands = [
            "/new", "/state", "/help", "/delete", "/upload", "/files", "/delete-file", "/exit"
        ]
        self._remote_files_cache = []
        self._cache_time = 0
        self._cache_ttl = 10  # Cache remote files for 10 seconds
    
    def _get_current_word(self, document):
        """Get the current word being typed (before cursor)."""
        text_before_cursor = document.text_before_cursor
        # Split by spaces and get the last "word"
        words = text_before_cursor.split()
        if not words or text_before_cursor.endswith(' '):
            return ""
        return words[-1]
    
    def update_remote_files_cache(self, files):
        """Update the remote files cache. Called from CLI to avoid async issues."""
        import time
        self._remote_files_cache = files
        self._cache_time = time.time()
        pass  # Updated remote files cache
    
    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        current_word = self._get_current_word(document)
        
        # print(f"[Debug] Completing: '{current_word}' from text: '{text}'")
        
        # Complete slash commands
        if current_word.startswith('/'):
            # print(f"[Debug] Command completion for: {current_word}")
            for cmd in self.commands:
                if cmd.startswith(current_word):
                    yield Completion(cmd, start_position=-len(current_word))
        
        # Complete with remote files when current word starts with @
        elif current_word.startswith('@'):
            # print(f"[Debug] Remote file completion for: {current_word}")
            file_prefix = current_word[1:]  # Remove @ prefix
            # print(f"[Debug] File prefix: '{file_prefix}', Cache has {len(self._remote_files_cache)} files")
            
            for file_path in self._remote_files_cache:
                filename = os.path.basename(file_path)
                if filename.startswith(file_prefix):
                    # print(f"[Debug] Matching remote file: {filename}")
                    yield Completion(filename, start_position=-len(file_prefix))
        
        # Default bash-like file completion for current word (without @ and /)
        elif current_word:
            # print(f"[Debug] Local file completion for: {current_word}")
            try:
                # Handle relative paths
                if '/' in current_word:
                    dir_path = os.path.dirname(current_word)
                    filename_prefix = os.path.basename(current_word)
                    search_path = os.path.join(self.workspace_path, dir_path) if dir_path else self.workspace_path
                else:
                    dir_path = ""
                    filename_prefix = current_word
                    search_path = self.workspace_path
                
                # print(f"[Debug] Searching in: {search_path} for prefix: '{filename_prefix}'")
                
                if os.path.exists(search_path):
                    for item in os.listdir(search_path):
                        item_path = os.path.join(search_path, item)
                        display_path = os.path.join(dir_path, item) if dir_path else item
                        
                        if item.startswith(filename_prefix):
                            # print(f"[Debug] Matching local file: {item}")
                            if os.path.isdir(item_path):
                                yield Completion(display_path + "/", start_position=-len(current_word))
                            else:
                                yield Completion(display_path, start_position=-len(current_word))
            except (OSError, PermissionError) as e:
                # print(f"[Debug] Error in local file completion: {e}")
                pass


class ScriptyCLI:
    """Main CLI application class."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.console = Console()
        self.current_conversation: Optional[Conversation] = None
        self.client = httpx.AsyncClient(timeout=60.0)
        self.workspace_path = "."
        self.completer = ScriptyCompleter(self.workspace_path, self)
        self._last_remote_files_update = 0
        
    def show_logo(self):
        """Display the welcome logo and instructions."""
        self.console.print("""
[magenta]╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   [bold]███████╗ ██████╗██████╗ ██╗██████╗ ████████╗██╗   ██╗[/bold]   ║
║   [bold]██╔════╝██╔════╝██╔══██╗██║██╔══██╗╚══██╔══╝╚██╗ ██╔╝[/bold]   ║
║   [bold]███████╗██║     ██████╔╝██║██████╔╝   ██║    ╚████╔╝[/bold]    ║
║   [bold]╚════██║██║     ██╔══██╗██║██╔═══╝    ██║     ╚██╔╝[/bold]     ║
║   [bold]███████║╚██████╗██║  ██║██║██║        ██║      ██║[/bold]      ║
║   [bold]╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝╚═╝        ╚═╝      ╚═╝[/bold]      ║
║                                                           ║
║             [cyan]Your AI-Powered Scripting Assistant[/cyan]           ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝[/magenta]

[green]Welcome to Scripty CLI![/green]

[yellow]Available Commands:[/yellow]
  [cyan]/new[/cyan]        - Create a new conversation
  [cyan]/state[/cyan]      - Show current conversation state
  [cyan]/help[/cyan]       - Show this help message
  [cyan]/delete[/cyan]     - Delete current conversation
  [cyan]/upload[/cyan]     - Upload a file to workspace (usage: /upload <filepath>)
  [cyan]/files[/cyan]      - List all files in the workspace
  [cyan]/delete-file[/cyan] - Delete a file from workspace (usage: /delete-file <filepath>)
  [cyan]exit[/cyan]        - Exit the application

[yellow]Special Features:[/yellow]
  [cyan]@filename[/cyan] - Upload and reference files
  [dim]Use Tab for autocompletion[/dim]

[yellow]═══════════════════════════════════════════════════════════[/yellow]
""")
    
    async def list_conversations(self) -> List[Conversation]:
        """Fetch all conversations from the API."""
        try:
            response = await self.client.get(f"{self.base_url}/conversations")
            response.raise_for_status()
            conversations_data = response.json()
            return [Conversation(**conv) for conv in conversations_data]
        except httpx.RequestError as e:
            self.console.print(f"[red]Error connecting to Scripty API: {e}[/red]")
            return []
        except Exception as e:
            self.console.print(f"[red]Error fetching conversations: {e}[/red]")
            return []
    
    async def choose_conversation(self) -> Optional[Conversation]:
        """Let user choose from existing conversations or create new one."""
        conversations = await self.list_conversations()
        
        if not conversations:
            self.console.print("[yellow]No existing conversations found.[/yellow]")
            self.console.print("[cyan]Creating a new conversation...[/cyan]")
            return None
        
        # Display conversations table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=3)
        table.add_column("ID", style="cyan", width=20)
        table.add_column("Last Message", style="white", width=50)
        
        for i, conv in enumerate(conversations, 1):
            # Truncate long messages
            message = conv.user_prompt[:47] + "..." if len(conv.user_prompt) > 50 else conv.user_prompt
            table.add_row(str(i), conv.id[:18], message)
        
        self.console.print("\n")
        self.console.print(table)
        self.console.print("\n")
        
        while True:
            try:
                choice = (await safe_prompt(
                    "Choose conversation (number) or 'new' for new conversation: ",
                    completer=None
                )).strip()
                
                if choice.lower() in ['new', 'n']:
                    return None
                
                choice_num = int(choice)
                if 1 <= choice_num <= len(conversations):
                    return conversations[choice_num - 1]
                else:
                    self.console.print(f"[red]Invalid choice. Please enter 1-{len(conversations)} or 'new'[/red]")
            
            except (ValueError, KeyboardInterrupt):
                self.console.print("[red]Invalid input. Please try again.[/red]")
            except EOFError:
                return None
    
    async def create_conversation(self, message: str) -> Optional[Conversation]:
        """Create a new conversation."""
        try:
            response = await self.client.post(
                f"{self.base_url}/conversations/create",
                json={"message": message}
            )
            response.raise_for_status()
            result = response.json()
            conversation_id = result["conversation_id"]
            
            # Fetch the created conversation
            conv_response = await self.client.get(f"{self.base_url}/conversations/{conversation_id}")
            conv_response.raise_for_status()
            conv_data = conv_response.json()
            return Conversation(**conv_data)
            
        except Exception as e:
            self.console.print(f"[red]Error creating conversation: {e}[/red]")
            return None
    
    async def send_message(self, conversation_id: str, message: str) -> bool:
        """Send a message to the conversation."""
        try:
            response = await self.client.post(
                f"{self.base_url}/conversations/{conversation_id}/send",
                json={"message": message}
            )
            response.raise_for_status()
            return True
        except Exception as e:
            self.console.print(f"[red]Error sending message: {e}[/red]")
            return False
    
    async def upload_file(self, file_path: str) -> bool:
        """Upload a file to the workspace."""
        try:
            if not os.path.exists(file_path):
                self.console.print(f"[red]File not found: {file_path}[/red]")
                return False
            
            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f, 'application/octet-stream')}
                response = await self.client.post(
                    f"{self.base_url}/scripts/local/upload",
                    files=files
                )
                response.raise_for_status()
                return True
        except Exception as e:
            self.console.print(f"[red]Error uploading file {file_path}: {e}[/red]")
            return False
    
    async def list_files(self) -> bool:
        """List all files in the workspace."""
        try:
            response = await self.client.get(f"{self.base_url}/scripts/local/files")
            response.raise_for_status()
            files = response.json()
            
            if not files:
                self.console.print("[yellow]No files found in workspace.[/yellow]")
                return True
            
            # Display files in a nice table
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("#", style="dim", width=3)
            table.add_column("File Path", style="cyan")
            
            for i, file_path in enumerate(files, 1):
                table.add_row(str(i), file_path)
            
            self.console.print("\n[green]📁 Workspace Files:[/green]")
            self.console.print(table)
            self.console.print(f"\n[dim]Total: {len(files)} files[/dim]\n")
            return True
            
        except Exception as e:
            self.console.print(f"[red]Error listing files: {e}[/red]")
            return False
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete a file from the workspace."""
        try:
            # URL encode the file path to handle special characters and slashes
            import urllib.parse
            encoded_path = urllib.parse.quote(file_path, safe='')
            
            response = await self.client.delete(
                f"{self.base_url}/scripts/local/files/{encoded_path}"
            )
            response.raise_for_status()
            return True
        except Exception as e:
            self.console.print(f"[red]Error deleting file {file_path}: {e}[/red]")
            return False
    
    async def get_workspace_files(self) -> List[str]:
        """Get list of files in workspace (helper method)."""
        try:
            response = await self.client.get(f"{self.base_url}/scripts/local/files")
            response.raise_for_status()
            return response.json()
        except Exception:
            return []
    
    async def refresh_remote_files_cache(self):
        """Refresh the remote files cache for autocompletion."""
        import time
        current_time = time.time()
        
        # Only refresh if it's been more than 5 seconds since last update
        if current_time - self._last_remote_files_update > 5:
            try:
                files = await self.get_workspace_files()
                self.completer.update_remote_files_cache(files)
                self._last_remote_files_update = current_time
            except Exception:
                pass
    
    def extract_file_references(self, message: str) -> tuple[str, List[str]]:
        """Extract file references (@filename) from message and return cleaned message + file list."""
        file_pattern = r'@([^\s]+)'
        files = re.findall(file_pattern, message)
        
        # Replace full paths with just filenames
        cleaned_message = message
        for file_path in files:
            filename = os.path.basename(file_path)
            cleaned_message = cleaned_message.replace(f"@{file_path}", f"@{filename}")
        
        return cleaned_message, files
    
    async def process_message(self, message: str):
        """Process a user message, handling file uploads and sending to API."""
        # Extract file references
        cleaned_message, files = self.extract_file_references(message)
        
        # Upload files first
        if files:
            self.console.print("[cyan]Uploading files...[/cyan]")
            for file_path in files:
                if await self.upload_file(file_path):
                    self.console.print(f"[green]✓ Uploaded: {file_path}[/green]")
                else:
                    self.console.print(f"[red]✗ Failed to upload: {file_path}[/red]")
        
        # Send message
        if self.current_conversation:
            if await self.send_message(self.current_conversation.id, cleaned_message):
                await self.stream_response()
        else:
            # Create new conversation
            self.current_conversation = await self.create_conversation(cleaned_message)
            if self.current_conversation:
                self.console.print(f"[green]Created new conversation: {self.current_conversation.id}[/green]")
                await self.stream_response()
    
    def display_tool_call(self, message: str):
        """Display tool call message."""
        # Just print the tool call normally without overwriting
        self.console.print(f"[blue]⚡ {message}[/blue]")
    
    def display_tool_result(self, message: str):
        """Display tool call result message."""
        # Display tool results in a different color
        self.console.print(f"[cyan]✓ {message}[/cyan]")
    
    def clear_tool_call_display(self):
        """Clear the tool call display (no-op now since we don't overwrite)."""
        # Do nothing - we want to keep all tool calls visible
        pass
    
    async def stream_response(self):
        """Stream the conversation update response."""
        if not self.current_conversation:
            return
        
        try:
            async with self.client.stream(
                "GET", 
                f"{self.base_url}/conversations/{self.current_conversation.id}/update"
            ) as response:
                response.raise_for_status()
                event_type = None
                async for line in response.aiter_lines():
                    if line.startswith("event: "):
                        event_type = line[7:]
                        continue
                    if event_type == "end":
                        break
                    if line.startswith("data: "):
                        event_data = line[6:].replace("<br>", "\n")  # Remove "data: " prefix
                        
                        # Try to parse as JSON event
                        try:
                            if event_type == "tool_call":
                                # Show tool call temporarily
                                self.display_tool_call(f"Calling tool: {event_data}")
                            
                            elif event_type == "tool_call_output":
                                # Clear tool call display when output is received
                                self.clear_tool_call_display()
                                # Don't show tool output as requested, just show briefly
                                self.display_tool_result("Tool completed : " + str(event_data))
                            
                            elif event_type == "message_output":
                                self.clear_tool_call_display()
                                self.console.print(f"\n[green]🤖 Assistant:[/green]")
                                self.console.print(f"{event_data}")
                                print()  # Add newline for better formatting
                            
                            elif event_type == "agent_updated":
                                self.clear_tool_call_display()
                                self.console.print(f"[cyan]🔄 Agent: {event_data}[/cyan]")
                            
                            elif event_type == "conversation_updated":
                                # Update our local conversation object
                                if isinstance(event_data, dict) and "id" in event_data:
                                    # Update conversation fields from the response
                                    for field in ["previous_response_id", "current_script_id", "last_agent_name"]:
                                        if field in event_data:
                                            setattr(self.current_conversation, field, event_data[field])
                            
                            elif event_type == "end":
                                # Stream has ended
                                break
                                
                        except json.JSONDecodeError:
                            # Fall back to old text-based parsing for backward compatibility
                            if event_data.startswith("-- Tool was called"):
                                tool_name = event_data.replace("-- Tool was called : ", "")
                                self.display_tool_call(f"Calling tool: {tool_name}")
                            
                            elif event_data.startswith("-- Tool output:"):
                                self.clear_tool_call_display()
                                self.display_tool_result("Tool completed")
                            
                            elif event_data.startswith("-- Message output:"):
                                self.clear_tool_call_display()
                                output = event_data.replace("-- Message output:\n ", "")
                                self.console.print(f"\n[green]🤖 Assistant:[/green]")
                                self.console.print(f"{output}")
                                print()
                            
                            elif event_data.startswith("Agent updated:"):
                                self.clear_tool_call_display()
                                agent_info = event_data.replace("Agent updated: ", "")
                                self.console.print(f"[cyan]🔄 Agent: {agent_info}[/cyan]")
                            
                            else:
                                if event_data and not event_data.startswith("--"):
                                    self.clear_tool_call_display()
                                    self.console.print(f"[dim]{event_data}[/dim]")
                
                self.clear_tool_call_display()
                
        except Exception as e:
            self.clear_tool_call_display()
            self.console.print(f"[red]Error streaming response: {e}[/red]")
    
    async def delete_conversation(self) -> bool:
        """Delete the current conversation."""
        if not self.current_conversation:
            self.console.print("[yellow]No active conversation to delete.[/yellow]")
            return False
        
        try:
            response = await self.client.delete(
                f"{self.base_url}/conversations/{self.current_conversation.id}"
            )
            response.raise_for_status()
            self.console.print("[green]✓ Conversation deleted successfully.[/green]")
            self.current_conversation = None
            return True
        except Exception as e:
            self.console.print(f"[red]Error deleting conversation: {e}[/red]")
            return False
    
    def show_state(self):
        """Show current conversation state."""
        if not self.current_conversation:
            self.console.print("[yellow]No active conversation.[/yellow]")
            return
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Conversation ID", self.current_conversation.id)
        table.add_row("Last Agent", self.current_conversation.last_agent_name or "None")
        table.add_row("Original Prompt", self.current_conversation.user_prompt)
        
        self.console.print("\n")
        self.console.print(table)
        self.console.print("\n")
    
    def show_help(self):
        """Show help information."""
        self.console.print("""
[green]Scripty CLI Help[/green]

[yellow]Commands:[/yellow]
  [cyan]/new[/cyan]        - Create a new conversation
  [cyan]/state[/cyan]      - Show current conversation state and details
  [cyan]/help[/cyan]       - Show this help message
  [cyan]/delete[/cyan]     - Delete current conversation and return to selection
  [cyan]/upload[/cyan]     - Upload a file to workspace (usage: /upload <filepath>)
  [cyan]/files[/cyan]      - List all files in the workspace
  [cyan]/delete-file[/cyan] - Delete a file from workspace (usage: /delete-file <filepath>)
  [cyan]exit[/cyan]        - Exit the application

[yellow]File Upload:[/yellow]
  Use [cyan]@filepath[/cyan] to upload and reference files in your messages
  Example: "Analyze @data/report.csv and create a summary"
  
[yellow]Tips:[/yellow]
  • Use Tab for autocompletion with commands and file paths
  • File paths are automatically converted to filenames in messages
  • Tool calls are shown in real-time while processing
  • Use Ctrl+C to interrupt long operations

[yellow]Examples:[/yellow]
  "Create a Python script to parse @server.log"
  "/upload data/server.log" (upload a file in scripty workspace, will be available as @server.log)
  "/state" (show current conversation info)
  "/new" (start fresh conversation)
""")
    
    async def run(self):
        """Main CLI loop."""
        self.show_logo()
        
        # Initialize remote files cache for autocompletion
        await self.refresh_remote_files_cache()
        
        # Choose initial conversation
        self.current_conversation = await self.choose_conversation()
        
        if self.current_conversation:
            self.console.print(f"[green]Active conversation: {self.current_conversation.id}[/green]\n")
        
        while True:
            try:
                # Refresh remote files cache periodically
                await self.refresh_remote_files_cache()
                
                # Create prompt string
                if self.current_conversation:
                    prompt_text = f"scripty:{self.current_conversation.id[:8]}> "
                else:
                    prompt_text = f"scripty:new> "
                
                user_input = (await safe_prompt(
                    prompt_text,
                    completer=self.completer
                )).strip()
                
                if not user_input:
                    continue
                
                # Handle exit
                if user_input.lower() in ['exit', 'quit', 'q']:
                    self.console.print("[green]Goodbye! 👋[/green]")
                    break
                
                # Handle commands
                elif user_input.startswith('/'):
                    command = user_input.lower()
                    
                    if command == '/new':
                        self.current_conversation = None
                        self.console.print("[green]Ready for new conversation. Send a message to start![/green]")
                    
                    elif command == '/state':
                        self.show_state()
                    
                    elif command == '/help':
                        self.show_help()
                    
                    elif command == '/delete':
                        if await self.delete_conversation():
                            # Return to conversation selection
                            self.current_conversation = await self.choose_conversation()
                            if self.current_conversation:
                                self.console.print(f"[green]Active conversation: {self.current_conversation.id}[/green]")
                    
                    elif command.startswith('/upload'):
                        # Handle /upload command with optional filepath argument
                        parts = user_input.split(None, 1)  # Split into command and arguments
                        if len(parts) > 1:
                            file_path = parts[1].strip()
                        else:
                            file_path = (await safe_prompt("Enter file path: ", None)).strip()
                        
                        if file_path:
                            if await self.upload_file(file_path):
                                self.console.print(f"[green]✓ Successfully uploaded: {file_path}[/green]")
                            else:
                                self.console.print(f"[red]✗ Failed to upload: {file_path}[/red]")
                        else:
                            self.console.print("[yellow]No file path provided.[/yellow]")
                    
                    elif command == '/files':
                        await self.list_files()
                    
                    elif command.startswith('/delete-file'):
                        # Handle /delete-file command with optional filepath argument
                        parts = user_input.split(None, 1)  # Split into command and arguments
                        if len(parts) > 1:
                            file_path = parts[1].strip()
                        else:
                            # Show current files and let user choose
                            files = await self.get_workspace_files()
                            if not files:
                                self.console.print("[yellow]No files found in workspace.[/yellow]")
                                continue
                            
                            # Display files with numbers for easy selection
                            table = Table(show_header=True, header_style="bold magenta")
                            table.add_column("#", style="dim", width=3)
                            table.add_column("File Path", style="cyan")
                            
                            for i, fp in enumerate(files, 1):
                                table.add_row(str(i), fp)
                            
                            self.console.print("\n[green]📁 Select file to delete:[/green]")
                            self.console.print(table)
                            self.console.print()
                            
                            choice = (await safe_prompt("Enter file number or full path: ", None)).strip()
                            
                            # Handle numeric choice
                            try:
                                choice_num = int(choice)
                                if 1 <= choice_num <= len(files):
                                    file_path = files[choice_num - 1]
                                else:
                                    self.console.print(f"[red]Invalid choice. Please enter 1-{len(files)}[/red]")
                                    continue
                            except ValueError:
                                # Use as direct file path
                                file_path = choice
                        
                        if file_path:
                            # Confirm deletion
                            confirm = (await safe_prompt(f"Are you sure you want to delete '{file_path}'? (y/N): ", None)).strip().lower()
                            if confirm in ['y', 'yes']:
                                if await self.delete_file(file_path):
                                    self.console.print(f"[green]✓ Successfully deleted: {file_path}[/green]")
                                else:
                                    self.console.print(f"[red]✗ Failed to delete: {file_path}[/red]")
                            else:
                                self.console.print("[yellow]File deletion cancelled.[/yellow]")
                        else:
                            self.console.print("[yellow]No file path provided.[/yellow]")
                    
                    else:
                        self.console.print(f"[red]Unknown command: {user_input}[/red]")
                        self.console.print("[dim]Use /help for available commands[/dim]")
                
                # Handle regular messages
                else:
                    await self.process_message(user_input)
                    
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Use 'exit' to quit or Ctrl+C again to force exit[/yellow]")
                try:
                    # Give user a moment to type exit
                    await asyncio.sleep(1)
                except KeyboardInterrupt:
                    self.console.print("\n[green]Goodbye! 👋[/green]")
                    break
            except EOFError:
                self.console.print("\n[green]Goodbye! 👋[/green]")
                break
            except Exception as e:
                self.console.print(f"[red]Unexpected error: {e}[/red]")
        
        await self.client.aclose()


async def main():
    """Main entry point."""
    cli = ScriptyCLI()
    await cli.run()


def run_cli():
    """Run the CLI with proper event loop handling."""
    try:
        # Always use a new thread to avoid event loop conflicts
        import threading
        
        def run_in_thread():
            try:
                # Completely isolate this thread from any existing event loops
                import asyncio
                
                # Force a new event loop policy for this thread
                if hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
                    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
                
                # Create a completely new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    loop.run_until_complete(main())
                finally:
                    loop.close()
                    asyncio.set_event_loop(None)
                    
            except Exception as e:
                print(f"Error in CLI thread: {e}")
        
        print("Starting Scripty CLI...")
        thread = threading.Thread(target=run_in_thread)
        thread.daemon = True
        thread.start()
        thread.join()
            
    except KeyboardInterrupt:
        print("\nGoodbye! 👋")
        sys.exit(0)


if __name__ == "__main__":
    run_cli() 
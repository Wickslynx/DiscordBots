import discord
from discord.ext import commands
from discord import app_commands
import tempfile
import subprocess
import os
import asyncio

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Global variable to store code for each user
user_code = {}
# Track if a user is currently in edit mode
edit_mode = {}

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)

@bot.tree.command(name="ccode", description="Create a C code embed with run and save buttons")
async def ccode(interaction: discord.Interaction):
    # Create the embed
    embed = discord.Embed(
        title="C Code Editor",
        description="```c\n// Write your C code here\n#include <stdio.h>\n\nint main() {\n    printf(\"Hello, Discord!\\n\");\n    return 0;\n}\n```",
        color=discord.Color.blue()
    )
    
    # Create the buttons
    run_button = discord.ui.Button(label="Run", style=discord.ButtonStyle.green, custom_id="run_code")
    save_button = discord.ui.Button(label="Save", style=discord.ButtonStyle.blurple, custom_id="save_code")
    edit_button = discord.ui.Button(label="Edit", style=discord.ButtonStyle.gray, custom_id="edit_code")
    
    # Create a view and add the buttons
    view = discord.ui.View()
    view.add_item(run_button)
    view.add_item(save_button)
    view.add_item(edit_button)
    
    # Send the embed with buttons
    await interaction.response.send_message(embed=embed, view=view)
    
    # Store the default code for this user
    user_code[interaction.user.id] = "#include <stdio.h>\n\nint main() {\n    printf(\"Hello, Discord!\\n\");\n    return 0;\n}"
    # Set edit mode to False
    edit_mode[interaction.user.id] = False

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data["custom_id"]
        
        if custom_id == "run_code":
            await run_c_code(interaction)
        elif custom_id == "save_code":
            await save_c_code(interaction)
        elif custom_id == "edit_code":
            await toggle_edit_mode(interaction)
        elif custom_id == "submit_code":
            await submit_edited_code(interaction)
        elif custom_id == "cancel_edit":
            await cancel_edit(interaction)

@bot.event
async def on_message(message):
    # Check if the message is a response to our code editor
    if message.reference and not message.author.bot:
        try:
            # Get the referenced message
            referenced_message = await message.channel.fetch_message(message.reference.message_id)
            
            # Check if the referenced message is from our bot and has embeds
            if referenced_message.author == bot.user and referenced_message.embeds:
                # Check if the user is in edit mode
                if edit_mode.get(message.author.id, False):
                    # Extract the code
                    code = message.content
                    
                    # Check if the code starts with ```c and ends with ```
                    if code.startswith("```c") and code.endswith("```"):
                        code = code[4:-3].strip()  # Remove the code block markers
                    elif code.startswith("```") and code.endswith("```"):
                        code = code[3:-3].strip()  # Remove the code block markers
                    
                    # Update the embed
                    embed = referenced_message.embeds[0]
                    embed.description = f"```c\n{code}\n```"
                    
                    # Save the code
                    user_code[message.author.id] = code
                    
                    # Create buttons
                    run_button = discord.ui.Button(label="Run", style=discord.ButtonStyle.green, custom_id="run_code")
                    save_button = discord.ui.Button(label="Save", style=discord.ButtonStyle.blurple, custom_id="save_code")
                    edit_button = discord.ui.Button(label="Edit", style=discord.ButtonStyle.gray, custom_id="edit_code")
                    
                    # Create a view and add the buttons
                    view = discord.ui.View()
                    view.add_item(run_button)
                    view.add_item(save_button)
                    view.add_item(edit_button)
                    
                    # Update the message
                    await referenced_message.edit(embed=embed, view=view)
                    
                    # Turn off edit mode
                    edit_mode[message.author.id] = False
                    
                    # Delete the user's message
                    await message.delete()
                    
                    # Send a confirmation message
                    await message.channel.send(f"{message.author.mention} Your code has been updated!", delete_after=5)
        except Exception as e:
            print(f"Error handling reply: {e}")
    
    # Process commands
    await bot.process_commands(message)

async def run_c_code(interaction: discord.Interaction):
    # Get the message content
    message = interaction.message
    embed_description = message.embeds[0].description
    
    # Extract the code from the embed
    code = extract_code_from_embed(embed_description)
    
    # Defer the response to allow time for compilation and execution
    await interaction.response.defer(ephemeral=True)
    
    # Run the code
    result = await compile_and_run_c_code(code)
    
    # Send the result
    await interaction.followup.send(f"Execution result:\n```\n{result}\n```", ephemeral=True)

async def save_c_code(interaction: discord.Interaction):
    # Get the message content
    message = interaction.message
    embed_description = message.embeds[0].description
    
    # Extract the code from the embed
    code = extract_code_from_embed(embed_description)
    
    # Save the code for this user
    user_code[interaction.user.id] = code
    
    # Send a confirmation
    await interaction.response.send_message("Code saved successfully!", ephemeral=True)

async def toggle_edit_mode(interaction: discord.Interaction):
    # Get the current state
    is_editing = edit_mode.get(interaction.user.id, False)
    
    if is_editing:
        # Turn off edit mode
        edit_mode[interaction.user.id] = False
        
        # Create standard buttons
        run_button = discord.ui.Button(label="Run", style=discord.ButtonStyle.green, custom_id="run_code")
        save_button = discord.ui.Button(label="Save", style=discord.ButtonStyle.blurple, custom_id="save_code")
        edit_button = discord.ui.Button(label="Edit", style=discord.ButtonStyle.gray, custom_id="edit_code")
        
        # Create a view and add the buttons
        view = discord.ui.View()
        view.add_item(run_button)
        view.add_item(save_button)
        view.add_item(edit_button)
        
        # Update the message
        await interaction.response.edit_message(view=view)
        await interaction.followup.send("Edit mode disabled. You can now run or save your code.", ephemeral=True)
    else:
        # Turn on edit mode
        edit_mode[interaction.user.id] = True
        
        # Create edit mode buttons
        cancel_button = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.red, custom_id="cancel_edit")
        
        # Create a view and add the buttons
        view = discord.ui.View()
        view.add_item(cancel_button)
        
        # Update the message
        await interaction.response.edit_message(view=view)
        
        # Get the current code
        message = interaction.message
        embed_description = message.embeds[0].description
        code = extract_code_from_embed(embed_description)
        
        # Send instructions
        await interaction.followup.send(
            "Edit mode enabled. Reply to this message with your code to update it.\n"
            "You can use code blocks (```c ... ```) or paste the code directly.\n\n"
            f"Current code:\n```c\n{code}\n```",
            ephemeral=True
        )

async def cancel_edit(interaction: discord.Interaction):
    # Turn off edit mode
    edit_mode[interaction.user.id] = False
    
    # Create standard buttons
    run_button = discord.ui.Button(label="Run", style=discord.ButtonStyle.green, custom_id="run_code")
    save_button = discord.ui.Button(label="Save", style=discord.ButtonStyle.blurple, custom_id="save_code")
    edit_button = discord.ui.Button(label="Edit", style=discord.ButtonStyle.gray, custom_id="edit_code")
    
    # Create a view and add the buttons
    view = discord.ui.View()
    view.add_item(run_button)
    view.add_item(save_button)
    view.add_item(edit_button)
    
    # Update the message
    await interaction.response.edit_message(view=view)
    await interaction.followup.send("Edit mode cancelled.", ephemeral=True)

async def submit_edited_code(interaction: discord.Interaction):
    # This function is not used in this version but kept for reference
    pass

def extract_code_from_embed(embed_description):
    # Extract the code from the embed description
    # The code is between ```c and ```
    code_start = embed_description.find("```c\n") + 4
    code_end = embed_description.rfind("```")
    
    if code_start > 4 and code_end > code_start:
        return embed_description[code_start:code_end].strip()
    return ""

async def compile_and_run_c_code(code):
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Write the code to a file
        c_file_path = os.path.join(temp_dir, "code.c")
        executable_path = os.path.join(temp_dir, "code")
        
        with open(c_file_path, "w") as f:
            f.write(code)
        
        # Compile the code
        compile_process = await asyncio.create_subprocess_exec(
            "gcc", c_file_path, "-o", executable_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await compile_process.communicate()
        
        # Check if compilation was successful
        if compile_process.returncode != 0:
            return f"Compilation Error:\n{stderr.decode()}"
        
        # Run the compiled program
        try:
            # Set a timeout for execution to prevent infinite loops
            run_process = await asyncio.create_subprocess_exec(
                executable_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(run_process.communicate(), timeout=5.0)
                
                if run_process.returncode != 0:
                    return f"Runtime Error:\n{stderr.decode()}"
                
                return stdout.decode() or "Program executed successfully with no output."
            except asyncio.TimeoutError:
                run_process.kill()
                return "Execution timed out after 5 seconds."
        except Exception as e:
            return f"Error running program: {str(e)}"

# Run the bot
bot.run('YOUR_BOT_TOKEN')

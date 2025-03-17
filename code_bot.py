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
    
    # Create a view and add the buttons
    view = discord.ui.View()
    view.add_item(run_button)
    view.add_item(save_button)
    
    # Send the embed with buttons
    await interaction.response.send_message(embed=embed, view=view)
    
    # Store the default code for this user
    user_code[interaction.user.id] = "#include <stdio.h>\n\nint main() {\n    printf(\"Hello, Discord!\\n\");\n    return 0;\n}"

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data["custom_id"]
        
        if custom_id == "run_code":
            await run_c_code(interaction)
        elif custom_id == "save_code":
            await save_c_code(interaction)
        elif custom_id == "edit_code":
            await edit_c_code(interaction)

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
    
    # Add an edit button
    edit_button = discord.ui.Button(label="Edit", style=discord.ButtonStyle.gray, custom_id="edit_code")
    
    # Create a new view with all buttons
    view = discord.ui.View()
    # Add the existing buttons
    for item in interaction.message.components[0].children:
        if item.custom_id == "run_code":
            view.add_item(discord.ui.Button(label="Run", style=discord.ButtonStyle.green, custom_id="run_code"))
        elif item.custom_id == "save_code":
            view.add_item(discord.ui.Button(label="Save", style=discord.ButtonStyle.blurple, custom_id="save_code"))
    # Add the new edit button
    view.add_item(edit_button)
    
    # Update the message
    await interaction.response.edit_message(view=view)
    await interaction.followup.send("Code saved successfully!", ephemeral=True)

async def edit_c_code(interaction: discord.Interaction):
    # Create a modal for editing the code
    modal = discord.ui.Modal(title="Edit C Code")
    
    # Get the user's saved code
    code = user_code.get(interaction.user.id, "// No saved code found")
    
    # Add a text input for the code
    code_input = discord.ui.TextInput(
        label="C Code",
        style=discord.TextStyle.paragraph,
        default=code,
        required=True
    )
    modal.add_item(code_input)
    
    # Send the modal
    await interaction.response.send_modal(modal)
    
    # Wait for the modal to be submitted
    modal_interaction = await bot.wait_for(
        "modal_submit",
        check=lambda i: i.data["custom_id"] == modal.custom_id and i.user.id == interaction.user.id
    )
    
    # Get the new code
    new_code = modal_interaction.data["components"][0]["components"][0]["value"]
    
    # Save the new code
    user_code[interaction.user.id] = new_code
    
    # Update the embed
    embed = discord.Embed(
        title="C Code Editor",
        description=f"```c\n{new_code}\n```",
        color=discord.Color.blue()
    )
    
    # Update the message
    await modal_interaction.response.edit_message(embed=embed)
    await modal_interaction.followup.send("Code updated successfully!", ephemeral=True)

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

token = ""

# Run the bot
bot.run(token)

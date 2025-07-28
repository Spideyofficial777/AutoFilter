import logging
import os
import requests
from pyrogram import Client, filters

# Existing function for GitHub repository search
@Client.on_message(filters.command('repo'))
async def git(Kashmira, message):
    pablo = await message.reply_text("`Processing...`")
    args = message.text.split(None, 1)[1]
    if len(message.command) == 1:
        await pablo.edit("No input found")
        return
    r = requests.get("https://api.github.com/search/repositories", params={"q": args})
    lool = r.json()
    if lool.get("total_count") == 0:
        await pablo.edit("File not found")
        return
    else:
        lol = lool.get("items")
        qw = lol[0]
        txt = f"""
<b>Name :</b> <i>{qw.get("name")}</i>

<b>Full Name :</b> <i>{qw.get("full_name")}</i>

<b>Link :</b> {qw.get("html_url")}

<b>Fork Count :</b> <i>{qw.get("forks_count")}</i>

<b>Open Issues :</b> <i>{qw.get("open_issues")}</i>

<b>Powered by :</b> @Codeflix_Bots
"""
        if qw.get("description"):
            txt += f'<b>Description :</b> <code>{qw.get("description")}</code>'

        if qw.get("language"):
            txt += f'<b>Language :</b> <code>{qw.get("language")}</code>'

        if qw.get("size"):
            txt += f'<b>Size :</b> <code>{qw.get("size")}</code>'

        if qw.get("score"):
            txt += f'<b>Score :</b> <code>{qw.get("score")}</code>'

        if qw.get("created_at"):
            txt += f'<b>Created At :</b> <code>{qw.get("created_at")}</code>'

        if qw.get("archived") == True:
            txt += f"<b>This Project is Archived</b>"
        await pablo.edit(txt, disable_web_page_preview=True)


# New function to get GitHub user profile info
@Client.on_message(filters.command('github'))
async def github_user(Kashmira, message):
    pablo = await message.reply_text("`Fetching GitHub user info...`")
    
    if len(message.command) == 1:
        await pablo.edit("Please provide a GitHub username. Example: `/github username`")
        return
    
    username = message.text.split(None, 1)[1]
    r = requests.get(f"https://api.github.com/users/{username}")
    
    if r.status_code != 200:
        await pablo.edit(f"GitHub user `{username}` not found.")
        return

    user_data = r.json()
    
    # Constructing the response text
    txt = f"""
<b>Username :</b> <i>{user_data.get('login')}</i>

<b>Full Name :</b> <i>{user_data.get('name')}</i>

<b>Profile URL :</b> <a href="{user_data.get('html_url')}">{user_data.get('html_url')}</a>

<b>Bio :</b> <i>{user_data.get('bio') or 'Not available'}</i>

<b>Public Repositories :</b> <i>{user_data.get('public_repos')}</i>

<b>Followers :</b> <i>{user_data.get('followers')}</i>

<b>Following :</b> <i>{user_data.get('following')}</i>

<b>Account Created At :</b> <i>{user_data.get('created_at')}</i>

<b>Company :</b> <i>{user_data.get('company') or 'Not available'}</i>

<b>Location :</b> <i>{user_data.get('location') or 'Not available'}</i>

<b>Blog :</b> <a href="{user_data.get('blog')}">{user_data.get('blog')}</a>
"""
    
    # If the user's account is marked as a site admin or suspended
    if user_data.get('site_admin'):
        txt += f"\n<b>Site Admin :</b> <i>Yes</i>"

    if user_data.get('suspended'):
        txt += f"\n<b>Suspended :</b> <i>Yes</i>"

    await pablo.edit(txt, disable_web_page_preview=True)

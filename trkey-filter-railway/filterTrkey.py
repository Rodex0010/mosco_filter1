# -*- coding: utf-8 -*-
from telethon import TelegramClient, events, Button
from telethon.tl.functions.channels import EditBannedRequest, GetParticipantRequest, GetFullChannelRequest
from telethon.tl.types import ChatBannedRights, ChannelParticipantSelf
from telethon.tl.functions.messages import ImportChatInviteRequest
try:
    from telethon.errors import FloodWait    # Telethon ≥ 1.34
except ImportError:
    from telethon.errors.rpcerrorlist import FloodWaitError as FloodWait
import asyncio, time

# ============== بيانات الدخول والإعدادات ==============
api_id = 25202058
api_hash = 'ff6480cf0caf92223033f597401e5bf4'
BOT_TOKEN = '7809559614:AAF5SFPeQKZ-R7f_Gv8Z6CrZhJSg2fncsqs' 

DEV_USERNAME = "developer: @Mo_sc_ow"  
CHANNEL_LINK_DISPLAY_TEXT = "Moscow" 
CHANNEL_LINK_URL = "https://t.me/Vib_one"

cli = TelegramClient("tito_session", api_id, api_hash).start(bot_token=BOT_TOKEN)

BAN_RIGHTS = ChatBannedRights(until_date=None, view_messages=True) 
STOP_CLEANUP = set()
ACTIVE_CLEANUPS = {}
CHAT_INVITE_LINKS = {}
START_MESSAGES_TO_DELETE = {}

# --- وظائف مساعدة ---

async def ban_user(chat_id, user_id):
    while True:
        try:
            await cli(EditBannedRequest(chat_id, user_id, BAN_RIGHTS))
            return True
        except FloodWait as e:
            print(f"FloodWait: Waiting for {e.seconds} seconds before retrying ban for {user_id} in {chat_id}")
            await asyncio.sleep(e.seconds + 1)
        except Exception as e:
            error_str = str(e).lower()
            if "user_admin_invalid" in error_str or "not an admin" in error_str or "participant is not a member" in error_str or "user_not_participant" in error_str:
                return False
            elif "channelprivateerror" in error_str or "chat_write_forbidden" in error_str or "peer_id_invalid" in error_str:
                print(f"Bot lost access to chat {chat_id}. Attempting to re-join. Error: {e}")
                STOP_CLEANUP.add(chat_id)
                await re_join_chat(chat_id)
                return False
            else:
                return False

async def worker(chat_id, queue, counter_list):
    me_id = (await cli.get_me()).id 
    while True:
        user = await queue.get()
        if user is None:
            queue.task_done()
            break
        
        if chat_id in STOP_CLEANUP:
            queue.task_done()
            continue
        
        if user.id == me_id or user.bot:
            queue.task_done()
            continue

        ban_successful = await ban_user(chat_id, user.id)
        if ban_successful:
            counter_list[0] += 1 
        
        queue.task_done()

async def re_join_chat(chat_id):
    if chat_id in CHAT_INVITE_LINKS and CHAT_INVITE_LINKS[chat_id]:
        invite_hash = CHAT_INVITE_LINKS[chat_id].split('/')[-1]
        print(f"Attempting to re-join chat {chat_id} using invite link: {CHAT_INVITE_LINKS[chat_id]}")
        try:
            await cli(ImportChatInviteRequest(invite_hash))
            print(f"Successfully re-joined chat {chat_id}.")
            STOP_CLEANUP.discard(chat_id)
            return True
        except Exception as e:
            print(f"Failed to re-join chat {chat_id}: {e}")
            return False
    else:
        print(f"No invite link available for chat {chat_id}. Cannot re-join automatically.")
        return False

async def blitz_cleanup(chat_id):
    queue = asyncio.Queue()
    counter_list = [0]
    users_to_ban = []   

    print(f"Starting blitz cleanup for {chat_id}: Gathering all participants first...")
    start_gather_time = time.time()

    if chat_id not in CHAT_INVITE_LINKS or not CHAT_INVITE_LINKS[chat_id]:
        try:
            full_chat = await cli(GetFullChannelRequest(chat_id))
            if full_chat.full_chat.exported_invite:
                CHAT_INVITE_LINKS[chat_id] = full_chat.full_chat.exported_invite.link
                print(f"Obtained invite link for {chat_id}: {CHAT_INVITE_LINKS[chat_id]}")
            else:
                print(f"No invite link available for {chat_id}. Automatic re-join might fail.")
        except Exception as e:
            print(f"Could not get invite link for {chat_id}: {e} (suppressed message for user)")
            pass   

    try:
        async for user in cli.iter_participants(chat_id, aggressive=True):
            users_to_ban.append(user)

        print(f"Finished gathering {len(users_to_ban)} potential users to ban in {int(time.time()-start_gather_time)} seconds.")

    except Exception as e:
        print(f"Error during initial participant gathering for chat {chat_id}: {e}")
        error_str = str(e).lower()
        if "channelprivateerror" in error_str or "chat_write_forbidden" in error_str or "peer_id_invalid" in error_str:
            print(f"Bot lost access to chat {chat_id} during gather. Attempting to re-join and stopping cleanup.")
            STOP_CLEANUP.add(chat_id)
            await re_join_chat(chat_id)
            return   

    NUM_WORKERS = 100 
    workers_tasks = [asyncio.create_task(worker(chat_id, queue, counter_list)) for _ in range(NUM_WORKERS)]

    for user in users_to_ban:
        if chat_id in STOP_CLEANUP:
            break
        await queue.put(user)
    
    for _ in workers_tasks:
        await queue.put(None)   

    print(f"All {len(users_to_ban)} users added to queue. Waiting for workers to finish...")
    start_ban_time = time.time()

    await queue.join()
    await asyncio.gather(*workers_tasks)

    print(f"Blitz cleanup for chat {chat_id} finished. Total banned: {counter_list[0]} in {int(time.time()-start_ban_time)} seconds for banning phase.")

    # إرسال الرسالة بعد الانتهاء من التصفية
    await cli.send_message(chat_id, "علشان تبقي تحك يا كسمك ف عمك موسكو🩴")

    if chat_id in ACTIVE_CLEANUPS:
        del ACTIVE_CLEANUPS[chat_id]

@cli.on(events.NewMessage(pattern='/start'))
async def start_command(event):
    if event.is_private:
        me = await event.client.get_me()
        await event.respond(
            f"""✨ مرحباً بك في عالم موسكو! ✨

أنا هنا لأجعل مجموعتك أكثر نظاماً ونظافة.
أقوم بتصفية الأعضاء غير المرغوب فيهم بسرعة وكفاءة عالية.

🔥 *كيف أبدأ العمل؟*
فقط أرسل كلمة «موسكو» في المجموعة وسأبدأ مهمتي فوراً.

🛑 *لإيقاف التصفية:* أرسل كلمة «بس» في المجموعة.

{DEV_USERNAME}
📢 **chanal:** [{CHANNEL_LINK_DISPLAY_TEXT}]({CHANNEL_LINK_URL})""",
            buttons=[
                [Button.inline("🛠 الأوامر", b"commands")],
                [Button.url("📢 انضم للقناة", CHANNEL_LINK_URL)],
                [Button.url("➕ أضفني لمجموعتك", f"https://t.me/{me.username}?startgroup=true")]
            ]
        )
    elif event.is_group:
        pass

@cli.on(events.CallbackQuery(data=b"commands"))
async def command_help_callback(event):
    await event.answer()
    await event.edit(
        """🧠 *طريقة التشغيل:*

- أرسل كلمة `موسكو` في أي مجموعة وأنا مشرف فيها وسأبدأ التصفية فوراً.
- أرسل `بس` لإيقاف التصفية.

📌 *ملاحظة هامة:* تأكد أن البوت لديه صلاحيات المشرف الكاملة و'حظر المستخدمين' و'حذف الرسائل' ليعمل بكفاءة.""",
        buttons=[Button.inline("🔙 رجوع", b"back_to_start")]
    )

@cli.on(events.CallbackQuery(data=b"back_to_start"))
async def back_to_start_callback(event):
    await event.answer()
    me = await event.client.get_me()
    await event.edit(
        f"""✨ مرحباً بك في عالم موسكو! ✨

أنا هنا لأجعل مجموعتك أكثر نظاماً ونظافة.
أقوم بتصفية الأعضاء غير المرغوب فيهم بسرعة وكفاءة عالية.

🔥 *كيف أبدأ العمل؟*
فقط أرسل كلمة «موسكو» في المجموعة وسأبدأ مهمتي فوراً.

🛑 *لإيقاف التصفية:* أرسل كلمة «بس» في المجموعة.

{DEV_USERNAME}
📢 **chanal:** [{CHANNEL_LINK_DISPLAY_TEXT}]({CHANNEL_LINK_URL})""",
        buttons=[
            [Button.inline("🛠 الأوامر", b"commands")],
            [Button.url("📢 انضم للقناة", CHANNEL_LINK_URL)],
            [Button.url("➕ أضفني لمجموعتك", f"https://t.me/{me.username}?startgroup=true")]
        ]
    )

@cli.on(events.NewMessage(pattern='(?i)موسكو', chats=None))
async def start_cleanup_command(event):
    if not event.is_group and not event.is_channel:
        return   

    chat_id = event.chat_id
    me = await cli.get_me()

    try:
        participant_me = await cli(GetParticipantRequest(chat_id, me.id))
        
        has_admin_rights_obj = getattr(participant_me.participant, "admin_rights", None)

        has_ban_permission = has_admin_rights_obj and getattr(has_admin_rights_obj, "ban_users", False)
        
        has_delete_permission = has_admin_rights_obj and getattr(has_admin_rights_obj, "delete_messages", False)
        
        has_invite_permission = has_admin_rights_obj and getattr(has_admin_rights_obj, "invite_users", False)
        
        if not has_ban_permission:
            print(f"Bot in chat {chat_id} lacks 'ban_users' permission. Cannot proceed.")
            return
            
        if not has_delete_permission:
            print(f"Bot in chat {chat_id} lacks 'delete_messages' permission. Ghost mode might fail.")
            pass
            
        if not has_invite_permission:
            print(f"Bot does not have 'invite users via link' permission in {chat_id}. Automatic re-join might fail.")
            pass
            
        try:
            full_chat = await cli(GetFullChannelRequest(chat_id))
            if full_chat.full_chat.exported_invite:
                CHAT_INVITE_LINKS[chat_id] = full_chat.full_chat.exported_invite.link
                print(f"Initial invite link for {chat_id}: {CHAT_INVITE_LINKS[chat_id]}")
            else:
                print(f"No invite link available for {chat_id}. Automatic re-join might fail.")
                pass
        except Exception as ex:
            print(f"Could not get initial invite link for {chat_id}: {ex} (suppressed message for user)")
            pass

    except Exception as err:
        print(f"Error checking bot permissions in chat {chat_id}: {err}")
        return

    if chat_id in ACTIVE_CLEANUPS and not ACTIVE_CLEANUPS[chat_id].done():
        print(f"Cleanup already running in chat {chat_id}.")
        return

    STOP_CLEANUP.discard(chat_id)

    initial_message = await event.reply("**قابل يا كسمك **🩴")
    START_MESSAGES_TO_DELETE[chat_id] = initial_message

    await asyncio.sleep(0.5)
    try:
        if chat_id in START_MESSAGES_TO_DELETE:
            await START_MESSAGES_TO_DELETE[chat_id].delete()
            del START_MESSAGES_TO_DELETE[chat_id]
    except Exception as e:
        print(f"Failed to delete initial message in {chat_id}: {e}")
        pass

    cleanup_task = asyncio.create_task(blitz_cleanup(chat_id))
    ACTIVE_CLEANUPS[chat_id] = cleanup_task

@cli.on(events.NewMessage(pattern='(?i)بس', chats=None))
async def stop_cleanup_command(event):
    if not event.is_group and not event.is_channel:
        pass 

    chat_id = event.chat_id
    
    STOP_CLEANUP.add(chat_id)

    if chat_id in ACTIVE_CLEANUPS:
        await asyncio.sleep(0.5)
        if ACTIVE_CLEANUPS[chat_id].done():
            del ACTIVE_CLEANUPS[chat_id]
            print(f"Cleanup in chat {chat_id} stopped.")
        else:
            try:
                ACTIVE_CLEANUPS[chat_id].cancel()
                await ACTIVE_CLEANUPS[chat_id]
                del ACTIVE_CLEANUPS[chat_id]
                print(f"Cleanup in chat {chat_id} stopped and task cancelled.")
            except asyncio.CancelledError:
                print(f"Cleanup task for {chat_id} was successfully cancelled.")
                del ACTIVE_CLEANUPS[chat_id]
            except Exception as e:
                print(f"Error stopping cleanup task for {chat_id}: {e}")
                pass
    else:
        print(f"No cleanup running in chat {chat_id} to stop.")
    pass 

@cli.on(events.ChatAction)
async def new_members_action(event):
    if event.user_added and event.user and event.user.id == (await cli.get_me()).id:
        print(f"User bot was added to chat {event.chat_id}. Checking permissions...")
        try:
            chat_id = event.chat_id
            me = await cli.get_me()
            participant_me = await cli(GetParticipantRequest(chat_id, me.id))
            
            has_admin_rights_obj = getattr(participant_me.participant, "admin_rights", None)
            
            has_ban_permission = has_admin_rights_obj and getattr(has_admin_rights_obj, "ban_users", False)
            has_delete_permission = has_admin_rights_obj and getattr(has_admin_rights_obj, "delete_messages", False)
            has_invite_permission = has_admin_rights_obj and getattr(has_admin_rights_obj, "invite_users", False)

            if not has_ban_permission:
                print(f"Bot added to chat {chat_id} but lacks 'ban_users' permission. Cannot perform cleanup.")
            elif not has_delete_permission:
                print(f"Bot added to chat {chat_id} but lacks 'delete_messages' permission. Ghost mode might fail.")
            elif not has_invite_permission:
                print(f"Bot added to chat {chat_id} but lacks 'invite_users' permission. Automatic re-join might fail.")
            else:
                print(f"Bot added to chat {chat_id} successfully and has all required permissions for ghost mode.")
        except Exception as e:
            print(f"Error checking permissions after addition to chat {event.chat_id}: {e}")
            pass
    elif event.user_added:
        print(f"User  added event detected for chat {event.chat_id}, but specific user ID could not be determined or was a service message. Skipping detailed permission check.")
        pass

@cli.on(events.NewMessage(chats=None))
async def delete_spam_messages(event):
    if not event.is_group and not event.is_channel:
        return 

    try:
        me = await cli.get_me()
        participant_me = await cli(GetParticipantRequest(event.chat_id, me.id))
        has_delete_permission = getattr(participant_me.participant, "admin_rights", None) and \
                                getattr(participant_me.participant.admin_rights, "delete_messages", False)
        if not has_delete_permission:
            return
    except Exception as e:
        return

    message_text = event.raw_text.lower() if event.raw_text else ""
    
    spam_keywords = [
        "freeether.net",
        "claim free ethereum",
        "free eth alert",
        "airdrop won't last forever",
        "connect your wallet, verify",
        "no registration. instant rewards",
        "free money slip away",
        "www.freeether.net"
    ]

    is_spam = False
    for keyword in spam_keywords:
        if keyword in message_text:
            is_spam = True
            break
            
    if is_spam:
        try:
            await event.delete()
            print(f"Spam message detected and deleted from chat {event.chat_id}.")
        except Exception as e:
            print(f"Failed to delete spam message in {event.chat_id}: {e}")
            pass 

print("🔥 موسكو - بوت التصفية الفاجر يعمل الآن!")
print(f"البوت يعمل بالتوكن: {BOT_TOKEN}")
print(f"الحساب يعمل بالـ API ID: {api_id}")

cli.run_until_disconnected()

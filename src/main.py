import logging
from util.logger import setup_logger
# intercept any other logging stuff
log = setup_logger('ring_automation', level=logging.DEBUG)
logging.getLogger('ring_doorbell.listen.eventlistener').setLevel(logging.DEBUG)
logging.getLogger('firebase_messaging.fcmpushclient').setLevel(logging.DEBUG)
import asyncio
import getpass
import json
from config import Config
from pathlib import Path
from ring_doorbell import Auth, AuthenticationError, Requires2FAError, Ring, RingEventListener
from ring.lightcontroller import LightController
from ring.ringeventhandler import RingEventHandler
from ring_doorbell.const import USER_AGENT
# can change this in future
user_agent = USER_AGENT
cache_file = Path(user_agent + ".token.cache")
gcm_cache_file = Path(user_agent + ".gcm.cache")

def log_debug_info(event_listener: RingEventListener) -> None:
    PREFIX = "main::log_debug_info: "
    if event_listener.subscribed:
        log.debug(f"{PREFIX} Listener subscribed")

        log.debug(f"{PREFIX} Listener started: {event_listener.started}")
        log.debug(f"{PREFIX} Listener subscribed: {event_listener.subscribed}")

        # Check for subscription-related attributes
        if hasattr(event_listener, '_subscriptions'):
            log.debug(f"{PREFIX} Listener _subscriptions: {event_listener._subscriptions}")
        if hasattr(event_listener, '_subscription_counter'):
            log.debug(f"{PREFIX} Subscription counter: {event_listener._subscription_counter}")

        # Check the receiver's state
        if hasattr(event_listener, '_receiver') and event_listener._receiver:
            receiver = event_listener._receiver
            log.debug(f"{PREFIX} Receiver type: {type(receiver)}")
            if hasattr(receiver, '_callbacks'):
                log.debug(f"{PREFIX} Receiver callbacks count: {len(receiver._callbacks)}")
                log.debug(f"{PREFIX} Receiver callbacks: {receiver._callbacks}")

def token_updated(token) -> None:
    cache_file.write_text(json.dumps(token))

def otp_callback():
    return input("2FA code: ")

def credentials_updated_callback(new_creds) -> None:
    log.debug(f"main::credentials_updated_callback: new creds [{new_creds}]")
    with open(gcm_cache_file, "w", encoding="utf-8") as f:
        json.dump(new_creds, f)
    log.info("main::credentials_updated_callback: GCM credentials updated and saved")

####
# this and _get_ring are copied from ring_doorbell.cli
async def _do_auth(username, password, user_agent=USER_AGENT):
    if not username:
        username = input("Username: ")

    if not password:
        password = getpass.getpass("Password: ")

    auth = Auth(user_agent, None, token_updated)
    try:
        await auth.async_fetch_token(username, password)
        return auth
    except Requires2FAError:
        await auth.async_fetch_token(username, password, input("2FA Code: "))
        return auth

async def _get_ring(username, password, do_update_data, user_agent=USER_AGENT):
    # connect to Ring account
    global cache_file, gcm_cache_file
    if user_agent != USER_AGENT:
        cache_file = Path(user_agent + ".token.cache")
        gcm_cache_file = Path(user_agent + ".gcm_token.cache")
    if cache_file.is_file():
        auth = Auth(
            user_agent,
            json.loads(cache_file.read_text(encoding="utf-8")),
            token_updated,
        )
        ring = Ring(auth)
        do_method = (
            ring.async_update_data if do_update_data else ring.async_create_session
        )
        try:
            await do_method()
        except AuthenticationError:
            auth = await _do_auth(username, password)
            ring = Ring(auth)
            do_method = (
                ring.async_update_data if do_update_data else ring.async_create_session
            )
            await do_method()
    else:
        auth = await _do_auth(username, password, user_agent=user_agent)
        ring = Ring(auth)
        do_method = (
            ring.async_update_data if do_update_data else ring.async_create_session
        )
        await do_method()

    return ring
####

async def listen(ring) -> None:
    credentials = None

    if gcm_cache_file.is_file():
        log.info(f"main::listen: Loading cached GCM credentials from [{gcm_cache_file}]")
        with open(gcm_cache_file, encoding="utf-8") as f:
            credentials = json.load(f)
    else:
        log.info("main::listen: No cached GCM credentials, will register new ones")
    
    # check if credentials were generated
    log.info(f"main::listen: Credentials file exists now: [{gcm_cache_file.is_file()}]")
    log.info("main::listen: ring.async_update_data()...")
    # need to call this here or our LightController's devices are empty
    await ring.async_update_data()

    log.info(f"main::listen: Setting up RingEventListener with credentials [{gcm_cache_file}]...")

    event_listener = RingEventListener(ring, credentials, credentials_updated_callback)
    event_handler = RingEventHandler(ring, LightController(ring, "Drive", config.get_timezone))
    
    log.info("main::listen: Starting event_listener...")
    await event_listener.start()
    event_listener.add_notification_callback(event_handler.on_event)

    if event_listener.started:
        if log.getEffectiveLevel() >= logging.DEBUG:
            log_debug_info(event_listener)
        print("main::listen: event_listener.started = True, listening...")
        await asyncio.get_event_loop().run_in_executor(None, input)

    else:
        log.error("main::listen: Failed to start event_listener")

    await event_listener.stop()

async def main():
    ring = await _get_ring(None, None, None, user_agent)
    await listen(ring)
    
    log.info("main::main: Clean shutdown")

if __name__ == "__main__":
    config = Config('src/config.json')
    asyncio.run(main())

from util.logger import logging
logger = logging.getLogger('ring_automation')
import asyncio
from typing import cast
from ring_doorbell import Ring, RingCapability, RingStickUpCam
from astral import LocationInfo
from astral.sun import sun
from datetime import datetime
import pytz

class LightController:
    def __init__(self, ring: Ring, device_name, timezone: str):
        self._turn_off_task = None
        self.ring = ring
        self.device_name = device_name
        self.device = ring.get_device_by_name(device_name)
        
        if not timezone:
            self.timezone = pytz.timezone("Europe/London")
        else:
            self.timezone = pytz.timezone(timezone)
        
        if not self.device:
            logger.error(f"lightcontroller::init: got unknown device [{device_name}]")
            return None
        if not self.device.has_capability(RingCapability.LIGHT):
            logger.error(f"lightcontroller::init: device [{device_name}] does not have a light...")
            return None
        self.floodlight = cast(RingStickUpCam, self.device)
        self._is_on = self.floodlight.light
        self._setting_light = False

        # lat/lon for sunset/sunrise times
        self.location = LocationInfo(latitude=self.device.latitude, longitude=self.device.longitude)

        logger.info(f"lightcontroller::init: is_dark [{self.is_dark()}]")

async def set_lights(self, enable: bool, duration: int) -> None:
    # i suppose we might hit a situation where we receive enable=False but we've
    # ticked over between 'dark' and 'light' between the ring API trigger and getting here
    # so should probably handle that by checking the value of enable here too. i.e. it's always
    # ok to turn the lights _off_ if it's light outside
    if not self.is_dark() and enable:
        logger.debug(f"lightcontroller::set_lights: not dark, ignoring lights on request")
        return None
    
    if enable and (self._turn_off_task and not self._turn_off_task.done()):
        logger.debug(f"lightcontroller::set_lights: cancelling existing _turn_off_task and creating a new one")
        self._turn_off_task.cancel()
        self._turn_off_task = None
        self._turn_off_task = asyncio.create_task(self._auto_off(duration))
        return None

    if self._setting_light:
        logger.debug(f"lightcontroller::set_lights: _setting_light [{self._setting_light}] API call in progress, skipping")
        return None

    if (enable and self._is_on) or (not enable and not self._is_on):
        logger.warning(f"lightcontroller::set_lights: {self.floodlight.name} light is already {self._is_on}")
        return None

    self._setting_light = True
    try:
        await self.floodlight.async_set_light(enable)
        # this is a bit of a hack but it seems we need to wait for the light status to resync
        await asyncio.sleep(3)
        await self.ring.async_update_devices()
        self._is_on = self.floodlight.light

        logger.info(f"lightcontroller::set_lights: {self.floodlight.name} light: requested [{enable}] current state [{self.floodlight.light}]")
        if not enable and self.floodlight.light:
            # probably a lag turning it off, schedule another attempt/check in 10s
            logger.warning(f"lightcontroller::set_lights: inconsistent state after disabler request self.is_on = [{self._is_on}] self.floodlight.light = [{self.floodlight.light}] scheduling another off task")
            self._turn_off_task = asyncio.create_task(self._auto_off(10))

        if enable:
            self._turn_off_task = asyncio.create_task(self._auto_off(duration))
    finally:
        self._setting_light = False

    async def _auto_off(self, duration: int) -> None:
        try:
            logger.info(f"lightcontroller::_auto_off: scheduled new off task for [{duration}]s")
            await asyncio.sleep(duration)
            await self.set_lights(False, None)
        except asyncio.CancelledError:
            logger.debug(f"lightcontroller::_auto_off: canceling existing off task for new motion")

    def is_dark(self) -> bool:
        now = datetime.now(self.timezone)
        s = sun(self.location.observer, date=now.date(), tzinfo=self.timezone)
        
        sunrise = s['sunrise']
        sunset = s['sunset']
        
        is_dark = now < sunrise or now > sunset
        logger.debug(f"lightcontroller::is_dark: now [{now.strftime('%H:%M')}] sunrise [{sunrise.strftime('%H:%M')}] sunset [{sunset.strftime('%H:%M')}], is_dark [{is_dark}]")
        return is_dark
    
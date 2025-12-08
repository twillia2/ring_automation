from util.logger import logging
logger = logging.getLogger('ring_automation')
import asyncio
from typing import cast
from ring_doorbell import Ring, RingCapability, RingStickUpCam

class LightController:
    def __init__(self, ring: Ring, device_name):
        self._turn_off_task = None
        self.ring = ring
        self.device_name = device_name
        self.device = ring.get_device_by_name(device_name)

        if not self.device:
            logger.error(f"lightcontroller::init: got unknown device [{device_name}]")
            return None
        if not self.device.has_capability(RingCapability.LIGHT):
            logger.error(f"lightcontroller::init: device [{device_name}] does not have a light...")
            return None
        self.floodlight = cast(RingStickUpCam, self.device)
        self.is_on = self.floodlight.light

    async def set_lights(self, enable: bool, duration: int) -> None:
        # make sure we have the latest status
        await self.ring.async_update_devices()
        if enable and (self._turn_off_task and not self._turn_off_task.done()):
            logger.debug(f"lightcontroller::set_lights: cancelling existing _turn_off_task and creating a new one")
            self._turn_off_task.cancel()
            self._turn_off_task = None
            self._turn_off_task = asyncio.create_task(self._auto_off(duration))
            return

        if (enable and self.is_on) or (not enable and not self.is_on):
            logger.warning(f"lightcontroller::set_lights: {self.floodlight.name} light is already {self.is_on}")
            return None

        await self.floodlight.async_set_light(enable)
        # this is a bit of a hack but it seems we need to wait for the light status to resync
        await asyncio.sleep(3)
        await self.ring.async_update_devices()
        self.is_on = self.floodlight.light

        logger.info(f"lightcontroller::set_lights: {self.floodlight.name} light: requested [{enable}] current state [{self.floodlight.light}]")
        if not enable and self.floodlight.light:
            # probably a lag turning it off, schedule another attempt/check in 10s
            logger.warning(f"lightcontroller::set_lights: inconsistent state after disabler request self.is_on = [{self.is_on}] self.floodlight.light = [{self.floodlight.light}] scheduling another off task")
            self._turn_off_task = asyncio.create_task(self._auto_off(10))

        if enable:
            self._turn_off_task = asyncio.create_task(self._auto_off(duration))
    
    # async def control_light(self, enable: bool):
    #     await self.floodlight.async_set_light(enable)
    #     await self.ring.async_update_devices()

    async def _auto_off(self, duration: int) -> None:
        try:
            logger.info(f"lightcontroller::_auto_off: scheduled new off task for [{duration}]s")
            await asyncio.sleep(duration)
            await self.set_lights(False, None)
        except asyncio.CancelledError:
            logger.debug(f"lightcontroller::_auto_off: canceling existing off task for new motion")

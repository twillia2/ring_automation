import asyncio

from util.logger import logging
from ring_doorbell import Ring, RingEvent, RingEventKind
from ring.lightcontroller import LightController

logger = logging.getLogger('ring_automation')

MAX_EVENTS = 20

class RingEventHandler:
    # lightcontrollers dict is keyed on the 'doorbot_id' (the device's numeric id)
    # we can get the device name string (for logging) from the LightController
    def __init__(self, ring: Ring, lightcontrollers: dict[str, LightController]):
        logger.info("ringeventhandler::__init__")
        self.ring = ring
        self.lightcontrollers = lightcontrollers
        self.processed_events = set()
        # TODO make configurable. 30s default
        self.light_duration = 30

    def handle_event_id(self, event: RingEvent, new_event: bool) -> None:
        logger.debug(f"ringeventhandler::handle_event_id: [{event.id}] new_event [{new_event}]")
        asyncio.run_coroutine_threadsafe(self.lightcontrollers[event.doorbot_id].set_lights(True, self.light_duration), asyncio.get_event_loop())

    def evict_event_id(self, id) -> None:
        if id in self.processed_events:
            self.processed_events.pop(id)
            logger.debug(f"ringeventhandler::evict_event_id: pop id [{id}] processed_events = {len(self.processed_events)}")

    def on_event(self, event: RingEvent) -> None:
        logger.debug(f"ringeventhandler::on_event: [{event}]")
        #callback function that gets called when Ring events occur.
        # RingEventHandler::on_event: RingEvent(id=7581554843738829838, 
        # doorbot_id=707916814, device_name='Drive', device_kind='cocoa_floodlight', 
        # now=1765218296.0, expires_in=180, kind='motion', state='vehicle', is_update=False)
        try:
            event_doorbot_id = event.doorbot_id
            if event_doorbot_id not in self.lightcontrollers:
               logger.info(f"ringeventhandler::on_event: ignoring event for device_name [{event.device_name}]")
               return None
            
            event_id = event.id
            event_kind = event.kind
            event_state = event.state

            logger.info(f"ringeventhandler::on_event: device_name [{event.device_name}] kind [{event_kind}] state [{event_state}] event_id: {event_id}")

            # handle only motion events since we're using this as a proxy for the PIR
            # logic should be:
            # if new motion event (not in processed events), turn on lights for 30s
            # if is_update=True and id in processed_events, extend lights on for extra 30s
            # then set timer to evict processed events from cache using the 'expires_in' value
            if event_kind == RingEventKind.MOTION.value:
                if event_id in self.processed_events:
                    logger.info(f"ringeventhandler::on_event: Update to existing [{event_state}] motion detected on [{event.device_name}]")
                    # extend lights
                    self.handle_event_id(event, False)
                    if len(self.processed_events > MAX_EVENTS):
                        self.evict_event_id(event.id)
                else:
                    logger.info(f"ringeventhandler::on_event: New [{event_state}] motion detected on [{event.device_name}]")
                    self.processed_events.add(event_id)
                    self.handle_event_id(event, True)
            # other event types blah, probably won't trigger on the floodlight actually
            else:
                logger.info(f"ringeventhandler::on_event: Other event: [{event_kind}]")
        
        except Exception as e:
            logger.error(f"ringeventhandler::on_event: Error handling event: [{e}]", exc_info=True)
    


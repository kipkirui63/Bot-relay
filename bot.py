import logging
import asyncio
from datetime import datetime
from monstr.client.client import Client, ClientPool
from monstr.client.event_handlers import EventHandler, DeduplicateAcceptor
from monstr.event.event import Event
from monstr.encrypt import Keys
from monstr.util import util_funcs
import aio_pika

class BotEventHandler(EventHandler):
    def __init__(self, as_user: Keys, channel):
        self._as_user = as_user
        self._channel = channel
        super().__init__(event_acceptors=[DeduplicateAcceptor()])

    async def do_event(self, evt: Event):
        if evt.pub_key == self._as_user.public_key_hex() or \
                self.accept_event(evt) is False:
            return

        if evt.kind == "follow":
            await self.handle_follow(evt)
        elif evt.kind == "follow_back":
            await self.handle_follow_back(evt)

    async def handle_follow(self, evt: Event):
        followed_user_id = evt.tags.get('followed_user_id')
        if followed_user_id:
            message_text = f'Hey, you have a new follower with user ID: {evt.pub_key}. Do you want to enter the raffle? Y or N'
            await self.send_message(message_text)

    async def handle_follow_back(self, evt: Event):
        follower_user_id = evt.tags.get('follower_user_id')
        if follower_user_id:
            message_text = f'Hey, {evt.pub_key} followed you back! Do you want to enter the raffle? Y or N'
            await self.send_message(message_text)

    async def send_message(self, message_text):
        response_event = Event(
            kind=Event.KIND_TEXT_NOTE,
            content=message_text,
            tags=[['bot_message']],
            pub_key=self._as_user.public_key_hex()
        )

        await self._channel.default_exchange.publish(aio_pika.Message(body=response_event.to_json().encode()), routing_key='events')

def get_args():
    return {
        'bot_account': Keys(USE_KEY)
    }

async def main(args):
    as_user = args['bot_account']

    connection = await aio_pika.connect_robust(
        f"amqp://{RABBITMQ_USERNAME}:{RABBITMQ_PASSWORD}@{RABBITMQ_HOST}:{RABBITMQ_PORT}/{RABBITMQ_VHOST}"
    )

    channel = await connection.channel()

    events_queue = await channel.declare_queue('events')

    my_handler = BotEventHandler(as_user=as_user, channel=channel)

    async with events_queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                event_data = Event.from_json(message.body.decode())
                await my_handler.do_event(event_data)

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    asyncio.run(main(get_args()))

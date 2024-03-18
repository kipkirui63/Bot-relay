import logging
import asyncio
from datetime import datetime
from monstr.client.client import Client, ClientPool
from monstr.client.event_handlers import EventHandler, DeduplicateAcceptor
from monstr.event.event import Event
from monstr.encrypt import Keys
from monstr.util import util_funcs
import json
import websocket

# Define the subscription filters for follow events
subscription_filters = {
    "authors": ['sub_id'],
    "kinds": ["FOLLOW", "FOLLOW_BACK"]
}

# Construct the subscription request (REQ message)
subscription_request = ["REQ", "bot_watch", subscription_filters]

# Convert the subscription request to JSON
subscription_request_json = json.dumps(subscription_request)

# Define the websocket endpoint
websocket_endpoint = "wss://nos.lol"

# Connect to the relay websocket
# ws = websocket.create_connection(websocket_endpoint)

# # Send the subscription request
# ws.send(subscription_request_json)
try:
    # Connect to the relay websocket
    ws = websocket.create_connection(websocket_endpoint)

    # Send the subscription request
    ws.send(subscription_request_json)
except Exception as e:
    print("An error occurred:", e)


# Default relay if not otherwise given
DEFAULT_RELAY = 'wss://nos.lol'
USE_KEY = 'nsec1fnyygyh57chwf7zhw3mwmrltc2hatfwn0hldtl4z5axv4netkjlsy0u220'


def get_args():
    return {
        'relays': DEFAULT_RELAY,
        'bot_account': Keys(USE_KEY)
    }


class BotEventHandler(EventHandler):

    def __init__(self, as_user: Keys, clients: ClientPool):
        self._as_user = as_user
        self._clients = clients
        self._replied = {}
        super().__init__(event_acceptors=[DeduplicateAcceptor()])

    def _make_reply_tags(self, src_evt: Event) -> list:
        return [
            ['p', src_evt.pub_key],
            ['e', src_evt.id, 'reply']
        ]

    def do_event(self, the_client: Client, sub_id, evt: Event):
        if evt.pub_key == self._as_user.public_key_hex() or \
                self.accept_event(the_client, sub_id, evt) is False:
            return

        logging.debug('BotEventHandler::do_event - received event %s' % evt)
        prompt_text, response_text = self.get_response_text(evt)

        response_event = Event(
            kind=evt.kind,
            content=response_text,
            tags=self._make_reply_tags(evt),
            pub_key=self._as_user.public_key_hex(),
            
        )

        if response_event.kind == Event.KIND_ENCRYPT:
            response_event.content = response_event.encrypt_content(priv_key=self._as_user.private_key_hex(),
                                                                    pub_key=evt.pub_key)

        response_event.sign(self._as_user.private_key_hex())
        self._clients.publish(response_event)

    def get_response_text(self, the_event):
        prompt_text = the_event.content
        if the_event.kind == Event.KIND_ENCRYPT:
            prompt_text = the_event.decrypted_content(priv_key=self._as_user.private_key_hex(),
                                                      pub_key=the_event.pub_key)

        pk = the_event.pub_key
        reply_n = self._replied[pk] = self._replied.get(pk, 0) + 1
        reply_name = util_funcs.str_tails(pk)

        if the_event.kind == 'FOLLOW':
            response_text = f'hey {reply_name}, thanks for following!'
        elif the_event.kind == 'FOLLOW_BACK':
            response_text = f'hey {reply_name}, thanks for following back!'
        else:
            response_text = f'hey {reply_name} this is reply {reply_n} to you'

        return prompt_text, response_text


async def main(args):
    as_user = args['bot_account']
    relays = args['relays']
    my_clients = ClientPool(clients=relays.split(','))
    my_handler = BotEventHandler(as_user=as_user, clients=my_clients)

    def on_connect(the_client: Client):
        the_client.subscribe(sub_id='bot_watch',
                             handlers=[my_handler],
                             filters={
                                 'kinds': [Event.KIND_ENCRYPT,
                                           Event.KIND_TEXT_NOTE,
                                           ],
                                 '#p': [as_user.public_key_hex()],
                                 'since': util_funcs.date_as_ticks(datetime.now())
                             })

    my_clients.set_on_connect(on_connect)
    print('Monitoring for events from or to account %s on relays %s' % (as_user.public_key_hex(),
                                                                        relays))
    await my_clients.run()


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    asyncio.run(main(get_args()))





























# import logging
# import asyncio
# from datetime import datetime
# from monstr.client.client import Client, ClientPool
# from monstr.client.event_handlers import EventHandler, DeduplicateAcceptor
# from monstr.event.event import Event
# from monstr.encrypt import Keys
# from monstr.util import util_funcs
# import json
# import websocket

# # Define the subscription filters for follow events
# subscription_filters = {
#     "authors": ["<pubkey_of_user_to_follow>"],
#     "kinds": ["FOLLOW", "FOLLOW_BACK"]
# }

# # Construct the subscription request (REQ message)
# subscription_request = ["REQ", "follow_subscription", subscription_filters]

# # Convert the subscription request to JSON
# subscription_request_json = json.dumps(subscription_request)

# # Define the websocket endpoint
# websocket_endpoint = "wss://nos.lol"

# # Connect to the relay websocket
# ws = websocket.create_connection(websocket_endpoint)

# # Send the subscription request
# ws.send(subscription_request_json)


# # Default relay if not otherwise given
# DEFAULT_RELAY = 'wss://nos.lol'
# USE_KEY = 'nsec1fnyygyh57chwf7zhw3mwmrltc2hatfwn0hldtl4z5axv4netkjlsy0u220'


# def get_args():
#     return {
#         'relays': DEFAULT_RELAY,
#         'bot_account': Keys(USE_KEY)
#     }


# class BotEventHandler(EventHandler):

#     def __init__(self, as_user: Keys, clients: ClientPool):
#         self._as_user = as_user
#         self._clients = clients
#         self._replied = {}
#         super().__init__(event_acceptors=[DeduplicateAcceptor()])

#     def _make_reply_tags(self, src_evt: Event) -> list:
#         return [
#             ['p', src_evt.pub_key],
#             ['e', src_evt.id, 'reply']
#         ]

#     def do_event(self, the_client: Client, sub_id, evt: Event):
#         if evt.pub_key == self._as_user.public_key_hex() or \
#                 self.accept_event(the_client, sub_id, evt) is False:
#             return

#         logging.debug('BotEventHandler::do_event - received event %s' % evt)
#         prompt_text, response_text = self.get_response_text(evt)

#         response_event = Event(
#             kind=evt.kind,
#             content=response_text,
#             tags=self._make_reply_tags(evt),
#             pub_key=self._as_user.public_key_hex()
#         )

#         if response_event.kind == Event.KIND_ENCRYPT:
#             response_event.content = response_event.encrypt_content(priv_key=self._as_user.private_key_hex(),
#                                                                     pub_key=evt.pub_key)

#         response_event.sign(self._as_user.private_key_hex())
#         self._clients.publish(response_event)

#     def get_response_text(self, the_event):
#         prompt_text = the_event.content
#         if the_event.kind == Event.KIND_ENCRYPT:
#             prompt_text = the_event.decrypted_content(priv_key=self._as_user.private_key_hex(),
#                                                       pub_key=the_event.pub_key)

#         pk = the_event.pub_key
#         reply_n = self._replied[pk] = self._replied.get(pk, 0) + 1
#         reply_name = util_funcs.str_tails(pk)

#         if the_event.kind == 'FOLLOW':
#             response_text = f'hey {reply_name}, thanks for following!'
#         elif the_event.kind == 'FOLLOW_BACK':
#             response_text = f'hey {reply_name}, thanks for following back!'
#         else:
#             response_text = f'hey {reply_name} this is reply {reply_n} to you'

#         return prompt_text, response_text


# async def main(args):
#     as_user = args['bot_account']
#     relays = args['relays']
#     my_clients = ClientPool(clients=relays.split(','))
#     my_handler = BotEventHandler(as_user=as_user, clients=my_clients)

#     def on_connect(the_client: Client):
#         the_client.subscribe(sub_id='bot_watch',
#                              handlers=[my_handler],
#                              filters={
#                                  'kinds': [Event.KIND_ENCRYPT,
#                                            Event.KIND_TEXT_NOTE,
#                                            'FOLLOW', 'FOLLOW_BACK'],
#                                  '#p': [as_user.public_key_hex()],
#                                  'since': util_funcs.date_as_ticks(datetime.now())
#                              })

#     my_clients.set_on_connect(on_connect)
#     print('Monitoring for events from or to account %s on relays %s' % (as_user.public_key_hex(),
#                                                                         relays))
#     await my_clients.run()


# if __name__ == "__main__":
#     logging.getLogger().setLevel(logging.DEBUG)
#     asyncio.run(main(get_args()))

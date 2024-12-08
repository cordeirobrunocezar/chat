from xmlrpc.server import SimpleXMLRPCServer
import xmlrpc.client
from socketserver import ThreadingMixIn
from dataclasses import dataclass
import concurrent.futures
import time
import datetime
import logging

logger = logging.getLogger(__name__)
rooms = {}
users = []
host = "localhost"
port = 65432

class Server(ThreadingMixIn, SimpleXMLRPCServer):
    pass

@dataclass
class Room:
    users: list
    messages: list

@dataclass
class Message:
    text: str
    timestamp: datetime.datetime
    sender: str
    type: str = "broadcast"
    addressee: str = None

rooms["default"] = Room([],[])

def create_room(room_name):
    global rooms
    if len(room_name) == 0:
        return False
    if room_name not in rooms:
        room = Room([], [])
        rooms[room_name] = room
        return True
    return False

def join_room(username, room_name):
    global rooms
    room = rooms[room_name]
    if username not in room.users:
        room.users.append(username)
        msg = Message(
            text=f"{username} joined.\n",
            timestamp=datetime.datetime.now(),
            sender='',
            )
        room.messages.append(msg)
        return True
    return False

def leave_room(username, room_name):
    global rooms
    room = rooms[room_name]
    msg = Message(
        text=f"{username} left.\n",
        timestamp=datetime.datetime.now(),
        sender='',
        )
    room.messages.append(msg)
    room.users.remove(username)
    return True

def send_message(username, room_name, message, recipient=None):
    global rooms
    if len(message) == 0:
        return False
    room = rooms[room_name]
    msg = Message(
            text=message + '\n',
            timestamp=datetime.datetime.now(),
            sender=username,
            )
    if recipient == username:
        return False
    if recipient:
        msg.type = "unicast"
        msg.addressee = recipient
    room.messages.append(msg)
    return True

def receive_messages(username, room_name):
    global rooms
    room = rooms[room_name]
    messages = room.messages
    answer = []
    for message in messages:
        if message.type == "broadcast":
            answer.append(f"[{message.timestamp.ctime()}]{message.sender}: {message.text}")
        if message.addressee == username:
            answer.append(f"[{message.timestamp.ctime()}]{message.sender} for you: {message.text}")
    return answer

def list_rooms():
    return list(rooms)

def list_users(room_name):
    global rooms
    room = rooms[room_name]
    return room.users

def register_user(username):
    global users
    if len(username) < 0:
        return False
    if username not in users:
        users.append(username)
        rooms["default"].users.append(username)
        return True
    return False

def disconnect(username, room_name):
    global users
    rooms[room_name].users.remove(username)
    users.remove(username)
    return True

def main():
    logging.basicConfig(filename='server.log', level=logging.INFO)
    logger.info(f"{datetime.datetime.now()} Started at {main.__name__}")

    server = Server((host, port))
    server.register_introspection_functions()
    server.register_function(create_room)
    server.register_function(join_room)
    server.register_function(send_message)
    server.register_function(receive_messages)
    server.register_function(list_rooms)
    server.register_function(list_users)
    server.register_function(register_user)
    server.register_function(disconnect)
    server.register_function(leave_room)
    
    try:
        with xmlrpc.client.ServerProxy(f"http://{host}:{port - 1}") as proxy:
            proxy.register_procedure("messenger", host, port)
    except Exception as e:
        logger.error(f"{datetime.datetime.now()} at {main.__name__}", exc_info=e)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt as e: 
        logger.error(f"{datetime.datetime.now()} at {main.__name__} serve_forever call", exc_info=e)
    except Exception as e:
        logger.error(f"{datetime.datetime.now()} at {main.__name__} serve_forever call", exc_info=e)
    logger.info(f"{datetime.datetime.now()} Ended at {main.__name__}")

if __name__ == "__main__":
    main()
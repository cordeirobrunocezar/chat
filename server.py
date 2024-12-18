from xmlrpc.server import SimpleXMLRPCServer
import xmlrpc.client
from socketserver import ThreadingMixIn
from dataclasses import dataclass
import time
import datetime
import logging
import threading
import concurrent.futures

HOST = "localhost"
PORT = 65432
logger = logging.getLogger(__name__)
messenger = None
rooms = {}
lock = threading.Lock()

class Server(ThreadingMixIn, SimpleXMLRPCServer):
    pass

class Messenger():
    def __init__(self):
        global rooms
        self.default_room = Room("default", ["everyone"], [], 0)
        rooms = {f"{self.default_room.name}":self.default_room}
        self.users = []

    def create_room(self, room_name):
        if len(room_name) == 0:
            return False
        if room_name not in rooms:
            room = Room(room_name, ["everyone"], [], 0)
            rooms[room_name] = room
            return True
        return False

    def join_room(self, username, room_name):
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

    def leave_room(self, username, room_name):
        msg = Message(
            text=f"{username} left.\n",
            timestamp=datetime.datetime.now(),
            sender='',
            )
        room = rooms[room_name]
        room.messages.append(msg)
        room.users.remove(username)
        return True

    def send_message(self, username, room_name, message, recipient=None):
        if len(message) == 0:
            return False
        if recipient == username:
            return False
        room = rooms[room_name]
        msg = Message(
                text=message + '\n',
                timestamp=datetime.datetime.now(),
                sender=username,
                )
        if recipient:
            msg.type = "unicast"
            msg.addressee = recipient
        room.messages.append(msg)
        return True

    def receive_messages(self, username, room_name):
        room = rooms[room_name]
        messages = room.messages
        answer = []
        for message in messages:
            if message.type == "broadcast" or message.addressee == "everyone":
                answer.append(f"[{message.timestamp.ctime()}]{message.sender}: {message.text}")
            if message.addressee == username:
                answer.append(f"[{message.timestamp.ctime()}]{message.sender} for you: {message.text}")
        return answer

    def list_rooms(self):
        return list(rooms)

    def list_users(self, room_name):
        room = rooms[room_name]
        return room.users

    def register_user(self, username):
        if len(username) < 0:
            return False
        if username not in self.users:
            self.users.append(username)
            rooms["default"].users.append(username)
            return True
        return False

    def disconnect(self, username, room_name):
        rooms[room_name].users.remove(username)
        self.users.remove(username)
        return True

@dataclass
class Room:
    name: str
    users: list
    messages: list
    timer: int

@dataclass
class Message:
    text: str
    timestamp: datetime.datetime
    sender: str
    type: str = "broadcast"
    addressee: str = None

class RoomManager(threading.Thread):
    def __init__(self):
        global logger
        global rooms
        threading.Thread.__init__(self, daemon=True)
    
    def run(self):
        while True:
            r = list(rooms)
            print(rooms)
            room_key = r.pop()
            self.manage_room(room_key)
            time.sleep(5)
    
    def manage_room(self, room_key: str) -> None:
        if room_key == "default":
            return

        with lock:
            room = rooms[room_key]
            q = len(room.users)
            t = room.timer

            logger.info(f"{datetime.datetime.now()} unlocked {room.name}")

            if q == 1:
                if t > 300:
                    rooms.pop(room_key)
                    logger.info(f"{datetime.datetime.now()} {room.name} popped")
                    return
                room.timer += 5
                logger.info(f"{datetime.datetime.now()} {room.name} timer is {t}")
            elif t > 0:
                room.timer = 0
                logger.info(f"{datetime.datetime.now()} someone entered {room.name}")

            logger.info(f"{datetime.datetime.now()} managed {room.name}")

def task():
    logger.info(f"{datetime.datetime.now()} at task call, starting messenger...")
    messenger = Messenger()
    with Server((HOST, PORT)) as server:
        server.register_introspection_functions()
        server.register_instance(messenger)
        try:
            server.serve_forever()
        except Exception as e:
            logger.error(f"{datetime.datetime.now()} at serve_forever call", exc_info=e)
        except KeyboardInterrupt as e:
            logger.error(f"{datetime.datetime.now()} at {main.__name__}", exc_info=e)
            exit()

def main():
    logging.basicConfig(filename='server.log', level=logging.INFO)
    logger.info(f"{datetime.datetime.now()} Started at {main.__name__}")
    try:
        try:
            with xmlrpc.client.ServerProxy(f"http://{HOST}:{PORT - 1}") as proxy:
                proxy.register_procedure("messenger", HOST, PORT)
        except Exception as e:
            logger.error(f"{datetime.datetime.now()} at {main.__name__}", exc_info=e)
            exit()
        s = threading.Thread(target=task, daemon=True)
        room_manager = RoomManager()
        s.start()
        # room_manager.start()
        while(True):
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                try:
                    future = executor.map(room_manager.manage_room, list(rooms))
                    time.sleep(5)
                except Exception as e:
                    logger.error(f"{datetime.datetime.now()} at future", exc_info=e)
                    exit()
    except KeyboardInterrupt as e:
        logger.error(f"{datetime.datetime.now()} at {main.__name__}", exc_info=e)
        exit()
    logger.info(f"{datetime.datetime.now()} Ended at {main.__name__}")

if __name__ == "__main__":
    main()
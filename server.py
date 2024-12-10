from xmlrpc.server import SimpleXMLRPCServer
import xmlrpc.client
from socketserver import ThreadingMixIn
from dataclasses import dataclass
import time
import datetime
import logging
import threading

HOST = "localhost"
PORT = 65432
logger = logging.getLogger(__name__)
messenger = None
rooms = {}

class Server(ThreadingMixIn, SimpleXMLRPCServer):
    pass

class Messenger():
    def __init__(self):
        global rooms
        self.default_room = Room("default", ["everyone"], [], Timer())
        rooms = {f"{self.default_room.name}":self.default_room}
        self.users = []

    def create_room(self, room_name):
        if len(room_name) == 0:
            return False
        if room_name not in rooms:
            room = Room(room_name, [], [], Timer())
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

class TimerError(Exception):
    pass

class Timer:
    def __init__(self):
        self._start_time = None
        self.buf = 0
    
    def start(self):
        if self._start_time is not None:
            raise TimerError(f"already running\n")
        self._start_time = time.monotonic_ns()

    def stop(self):
        if self._start_time is None:
            raise TimerError(f"not started")
        self.buf = 0
        elapsed_time = time.monotonic_ns() - self._start_time
        self._start_time = None
        return elapsed_time

    def pause(self):
        if self._start_time is None:
            raise TimerError(f"not started (pause)")
        elapsed_time = time.monotonic_ns() - self._start_time
        self.buf += elapsed_time
        return self.buf

@dataclass
class Room:
    name: str
    users: list
    messages: list
    timer: Timer

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
            for room_name in r:
                if room_name != "default":
                    room = rooms[room_name]
                    self.manage_room(room)
            time.sleep(2)
    
    def manage_room(self, room: Room) -> None:
        q = len(room.users)
        t = room.timer._start_time
        if t:
            total = room.timer.pause() * 1e-9
            if total > 300 and q == 0:
                room.timer.stop()
                rooms.pop(room.name)
        if not t and q == 0:
            room.timer.start()
        if t and q > 0:
            room.timer.stop()

def task():
    messenger = Messenger()
    with Server((HOST, PORT)) as server:
        server.register_introspection_functions()
        server.register_instance(messenger)
        try:
            server.serve_forever()
        except Exception as e:
            logger.error(f"{datetime.datetime.now()} at serve_forever call", exc_info=e)

def main():
    logging.basicConfig(filename='server.log', level=logging.INFO)
    logger.info(f"{datetime.datetime.now()} Started at {main.__name__}")
    try:
        try:
            with xmlrpc.client.ServerProxy(f"http://{HOST}:{PORT - 1}") as proxy:
                proxy.register_procedure("messenger", HOST, PORT)
        except Exception as e:
            logger.error(f"{datetime.datetime.now()} at {main.__name__}", exc_info=e)
        s = threading.Thread(target=task)
        s.start()
        room_manager = RoomManager()
        room_manager.start()
        s.join()
    except KeyboardInterrupt as e:
        logger.error(f"{datetime.datetime.now()} at {main.__name__}", exc_info=e)
    logger.info(f"{datetime.datetime.now()} Ended at {main.__name__}")

if __name__ == "__main__":
    main()
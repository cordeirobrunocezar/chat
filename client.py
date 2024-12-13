import time
import xmlrpc.client
from tkinter import *
from tkinter.ttk import *
from tkinter import messagebox
from dataclasses import dataclass
import datetime
import logging
import concurrent.futures

logger = logging.getLogger(__name__)

HOST = "localhost"
PORT = 65431
addr = None

handler = None

@dataclass
class User:
    name: str
    current_room: str

class App():
    def __init__(self):
        self.root = Tk()
        self.root.title("Messenger")

        self.buf = None

        while not self._login():
            pass
        self.user = User(self.buf, "default")

        self.label_clock = Label()
        self.label_clock.pack()

        self.text_chat = Text(takefocus=0,)
        self.text_chat.pack()
        self.text_chat.configure(wrap=WORD, state=DISABLED)

        self.entry_message = Entry()
        self.entry_message.pack(fill=X)
        self.entry_message.focus()
        self.root.bind('<Return>', self._send)

        Label(text="users").pack()

        self.users = []
        self.users_var = StringVar(value=self.users)
        self.listbox_users = Listbox(
            height=10,
            listvariable=self.users_var,
            takefocus=0,
            )
        self.listbox_users.pack()

        Label(text="rooms").pack()

        self.rooms = []
        self.rooms_var = StringVar(value=self.rooms)
        self.listbox_rooms = Listbox(
            height=10,
            listvariable=self.rooms_var,
            takefocus=0,
            )
        self.listbox_rooms.bind("<<ListboxSelect>>", self._join)
        self.listbox_rooms.pack()

        self.root.option_add('*tearOff', FALSE)
        menubar = Menu(self.root)
        self.root.configure(menu=menubar)
        menu_file = Menu(menubar)
        menubar.add_cascade(menu=menu_file, label='File')
        menu_file.add_command(label='New', command=self._new)

        self._update_clock()
        self._update_chat()
        self._update_rooms()
        self._update_users()

        # exit button callback -> _close
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self.root.mainloop()

    def _join(self, event):
        idxs = self.listbox_rooms.curselection()
        if len(idxs) == 1:
            idx = int(idxs[0])
            r = self.rooms[idx]
            if handler._join_room(self.user, r):
                self.user.current_room = r

    def _new(self):
        self._create_window("room name")
        handler._create_room(self.buf)

    def _send(self, event):
        idxs = self.listbox_users.curselection()
        if len(idxs) == 1:
            idx = int(idxs[0])
            u = self.users[idx]
            handler._send_message(self.user, self.entry_message.get(), u)
        else:
            handler._send_message(self.user, self.entry_message.get())
        self.entry_message.delete(0, END)
        self.listbox_users.selection_clear(1, END)

    def _receive(self):
        messages = handler._receive_messages(self.user)
        if len(messages) > 0:
            self.text_chat.configure(state=NORMAL)
            self.text_chat.delete(1.0, END)
            self.text_chat.insert(1.0, ''.join(messages))
            self.text_chat.yview_moveto(1.0)
            self.text_chat.configure(state=DISABLED)
    
    def _retrieve_rooms(self):
        self.rooms = handler._list_rooms()
        self.rooms_var.set(self.rooms)

    def _retrieve_users(self):
        self.users = handler._list_users(self.user)
        self.users_var.set(self.users)

    def _login(self):
        self._create_window("username")
        return handler._register_user(self.buf)
    
    def _update_clock(self):
        current_time = time.ctime()
        self.label_clock.configure(
            text=f"({self.user.name}) [{self.user.current_room}] {current_time}"
            )
        self.root.after(1000, self._update_clock)

    def _update_chat(self):
        self._receive()
        self.root.after(1000, self._update_chat)
    
    def _update_rooms(self):
        self._retrieve_rooms()
        self.root.after(1000, self._update_rooms)
    
    def _update_users(self):
        self._retrieve_users()
        self.root.after(1000, self._update_users)

    def _dismiss(self):
        self.buf = self.entry_window.get()
        self.window.grab_release()
        self.window.destroy()

    def _create_window(self, title):
        self.window = Toplevel(self.root)
        title = Label(self.window, text=f"{title}")
        title.pack()
        self.entry_window = Entry(self.window)
        self.entry_window.pack(fill=X)
        self.entry_window.focus()
        self.entry_window.bind('<Return>', self._dismiss)
        button = Button(self.window, text="Confirm", command=self._dismiss).pack()
        self.window.transient(self.root)
        self.window.wait_visibility()
        self.window.grab_set()
        self.window.wait_window()
    
    def _close(self):
        handler._disconnect(self.user)
        self.root.grab_release()
        self.root.destroy()

class Handler():
    def __init__(self, addr):
        self.addr = addr
    
    def _register_user(self, username):
        try:
            with xmlrpc.client.ServerProxy(f"http://{self.addr}") as proxy:
                return proxy.register_user(username)
        except Exception as e:
            logger.error(f"{datetime.datetime.now()} at {self._register_user.__name__}", exc_info=e)
            messagebox.showerror(message=e)
            exit()

    def _receive_messages(self, usr):
        try:
            with xmlrpc.client.ServerProxy(f"http://{self.addr}", allow_none=True) as proxy:
                return proxy.receive_messages(usr.name, usr.current_room)
        except Exception as e:
            logger.error(f"{datetime.datetime.now()} at {self._receive_messages.__name__}", exc_info=e)
            messagebox.showerror(message=e)
            exit()

    def _send_message(self, usr, message, recipient=None):
        try:
            with xmlrpc.client.ServerProxy(f"http://{self.addr}", allow_none=True) as proxy:
                return proxy.send_message(usr.name, usr.current_room, message, recipient)
        except Exception as e:
            logger.error(f"{datetime.datetime.now()} at {self._send_message.__name__}", exc_info=e)
            messagebox.showerror(message=e)
            exit()

    def _create_room(self, room_name):
        try:
            with xmlrpc.client.ServerProxy(f"http://{self.addr}") as proxy:
                return proxy.create_room(room_name)
        except Exception as e:
            logger.error(f"{datetime.datetime.now()} at {self._create_room.__name__}", exc_info=e)
            messagebox.showerror(message=e)
            exit()

    def _join_room(self, usr, room_name):
        self._leave_room(usr)
        try:
            with xmlrpc.client.ServerProxy(f"http://{self.addr}") as proxy:
                answer = proxy.join_room(usr.name, room_name)
                return answer
        except Exception as e:
            logger.error(f"{datetime.datetime.now()} at {self._join_room.__name__}", exc_info=e)
            messagebox.showerror(message=e)
            exit()

    def _leave_room(self, usr):
        try:
            with xmlrpc.client.ServerProxy(f"http://{self.addr}") as proxy:
                return proxy.leave_room(usr.name, usr.current_room)
        except Exception as e:
            logger.error(f"{datetime.datetime.now()} at {self._leave_room.__name__}", exc_info=e)
            messagebox.showerror(message=e)
            exit()

    def _disconnect(self, usr):
        try:
            with xmlrpc.client.ServerProxy(f"http://{self.addr}") as proxy:
                return proxy.disconnect(usr.name, usr.current_room)
        except Exception as e:
            logger.error(f"{datetime.datetime.now()} at {self._disconnect.__name__}", exc_info=e)
            messagebox.showerror(message=e)
            exit()

    def _list_rooms(self):
        try:
            with xmlrpc.client.ServerProxy(f"http://{self.addr}") as proxy:
                return proxy.list_rooms()
        except Exception as e:
            logger.error(f"{datetime.datetime.now()} at {self._list_rooms.__name__}", exc_info=e)
            messagebox.showerror(message=e)
            exit()

    def _list_users(self, usr):
        try:
            with xmlrpc.client.ServerProxy(f"http://{self.addr}") as proxy:
                return proxy.list_users(usr.current_room)
        except Exception as e:
            logger.error(f"{datetime.datetime.now()} at {self._list_users.__name__}", exc_info=e)
            messagebox.showerror(message=e)
            exit()

def main():
    global handler
    global addr
    logging.basicConfig(filename='client.log', level=logging.INFO)
    logger.info(f"{datetime.datetime.now()} Started at {main.__name__}")
    try:
        try:
            with xmlrpc.client.ServerProxy(f"http://{HOST}:{PORT}") as proxy:
                addr = proxy.lookup_procedure("messenger")
        except Exception as e:
            logger.error(f"{datetime.datetime.now()} at {main.__name__}", exc_info=e)
        handler = Handler(addr)
        app = App()
    except KeyboardInterrupt as e:
        logger.error(f"{datetime.datetime.now()} at {main.__name__}", exc_info=e)
    logger.info(f"{datetime.datetime.now()} Ended at {main.__name__}")

if __name__ == "__main__":
    # with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
    #     future = executor.submit(main)
    main()

# https://docs.python.org/3/library/xmlrpc.server.html
# https://docs.python.org/3/library/xmlrpc.server.html#xmlrpc.server.SimpleXMLRPCServer
# https://docs.python.org/3/library/socketserver.html#socketserver.ThreadingMixIn
# https://docs.python.org/3/library/concurrent.futures.html
# https://tkdocs.com/tutorial/morewidgets.html
# https://tkdocs.com/shipman
# https://tkdocs.com/tutorial/windows.html#dialogs
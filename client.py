import time
import xmlrpc.client
from concurrent.futures import ThreadPoolExecutor
from tkinter import *
from tkinter.ttk import *
from tkinter import messagebox
from dataclasses import dataclass
import datetime
import logging

logger = logging.getLogger(__name__)

addr = ""
host = "localhost"
port = 65431

@dataclass
class User:
    name: str
    current_room: str

class App():
    def __init__(self):
        self.root = Tk()
        self.root.title("App")

        while not self._login():
            pass
        self.user = User(self.buf, "default")

        self.lbl_clock = Label()
        self.lbl_clock.pack()

        self.txt_chat = Text(takefocus=0,)
        self.txt_chat.pack()
        self.txt_chat.configure(state=DISABLED)

        self.ent = Entry()
        self.ent.pack(fill=X)
        self.ent.focus()
        self.root.bind('<Return>', self._send)

        Label(text="users").pack()

        self.lst_usrs = []
        self.lst_usrs_var = StringVar(value=self.lst_usrs)
        self.lstbox_usrs = Listbox(
            height=10,
            listvariable=self.lst_usrs_var,
            takefocus=0,
            )
        self.lstbox_usrs.pack()

        Label(text="rooms").pack()

        self.rooms = []
        self.rooms_var = StringVar(value=self.rooms)
        self.lstbox_rooms = Listbox(
            height=10,
            listvariable=self.rooms_var,
            takefocus=0,
            )
        self.lstbox_rooms.bind("<<ListboxSelect>>", self._join)
        self.lstbox_rooms.pack()

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
        idxs = self.lstbox_rooms.curselection()
        if len(idxs) == 1:
            idx = int(idxs[0])
            r = self.rooms[idx]
            if _join_room(self.user, r):
                self.user.current_room = r

    def _new(self):
        self._dialog()
        _create_room(self.buf)

    def _send(self, event):
        idxs = self.lstbox_usrs.curselection()
        if len(idxs) == 1:
            idx = int(idxs[0])
            u = self.users[idx]
            _send_message(self.user, self.ent.get(), u)
        else:
            _send_message(self.user, self.ent.get())
        self.ent.delete(0, END)
        self.lstbox_usrs.selection_clear(1, END)

    def _receive(self):
        messages = _receive_messages(self.user)
        if len(messages) > 0:
            self.txt_chat.configure(state=NORMAL)
            self.txt_chat.delete(1.0, END)
            self.txt_chat.insert(1.0, ''.join(messages))
            self.txt_chat.yview_moveto(1.0)
            self.txt_chat.configure(state=DISABLED)
    
    def _retrieve_rooms(self):
        self.rooms = _list_rooms()
        self.rooms_var.set(self.rooms)

    def _retrieve_users(self):
        self.users = _list_users(self.user)
        self.lst_usrs_var.set(self.users)

    def _login(self):
        self._dialog()
        return _register_user(self.buf)
    
    def _update_clock(self):
        current_time = time.ctime()
        self.lbl_clock.configure(
            text=self.user.current_room+' '+current_time
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
        self.buf = self.ent_dlg.get()
        self.dlg.grab_release()
        self.dlg.destroy()

    def _dialog(self):
        self.dlg = Toplevel(self.root)
        self.ent_dlg = Entry(self.dlg)
        self.ent_dlg.pack(fill=X)
        self.ent_dlg.focus()
        Button(self.dlg, text="Confirm", command=self._dismiss).pack()
        self.dlg.transient(self.root)
        self.dlg.wait_visibility()
        self.dlg.grab_set()
        self.dlg.wait_window()
    
    def _close(self):
        _disconnect(self.user)
        self.root.grab_release()
        self.root.destroy()

def _register_user(username):
    try:
        with xmlrpc.client.ServerProxy(f"http://{addr}") as proxy:
            return proxy.register_user(username)
    except Exception as e:
        logger.error(f"{datetime.datetime.now()} at {_register_user.__name__}", exc_info=e)
        messagebox.showerror(message=e)
        exit()

def _receive_messages(usr):
    try:
        with xmlrpc.client.ServerProxy(f"http://{addr}", allow_none=True) as proxy:
            return proxy.receive_messages(usr.name, usr.current_room)
    except Exception as e:
        logger.error(f"{datetime.datetime.now()} at {_receive_messages.__name__}", exc_info=e)
        messagebox.showerror(message=e)
        exit()

def _send_message(usr, message, recipient=None):
    try:
        with xmlrpc.client.ServerProxy(f"http://{addr}", allow_none=True) as proxy:
            return proxy.send_message(usr.name, usr.current_room, message, recipient)
    except Exception as e:
        logger.error(f"{datetime.datetime.now()} at {_send_message.__name__}", exc_info=e)
        messagebox.showerror(message=e)
        exit()

def _create_room(room_name):
    try:
        with xmlrpc.client.ServerProxy(f"http://{addr}") as proxy:
            return proxy.create_room(room_name)
    except Exception as e:
        logger.error(f"{datetime.datetime.now()} at {_create_room.__name__}", exc_info=e)
        messagebox.showerror(message=e)
        exit()

def _join_room(usr, room_name):
    _leave_room(usr)
    try:
        with xmlrpc.client.ServerProxy(f"http://{addr}") as proxy:
            answer = proxy.join_room(usr.name, room_name)
            return answer
    except Exception as e:
        logger.error(f"{datetime.datetime.now()} at {_join_room.__name__}", exc_info=e)
        messagebox.showerror(message=e)
        exit()

def _leave_room(usr):
    try:
        with xmlrpc.client.ServerProxy(f"http://{addr}") as proxy:
            return proxy.leave_room(usr.name, usr.current_room)
    except Exception as e:
        logger.error(f"{datetime.datetime.now()} at {_leave_room.__name__}", exc_info=e)
        messagebox.showerror(message=e)
        exit()

def _disconnect(usr):
    try:
        with xmlrpc.client.ServerProxy(f"http://{addr}") as proxy:
            return proxy.disconnect(usr.name, usr.current_room)
    except Exception as e:
        logger.error(f"{datetime.datetime.now()} at {_disconnect.__name__}", exc_info=e)
        messagebox.showerror(message=e)
        exit()

def _list_rooms():
    try:
        with xmlrpc.client.ServerProxy(f"http://{addr}") as proxy:
            return proxy.list_rooms()
    except Exception as e:
        logger.error(f"{datetime.datetime.now()} at {_list_rooms.__name__}", exc_info=e)
        messagebox.showerror(message=e)
        exit()

def _list_users(usr):
    try:
        with xmlrpc.client.ServerProxy(f"http://{addr}") as proxy:
            return proxy.list_users(usr.current_room)
    except Exception as e:
        logger.error(f"{datetime.datetime.now()} at {_list_users.__name__}", exc_info=e)
        messagebox.showerror(message=e)
        exit()

def main():
    logging.basicConfig(filename='myapp.log', level=logging.INFO)
    logger.info(f"{datetime.datetime.now()} Started at {main.__name__}")
    try:
        global addr
        with xmlrpc.client.ServerProxy(f"http://{host}:{port}") as proxy:
            addr = proxy.lookup_procedure("messenger")
    except Exception as e:
        logger.error(f"{datetime.datetime.now()} at {main.__name__}", exc_info=e)
        messagebox.showerror(message=e)
    app = App()
    logger.info(f"{datetime.datetime.now()} Ended at {main.__name__}")

if __name__ == "__main__":
    main()

# https://docs.python.org/3/library/xmlrpc.server.html
# https://docs.python.org/3/library/xmlrpc.server.html#xmlrpc.server.SimpleXMLRPCServer
# https://docs.python.org/3/library/socketserver.html#socketserver.ThreadingMixIn
# https://docs.python.org/3/library/concurrent.futures.html
# https://tkdocs.com/tutorial/morewidgets.html
# https://tkdocs.com/shipman
# https://tkdocs.com/tutorial/windows.html#dialogs
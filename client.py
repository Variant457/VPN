from winproxy import ProxySetting
from tkinter import Tk, Label, Button
from sys import exit

class Client():
    def __init__(self):
        # Server Constructor Variables
        self.port = 12780
        self.proxy = ProxySetting()
        self.server_IPs = {
            "stockholm": "0.0.0.0",         # Replace '0.0.0.0' with the server's IP
            "malaysia": "0.0.0.0"           # Replace '0.0.0.0' with the server's IP
        }

        # Screen Constructor Variables
        self.screen = Tk()
        self.is_proxy_active = False
        self.connect_label = Label(
            self.screen, 
            text= "Choose which location you want to connect to:"
        )
        self.disconnect_label = Label(
            self.screen,
            text= "Click Disconnect to Disconnect from the selected VPN Server:"
        )
        self.stockholm_button = Button(
            self.screen, 
            text= "Stockholm", 
            width= 25, 
            command= lambda:self.boot_vpn(self.server_IPs["stockholm"])
        )
        self.malaysia_button = Button(
            self.screen, 
            text= "Malaysia", 
            width= 25, 
            command= lambda:self.boot_vpn(self.server_IPs["malaysia"])
        )
        self.disconnect_Button = Button(
            self.screen, 
            text= "Disconnect", 
            bg= "red", 
            width= 50, 
            command= lambda:self.disconnect_vpn()
        )

    def create_window(self):
        # Applies Initial Labels and Buttons to the screen
        self.screen.title("VPN")
        self.connect_label.pack()
        self.stockholm_button.pack()
        self.malaysia_button.pack()
        self.screen.protocol("WM_DELETE_WINDOW", self.close_window)
        self.screen.mainloop()

    def close_window(self):
        # Disconnects if the proxy is currently active when window is closed
        if self.is_proxy_active:
            self.disconnect_vpn()

        exit()  # Closes terminal

    def boot_vpn(self, host):
        # Tells Windows to connect to specified proxy server
        self.proxy.server = dict(all= f"{host}:{self.port}")
        self.proxy.enable = True
        self.proxy.registry_write()

        # Hides Server Options
        self.connect_label.pack_forget()
        self.stockholm_button.pack_forget()
        self.malaysia_button.pack_forget()

        # Adds Disconnect Option
        self.disconnect_label.pack()
        self.disconnect_Button.pack()
        self.is_proxy_active = True
        
    def disconnect_vpn(self):
        # Tells Windows to disconnect from the proxy
        self.proxy.enable = False
        self.proxy.registry_write()

        # Hides Disconnect Option
        self.disconnect_label.pack_forget()
        self.disconnect_Button.pack_forget()
        self.is_proxy_active = False

        # Readds Server Options
        self.connect_label.pack()
        self.stockholm_button.pack()
        self.malaysia_button.pack()

def main():
    Client().create_window()
    
main()

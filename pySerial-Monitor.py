#!/usr/bin/env python3
import sys
import serial
import curses
import curses.panel
import time
import threading
import array
from curses import wrapper
from curses.textpad import Textbox, rectangle


class SerialMonitor(object):
    def __init__(self, stdscr, port=None, baud=9600, bytesize=8, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_TWO, timeout=None):
        try:
            self.port=port
            self.baud=baud
            self.bytesize=bytesize
            self.parity=parity
            self.stopbits=stopbits
            self.timeout=timeout
            self.ser=None

            self.init_curses() #Initialize curses module and necessary windows

            self.setup_serial() #Initialize serial connection

            #Initial message if all went well
            self.mainWin_print("Welcome to PySerial Monitor (Designed for AVR devices.) Press \'UP\' and \'DOWN\' keys to navigate, \'Enter\' to enter edit mode, \
\'Ctrl+C\' to exit edit mode or quit the program if you're not in edit mode", timestamp=False)

            #Start a thread to read from serial port
            if self.ser!=None:
                self.read_thread = threading.Thread(target=self.serialRead_t, daemon=True)
                self.read_thread.start()

            self.main_handler() #Go to the function that handles the main part of the program until exit
            curses.endwin()
            sys.exit(0)
        except SystemExit:
            curses.endwin()

    def init_curses(self):
        curses.curs_set(0) #Hide the cursor
        curses.doupdate()
        self.MAX_CONTENTS=100 #The maximum size of the messages that the program will keep in the array
        self.CONTENTS=[] #The array that keeps all entries to the console
        self.CUR_LINE=0 #Current line to be written
        self.stdscr = stdscr
        curses.start_color() #Init colours
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
        #The two main windows one for the output one for the input
        self.mainWin, self.mainWin_panel = self.create_panel(curses.LINES-1, curses.COLS, 0, 0, curses.color_pair(1))
        self.inputWin, self.inputWin_panel = self.create_panel(1, curses.COLS, curses.LINES-1, 0, curses.color_pair(2), top=True)
        self.stdscr.bkgd(' ', curses.color_pair(1))
        self.stdscr.refresh()

    def mainWin_print(self, msg="", timestamp=True, bold=False):
        #Function to print at the main output window
        if timestamp:msg=self.time_stamp()+msg
        x = msg.find('\n') #Splits the message if new line char is present
        newstr=""
        leftovers=""
        if x!=-1:
            newstr=msg[:x]
            leftovers=msg[x+1:]
        else:
            if len(msg)>curses.COLS:
                newstr = msg[:curses.COLS]
                leftovers=msg[len(newstr):]
            else:
                newstr=msg
        self.CONTENTS.append( newstr)
        if len(self.CONTENTS)>self.MAX_CONTENTS:self.CONTENTS.pop(0)
        if (self.CUR_LINE!=self.MAX_CONTENTS): self.CUR_LINE+= 1
        self.reveal_contents()
        if leftovers!="":
            self.mainWin_print(msg=leftovers, timestamp=False)


    def reveal_contents(self):
        #Print the messages from the contents array based on the current position of the console
        self.mainWin.clear()
        if len(self.CONTENTS)>curses.LINES-1:
            for i in range (curses.LINES-1):
                self.mainWin.addstr(i, 0, self.CONTENTS[self.CUR_LINE-curses.LINES+i+1])
        else:
            for i in range (len(self.CONTENTS)):
                self.mainWin.addstr(i, 0, self.CONTENTS[i])
        self.mainWin.refresh()
        self.mainWin_panel.show()
        self.inputWin_panel.show()
        curses.panel.update_panels()
        curses.doupdate()

    def shift_contents(self):
        for i in range(self.BUFFER-2):
            self.CONTENTS[i]=self.CONTENTS[i+1]
        self.CONTENTS[self.BUFFER-1]=""

    def create_panel(self, lines, cols, x, y, color, top=False):
        #Fuction that creates a new window+panel
        win = curses.newwin(lines, cols, x, y)
        win.bkgd(' ', color)
        win_panel = curses.panel.new_panel(win)
        if top==False:
            win_panel.top()
        else:
            win_panel.bottom()
        curses.panel.update_panels()
        win.clear()
        win.refresh()
        return win, win_panel

    def setup_serial(self):
        #The fuction that initializes the serial port
        if self.port==None:
            portname = "/dev/ttyUSB"
            while self.ser==None:
                if self.ser:
                    break
                for i in range(0, 64):
                    try:
                        self.port = portname + str(i)
                        self.ser = serial.Serial(self.port, baudrate=self.baud, bytesize=self.bytesize, parity=self.parity, \
                        stopbits=self.stopbits, timeout=self.timeout)
                        self.mainWin_print("Connected to port:" + self.ser.name + '\r')
                        break
                    except:
                        self.ser=None
                        pass

                if self.ser==None:
                    self.mainWin_print("Error! No device found... Press \'ENTER\' to retry or any key to quit.")
                    try:
                        keyP = self.inputWin.getch()
                        if keyP == ord('\n'):
                            continue
                        else:
                            curses._sys.exit(1)
                    except KeyboardInterrupt:
                        curses.endwin()
                        sys.exit(1)
        else:
            try:
                self.ser = serial.Serial(port, baudrate=self.baud, bytesize=self.bytesize, parity=self.parity, \
                    stopbits=self.stopbits, timeout=self.timeout)
            except:
                curses.endwin()
                sys.exit(1)

    def serialRead_t(self):
        #The that is reading messages from the serial port
        #The default C null character is used as a termination character
        while True:
            bytesRead = self.ser.read_until(b'\0')
            s = str(bytesRead, 'ascii').replace('\0', '')
            self.mainWin_print(s)

    def main_handler(self):
        #The main function that takes input and handles it
        self.box=None
        while True:
            try:
                keyP = self.inputWin.getch()
                if keyP == ord('\n'): #Press enter to enter edit mode and stay in edit mode
                    while True:       #until Ctrl+C is pressed
                        self.box = Textbox(self.inputWin)
                        self.box.edit()
                        message = self.box.gather()
                        self.mainWin_print("-> " + message)
                        if self.ser!=None:
                            self.send_bytes(message)
                        self.inputWin.clear()
                        self.inputWin.refresh()
                elif keyP == curses.KEY_UP: #If not in edit mode go up...
                    if (self.CUR_LINE>=curses.LINES):
                        self.CUR_LINE-=1
                        self.reveal_contents()
                elif keyP == curses.KEY_DOWN: #...or down in the console to look through messages
                    if (self.CUR_LINE<len(self.CONTENTS)):
                        self.CUR_LINE+=1
                        self.reveal_contents()
            except KeyboardInterrupt: #Crtl+C is pressed and the interrupt needs to be handled
                self.inputWin.clear()
                self.inputWin.refresh()
                if (self.box!=None):#close the edit box if it is open
                    self.box=None
                else:               #or exit the loop and return to the main program (that basically exits)
                    break
                continue

    def send_bytes(self, string):
        #Send the message written to the device with a null termination character
        self.ser.write(str.encode(string)+(b'\0'))

    def time_stamp(self):
        #Return current time (H:M:S) in string format
        time_struct = time.localtime()
        time_s = time.strftime("%H:%M:%S: ", time_struct)
        return time_s

def main(stdscr):
    if len(sys.argv)==6:
        try:
            SerialMonitor(stdscr, sys.argv[0], sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
        except Exception as e:
            print(str(e))
    elif len(sys.argv)==1:
        SerialMonitor(stdscr)
    else:
        sys.exit(1)

if __name__ == "__main__":
    stdscr = curses.initscr()
    wrapper(main)
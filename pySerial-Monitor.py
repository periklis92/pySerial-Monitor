#!/usr/bin/env python3
#Serial Monitor (only tested with AVR)
#Version 0.1
#Written by: Periklis Stinis
import sys
import serial
import curses
import curses.panel
import time
import threading

from curses import wrapper
from curses.textpad import Textbox, rectangle


class SerialMonitor(object):
    def __init__(self, stdscr, port=None, baud=9600, bytesize=8, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_TWO, timeout=None):
        try:
            self.ser=None
            self.init_curses() #Initialize curses module and necessary windows

            self.setup_serial(port, baud, bytesize, parity, stopbits, timeout) #Initialize serial connection

            #Initial message if all went well
            self.mainWin_print("Welcome to PySerial Monitor (Designed for AVR devices.) Press \'UP\' and \'DOWN\' keys to navigate, \n\'Enter\' to enter edit mode, \
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
        self.BUFFER=1000 #The maximum size of the messages that the program will keep in the array
        self.CONTENTS=['' for i in range(self.BUFFER)] #The array that keeps all entries to the console
        self.CONTENTS_PTR=0 #Current last message shown to the console
        self.CUR_LINE=0 #Current line to be written
        self.NUM_CONTENTS=0 #How much of the contents array is full
        self.stdscr = stdscr
        curses.start_color() #Init colours
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
        #The two main windows one for the output one for the input
        self.mainWin, self.mainWin_panel = self.create_panel(curses.LINES-1, curses.COLS, 0, 0, curses.color_pair(1))
        self.inputWin, self.inputWin_panel = self.create_panel(1, curses.COLS, curses.LINES-1, 0, curses.color_pair(2), top=True)
        self.stdscr.bkgd(' ', curses.color_pair(1))
        self.stdscr.refresh()

    def mainWin_print(self, msg, timestamp=True):
        #Function to print at the main output window
        x = msg.split('\n') #Splits the message if new line char is present
        self.CONTENTS_PTR=self.NUM_CONTENTS
        for i in range(len(x)): #Write each line
            if timestamp:
                new_msg = self.time_stamp() + str(x[i])
            else:
                new_msg = str(x[i])
            self.CONTENTS[self.CONTENTS_PTR] = new_msg
            self.CONTENTS_PTR+= 1
            self.NUM_CONTENTS+=1
            if (self.CUR_LINE<curses.LINES-1):
                self.CUR_LINE+= 1
        self.reveal_contents()

    def reveal_contents(self):
        #Print the messages from the contents array based on the current position of the console
        self.mainWin.clear()
        if self.CONTENTS_PTR>curses.LINES-1:
            for i in range (curses.LINES-1):
                self.mainWin.addstr(i, 0, self.CONTENTS[(self.CONTENTS_PTR-self.CUR_LINE)+i])
        else:
            for i in range (self.CONTENTS_PTR):
                self.mainWin.addstr(i, 0, self.CONTENTS[i])
        self.mainWin.refresh()
        self.mainWin_panel.show()
        self.inputWin_panel.show()
        curses.panel.update_panels()
        curses.doupdate()

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

    def setup_serial(self, port, baud, bytesize, parity, stopbits, timeout):
        #The fuction that initializes the serial port
        if port==None:
            portname = "/dev/ttyUSB"
            while self.ser==None:
                if self.ser:
                    break
                for i in range(0, 64):
                    try:
                        port = portname + str(i)
                        self.ser = serial.Serial(port, baudrate=baud, bytesize=bytesize, parity=parity, stopbits=stopbits, timeout=timeout)
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
                self.ser = serial.Serial(port, baudrate=baud, bytesize=bytesize, parity=parity, stopbits=stopbits, timeout=timeout)
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
                    if (self.CONTENTS_PTR>=curses.LINES):
                        self.CONTENTS_PTR-=1
                        self.reveal_contents()
                elif keyP == curses.KEY_DOWN: #...or down in the console to look through messages
                    if (self.CONTENTS_PTR<self.NUM_CONTENTS):
                        self.CONTENTS_PTR+=1
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

import tkinter


class HuginnGUI:
    def __init__(self, parent):
        self.parent = parent
        parent.title('Huginn')

        self.label = tkinter.Label(parent, text="Huginn Balloon Telemetry")
        self.label.pack()

        self.close_button = tkinter.Button(parent, text="Close", command=parent.quit)
        self.close_button.pack()


if __name__ == '__main__':
    root = tkinter.Tk()
    huginn_gui = HuginnGUI(root)
    root.mainloop()

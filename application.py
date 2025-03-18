import PySimpleGUI as sg
import threading
import sys
import io
import FDPTOSTSCRIPTORIG  # ✅ Import the script directly
from PIL import Image

# ✅ Set the path to your image
image_path = r"C:\Users\Owner\PyCharmMiscProject/JOBSYNC.png"

# ✅ Load the image and get its size
img = Image.open(image_path)
img_width, img_height = img.size

# ✅ Function to run the script asynchronously and update log
def run_script():
    def execute_script():
        window["-LOG-"].update("Running script...\n", append=True)  # ✅ Show that script is starting

        try:
            # ✅ Capture live output
            old_stdout, old_stderr = sys.stdout, sys.stderr
            sys.stdout, sys.stderr = io.StringIO(), io.StringIO()

            FDPTOSTSCRIPTORIG.main()  # ✅ Run the script directly

            while True:
                output = sys.stdout.getvalue()
                if output:
                    window["-LOG-"].update(output, append=True)  # ✅ Show script output in real-time
                    sys.stdout = io.StringIO()  # ✅ Clear buffer
                window.refresh()

                if "Script has finished running!" in output:
                    break  # ✅ Exit loop once script completes

            # ✅ Retrieve error output
            stderr_output = sys.stderr.getvalue()
            if stderr_output:
                window["-LOG-"].update(f"\n❌ ERROR: {stderr_output}\n", append=True)

            # ✅ Restore standard output
            sys.stdout, sys.stderr = old_stdout, old_stderr

            window["-LOG-"].update("\n✅ Script has finished running!\n", append=True)

        except Exception as e:
            window["-LOG-"].update(f"\n❌ Failed to run script: {e}\n", append=True)

    # ✅ Run in a separate thread to keep UI responsive
    threading.Thread(target=execute_script, daemon=True).start()

# ✅ Button styling
button_style = {
    "size": (30, 3),
    "font": ("Codec Pro", 14, "bold"),
    "button_color": ("#5F16E9", "white"),
    "border_width": 1,
    "pad": (10, 20)
}

# ✅ Define the log output box BEFORE layout
log_output = sg.Frame(
    "",  # ✅ Title of the frame (Can be changed)
    [[sg.Multiline(
        size=(100, 16),
        key="-LOG-",
        autoscroll=True,
        disabled=True,
        background_color="white",
        text_color="black",
        font=("Codec Pro", 14),
        expand_x=True,
        expand_y=True,
        pad=(0, 0)
    )]],
    font=("Codec Pro", 12, "bold"),
    title_color="white",
    relief=sg.RELIEF_SOLID,
    border_width=3,
    pad=(0, 0),
    background_color="white"
)

# ✅ Create the button section with a full white background
button_area = sg.Column(
    [[sg.Push(), sg.Button("SEND BOOKINGS TO ST", **button_style, key="-BUTTON-SHADOW"), sg.Push()]],
    element_justification="center",
    background_color="#64778D",
    expand_x=True,
    expand_y=False,
    pad=(0, 0)
)

# ✅ Create the layout (Image on top, button area, then log output below)
layout = [
    [sg.Image(filename=image_path, key="-IMAGE-")],
    [button_area],
    [sg.Column(
        [[sg.Text("Log Output:", font=("Codec Pro", 12, "bold"), text_color="white", background_color="#64778D", pad=(35, 0))]],
        element_justification="left", expand_x=True, background_color="#64778D"
    )],
    [log_output],
    [sg.Text("", size=(1, 1), background_color="#64778D", pad=(0, 50))]  # ✅ Adds bottom margin
]

# ✅ Create the window
window = sg.Window(
    "Job Sync", layout, size=(img_width, img_height + 550),
    margins=(0, 0), finalize=True, element_justification="center"
)

# ✅ Define button colors
normal_color = ("#5F16E9", "white")
hover_color = ("white", "#5F16E9")

# ✅ Event Loop with Hover Effect
while True:
    event, values = window.read(timeout=100)

    if event == sg.WINDOW_CLOSED:
        break

    # ✅ Get mouse position
    mouse_x, mouse_y = window.mouse_location()

    # ✅ Check if the mouse is over the button
    button_widget = window["-BUTTON-SHADOW"].Widget
    bx, by, bw, bh = button_widget.winfo_rootx(), button_widget.winfo_rooty(), button_widget.winfo_width(), button_widget.winfo_height()

    if bx <= mouse_x <= bx + bw and by <= mouse_y <= by + bh:
        window["-BUTTON-SHADOW"].update(button_color=hover_color)
    else:
        window["-BUTTON-SHADOW"].update(button_color=normal_color)

    if event == "-BUTTON-SHADOW":
        run_script()  # ✅ Run script in a separate thread

# ✅ Close window
window.close()


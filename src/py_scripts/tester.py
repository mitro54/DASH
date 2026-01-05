import dais

# This function is automatically called by C++
def on_command(cmd_text):
    if "help" in cmd_text:
        dais.log("I noticed you are asking for help!")
        dais.log("I am a Python script running inside your C++ shell.")

    if cmd_text == "status":
        dais.log("Plugin seems to operate.")
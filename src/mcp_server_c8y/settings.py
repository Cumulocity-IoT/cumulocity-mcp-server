def init():
    global selected_transport
    global toolBlacklist, methodWhitelist
    selected_transport = ""

    toolBlacklist = []
    methodWhitelist = ["get"]

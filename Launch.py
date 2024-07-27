from PyQt5.QtNetwork import QLocalSocket, QLocalServer
from window_Welcome import *

if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(sys.argv)
    serverName = 'lock'
    socket = QLocalSocket()
    socket.connectToServer(serverName)
    if socket.waitForConnected(500):
        app.quit()
    else:
        localServer = QLocalServer()
        localServer.listen(serverName)
        LOG.debug("\n\n\n********************************************************\n" + str(global_curWwiseProjPath) + "\n********************************************************\n")
        if len(global_curWwisePath) == 0:
            pass
        elif len(key) == 0 or len(KeyInfoDict) == 0 or SoundListDictFlag is False:
            Window = Window_Welcome()
            Window.ui.show()
            Window.pushButton_LaunchTool.setEnabled(False)
            sys.exit(app.exec_())
        else:
            if key.get("ifNotShowWelcome", "") != "True":
                Window = Window_Welcome()
                Window.ui.show()
                sys.exit(app.exec_())
            else:
                Window = Window_Main()
                app.aboutToQuit.connect(Window.cleanup)
                sys.exit(app.exec_())

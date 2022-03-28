import pydicom
import sys
import matplotlib.image as mpimg
import math
import csv
import copy
from PyQt5.QtWidgets import *
from PyQt5 import QtGui
from PyQt5.QtCore import Qt, pyqtSignal


class ImageWidget(QWidget):
    zoom_min = 0
    zoom_max = 0
    zoom = 0
    mouse_x = 0
    mouse_y = 0
    draw_x = 0
    draw_y = 0
    precision = 50

    def __init__(self, depthSlider: QSlider, statusBarPointer: QStatusBar, output: QTreeWidget):
        super().__init__()
        self.tool = None
        self.output = output

        # list of lines for aggregation when mouse is pressed
        self.list_blue = []
        self.list_red = []

        # list of lines for displaying paths
        self.list_of_lines_blue = []
        self.list_of_lines_red = []

        # list of lines for output with formating
        self.list_red_item: QTreeWidgetItem = []
        self.list_blue_item: QTreeWidgetItem = []

        self.mouse_pressed = False
        self.depth_slider = depthSlider
        self.status_bar = statusBarPointer
        self.file_extension = ".jpg"

        self.depth_slider.setMinimum(self.zoom_min)
        self.depth_slider.setMaximum(self.zoom_max)
        self.depth_slider.setValue(self.zoom)
        self.depth_slider.valueChanged.connect(self.depthChange)

        self.rows = 0
        self.cols = 0
        self.format = QtGui.QImage.Format_Grayscale8
        self.dataset = mpimg.imread('start.png')
        self.image = QtGui.QImage()
        self.image.load("start.png")
        self.rows = int(len(self.dataset))
        self.cols = self.rows

        self.window_width = int(self.frameGeometry().width())
        self.window_height = int(self.frameGeometry().height())
        self.setMouseTracking(True)
        policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setSizePolicy(policy)
        self.setAcceptDrops(True)

    def precisionChange(self):
        self.precision = self.sender().value()

    def toolChange(self, tool):
        self.tool = tool

    def depthChange(self):
        self.zoom = self.depth_slider.value()
        self.updateImage()

    def updateImage(self):
        if(self.file_extension.lower() == ".dcm"):
            self.image = QtGui.QImage(
                self.dataset.pixel_array[self.zoom], self.rows, self.cols, self.format)
            self.status_bar.showMessage(
                "Layer: " + str(self.zoom+1) + ", Coordinates: (x:"+str(self.mouse_x)+", y:"+str(self.mouse_y)+")")
        elif(self.file_extension == ".png"):
            self.image = QtGui.QImage(
                self.dataset, self.rows, self.cols, QtGui.QImage.Format_RGB32)
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.drawImage(self.draw_x, self.draw_y, self.image)
        self.drawOnImage(
            painter, self.zoom, self.draw_x)
        painter.end()

    def wheelEvent(self, event):
        self.zoom += int(event.angleDelta().y()/100)
        if(self.zoom < self.zoom_min):
            self.zoom = self.zoom_min
        if(self.zoom > self.zoom_max):
            self.zoom = self.zoom_max
        self.updateImage()
        self.depth_slider.setValue(self.zoom)

    def mouseMoveEvent(self, event):
        self.mouse_x = event.x()-self.draw_x
        self.mouse_y = event.y()-self.draw_x
        if self.mouse_pressed:
            # self.mouse(x1, y1, self.zoom)
            dist = math.sqrt((self.mouse_x - self.start_x) **
                             2 + (self.mouse_y - self.start_y)**2)
            if dist > self.precision:
                self.mouse(self.mouse_x, self.mouse_y, self.zoom)
                self.start_x = self.mouse_x
                self.start_y = self.mouse_y
        self.status_bar.showMessage(
            "Layer: " + str(self.zoom+1) + ", Coordinates: (x:"+str(self.mouse_x)+", y:"+str(self.mouse_y)+")")

    def resizeEvent(self, event):
        self.window_width = int(self.frameGeometry().width())
        self.window_height = int(self.frameGeometry().height())
        self.draw_x = (self.window_height-self.rows)//2
        self.draw_y = self.draw_x
        self.updateImage()
        self.setMinimumWidth(self.window_height)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls:
            event.accept()
        else:
            event.ingore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        self.ImageChange(urls[0].toLocalFile())

    def mousePressEvent(self, event):
        self.mouse(self.mouse_x, self.mouse_y, self.zoom)
        self.start_x = self.mouse_x
        self.start_y = self.mouse_y
        self.mouse_pressed = True

    def mouseReleaseEvent(self, event):
        self.mouse_pressed = False
        if self.tool == "Base marker":
            line = QTreeWidgetItem(
                ["Base line " + str(len(self.list_of_lines_red))])
            line.setForeground(0, QtGui.QBrush(Qt.red))
            for i in self.list_red_item:
                line.addChild(i)
            self.output.insertTopLevelItems(0, [line])

            self.list_of_lines_red.append(self.list_red.copy())
            self.list_red.clear()
        elif self.tool == "Object marker":
            line = QTreeWidgetItem(
                ["Object marker " + str(len(self.list_of_lines_blue))])
            line.setForeground(0, QtGui.QBrush(Qt.blue))
            for i in self.list_blue_item:
                line.addChild(i)
            self.output.insertTopLevelItems(0, [line])

            self.list_of_lines_blue.append(self.list_blue.copy())
            self.list_blue.clear()

    def ImageChange(self, filename):
        """Loading new image and reseting parameters"""
        self.file_extension = filename[(filename.rfind(".")):]
        self.dataset = pydicom.dcmread(filename)
        self.format = QtGui.QImage.Format_Grayscale8
        for i in self.dataset.pixel_array[0]:
            for j in i:
                if(j > 255):
                    self.format = QtGui.QImage.Format_Grayscale16
                    break

        self.clearOutput()
        self.zoom_max = len(self.dataset.pixel_array)-1
        self.rows = int(self.dataset.Rows)
        self.cols = int(self.dataset.Columns)
        self.zoom = 0
        self.depth_slider.setMinimum(self.zoom_min)
        self.depth_slider.setMaximum(self.zoom_max)
        self.depth_slider.setValue(self.zoom_min)
        self.draw_x = (self.window_height-self.rows)//2
        self.draw_y = self.draw_x
        self.updateImage()

    def getLine(self, start, end):

        # Setup initial conditions
        x1, y1 = start
        x2, y2 = end
        dx = x2 - x1
        dy = y2 - y1

        # Determine how steep the line is
        is_steep = abs(dy) > abs(dx)

        # Rotate line
        if is_steep:
            x1, y1 = y1, x1
            x2, y2 = y2, x2

        # Swap start and end points if necessary and store swap state
        swapped = False
        if x1 > x2:
            x1, x2 = x2, x1
            y1, y2 = y2, y1
            swapped = True

        # Recalculate differentials
        dx = x2 - x1
        dy = y2 - y1

        # Calculate error
        error = int(dx / 2.0)
        ystep = 1 if y1 < y2 else -1

        # Iterate over bounding box generating points between start and end
        y = y1
        points = []
        for x in range(x1, x2 + 1):
            coord = (y, x) if is_steep else (x, y)
            points.append(coord)
            error -= abs(dy)
            if error < 0:
                y += ystep
                error += dx

        # Reverse the list if the coordinates were swapped
        if swapped:
            points.reverse()
        return points

    def mouse(self, x, y, z):
        if self.tool == "Base marker":
            tmp = QTreeWidgetItem([(str(x)+", "+str(y)+", ")+str(z)])
            self.list_red_item.append(tmp)
            self.list_red.append([x, y, z])
        elif self.tool == "Object marker":
            tmp = QTreeWidgetItem([(str(x)+", "+str(y)+", ")+str(z)])
            self.list_blue_item.append(tmp)
            self.list_blue.append([x, y, z])

    def drawOnImage(self, painter, layer, offset):
        for j in self.list_of_lines_red:
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 0, 0), 2))
            if(len(j) > 1):
                for i in range(1, len(j)):
                    x1, y1, z1 = j[i-1]
                    x2, y2, z2 = j[i]
                    if layer == z1:
                        points = self.getLine((x1, y1), (x2, y2))
                        for i in points:
                            x, y = i
                            painter.drawPoint(x+offset, y+offset)
            elif len(j) == 1:
                painter.setPen(QtGui.QPen(QtGui.QColor(255, 0, 0), 5))
                if layer == j[0][2]:
                    painter.drawPoint(j[0][0]+offset, j[0][1]+offset)

        for j in self.list_of_lines_blue:
            if(len(j) > 1):
                painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 255), 2))
                for i in range(1, len(j)):
                    x1, y1, z1 = j[i-1]
                    x2, y2, z2 = j[i]
                    if layer == z1:
                        points = self.getLine((x1, y1), (x2, y2))
                        for i in points:
                            x, y = i
                            painter.drawPoint(x+offset, y+offset)
            elif len(j) == 1:
                painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 255), 5))
                if layer == j[0][2]:
                    painter.drawPoint(j[0][0]+offset, j[0][1]+offset)

        # drawing when mouse is pressed
        if(len(self.list_red) > 0):
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 0, 0), 2))
            for i in range(1, len(self.list_red)):
                x1, y1, z1 = self.list_red[i-1]
                x2, y2, z2 = self.list_red[i]
                if layer == z1:
                    points = self.getLine((x1, y1), (x2, y2))
                    for i in points:
                        x, y = i
                        painter.drawPoint(x+offset, y+offset)

        # drawing when mouse is pressed
        if(len(self.list_blue) > 0):
            painter.setPen(QtGui.QPen(QtGui.QColor(0, 0, 255), 2))
            for i in range(1, len(self.list_blue)):
                x1, y1, z1 = self.list_blue[i-1]
                x2, y2, z2 = self.list_blue[i]
                if layer == z1:
                    points = self.getLine((x1, y1), (x2, y2))
                    for i in points:
                        x, y = i
                        painter.drawPoint(x+offset, y+offset)

        self.update()

    def clearOutput(self):
        self.output.clear()
        self.list_blue.clear()
        self.list_red.clear()
        self.list_of_lines_red.clear()
        self.list_of_lines_blue.clear()
        self.list_red_item.clear()
        self.list_blue_item.clear()

    def savePoints(self, filename):
        with open(filename, 'w', encoding='UTF8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['x', 'y', 'z', 'index'])
            for index, j in enumerate(self.list_of_lines_blue):
                tmp = copy.deepcopy(j)
                tmp[0].append('Object marker ' + str(index))
                writer.writerows(tmp)
                writer.writerow([])
            for index, j in enumerate(self.list_of_lines_red):
                tmp = copy.deepcopy(j)
                tmp[0].append('Base line ' + str(index))
                writer.writerows(tmp)
                writer.writerow([])


class MainWidget(QWidget):
    activeToolSig = pyqtSignal(str)

    def __init__(self, statusBarPointer):
        super().__init__()

        # init gui elements
        depth_slider = QSlider()
        depth_slider.setOrientation(Qt.Vertical)

        precision_slider = QSlider()
        precision_slider.setOrientation(Qt.Horizontal)
        precision_slider.setRange(10, 80)
        precision_slider.setValue(40)
        precision_slider.setTickInterval(10)
        precision_slider.setTickPosition(QSlider.TicksBelow)

        pointList_widget = QTreeWidget()
        pointList_widget.setHeaderLabels(["Sets"])

        button_object = QPushButton("Object marker")
        button_object.setCheckable(True)

        button_base = QPushButton("Base marker")
        button_base.setCheckable(True)

        self.iw = ImageWidget(depth_slider, statusBarPointer,
                              pointList_widget)

        self.tool_buttons = [button_object, button_base]

        # layouts
        layout_buttons = QVBoxLayout()
        layout_buttons.addWidget(button_object)
        layout_buttons.addWidget(button_base)
        layout_buttons.addWidget(pointList_widget)
        layout_buttons.addWidget(QLabel("Precision:"))
        layout_buttons.addWidget(precision_slider)
        layout_buttons.setSizeConstraint(QLayout.SetFixedSize)
        layout_buttons.setContentsMargins(0, 0, 0, 0)

        layout = QHBoxLayout()
        layout.addWidget(depth_slider)
        layout.addWidget(self.iw)
        layout.addLayout(layout_buttons)
        self.setLayout(layout)

        # connecting slots&signals
        self.activeToolSig.connect(self.iw.toolChange)
        precision_slider.valueChanged.connect(self.iw.precisionChange)
        for i in self.tool_buttons:
            i.clicked.connect(self.toolButtonEvent)

    def ImageChange(self, filename):
        self.iw.ImageChange(filename)

    def savePoints(self, filename):
        self.iw.savePoints(filename)

    def toolButtonEvent(self):
        for i in self.tool_buttons:
            i.setChecked(False)
        if not self.sender().isChecked():
            self.sender().setChecked(True)
        self.activeToolSig.emit(self.sender().text())


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(open('style.qss').read())
        self.setWindowTitle("DCMviewer")

        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        self.main_widget = MainWidget(status_bar)
        self.setCentralWidget(self.main_widget)

        menu_bar = QMenuBar()
        self.setMenuBar(menu_bar)
        fileMenu = menu_bar.addMenu('&File')

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(qApp.quit)
        open_file_action = QAction("Open", self)
        open_file_action.triggered.connect(self.openFileNameDialog)
        save_file_action = QAction("Save points...", self)
        save_file_action.triggered.connect(self.saveFileDialog)

        fileMenu.addAction(open_file_action)
        fileMenu.addAction(save_file_action)
        fileMenu.addAction(exit_action)

    def openFileNameDialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open file", "", "DCM Files (*.dcm)", options=options)
        if filename:
            print(filename)
            if filename.lower().rfind('.dcm') != -1:
                self.main_widget.ImageChange(filename)

    def saveFileDialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save file", "", "*.csv", options=options)
        if filename:
            tmp = filename.rfind('.')
            # no extension found
            if tmp == -1:
                filename += '.csv'
            # filename consist of only extension + remove '.' as it would save as hidden file on linux
            if tmp == 0:
                filename += '.csv'
                filename = filename[1::]
            self.main_widget.savePoints(filename)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(700, 520)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

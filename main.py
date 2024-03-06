from math import ceil

import pyqtgraph
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.uic import loadUiType
import numpy as np
import os
from os import path
import sys
import pandas as pd
import qdarkstyle
from PyQt5.QtCore import Qt
from pyqtgraph import mkPen
from pyqtgraph import mkPen
from reportlab.lib import styles, colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle, PageBreak, Image, SimpleDocTemplate, Spacer
import pyqtgraph.exporters


# import UI file
FORM_CLASS, _ = loadUiType(path.join(path.dirname(__file__), "main.ui"))


# initiate UI file
class MainApp(QMainWindow, FORM_CLASS):
    def __init__(self, parent=None):
        super(MainApp, self).__init__(parent)
        QMainWindow.__init__(self)
        self.setupUi(self)
        self.initialize()
        self.initializeUI()
        self.Handle_Buttons()
        pyqtgraph.setConfigOptions(antialias=True)

    def initializeUI(self):
        self.setWindowTitle("Multi-Channel Signal Viewer")

    def initialize(self):
        self.data = []
        self.current_sample = []
        self.curves=[]

        # controlling speed by a horizontal slider
        self.speedSlider_1.setMinimum(10)
        self.speedSlider_1.setValue(10)
        self.speedSlider_1.valueChanged.connect(self.updateSpeedForView1)

        self.hideCheckBox_1.setChecked(True)
        self.hideCheckBox_2.setChecked(True)

        # Create a timer object
        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(lambda: self.updateData(0))
        self.number_of_signals = 0

        self.timer.start(1000 // self.speedSlider_1.value())

        self.data_2 = []
        self.current_sample_2 = []
        self.curves_2 = []

        self.speedSlider_2.setMinimum(10)
        self.speedSlider_2.setValue(10)
        self.speedSlider_2.valueChanged.connect(self.updateSpeedForView2)

        self.timer_2 = QTimer()
        self.timer_2.setInterval(1000)
        self.timer_2.timeout.connect(lambda: self.updateData(1))
        self.number_of_signals_2=0

        self.timer_2.start(1000 // self.speedSlider_2.value())

        self.playing = True  # Initially, the playback is played
        self.playing_2 = True

        # Initialize graph linking flag
        self.graphs_linked = False

        # set limits
        self.graphicsView.setTitle("Graph 1")
        self.graphicsView_2.setTitle("Graph 2")

        # add legend
        self.legend_2 = self.graphicsView_2.addLegend()
        self.legend = self.graphicsView.addLegend()
        self.graphicsView.setLabel('bottom', "Time")
        self.graphicsView.setLabel('left', "Amplitude")
        self.graphicsView_2.setLabel('bottom', "Time")
        self.graphicsView_2.setLabel('left', "Amplitude")
        self.img = []  # Initialize the img array
        self.snapshot_count = 0  # Initialize the snapshot count

        self.means = []
        self.stdevs = []
        self.durations = []
        self.mins = []
        self.maxs = []

    def toggleGraphLinking(self, checkbox):
        # self.temp = self.speedSlider_2
        if checkbox.isChecked():
            # Link the two graphs
            self.graphs_linked = True
            self.speedSlider_1.valueChanged.connect(lambda: self.updateSpeed(self.speedSlider_1.value(), 2))
            self.updateData(0)
            self.updateData(1)

            self.speedSlider_2.setValue(10)
            self.speedSlider_1.setValue(10)

            # Disable the buttons for the second graph
            self.zoomInButton_2.setEnabled(False)
            self.zoomOutButton_2.setEnabled(False)
            self.fitScreenButton_2.setEnabled(False)
            self.playpauseButton_2.setEnabled(False)
            self.speedSlider_2.setEnabled(False)
            self.moveSignalButton_2.setEnabled(False)
            self.moveSignalButton_1.setEnabled(False)


        else:
            # Unlink the two graphs
            self.graphicsView.setXLink(None)
            self.graphicsView.setYLink(None)
            self.graphs_linked = False

            # Enable the buttons for the second graph
            self.zoomInButton_2.setEnabled(True)
            self.zoomOutButton_2.setEnabled(True)
            self.fitScreenButton_2.setEnabled(True)
            self.playpauseButton_2.setEnabled(True)
            self.speedSlider_2.setEnabled(True)
            self.moveSignalButton_2.setEnabled(True)
            self.moveSignalButton_1.setEnabled(True)

            self.timer.start(1000 // self.speedSlider_1.value())
            self.timer_2.start(1000 // self.speedSlider_2.value())


    def togglePlayPause(self, graph_index):
        if self.graphs_linked:
            if self.playing:
                # Pause the playback for both graphs
                self.playing = False
                self.playing_2 = False
                self.playpauseButton_1.setIcon(QIcon("img/play-button.png"))
                self.playpauseButton_2.setIcon(QIcon("img/play-button.png"))
            else:
                # Start or resume playback for both graphs
                self.playing = True
                self.playing_2 = True
                self.playpauseButton_1.setIcon(QIcon("img/pause-button.png"))
                self.playpauseButton_2.setIcon(QIcon("img/pause-button.png"))
        elif graph_index == 0:
            # If the graphs are not linked, handle the play/pause for the active graph
            if self.playing:
                # Pause the playback for the active graph
                self.playing = False
                self.playpauseButton_1.setIcon(QIcon("img/play-button.png"))
            else:
                # Start or resume playback for the active graph
                self.playing = True
                self.playing_2 = True  # Also ensure the other graph continues playing
                self.playpauseButton_1.setIcon(QIcon("img/pause-button.png"))
                self.playpauseButton_2.setIcon(QIcon("img/pause-button.png"))
        elif graph_index == 1:
            if self.playing_2:
                # Pause the playback for graphicsView_2
                self.playing_2 = False
                self.playpauseButton_2.setIcon(QIcon("img/play-button.png"))
            else:
                # Start or resume playback for graphicsView_2
                self.playing_2 = True
                self.playing = True  # Also ensure the other graph continues playing
                self.playpauseButton_2.setIcon(QIcon("img/pause-button.png"))
                self.playpauseButton_1.setIcon(QIcon("img/pause-button.png"))

    def zoomOut(self, graph_index):
        # You can adjust the zoom factor as needed
        zoom_factor = 1.2

        if graph_index == 0:
            self.graphicsView.getViewBox().scaleBy((zoom_factor, zoom_factor))

        elif graph_index == 1:
            self.graphicsView_2.getViewBox().scaleBy((zoom_factor, zoom_factor))

        # Check if the graphs are linked and perform the same action on the other graph
        if self.graphs_linked:
            if graph_index == 0:
                self.graphicsView_2.getViewBox().scaleBy((zoom_factor, zoom_factor))
            elif graph_index == 1:
                self.graphicsView.getViewBox().scaleBy((zoom_factor, zoom_factor))


    def zoomIn(self, graph_index):
        # You can adjust the zoom factor as needed
        zoom_factor = 0.8

        if graph_index == 0:
            self.graphicsView.getViewBox().scaleBy((zoom_factor, zoom_factor))
        elif graph_index == 1:
            self.graphicsView_2.getViewBox().scaleBy((zoom_factor, zoom_factor))

        # Check if the graphs are linked and perform the same action on the other graph
        if self.graphs_linked:
            if graph_index == 0:
                self.graphicsView_2.getViewBox().scaleBy((zoom_factor, zoom_factor))
            elif graph_index == 1:
                self.graphicsView.getViewBox().scaleBy((zoom_factor, zoom_factor))

    def fitScreen(self, graph_index):
        if graph_index == 0:
            self.graphicsView.getViewBox().autoRange()
        elif graph_index == 1:
            self.graphicsView_2.getViewBox().autoRange()

        # Check if the graphs are linked and perform the same action on the other graph
        if self.graphs_linked:
            if graph_index == 0:
                self.graphicsView_2.getViewBox().autoRange()
            elif graph_index == 1:
                self.graphicsView.getViewBox().autoRange()


    def updateSpeedForView1(self):
        speed = self.speedSlider_1.value()
        self.updateSpeed(speed, 0)

        if self.graphs_linked:
            self.updateSpeed(speed, 1)

    def updateSpeedForView2(self):
        speed = self.speedSlider_2.value()
        self.updateSpeed(speed, 1)

        if self.graphs_linked:
            self.updateSpeed(speed, 0)

    def updateSpeed(self, input, timer_index):
        if timer_index == 0:
            self.timer.setInterval(1000 // input)
        if timer_index == 1:
            self.timer_2.setInterval(1000 // input)

    def hide_graph(self, graph_index):
        if graph_index == 0:
            if not self.hideCheckBox_1.isChecked():
                self.curves[self.channelsComboBox_1.currentIndex()].hide()
            else:
                self.curves[self.channelsComboBox_1.currentIndex()].show()
        elif graph_index == 1:
            if not self.hideCheckBox_2.isChecked():
                self.curves_2[self.channelsComboBox_2.currentIndex()].hide()
            else:
                self.curves_2[self.channelsComboBox_2.currentIndex()].show()

    def change_color(self, graph_index):
        color = QColorDialog.getColor()
        if graph_index == 0:
            self.curves[self.channelsComboBox_1.currentIndex()].setPen(color)
        elif graph_index == 1:
            self.curves_2[self.channelsComboBox_2.currentIndex()].setPen(color)

    def add_label(self, graph_index):
        if graph_index == 0:
            self.channelsComboBox_1.setItemText(self.channelsComboBox_1.currentIndex(), self.addLabelLineEdit_1.text())
            self.graphicsView.addLegend()
            self.legend.removeItem(self.curves[self.channelsComboBox_1.currentIndex()])
            # Add the curve back with the new text
            self.legend.addItem(self.curves[self.channelsComboBox_1.currentIndex()], self.addLabelLineEdit_1.text())
        elif graph_index == 1:
            self.channelsComboBox_2.setItemText(self.channelsComboBox_2.currentIndex(), self.addLabelLineEdit_2.text())
            self.legend_2.removeItem(self.curves_2[self.channelsComboBox_2.currentIndex()])
            # Add the curve back with the new text
            self.legend_2.addItem(self.curves_2[self.channelsComboBox_2.currentIndex()], self.addLabelLineEdit_2.text())

    def loadData(self, filepath, graph_index):
        _, extension = os.path.splitext(filepath)
        if not path.exists(filepath):
            QMessageBox.critical(self, "File Not Found", f"Could not find file at {filepath}.")
            return

        if graph_index == 0:
            data = None

            if extension == '.dat':
                # Read the .dat file as 16-bit integers
                data = np.fromfile(filepath, dtype=np.int16)
            elif extension == '.csv':
                data = np.loadtxt(filepath, delimiter=',',skiprows=1)

            # Calculate statistics for the data before normalization
            self.mean_value = np.mean(data)
            self.std_deviation = np.std(data)
            self.duration = len(data)  # Duration is the length of the data
            self.min_value = np.min(data)
            self.max_value = np.max(data)

            # Normalize the data
            data = (data - np.min(data)) / (np.max(data) - np.min(data))

            self.data.append(data)
            self.current_sample.append(0)

            colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

            # Get a color from the list for each new curve
            color = colors[len(self.curves) % len(colors)]
            curve = pyqtgraph.PlotDataItem(pen=mkPen(color=color, width=1), antialias=True)
            self.graphicsView.addItem(curve)
            self.curves.append(curve)
            self.graphicsView.setLimits(xMin=0,xMax=len(self.data[self.channelsComboBox_1.currentIndex()]), yMin=0, yMax=1.1)

        if graph_index == 1:
            data_2 = None

            if extension == '.dat':
                # Read the .dat file as 16-bit integers
                data_2 = np.fromfile(filepath, dtype=np.int16)
            elif extension == '.csv':
                # Read the .csv file
                data_2 = np.loadtxt(filepath, delimiter=',', skiprows=1)

            # Calculate statistics for the data before normalization
            self.mean_value_2 = np.mean(data_2)
            self.std_deviation_2 = np.std(data_2)
            self.duration_2 = len(data_2)
            self.min_value_2 = np.min(data_2)
            self.max_value_2 = np.max(data_2)

            # Normalize the data
            data_2 = (data_2 - np.min(data_2)) / (np.max(data_2) - np.min(data_2))

            self.data_2.append(data_2)

            # Reset the current sample
            self.current_sample_2.append(0)
            colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

            # Get a color from the list for each new curve
            color = colors[len(self.curves) % len(colors)]
            curve = pyqtgraph.PlotDataItem(pen=mkPen(color=color, width=1), antialias=True)
            self.graphicsView_2.addItem(curve)
            self.curves_2.append(curve)
            self.graphicsView_2.setLimits(xMin=0, xMax=len(self.data_2[self.channelsComboBox_2.currentIndex()]), yMin=0,
                                          yMax=1.1)

    def updateData(self, graph_index):
        if graph_index == 0:
            if not self.data:
                return

            if self.playing:
                for i in range(len(self.data)):
                    # Update data for each curve
                    self.curves[i].setData(self.data[i][:self.current_sample[i]])

                    # Update the current sample
                    self.current_sample[i] += 1
                    self.graphicsView.setXRange(max([self.current_sample[self.channelsComboBox_1.currentIndex()]]) - 500,
                                                max([self.current_sample[self.channelsComboBox_1.currentIndex()]]))
                    self.graphicsView.setLimits(xMin=0, xMax=self.current_sample[self.channelsComboBox_1.currentIndex()] + 100,
                                                yMin=0, yMax = 1.1)

                    # Loop back to the start if we've reached the end of the signal
                    if self.current_sample[i] >= len(self.data[i]) and self.rewindCheckBox_1.isChecked():
                        self.current_sample[i] = 0
                    elif self.current_sample[i] >= len(self.data[i]) and not self.rewindCheckBox_1.isChecked():
                        self.timer.stop()

                # Add a grid
                self.graphicsView.showGrid(x=True, y=True)

                # Continue the timer
                self.timer.start(1000 // self.speedSlider_1.value())

        elif graph_index == 1:
            if not self.data_2:
                return
            if self.playing_2:
                for i in range(len(self.data_2)):  # Loop over each signal
                    self.curves_2[i].setData(self.data_2[i][:self.current_sample_2[i]])

                    self.current_sample_2[i] += 1
                    self.graphicsView_2.setXRange(max([self.current_sample_2[self.channelsComboBox_2.currentIndex()]]) - 500,
                                                max([self.current_sample_2[self.channelsComboBox_2.currentIndex()]]))
                    self.graphicsView_2.setLimits(xMin=0, xMax=self.current_sample_2[self.channelsComboBox_2.currentIndex()] + 100,
                                                yMin=0, yMax = 1.1)

                    # Loop back to the start if we've reached the end of the signal
                    if self.current_sample_2[i] >= len(self.data_2[i]) and self.rewindCheckBox_2.isChecked():
                        self.current_sample_2[i] = 0
                    elif self.current_sample_2[i] >= len(self.data_2[i]) and not self.rewindCheckBox_2.isChecked():
                        self.timer_2.stop()

                self.graphicsView_2.showGrid(x=True, y=True)
                self.timer_2.start(1000 // self.speedSlider_2.value())

    # function to Handle Buttons
    def Handle_Buttons(self):
        self.addSignalButton_1.clicked.connect(lambda: self.addSignalFromFile(0))
        self.addSignalButton_2.clicked.connect(lambda: self.addSignalFromFile(1))

        self.playpauseButton_1.clicked.connect(lambda: self.togglePlayPause(0))
        self.playpauseButton_2.clicked.connect(lambda: self.togglePlayPause(1))

        self.zoomOutButton_1.clicked.connect(lambda: self.zoomOut(0))
        self.zoomOutButton_2.clicked.connect(lambda: self.zoomOut(1))

        self.zoomInButton_1.clicked.connect(lambda: self.zoomIn(0))
        self.zoomInButton_2.clicked.connect(lambda: self.zoomIn(1))

        self.fitScreenButton_1.clicked.connect(lambda: self.fitScreen(0))
        self.fitScreenButton_2.clicked.connect(lambda: self.fitScreen(1))

        self.colorButton_1.clicked.connect(lambda: self.change_color(0))
        self.colorButton_2.clicked.connect(lambda: self.change_color(1))
        self.addLabelButton_1.clicked.connect(lambda: self.add_label(0))
        self.addLabelButton_2.clicked.connect(lambda: self.add_label(1))

        self.linkCheckBox.toggled.connect(lambda: self.toggleGraphLinking(self.linkCheckBox))
        self.hideCheckBox_1.toggled.connect(lambda: self.hide_graph(0))
        self.hideCheckBox_2.toggled.connect(lambda: self.hide_graph(1))

        self.moveSignalButton_1.clicked.connect(lambda: self.moveSignalFromGraph(0))
        self.moveSignalButton_2.clicked.connect(lambda: self.moveSignalFromGraph(1))


        self.exportButton.clicked.connect(self.generate_pdf_with_images)

        self.snapshotButton_1.clicked.connect(
            lambda: self.capture_and_append_snapshot(self.graphicsView))

        self.snapshotButton_2.clicked.connect(
            lambda: self.capture_and_append_snapshot(self.graphicsView_2))

        self.horizontalScrollSlider_1.valueChanged.connect(lambda: self.slider_value_changed(0))
        self.horizontalScrollSlider_2.valueChanged.connect(lambda: self.slider_value_changed(1))

        self.addSignalButton_1.setShortcut(QKeySequence('A,1'))
        self.addSignalButton_2.setShortcut(QKeySequence('A,2'))
        self.playpauseButton_1.setShortcut(QKeySequence('P,1'))
        self.playpauseButton_2.setShortcut(QKeySequence('P,2'))
        self.zoomInButton_1.setShortcut(QKeySequence('Z,1'))
        self.zoomInButton_2.setShortcut(QKeySequence('Z,2'))
        self.exportButton.setShortcut(QKeySequence('E'))


    def slider_value_changed(self, graph_index):
        if self.graphs_linked:
            if graph_index == 0:
                slider_value = self.horizontalScrollSlider_1.value()
                new_x_range = (slider_value * 100, min(slider_value * 100 + 100,
                                                       self.current_sample[self.channelsComboBox_1.currentIndex()]))
                self.graphicsView.setXRange(*new_x_range)
                self.graphicsView_2.setXRange(*new_x_range)
            elif graph_index == 1:
                slider_value_2 = self.horizontalScrollSlider_2.value()
                new_x_range_2 = (slider_value_2 * 100, min(slider_value_2 * 100 + 100, self.current_sample_2[
                    self.channelsComboBox_2.currentIndex()]))
                self.graphicsView_2.setXRange(*new_x_range_2)
                self.graphicsView.setXRange(*new_x_range_2)
        else:
            if graph_index == 0:
                slider_value = self.horizontalScrollSlider_1.value()
                new_x_range = (slider_value * 100, min(slider_value * 100 + 100,
                                                       self.current_sample[self.channelsComboBox_1.currentIndex()]))
                self.graphicsView.setXRange(*new_x_range)
            elif graph_index == 1:
                slider_value_2 = self.horizontalScrollSlider_2.value()
                new_x_range_2 = (slider_value_2 * 100, min(slider_value_2 * 100 + 100, self.current_sample_2[
                    self.channelsComboBox_2.currentIndex()]))
                self.graphicsView_2.setXRange(*new_x_range_2)

    def moveSignalFromGraph(self,graph_index):
        if graph_index == 0:
            # Get the currently selected signal index from the channelsComboBox_1
            selected_signal_index = self.channelsComboBox_1.currentIndex()

            # Check if the selected index is valid
            if selected_signal_index >= len(self.data):
                QMessageBox.critical(self, "Invalid Signal", "Please select a valid signal.")
                return

            # Get the data for the selected signal
            selected_signal_data = self.data[selected_signal_index]
            selected_curve_data = self.curves[selected_signal_index]
            selected_current_sample_data = self.current_sample[selected_signal_index]

            # Remove the signal data from the first graph data list
            self.graphicsView.removeItem(self.curves[selected_signal_index])

            # Remove the addLabelLineEdit_1 text and channelsComboBox_1 item
            self.addLabelLineEdit_1.setText('')
            self.channelsComboBox_2.addItem(f'{self.channelsComboBox_1.itemText(self.channelsComboBox_1.currentIndex())}')
            self.channelsComboBox_1.removeItem(selected_signal_index)
            self.data.pop(selected_signal_index)
            self.curves.pop(selected_signal_index)
            self.current_sample.pop(selected_signal_index)
            self.number_of_signals -= 1

            # Create a new PlotDataItem for the second graph with the selected signal data
            new_curve = pyqtgraph.PlotDataItem(selected_signal_data)

            # Add the signal data and the new curve to the second graph data list
            self.data_2.append(selected_signal_data)
            self.curves_2.append(new_curve)
            self.current_sample_2.append(selected_current_sample_data)

            # Add the new curve to the second graph's PlotWidget\
            self.graphicsView_2.addItem(new_curve)
            self.number_of_signals_2 += 1
            self.addLabelLineEdit_2.setText(self.channelsComboBox_2.itemText(self.channelsComboBox_2.currentIndex()))
            curve_name = self.channelsComboBox_2.itemText(len(self.data_2)-1)
            self.legend_2.addItem(self.curves_2[len(self.data_2)-1], curve_name)
            self.graphicsView_2.setLimits(xMin=0, xMax=len(self.data_2[self.channelsComboBox_2.currentIndex()]), yMin=0, yMax=1.1)

            # Update the graphs
            self.updateData(0)
            self.updateData(1)

        elif graph_index == 1:
            selected_signal_index = self.channelsComboBox_2.currentIndex()

            # Check if the selected index is valid
            if selected_signal_index >= len(self.data_2):
                QMessageBox.critical(self, "Invalid Signal", "Please select a valid signal.")
                return

            # Get the data for the selected signal
            selected_signal_data = self.data_2[selected_signal_index]
            selected_curve_data = self.curves_2[selected_signal_index]
            selected_current_sample_data = self.current_sample_2[selected_signal_index]

            # Remove the signal data from the first graph data list
            self.graphicsView_2.removeItem(self.curves_2[selected_signal_index])
            self.addLabelLineEdit_2.setText('')
            self.channelsComboBox_1.addItem(
                f'{self.channelsComboBox_2.itemText(self.channelsComboBox_2.currentIndex())}')
            self.channelsComboBox_2.removeItem(selected_signal_index)
            self.data_2.pop(selected_signal_index)
            self.curves_2.pop(selected_signal_index)
            self.current_sample_2.pop(selected_signal_index)
            self.number_of_signals -= 1

            # Create a new PlotDataItem for the second graph with the selected signal data
            new_curve = pyqtgraph.PlotDataItem(selected_signal_data)

            # Add the signal data and the new curve to the second graph data list
            self.data.append(selected_signal_data)
            self.curves.append(new_curve)
            self.current_sample.append(selected_current_sample_data)

            # Add the new curve to the second graph's PlotWidget\
            self.graphicsView.addItem(new_curve)
            self.number_of_signals_2 += 1
            self.addLabelLineEdit_1.setText(self.channelsComboBox_1.itemText(self.channelsComboBox_1.currentIndex()))
            curve_name = self.channelsComboBox_1.itemText(len(self.data)-1)
            self.legend.addItem(self.curves[len(self.data)-1], curve_name)
            self.graphicsView_2.setLimits(xMin=0, xMax=len(self.data[self.channelsComboBox_1.currentIndex()]), yMin=0,
                                          yMax=1.1)
            # self.legend_2.addItem(self.curves_2[len(self.data_2)-1], curve_name)


            # Update the graphs
            self.updateData(0)
            self.updateData(1)


    def addSignalFromFile(self, index):
        # Open a QFileDialog in 'Open File' mode
        filepath,_= QFileDialog.getOpenFileName(self, "Open File")

        # If a file was selected
        if filepath:
            if index == 0:
                self.loadData(filepath, index)
                self.updateData(index)
                self.number_of_signals += 1
                self.channelsComboBox_1.addItem(f'channel {self.number_of_signals}')
                self.addLabelLineEdit_1.setText(self.channelsComboBox_1.itemText(self.channelsComboBox_1.currentIndex()))
                curve_name = "channel " + str(self.number_of_signals) + " "
                self.legend.addItem(self.curves[len(self.data) - 1], curve_name)

            elif index == 1:
                self.loadData(filepath, index)  # Load data into graphicsView_2
                self.updateData(index)  # Update graphicsView_2 initially
                self.number_of_signals_2 += 1
                self.channelsComboBox_2.addItem(f'channel {self.number_of_signals_2}')
                self.addLabelLineEdit_2.setText(self.channelsComboBox_2.itemText(self.channelsComboBox_2.currentIndex()))
                # curve_name = self.channelsComboBox_2.itemText(self.channelsComboBox_2.currentIndex())
                curve_name = "channel " + str(self.number_of_signals_2) + " "
                self.legend_2.addItem(self.curves_2[self.channelsComboBox_2.currentIndex()], curve_name)


    def create_graph_snapshot(self, graph_widget, filename):
        exporter = pyqtgraph.exporters.ImageExporter(graph_widget.plotItem)
        exporter.export(filename)

        mean, std_deviation, duration, min_value, max_value = self.calculate_graph_stats(graph_widget)

        self.means.append(mean)  # Append the mean to the array
        self.stdevs.append(std_deviation)  # Append standard deviation
        self.durations.append(duration)  # Append duration
        self.mins.append(min_value)  # Append min value
        self.maxs.append(max_value)  # Append max value
        print(self.means, self.stdevs, self.durations, self.mins, self.maxs)
        QMessageBox.information(self, "Snapshot Created", f"Snapshot saved as {filename} ")

    def capture_and_append_snapshot(self, graphics_view):
        filename = f"snapshot{self.snapshot_count}.png"  # Generate a unique filename
        self.create_graph_snapshot(graphics_view, filename)
        self.img.append(filename)
        self.snapshot_count += 1  # Increment the snapshot count
        print(self.img)

    def calculate_graph_stats(self, graph_widget):
        # Calculate standard deviation, duration, min, and max values of the graph data
        data = graph_widget.plotItem.curves[0].getData()  # Adjust this to access your graph data
        y_values = data[1]  # Assuming the y-values are in the second part of the data

        mean = sum(y_values) / len(y_values)
        std_deviation = np.std(y_values)
        duration = len(y_values)
        min_value = np.min(y_values)
        max_value = np.max(y_values)

        return mean, std_deviation, duration, min_value, max_value

    def generate_pdf_with_images(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        pdf_filename = "images_report.pdf"

        doc = SimpleDocTemplate(pdf_filename, pagesize=letter)
        elements = []

        title_style_2 = ParagraphStyle(
            'CustomTitle2',
            parent=getSampleStyleSheet()['Heading2'],
            fontSize=16,  # Adjust the font size as needed
            alignment=0
        )

        title_style = ParagraphStyle(
            'CustomTitle',
            parent=getSampleStyleSheet()['Heading1'],
            fontSize=20,  # Adjust the font size as needed
            alignment=1
        )

        for i, image_filename in enumerate(self.img):
            image_path = os.path.join(script_dir, image_filename)

            if os.path.exists(image_path):
                # title_style = getSampleStyleSheet()['Heading1']
                title_paragraph = Paragraph(f"Graph{i+1}", title_style)
                elements.append(title_paragraph)
                elements.append(Spacer(2, 15))

                img_ = Image(image_path, width=350, height=300)
                elements.append(img_)

                # Create a table for the statistics
                statistics_data = [
                    ["Statistics Parameters", "Value"],
                    ["Mean Value", format(self.means[i], ".3f") + " μV"],
                    ["Std Deviation", format(self.stdevs[i], ".3f") + " μV"],
                    ["Duration", format(self.durations[i], ".3f") + " seconds"],
                    ["Min Value", format(self.mins[i], ".3f") + " μV"],
                    ["Max Value", format(self.maxs[i], ".3f") + " μV"]
                ]

                table = Table(statistics_data, colWidths=[300, 200])
                table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.darkslategray),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold')
                ]))

                # Add a Spacer to create space between the image and the table
                elements.append(Spacer(10, 50))  # You can adjust the vertical space as needed

                title_paragraph_2 = Paragraph(text="Statistics of the displayed signal" , style=title_style_2)

                elements.append(title_paragraph_2)

                elements.append(Spacer(2, 20))
                elements.append(table)
                elements.append(PageBreak())

        doc.build(elements)
        QMessageBox.information(self, "PDF Created", f"PDF report saved as {pdf_filename}")
        


def main():
        app = QApplication(sys.argv)
        window = MainApp()
        app.setStyleSheet(qdarkstyle.load_stylesheet())
        window.show()
        app.exec_()


if __name__ == '__main__':
    main()
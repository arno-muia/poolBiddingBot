import sys
import psycopg2
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QLineEdit, QSpinBox, QPushButton, QVBoxLayout, QHBoxLayout, QTextEdit, QDialog, QScrollArea, QGridLayout, QCheckBox, QMessageBox
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtCore import QTimer
from bot.bidding_bot import BiddingThread
from data.categories import load_valid_categories_from_db, add_category_to_db
from selenium import webdriver
import time



class CategoryPopup(QDialog):
    def __init__(self, valid_categories):
        super().__init__()
        self.setWindowTitle("Choose Categories")
        self.setStyleSheet("""
            background-color: #808080;  /* Dark background */
            
            /* Styling for checkboxes */
            QCheckBox {
                color: #FFFFFF;  /* White font color */
                font-size: 14px;
                padding: 5px;
                font-family: Arial, sans-serif;
            }

            /* Styling for buttons */
            QPushButton {
                background-color: #0000FF;  /* Default state color */
                font-size: 14px;
                padding: 10px 20px;
                border-radius: 8px;
                margin: 5px;
                border: none;
                font-family: Arial, sans-serif;
            }
            QPushButton:hover {
                background-color: #A9A9A9;  /* Hover state color */
            }
            QPushButton:pressed {
                background-color: ADD8E6;  /* Pressed state color */
            }
        """)

        layout = QVBoxLayout()
        grid_layout = QGridLayout()

         # Initialize the category_checkboxes list
        self.category_checkboxes = []

                 # Adding each category as a checkbox
        for i, category in enumerate(valid_categories):
            checkbox = QCheckBox(category)
            self.category_checkboxes.append(checkbox)
            grid_layout.addWidget(checkbox, i // 6, i % 6)  # Arrange in a grid with 4 columns

        layout.addLayout(grid_layout)


        # Select All checkbox at the top
        self.select_all_checkbox = QCheckBox("Select All")
        self.select_all_checkbox.setStyleSheet("font-size: 14px; color: #FFFFFF; margin: 5px;")
        self.select_all_checkbox.stateChanged.connect(self.select_all)
        layout.addWidget(self.select_all_checkbox)

        # OK button to confirm selection
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        layout.addWidget(ok_button)
    

        self.setLayout(layout)
        self.setFixedSize(1500, 950)  # Adjust size to fit all tabs

    def select_all(self, state):
        # Check or uncheck all categories based on the Select All checkbox state
        is_checked = state == QtCore.Qt.Checked
        for checkbox in self.category_checkboxes:
            checkbox.setChecked(is_checked)



    def get_selected_categories(self):
        # Return a list of selected categories based on checked checkboxes
        return [checkbox.text() for checkbox in self.category_checkboxes if checkbox.isChecked()]

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ArnoTech Solutions")
        self.setGeometry(200, 200, 600, 800)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2F3136;  /* Very dark background */
            }
            QLabel {
                color: #B9BBBE;  /* Light grey text color */
                font-size: 14px;
            }
            QLineEdit, QSpinBox, QTextEdit {
                background-color: #40444B;  /* Dark grey background for input fields */
                color: #DCDDDE;            /* Light grey text color */
                border: 1px solid #5865F2; /* Neon blue border */
                border-radius: 8px;        /* Rounded edges */
                padding: 6px;              /* Padding inside text box */
            }
            QPushButton {
                background-color: #5865F2;  /* Neon blue button background */
                color: #FFFFFF;
                padding: 10px;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4752C4;  /* Darker blue on hover */
            }
        """)



        # Ensure the valid_categories table exists
        #create_table_if_not_exists()

        # Load categories from the file and insert them into the database
        #load_categories_into_db()

        
        # Load valid categories from the database
        self.valid_categories = load_valid_categories_from_db()

        # Initialize new_categories
        self.new_categories = []  # Add this line
        
        self.selected_categories = []
        self.layout = QVBoxLayout()

        # Header
        header = QLabel("Studypool Bidding Bot")
        header.setAlignment(QtCore.Qt.AlignCenter)  # Center the header
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #FFFFFF;")
        self.layout.addWidget(header)

        # Email and Password fields
        self.email_input = self.create_input("Email")
        self.password_input = self.create_input("Password", is_password=True)

        # Minimum Budget
        self.budget_label = QLabel("Minimum Budget ($)")
        self.budget_label.setStyleSheet("color: #B9BBBE; font-size: 14px;")
        self.layout.addWidget(self.budget_label)
        self.budget_input = QSpinBox()
        self.budget_input.setMinimum(0)  # Minimum value for budget
        self.budget_input.setValue(0)  # Default value
        self.layout.addWidget(self.budget_input)

        # Minimum Time Left
        self.time_left_label = QLabel("Minimum Time Left (hours)")
        self.time_left_label.setStyleSheet("color: #B9BBBE; font-size: 14px;")
        self.layout.addWidget(self.time_left_label)
        self.time_left_input = QSpinBox()
        self.time_left_input.setMinimum(0)  # Minimum value for time left
        self.time_left_input.setValue(0)  # Default value
        self.layout.addWidget(self.time_left_input)

        # Category selection button
        self.selected_categories_label = QLabel("Select Categories")
        self.selected_categories_label.setStyleSheet("""
            background-color: #40444B; padding: 8px; border-radius: 5px; color: #B9BBBE; 
            font-weight: bold; font-size: 14px;
        """)
        self.selected_categories_label.mousePressEvent = self.open_category_popup
        self.layout.addWidget(self.selected_categories_label)

        # Start and Stop buttons
        start_btn = QPushButton("Start Bidding")
        start_btn.clicked.connect(self.start_bidding)
        self.layout.addWidget(start_btn)

        stop_btn = QPushButton("Stop Bidding")
        stop_btn.clicked.connect(self.stop_bidding)
        #self.layout.addWidget(start_btn)
        self.layout.addWidget(stop_btn)

        # Status updates
        status_label = QLabel("Status Updates")
        status_label.setStyleSheet("color: #B9BBBE; font-size: 14px;")
        self.layout.addWidget(status_label)

        # Status TextEdit
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setStyleSheet("background-color: #202225; color: #DCDDDE;")
        self.layout.addWidget(self.status_text)

        # Clear button below status updates
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_status)
        self.layout.addWidget(clear_btn)

        # Container for layout
        container = QtWidgets.QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)

    def changeEvent(self, event):
        if event.type() == QtCore.QEvent.WindowStateChange:
            # If the window is minimized, stop any automatic restoration
            if self.isMinimized():
                self.setWindowState(QtCore.Qt.WindowMinimized)  # Ensure it stays minimized
            super().changeEvent(event)
            
    def create_input(self, label_text, is_password=False):
        label = QLabel(label_text)
        self.layout.addWidget(label)
        input_field = QLineEdit()
        input_field.setEchoMode(QLineEdit.Password if is_password else QLineEdit.Normal)
        self.layout.addWidget(input_field)
        return input_field

    def open_category_popup(self, event):
        # Reload valid categories from the database
        self.valid_categories = load_valid_categories_from_db()

        # Open the category popup to select categories
        self.category_popup = CategoryPopup(self.valid_categories)
        if self.category_popup.exec_() == QDialog.Accepted:
            selected_categories = self.category_popup.get_selected_categories()
            if selected_categories:
                self.selected_categories = selected_categories
                self.selected_categories_label.setText(f"{len(selected_categories)} categories selected")
                self.valid_categories = load_valid_categories_from_db()  # Reload updated categories

                # Check for new categories and add them to the database
                for category in selected_categories:
                    if category not in self.valid_categories:
                        add_category_to_db(category)
                        self.new_categories.append(category)  # Mark it as new
                        print(f"Added new category: {category}")  # Debugging message

            else:
                self.selected_categories_label.setText("Select Categories")

    def stop_bidding(self):
        if hasattr(self, 'bidding_thread') and self.bidding_thread.isRunning():
            self.bidding_thread.stop_bidding = True
            self.update_status("Stopping the bidding process...")

            # Use QTimer to periodically check if the thread has stopped
            QTimer.singleShot(15, self.check_thread_stopped)
        else:
            self.update_status("No bidding process running.")

    def start_bidding(self):
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()
        selected_categories = self.selected_categories
        min_budget = self.budget_input.value()
        min_time_left = self.time_left_input.value()


        # Exclude new categories from bidding
        eligible_categories = [category for category in self.selected_categories if category not in self.new_categories]


        if not email or not password:
            QMessageBox.warning(self, "Input Error", "Please enter both email and password.")
        elif not selected_categories:  # Check if categories have been selected
            QMessageBox.warning(self, "Input Error", "Please select at least one category.")
        else:
            # Initialize the bidding thread with selected categories
            self.bidding_thread = BiddingThread(email, password, selected_categories, min_budget, min_time_left)
            self.bidding_thread.bidding_started.connect(self.update_status)
            self.bidding_thread.bid_placed.connect(self.update_status)
            self.bidding_thread.start()

            # Display "Email Hidden" and "Password Hidden" after clearing inputs
            self.email_input.clear()
            self.password_input.clear()
            self.email_input.setPlaceholderText("Email Hidden")
            self.password_input.setPlaceholderText("Password Hidden")

    def update_status(self, message):
        if "Login successful" in message:
            self.status_text.append("Login successful.")
        elif "Bidding started" in message:
            self.status_text.append("Bidding process has started.")
        elif "Valid question found" in message:
            # Display valid question and bid placed message directly
            self.status_text.append(message)
        elif "Error placing the bid" in message:
            self.status_text.append("Error placing the bid.")

    def check_thread_stopped(self):
        if not self.bidding_thread.isRunning():
            self.update_status("Bidding has been stopped.")
            self.bidding_thread.quit()
            self.bidding_thread.wait()
        else:
            # If the thread is still running, check again after 100 ms
            QTimer.singleShot(100, self.check_thread_stopped)


    def clear_status(self):
        self.status_text.clear()

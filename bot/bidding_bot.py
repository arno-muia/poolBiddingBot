from PyQt5.QtCore import QThread, pyqtSignal
#from gui.main_window import valid_categories
from data.categories import load_valid_categories_from_db, add_category_to_db
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, NoSuchWindowException, WebDriverException
import time
import logging
import os


# Configure logging for better error tracking
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class BiddingThread(QThread):
    bidding_started = pyqtSignal(str)
    bid_placed = pyqtSignal(str)

    def __init__(self, email, password, selected_categories, min_budget, min_time_left):
        super().__init__()
        self.email = email
        self.password = password
        self.selected_categories = selected_categories
        self.min_budget = min_budget
        self.min_time_left = min_time_left
        self.stop_bidding = False  # Flag to stop the bidding
        self.driver = None
        
    

    def run(self):
        self.start_bidding()

    def initialize_driver(self):
        try:

            driver = webdriver.Chrome()
            
            return driver
        except WebDriverException as e:
            self.bidding_started.emit(f"Error initializing WebDriver: {e}")
            return None

    def start_bidding(self):
        driver = self.initialize_driver()
        if driver is None:
            self.bidding_started.emit("Failed to initialize WebDriver.")
            return

        self.driver = driver  # Store driver to reference it later for quitting

        try:
            for attempt in range(3):  # Attempt to log in up to 3 times
                if self.stop_bidding:  # Check if bidding should stop
                    self.bidding_started.emit("Bidding stopped.")
                    driver.quit()
                    return
                
                try:
                    if attempt == 0:
                        # Navigate to the Studypool homepage initially
                        driver.get('https://www.studypool.com')

                    # Click the "Login" button (on the current page or the homepage for the first attempt)
                    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.LINK_TEXT, 'Login'))).click()
                    WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH, '//input[@placeholder="Email/Username"]')))

                    # Enter credentials
                    email_input = driver.find_element(By.XPATH, '//input[@placeholder="Email/Username"]')
                    email_input.clear()
                    email_input.send_keys(self.email)
                    password_input = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, 'UserLogin_password')))
                    password_input.clear()
                    password_input.send_keys(self.password)
                    password_input.send_keys(Keys.RETURN)

                    # Wait for confirmation of login
                    WebDriverWait(driver, 2).until(EC.presence_of_element_located((By.XPATH, '//a[@href="/questions/newest"]')))

                    self.bidding_started.emit("Login successful. Starting bidding...")
                    self.bidding_started.emit("Bidding started...")

                    # After successful login, open the bidding page
                    driver.get('https://www.studypool.com/questions/newest')
                    WebDriverWait(driver, 10).until(EC.url_contains("questions/newest"))
                    self.process_questions(driver)
                    break  # Exit the loop if login is successful

                except Exception as login_error:
                    self.bidding_started.emit(f"Login attempt {attempt + 1} failed: {str(login_error)}")
                    if attempt < 2:  # Retry if attempts are less than 3
                        self.bidding_started.emit("Retrying login in 2 seconds...")
                        time.sleep(2)  # Wait for 2 seconds before retrying
                    else:
                        self.bidding_started.emit("Failed to log in after 3 attempts.")
                        driver.quit()
                        return

        except Exception as e:
            self.bidding_started.emit(f"An error occurred: {str(e)}")
        finally:
            if self.driver:
                self.driver.quit()  # Ensure the driver is quit when done

    def process_questions(self, driver):
        retry_attempts = 3
        while not self.stop_bidding:  # Check if bidding should stop
            try:

                # Check if stop_bidding flag is set before continuing
                if self.stop_bidding:
                    self.bidding_started.emit("Bidding stopped.")
                    driver.quit()
                    return

                if len(driver.window_handles) == 1:
                    driver.switch_to.window(driver.window_handles[0])

                for attempt in range(retry_attempts):
                    if self.stop_bidding:  # Check if bidding should stop
                        self.bidding_started.emit("Bidding stopped.")
                        driver.quit()
                        return
                    
                    try:
                        questions = WebDriverWait(driver, 10).until(
                            EC.presence_of_all_elements_located((By.CLASS_NAME, 'question-list-entry'))
                        )
                        break
                    except TimeoutException:
                        self.bidding_started.emit(f"Attempt {attempt + 1} of {retry_attempts} - Retrying to detect questions...")
                else:
                    self.bidding_started.emit("Failed to load questions after multiple attempts.")
                    return

                for question in questions:
                    try:
                        if self.is_valid_question(question, driver):
                            #self.bidding_started.emit("Valid question found. Bid placed successfully!")
                            break
                    except Exception as e:
                        # Log the error, close the tab, and emit an error message
                        self.bidding_started.emit("Error placing the bid")
                        print(f"Error encountered in question processing: {e}")
                        if len(driver.window_handles) > 1:
                            driver.close()
                            driver.switch_to.window(driver.window_handles[0])
                else:
                    self.bidding_started.emit("No valid question found. Waiting for new questions...")

                time.sleep(2)

            except NoSuchWindowException:
                self.bidding_started.emit("The main window was closed unexpectedly. Reopening the main page...")
                driver.get('https://www.studypool.com/questions/newest')
                WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'question-list-entry')))
        
        
        driver.quit()

    def is_valid_question(self, question, driver):
        try:
            
            # Fetch valid categories from the database
            valid_categories = load_valid_categories_from_db()

            # Check if question is "viewed" or "bid on"
            icon_elements = question.find_elements(By.CLASS_NAME, 'material-icons')
            for icon_element in icon_elements:
                icon_text = icon_element.text.strip()
                if icon_text in ["visibility", "check_circle_outline"]:
                    return False  # Skip if already viewed or bid on

            # Extract budget, subject, and time left
            budget_text = question.find_element(By.CLASS_NAME, 'budget-col').text.strip()
            if budget_text and '$' in budget_text:
                budget_amount = budget_text.split()[0].replace('$', '').strip()
                budget = float(budget_amount)
            else:
                return False

            subject = question.find_element(By.CLASS_NAME, 'subject-col').text.lower().strip()
            time_left_text = question.find_element(By.CLASS_NAME, 'time-col').text.strip()
            if 'D' in time_left_text:
                time_left = int(time_left_text.replace('D', '').strip()) * 24
            elif 'H' in time_left_text:
                time_left = int(time_left_text.replace('H', '').strip())
            else:
                return False

            # Check if the subject is not in the valid categories list
            if subject not in valid_categories:
                add_category_to_db(subject)  # Add category using the function
                return False  # Skip this question and do not bid

            # Validate against user-selected categories, minimum budget, and time left
            if (
                budget >= self.min_budget and
                time_left >= self.min_time_left and
                any(selected_category.lower() in subject for selected_category in self.selected_categories)
            ):
                # Click the question title to view details
                title_element = question.find_element(By.CLASS_NAME, 'questionTitleCol')
                driver.execute_script("arguments[0].click();", title_element)
                driver.switch_to.window(driver.window_handles[-1])

                WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, 'finalize-bid-check')))
                finalize_bid_checkbox = driver.find_element(By.CLASS_NAME, 'finalize-bid-check')
                if not finalize_bid_checkbox.is_selected():
                    finalize_bid_checkbox.click()

                place_bid_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "a.btn.btn-blue.btn-lg"))
                )
                place_bid_button.click()

                # Wait for the confirmation popup and try different methods to click the final "Place Bid" button
                try:
                    # Alternative 1: CSS Selector for final confirmation button
                    confirm_bid_button = WebDriverWait(driver, 1).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "a.cta-resolve.primary-cta.btn-lightBlue"))
                    )
                    confirm_bid_button.click()
                except TimeoutException:
                    print("Could not click final confirmation using CSS; trying XPath...")

                    # Alternative 2: XPath for final confirmation button
                    try:
                        confirm_bid_button = WebDriverWait(driver, 1).until(
                            EC.element_to_be_clickable((By.XPATH, "//a[contains(@class, 'cta-resolve') and contains(text(), 'Place Bid')]"))
                        )
                        confirm_bid_button.click()
                    except TimeoutException:
                        print("Could not click final confirmation using XPath; trying JavaScript...")

                        # Alternative 3: JavaScript click for the final confirmation button
                        confirm_bid_button = driver.find_element(By.CSS_SELECTOR, "a.cta-resolve.primary-cta.btn-lightBlue")
                        driver.execute_script("arguments[0].click();", confirm_bid_button)

                # Prepare question details for log
                question_details = f"{subject}, {budget_text}, {time_left_text}"
                self.bid_placed.emit(f"Valid question found: {question_details}. Bid placed successfully!")

                # Close bid tab and return to main tab
                driver.close()
                driver.switch_to.window(driver.window_handles[0])

                return True

        except (NoSuchElementException, TimeoutException, NoSuchWindowException, WebDriverException, ValueError, IndexError) as e:
            print(f"Error encountered in bid placement: {e}")
            raise e  # Re-raise the exception to handle it in process_questions

        return False

    def stop(self):
        # Stop the bidding and quit the browser
        self.stop_bidding = True
        if self.driver:
            self.driver.quit()  # Close the browser
        self.quit()  # Stop the thread gracefully
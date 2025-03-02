from PyQt5.QtCore import QTimer

def stop_bidding_process(bidding_thread, update_status_function, check_thread_stopped_function):
    """Cleanly stop the bidding process."""
    if bidding_thread and bidding_thread.isRunning():
        update_status_function("Stopping the bidding process...")

        # Set the stop flag for the bidding thread to stop
        bidding_thread.stop_bidding = True

        # Ensure thread is properly cleaned up
        QTimer.singleShot(100, lambda: check_thread_stopped_function())
    else:
        update_status_function("No bidding process running.")

def check_thread_stopped(bidding_thread, update_status_function):
    """Check if the bidding thread has stopped and update status."""
    if not bidding_thread.isRunning():
        update_status_function("Bidding has been stopped.")
        bidding_thread.quit()
        bidding_thread.wait()  # Ensure the thread has finished
    else:
        # If the thread is still running, check again after 100 ms
        QTimer.singleShot(100, lambda: check_thread_stopped(bidding_thread, update_status_function))

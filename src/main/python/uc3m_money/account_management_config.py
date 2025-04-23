"""Global constants for finding the path"""
import os.path

# Get the absolute path to the project root directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
JSON_FILES_PATH = os.path.join(PROJECT_ROOT, "src/unittest/JSONFiles/")
JSON_FILES_DEPOSITS = JSON_FILES_PATH + "deposits/"
TRANSFERS_STORE_FILE = JSON_FILES_PATH + "transfers_store.json"
DEPOSITS_STORE_FILE = JSON_FILES_PATH + "deposits_store.json"
TRANSACTIONS_STORE_FILE = JSON_FILES_PATH + "transactions.json"
BALANCES_STORE_FILE = JSON_FILES_PATH + "balances.json"

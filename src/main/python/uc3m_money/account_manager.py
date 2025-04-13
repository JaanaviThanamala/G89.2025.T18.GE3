"""Account manager module """
import re
import json
from datetime import datetime, timezone
from uc3m_money.account_management_exception import AccountManagementException
from uc3m_money.account_management_config import (TRANSFERS_STORE_FILE,
                                        DEPOSITS_STORE_FILE,
                                        TRANSACTIONS_STORE_FILE,
                                        BALANCES_STORE_FILE)

from uc3m_money.transfer_request import TransferRequest
from uc3m_money.account_deposit import AccountDeposit


class AccountManager:
    """Class for providing the methods for managing the orders"""
    # Applied Singleton pattern to AccountManager
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AccountManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        pass

    @staticmethod
    def validate_iban(iban: str) -> str:
        """Renamed valvian() to validate_iban to improve clarity and naming consistency """
        """Validates the format and control digit of a Spanish IBAN."""
        AccountManager._check_iban_format(iban)
        expected_check_digits = AccountManager._calculate_check_digits(iban)
        actual_check_digits = int(iban[2:4])

        if expected_check_digits != actual_check_digits:
            raise AccountManagementException("Invalid IBAN control digit")

        return iban

    @staticmethod
    
    def _check_iban_format(iban: str):
        # Broke down the original IBAN validation logic into two helper methods:
        #  _check_iban_format() — uses regex to check IBAN structure 
        # _calculate_check_digits() — implements the modulo 97 algorithm

        """Validates the IBAN structure using regex."""
        pattern = re.compile(r"^ES[0-9]{22}")
        if not pattern.fullmatch(iban):
            raise AccountManagementException("Invalid IBAN format")

    @staticmethod
    def _calculate_check_digits(iban: str) -> int:
        """Calculates the correct IBAN check digits using modulo 97 algorithm."""
        rearranged_iban = iban[:2] + "00" + iban[4:]
        rearranged_iban = rearranged_iban[4:] + rearranged_iban[:4]

        alphanum_map = {chr(i): str(10 + i - ord('A')) for i in range(ord('A'), ord('Z') + 1)}
        numeric_iban = ''.join(alphanum_map.get(c, c) for c in rearranged_iban)

        mod_result = int(numeric_iban) % 97
        return 98 - mod_result
    
    def validate_concept(self, concept: str):
        """regular expression for checking the minimum and maximum length as well as
        the allowed characters and spaces restrictions
        there are other ways to check this"""
        myregex = re.compile(r"^(?=^.{10,30}$)([a-zA-Z]+(\s[a-zA-Z]+)+)$")

        res = myregex.fullmatch(concept)
        if not res:
            raise AccountManagementException ("Invalid concept format")

    def validate_transfer_date(self, t_d):
        """validates the arrival date format  using regex"""
        mr = re.compile(r"^(([0-2]\d|3[0-1])\/(0\d|1[0-2])\/\d\d\d\d)$")
        res = mr.fullmatch(t_d)
        if not res:
            raise AccountManagementException("Invalid date format")

        try:
            my_date = datetime.strptime(t_d, "%d/%m/%Y").date()
        except ValueError as ex:
            raise AccountManagementException("Invalid date format") from ex

        if my_date < datetime.now(timezone.utc).date():
            raise AccountManagementException("Transfer date must be today or later.")

        if my_date.year < 2025 or my_date.year > 2050:
            raise AccountManagementException("Invalid date format")
        return t_d
    #pylint: disable=too-many-arguments
    # New helper for transfer type validation
    def _validate_transfer_type(self, transfer_type: str):
        if not re.fullmatch(r"(ORDINARY|INMEDIATE|URGENT)", transfer_type):
            raise AccountManagementException("Invalid transfer type")
    
    # New helper for transfer amount validation
    def _validate_transfer_amount(self, amount: float):
        try:
            float_amount = float(amount)
        except ValueError as exc:
            raise AccountManagementException("Invalid transfer amount") from exc

        str_amount = str(float_amount)
        if '.' in str_amount and len(str_amount.split('.')[1]) > 2:
            raise AccountManagementException("Invalid transfer amount")

        if float_amount < 10 or float_amount > 10000:
            raise AccountManagementException("Invalid transfer amount")

        return float_amount

    #Extracted reusable JSON loader
    def _load_json_file(self, path):
        try:
            with open(path, "r", encoding="utf-8", newline="") as file:
                return json.load(file)
        except FileNotFoundError:
            return []
        except json.JSONDecodeError as ex:
            raise AccountManagementException("JSON Decode Error - Wrong JSON Format") from ex

    # Extracted reusable JSON writer
    def _save_json_file(self, path, data):
        try:
            with open(path, "w", encoding="utf-8", newline="") as file:
                json.dump(data, file, indent=2)
        except (FileNotFoundError, json.JSONDecodeError) as ex:
            raise AccountManagementException("Error writing to JSON file") from ex

    def transfer_request(self, from_iban, to_iban, concept, transfer_type, date, amount):
        #Simplified long function using helpers above
        self.validate_iban(from_iban)
        self.validate_iban(to_iban)
        self.validate_concept(concept)
        self._validate_transfer_type(transfer_type)
        self.validate_transfer_date(date)
        float_amount = self._validate_transfer_amount(amount)

        request = TransferRequest(from_iban, to_iban, concept, transfer_type, date, amount)
        transfers = self._load_json_file(TRANSFERS_STORE_FILE)

        for t in transfers:
            if all(t[key] == getattr(request, key) for key in ["from_iban", "to_iban", "transfer_date", "transfer_amount", "transfer_concept", "transfer_type"]):
                raise AccountManagementException("Duplicated transfer in transfer list")

        transfers.append(request.to_json())
        self._save_json_file(TRANSFERS_STORE_FILE, transfers)

        return request.transfer_code

    def deposit_into_account(self, input_file: str) -> str:
        # Simplified deposit logic using shared helpers
        input_data = self._load_json_file(input_file)
        try:
            deposit_iban = input_data["IBAN"]
            deposit_amount = input_data["AMOUNT"]
        except KeyError as e:
            raise AccountManagementException("Error - Invalid Key in JSON") from e

        self.validate_iban(deposit_iban)
        if not re.fullmatch(r"^EUR [0-9]{4}\.[0-9]{2}", deposit_amount):
            raise AccountManagementException("Error - Invalid deposit amount")

        deposit_amount_float = float(deposit_amount[4:])
        if deposit_amount_float == 0:
            raise AccountManagementException("Error - Deposit must be greater than 0")

        deposit_obj = AccountDeposit(to_iban=deposit_iban, deposit_amount=deposit_amount_float)
        deposits = self._load_json_file(DEPOSITS_STORE_FILE)
        deposits.append(deposit_obj.to_json())
        self._save_json_file(DEPOSITS_STORE_FILE, deposits)

        return deposit_obj.deposit_signature
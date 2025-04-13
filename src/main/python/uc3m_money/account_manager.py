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
        """Broke down the original IBAN validation logic into two helper methods:
         _check_iban_format() — uses regex to check IBAN structure 
         _calculate_check_digits() — implements the modulo 97 algorithm"""
         
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
    def transfer_request(self, from_iban: str,
                         to_iban: str,
                         concept: str,
                         transfer_type: str,
                         date: str,
                         amount: float)->str:
        """first method: receives transfer info and
        stores it into a file"""
        self.validate_iban(from_iban)
        self.validate_iban(to_iban)
        self.validate_concept(concept)
        mr = re.compile(r"(ORDINARY|INMEDIATE|URGENT)")
        res = mr.fullmatch(transfer_type)
        if not res:
            raise AccountManagementException("Invalid transfer type")
        self.validate_transfer_date(date)



        try:
            f_amount  = float(amount)
        except ValueError as exc:
            raise AccountManagementException("Invalid transfer amount") from exc

        n_str = str(f_amount)
        if '.' in n_str:
            decimales = len(n_str.split('.')[1])
            if decimales > 2:
                raise AccountManagementException("Invalid transfer amount")

        if f_amount < 10 or f_amount > 10000:
            raise AccountManagementException("Invalid transfer amount")

        my_request = TransferRequest(from_iban=from_iban,
                                     to_iban=to_iban,
                                     transfer_concept=concept,
                                     transfer_type=transfer_type,
                                     transfer_date=date,
                                     transfer_amount=amount)

        try:
            with open(TRANSFERS_STORE_FILE, "r", encoding="utf-8", newline="") as file:
                t_l = json.load(file)
        except FileNotFoundError:
            t_l = []
        except json.JSONDecodeError as ex:
            raise AccountManagementException("JSON Decode Error - Wrong JSON Format") from ex

        for t_i in t_l:
            if (t_i["from_iban"] == my_request.from_iban and
                    t_i["to_iban"] == my_request.to_iban and
                    t_i["transfer_date"] == my_request.transfer_date and
                    t_i["transfer_amount"] == my_request.transfer_amount and
                    t_i["transfer_concept"] == my_request.transfer_concept and
                    t_i["transfer_type"] == my_request.transfer_type):
                raise AccountManagementException("Duplicated transfer in transfer list")

        t_l.append(my_request.to_json())

        try:
            with open(TRANSFERS_STORE_FILE, "w", encoding="utf-8", newline="") as file:
                json.dump(t_l, file, indent=2)
        except FileNotFoundError as ex:
            raise AccountManagementException("Wrong file  or file path") from ex
        except json.JSONDecodeError as ex:
            raise AccountManagementException("JSON Decode Error - Wrong JSON Format") from ex

        return my_request.transfer_code

    def deposit_into_account(self, input_file:str)->str:
        """manages the deposits received for accounts"""
        try:
            with open(input_file, "r", encoding="utf-8", newline="") as file:
                i_d = json.load(file)
        except FileNotFoundError as ex:
            raise AccountManagementException("Error: file input not found") from ex
        except json.JSONDecodeError as ex:
            raise AccountManagementException("JSON Decode Error - Wrong JSON Format") from ex

        # comprobar valores del fichero
        try:
            deposit_iban = i_d["IBAN"]
            deposit_amount = i_d["AMOUNT"]
        except KeyError as e:
            raise AccountManagementException("Error - Invalid Key in JSON") from e


        deposit_iban = self.validate_iban(deposit_iban)
        myregex = re.compile(r"^EUR [0-9]{4}\.[0-9]{2}")
        res = myregex.fullmatch(deposit_amount)
        if not res:
            raise AccountManagementException("Error - Invalid deposit amount")

        d_a_f = float(deposit_amount[4:])
        if d_a_f == 0:
            raise AccountManagementException("Error - Deposit must be greater than 0")

        deposit_obj = AccountDeposit(to_iban=deposit_iban,
                                     deposit_amount=d_a_f)

        try:
            with open(DEPOSITS_STORE_FILE, "r", encoding="utf-8", newline="") as file:
                d_l = json.load(file)
        except FileNotFoundError as ex:
            d_l = []
        except json.JSONDecodeError as ex:
            raise AccountManagementException("JSON Decode Error - Wrong JSON Format") from ex

        d_l.append(deposit_obj.to_json())

        try:
            with open(DEPOSITS_STORE_FILE, "w", encoding="utf-8", newline="") as file:
                json.dump(d_l, file, indent=2)
        except FileNotFoundError as ex:
            raise AccountManagementException("Wrong file  or file path") from ex
        except json.JSONDecodeError as ex:
            raise AccountManagementException("JSON Decode Error - Wrong JSON Format") from ex

        return deposit_obj.deposit_signature


    def read_transactions_file(self):
        """loads the content of the transactions file
        and returns a list"""
        try:
            with open(TRANSACTIONS_STORE_FILE, "r", encoding="utf-8", newline="") as file:
                input_list = json.load(file)
        except FileNotFoundError as ex:
            raise AccountManagementException("Wrong file  or file path") from ex
        except json.JSONDecodeError as ex:
            raise AccountManagementException("JSON Decode Error - Wrong JSON Format") from ex
        return input_list


    def calculate_balance(self, iban:str)->bool:
        """calculate the balance for a given iban"""
        iban = self.validate_iban(iban)
        t_l = self.read_transactions_file()
        iban_found = False
        bal_s = 0
        for transaction in t_l:
            #print(transaction["IBAN"] + " - " + iban)
            if transaction["IBAN"] == iban:
                bal_s += float(transaction["amount"])
                iban_found = True
        if not iban_found:
            raise AccountManagementException("IBAN not found")

        last_balance = {"IBAN": iban,
                        "time": datetime.timestamp(datetime.now(timezone.utc)),
                        "BALANCE": bal_s}

        try:
            with open(BALANCES_STORE_FILE, "r", encoding="utf-8", newline="") as file:
                balance_list = json.load(file)
        except FileNotFoundError:
            balance_list = []
        except json.JSONDecodeError as ex:
            raise AccountManagementException("JSON Decode Error - Wrong JSON Format") from ex

        balance_list.append(last_balance)

        try:
            with open(BALANCES_STORE_FILE, "w", encoding="utf-8", newline="") as file:
                json.dump(balance_list, file, indent=2)
        except FileNotFoundError as ex:
            raise AccountManagementException("Wrong file  or file path") from ex
        return True

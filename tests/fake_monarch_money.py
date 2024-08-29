import json
import os

from typing import Any, Dict, List, Optional


class FakeMonarchMoney:
    def __init__(self):
        self.get_accounts_count: int = 0
        self.balances: Dict[str, float] = {}
        self.category_exists = True
        self.create_transaction_count = 0
        self.new_transaction_category_group_id = ""
        self.new_transaction_category_name = ""
        self.new_transaction_date = ""
        self.new_transaction_account_id = ""
        self.new_transaction_amount = 0
        self.new_transaction_merchant = ""
        self.new_transaction_category_id = ""
        self.new_transaction_notes = ""
        self.update_transaction_count = 0
        self.update_transaction_id = ""
        self.update_transaction_notes = ""
        return

    async def login(self, username: str, password: str) -> None:
        return

    async def get_accounts(self) -> Dict:
        self.get_accounts_count += 1
        return self._load_json_response("accounts.json")

    async def create_manual_account(
        self,
        account_type: str = "",
        account_sub_type: str = "",
        is_in_net_worth: bool = True,
        account_name: str = "",
        account_balance: float = 0,
    ) -> Dict:
        return self._load_json_response("new_account.json")

    async def get_transactions(
        self,
        limit: int = 0,
        start_date: str = "",
        end_date: str = "",
        account_ids: List[str] = [],
    ) -> Dict:
        self.get_transactions_start_date = start_date
        self.get_transactions_end_date = end_date
        self.get_transactions_account_ids = account_ids
        return self._load_json_response("get_transactions.json")

    async def update_account(
        self, account_id: str = "", account_balance: float = 0
    ) -> None:
        self.balances[account_id] = account_balance
        return

    async def get_transaction_categories(self) -> Dict[str, Any]:
        if self.category_exists:
            return self._load_json_response("transaction_categories.json")
        else:
            return {"categories": []}
        return

    async def get_transaction_category_groups(self) -> Dict[str, Any]:
        return self._load_json_response("transaction_category_groups.json")

    async def create_transaction_category(
        self,
        group_id: str,
        transaction_category_name: str,
    ):
        self.new_transaction_category_group_id = group_id
        self.new_transaction_category_name = transaction_category_name
        return self._load_json_response("create_transaction_category.json")

    async def create_transaction(
        self,
        date: str,
        account_id: str,
        amount: float,
        merchant_name: str,
        category_id: str,
        notes: str = "",
    ) -> Dict[str, Any]:
        self.create_transaction_count += 1
        self.new_transaction_date = date
        self.new_transaction_account_id = account_id
        self.new_transaction_amount = amount
        self.new_transaction_merchant = merchant_name
        self.new_transaction_category_id = category_id
        self.new_transaction_notes = notes
        return self._load_json_response("create_transaction.json")

    async def update_transaction(
        self,
        transaction_id: str,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        self.update_transaction_count += 1
        self.update_transaction_id = transaction_id
        self.update_transaction_notes = notes
        return

    def _load_json_response(self, filename: str) -> Dict:
        tests_dir = os.path.split(os.path.realpath(__file__))[0]
        json_dir = os.path.join(tests_dir, "monarch_responses")
        json_file = os.path.join(json_dir, filename)
        with open(json_file) as f:
            return json.load(f)

**Analyzer ID:** `prebuilt-bankStatement.us`

**Description:** US bank statements.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`BankAddress`|`string`|`extract`|Listed address of the bank|123 Main St, Redmond, WA 98052|
|`BankName`|`string`|`extract`|Listed name of the bank|Contoso Bank|
|`AccountHolderAddress`|`string`|`extract`|Address of the account holder|456 Main St, Redmond, WA 98052|
|`AccountHolderName`|`string`|`extract`|Name of the account holder|JOHN DOE|
|`StatementStartDate`|`date`|`extract`|Start date of the bank statement|2017-07-01|
|`StatementEndDate`|`date`|`extract`|End date of the bank statement|2017-07-31|
|`Accounts`|`array`|`generate`|||
|`Accounts.*`|`object`|`generate`|||
|`Accounts.*.Number`|`string`|`extract`|Account number on the bank statement|987-654-3210|
|`Accounts.*.Type`|`string`|`extract`|Type of account on the bank statement|Checking|
|`Accounts.*.BeginningBalance`|`number`|`extract`|Beginning balance on the bank statement|1488.03|
|`Accounts.*.EndingBalance`|`number`|`extract`|Ending balance on the bank statement|1488.03|
|`Accounts.*.TotalServiceFees`|`number`|`extract`|Total service fees|0|
|`Accounts.*.Transactions`|`array`|`generate`|||
|`Accounts.*.Transactions.*`|`object`|`generate`|Extracted transaction line item||
|`Accounts.*.Transactions.*.Date`|`date`|`extract`|Transaction date|2023-07-17|
|`Accounts.*.Transactions.*.Description`|`string`|`extract`|Transaction description|OnlineTransfer From Chk...6609 Transaction#: 6373187418|
|`Accounts.*.Transactions.*.CheckNumber`|`string`|`extract`|Check number of the transaction|6609|
|`Accounts.*.Transactions.*.DepositAmount`|`number`|`extract`|Amount of deposit in the transaction|1500|
|`Accounts.*.Transactions.*.WithdrawalAmount`|`number`|`extract`|Amount of withdrawal in the transaction|200|
|`Accounts.*.Checks`|`array`|`generate`|||
|`Accounts.*.Checks.*`|`object`|`generate`|Extracted check line item||
|`Accounts.*.Checks.*.Number`|`string`|`extract`|Check number|7175|
|`Accounts.*.Checks.*.Date`|`date`|`extract`|Check date|2023-03-11|
|`Accounts.*.Checks.*.Amount`|`number`|`extract`|Check amount|150|

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`TaxYear`|`string`|`extract`|Tax Year extracted from Form 1099-SSA.|2022|
|`Beneficiary`|`object`|`generate`|Extracted beneficiary information.||
|`Beneficiary.Name`|`string`|`extract`|Beneficiary's full name.|BETH MITCHELL|
|`Beneficiary.SSN`|`string`|`extract`|Beneficiary's Social Security Number.|294-98-3046|
|`Beneficiary.Address`|`string`|`extract`|Beneficiary's address as written on the form.|828 E 2ND ST, CHARLESTON, FL 50850|
|`Box3`|`number`|`extract`|Total benefits paid during the year.|24360|
|`Box4`|`number`|`extract`|Benefits repaid by the beneficiary.|0|
|`Box5`|`number`|`extract`|Net benefits after repayment (Box 3 minus Box 4).|24360|
|`Box6`|`number`|`extract`|Voluntary Federal income tax withheld from benefits.|0|
|`DescriptionOfAmountInBox3`|`string`|`extract`|Description of the amount in Box 3 (Benefits paid).|Benefits paid|
|`DescriptionOfAmountInBox4`|`string`|`extract`|Description of the amount in Box 4 (Benefits repaid).|Benefits repaid|
|`Box8`|`string`|`extract`|Claim number associated with the form.|959-78-6976H|

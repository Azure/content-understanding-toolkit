| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`PayerName`|`string`|`extract`|Name of the payer (drawer)|Jane Doe|
|`PayerAddress`|`string`|`extract`|Address of the payer (drawer)|123 Main St, Redmond, WA 98052|
|`PayeeName`|`string`|`extract`|Name of the payee|John Smith|
|`CheckDate`|`date`|`extract`|Date the check was written|2024-06-20|
|`Amount`|`number`|`extract`|Amount of the check in numeric form|123456|
|`AmountInWords`|`string`|`extract`|Amount of the check written in words (maps from source 'WordAmount')|One Hundred Twenty-Three Thousand Four Hundred Fifty-Six And 00/100 Dollars|
|`BankName`|`string`|`extract`|Name of the bank|Contoso Bank|
|`Memo`|`string`|`extract`|Short note describing the payment|Fees & Charges|
|`MICR`|`object`|`generate`|Magnetic Ink Character Recognition (MICR) line||
|`MICR.RoutingNumber`|`string`|`extract`|Routing number of the bank|125000024|
|`MICR.AccountNumber`|`string`|`extract`|Account number|55432|
|`MICR.CheckNumber`|`string`|`extract`|Check number|370654|
|`PayerSignatures`|`array`|`generate`|Payer's signature presence classification, one per signature line (signed \| unsigned \| notFound).||
|`PayerSignatures.*`|`string`|`classify`|||

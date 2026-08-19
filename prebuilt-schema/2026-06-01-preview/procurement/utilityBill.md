| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`AccountNumber`|`string`|`extract`||1234567890-1|
|`TotalAdjustmentAmount`|`object`|`generate`|||
|`TotalAdjustmentAmount.CurrencyCode`|`string`|`generate`||USD|
|`TotalAdjustmentAmount.Amount`|`number`|`extract`||0|
|`AmountDue`|`object`|`generate`|||
|`AmountDue.CurrencyCode`|`string`|`generate`||USD|
|`AmountDue.Amount`|`number`|`extract`||2004.89|
|`BalanceForward`|`object`|`generate`|||
|`BalanceForward.CurrencyCode`|`string`|`generate`||USD|
|`BalanceForward.Amount`|`number`|`extract`||502|
|`BillingDate`|`date`|`extract`||2025-08-01|
|`BillNumber`|`string`|`extract`||BILL-1001|
|`CountryRegion`|`string`|`generate`|Country or region where the utility bill was issued|USA|
|`LineItems`|`array`|`generate`|||
|`LineItems.*`|`object`|`generate`|||
|`LineItems.*.TotalAmount`|`object`|`generate`|||
|`LineItems.*.TotalAmount.CurrencyCode`|`string`|`generate`||USD|
|`LineItems.*.TotalAmount.Amount`|`number`|`extract`||40|
|`LineItems.*.Description`|`string`|`extract`||Consulting service|
|`LineItems.*.Quantity`|`number`|`extract`||2|
|`LineItems.*.ServiceEndDate`|`date`|`extract`||2025-01-15|
|`LineItems.*.ServiceStartDate`|`date`|`extract`||2025-01-15|
|`LineItems.*.QuantityUnit`|`string`|`extract`||hours|
|`LineItems.*.UnitPrice`|`object`|`generate`|||
|`LineItems.*.UnitPrice.CurrencyCode`|`string`|`generate`||USD|
|`LineItems.*.UnitPrice.Amount`|`number`|`extract`||0.02408|
|`ChargeSummaries`|`array`|`generate`|||
|`ChargeSummaries.*`|`object`|`generate`|||
|`ChargeSummaries.*.Amount`|`object`|`generate`|||
|`ChargeSummaries.*.Amount.CurrencyCode`|`string`|`generate`||USD|
|`ChargeSummaries.*.Amount.Amount`|`number`|`extract`||1107.65|
|`ChargeSummaries.*.Description`|`string`|`extract`||TOTAL ELECTRIC|
|`CustomerAddress`|`string`|`extract`||123 Other St, Redmond WA, 98052|
|`CustomerName`|`string`|`extract`||Microsoft Corp|
|`CustomerTaxId`|`string`|`extract`||765432-1|
|`DueDate`|`date`|`extract`||2019-12-15|
|`PreviousBalance`|`object`|`generate`|||
|`PreviousBalance.CurrencyCode`|`string`|`generate`||USD|
|`PreviousBalance.Amount`|`number`|`extract`||1502.89|
|`PreviousPaymentAmount`|`object`|`generate`|||
|`PreviousPaymentAmount.CurrencyCode`|`string`|`generate`||USD|
|`PreviousPaymentAmount.Amount`|`number`|`extract`||-1000.89|
|`PONumber`|`string`|`extract`||PO-3333|
|`ServiceAddress`|`string`|`extract`||123 Service St, Redmond WA, 98052|
|`ServiceEndDate`|`date`|`extract`||2019-11-14|
|`ServiceStartDate`|`date`|`extract`||2019-10-14|
|`TotalCurrentChargeAmount`|`object`|`generate`|||
|`TotalCurrentChargeAmount.CurrencyCode`|`string`|`generate`||USD|
|`TotalCurrentChargeAmount.Amount`|`number`|`extract`||1502.89|
|`TotalTaxAmount`|`object`|`generate`|||
|`TotalTaxAmount.CurrencyCode`|`string`|`generate`||USD|
|`TotalTaxAmount.Amount`|`number`|`generate`||10|
|`VendorAddress`|`string`|`extract`||123 456th St, New York, NY 10001|
|`VendorName`|`string`|`extract`||CONTOSO LTD.|
|`VendorTaxId`|`string`|`extract`||123456-7|

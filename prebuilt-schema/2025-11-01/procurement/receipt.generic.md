**Analyzer ID:** `prebuilt-receipt.generic`

**Description:** General sales receipts.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`MerchantName`|`string`|`extract`|Name of the merchant issuing the receipt|Contoso|
|`MerchantPhoneNumber`|`string`|`extract`|Listed phone number of merchant|987-654-3210|
|`MerchantAddress`|`string`|`extract`|Listed address of merchant|123 Main St Redmond WA 98052|
|`TotalAmount`|`object`|`generate`|Full transaction total of receipt||
|`TotalAmount.CurrencyCode`|`string`|`generate`||USD|
|`TotalAmount.Amount`|`number`|`extract`||2516.28|
|`TransactionDate`|`date`|`extract`|Date the receipt was issued|2019-06-10|
|`TransactionTime`|`time`|`extract`|Time the receipt was issued|13:59:00|
|`SubtotalAmount`|`object`|`generate`|Subtotal of receipt, often before taxes are applied||
|`SubtotalAmount.CurrencyCode`|`string`|`generate`||USD|
|`SubtotalAmount.Amount`|`number`|`generate`||2297.97|
|`TotalTaxAmount`|`object`|`generate`|Tax on receipt, often sales tax or equivalent (aggregate)||
|`TotalTaxAmount.CurrencyCode`|`string`|`generate`||USD|
|`TotalTaxAmount.Amount`|`number`|`generate`||218.31|
|`TipAmount`|`object`|`generate`|Tip included by buyer||
|`TipAmount.CurrencyCode`|`string`|`generate`||USD|
|`TipAmount.Amount`|`number`|`extract`||10|
|`LineItems`|`array`|`generate`|||
|`LineItems.*`|`object`|`generate`|Extracted line item||
|`LineItems.*.TotalAmount`|`object`|`generate`|Total amount of the line item (may include taxes)||
|`LineItems.*.TotalAmount.CurrencyCode`|`string`|`generate`||USD|
|`LineItems.*.TotalAmount.Amount`|`number`|`extract`||1998|
|`LineItems.*.Description`|`string`|`extract`|Item description|Surface Pro 6|
|`LineItems.*.Quantity`|`number`|`extract`|Quantity of each item|2|
|`LineItems.*.UnitPrice`|`object`|`generate`|Individual price of each item unit||
|`LineItems.*.UnitPrice.CurrencyCode`|`string`|`generate`||USD|
|`LineItems.*.UnitPrice.Amount`|`number`|`extract`||10|
|`LineItems.*.ProductCode`|`string`|`extract`|Product code, product number, or SKU associated with the specific line item|A123|
|`LineItems.*.QuantityUnit`|`string`|`extract`|Quantity unit of each item|hours|
|`CountryRegion`|`string`|`generate`|Country or region where the receipt was issued|USA|
|`TaxDetails`|`array`|`generate`|List of tax details||
|`TaxDetails.*`|`object`|`generate`|A single tax detail||
|`TaxDetails.*.Amount`|`object`|`generate`|The amount of the tax detail||
|`TaxDetails.*.Amount.CurrencyCode`|`string`|`generate`||USD|
|`TaxDetails.*.Amount.Amount`|`number`|`extract`||10|
|`TaxDetails.*.Rate`|`number`|`extract`|The rate of the tax detail (decimal fraction)|0.10|
|`TaxDetails.*.NetAmount`|`object`|`generate`|The net amount before tax.||
|`TaxDetails.*.NetAmount.CurrencyCode`|`string`|`generate`||USD|
|`TaxDetails.*.NetAmount.Amount`|`number`|`extract`||10|
|`TaxDetails.*.Description`|`string`|`extract`|The description of the tax detail|Sales Tax|

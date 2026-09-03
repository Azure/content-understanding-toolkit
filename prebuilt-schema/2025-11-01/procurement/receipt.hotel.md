**Analyzer ID:** `prebuilt-receipt.hotel`

**Description:** Hotel receipts and folios.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`MerchantName`|`string`|`extract`|Name of the merchant issuing the receipt|Contoso|
|`MerchantPhoneNumber`|`string`|`extract`|Listed phone number of merchant|987-654-3210|
|`MerchantAddress`|`string`|`extract`|Listed address of merchant|123 Main St Redmond WA 98052|
|`GrossAmount`|`object`|`generate`|Gross amount of receipt||
|`GrossAmount.CurrencyCode`|`string`|`generate`||USD|
|`GrossAmount.Amount`|`number`|`generate`||104.92|
|`Balance`|`object`|`generate`|Balance due on receipt||
|`Balance.CurrencyCode`|`string`|`generate`||USD|
|`Balance.Amount`|`number`|`extract`||0|
|`ArrivalDate`|`date`|`extract`|Date of arrival|2021-03-27|
|`DepartureDate`|`date`|`extract`|Date of departure|2021-03-28|
|`LineItems`|`array`|`generate`|||
|`LineItems.*`|`object`|`generate`|Extracted line item||
|`LineItems.*.TotalAmount`|`object`|`generate`|Total amount of the line item (may include taxes)||
|`LineItems.*.TotalAmount.CurrencyCode`|`string`|`generate`||USD|
|`LineItems.*.TotalAmount.Amount`|`number`|`extract`||88|
|`LineItems.*.Description`|`string`|`extract`|Item description|Room Charge|
|`LineItems.*.Date`|`date`|`extract`|Item date|2021-03-27|
|`LineItems.*.Category`|`string`|`classify`|Item category|Room|
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

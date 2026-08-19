| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`AmountDue`|`object`|`generate`|Total Amount Due to the vendor||
|`AmountDue.Amount`|`number`|`extract`||665|
|`AmountDue.CurrencyCode`|`string`|`generate`||USD|
|`BalanceForward`|`object`|`generate`|Explicit previously unpaid balance||
|`BalanceForward.Amount`|`number`|`extract`||500|
|`BalanceForward.CurrencyCode`|`string`|`generate`||USD|
|`BillingAddress`|`string`|`extract`|Explicit billing address for the customer|123 Bill St, Redmond WA, 98052|
|`BillingAddressRecipient`|`string`|`extract`|Name associated with the BillingAddress|Microsoft Services|
|`CountryRegion`|`string`|`generate`|Country or region where the invoice was issued|USA|
|`CustomerAddress`|`string`|`extract`|Mailing address for the Customer|123 Other St, Redmond WA, 98052|
|`CustomerAddressRecipient`|`string`|`extract`|Name associated with the CustomerAddress|Microsoft Corp|
|`CustomerId`|`string`|`extract`|Reference ID for the customer|CID-12345|
|`CustomerName`|`string`|`extract`|Customer being invoiced|Microsoft Corp|
|`CustomerTaxId`|`string`|`extract`|The government ID number associated with the customer|765432-1|
|`DueDate`|`date`|`extract`|Date payment for this invoice is due|2019-12-15|
|`InvoiceDate`|`date`|`extract`|Date the invoice was issued|2019-11-15|
|`InvoiceId`|`string`|`extract`|ID for this specific invoice (often 'Invoice Number')|INV-100|
|`LineItems`|`array`|`generate`|List of line items||
|`LineItems.*`|`object`|`generate`|||
|`LineItems.*.Date`|`date`|`extract`|Date corresponding to each line item. Often it is a date the line item was shipped|2021-03-04|
|`LineItems.*.Description`|`string`|`extract`|The text description for the invoice line item|Consulting service|
|`LineItems.*.ProductCode`|`string`|`extract`|Product code, product number, or SKU associated with the specific line item|A123|
|`LineItems.*.Quantity`|`number`|`extract`|The quantity for this invoice line item|2|
|`LineItems.*.QuantityUnit`|`string`|`extract`|The unit of the line item, e.g., kg, lb, hours|hours|
|`LineItems.*.TaxAmount`|`object`|`generate`|Tax associated with each line item||
|`LineItems.*.TaxAmount.Amount`|`number`|`extract`||8|
|`LineItems.*.TaxAmount.CurrencyCode`|`string`|`generate`||USD|
|`LineItems.*.TaxRate`|`number`|`extract`|Tax rate associated with each line item (decimal fraction)|0.18|
|`LineItems.*.TotalAmount`|`object`|`generate`|The amount of the line item||
|`LineItems.*.TotalAmount.Amount`|`number`|`extract`||80|
|`LineItems.*.TotalAmount.CurrencyCode`|`string`|`generate`||USD|
|`LineItems.*.UnitPrice`|`object`|`generate`|The net or gross price (depending on the gross invoice setting of the invoice) of one unit of this item||
|`LineItems.*.UnitPrice.Amount`|`number`|`extract`||40|
|`LineItems.*.UnitPrice.CurrencyCode`|`string`|`generate`||USD|
|`PaymentTerm`|`string`|`extract`|The terms under which the payment is meant to be paid|Net90|
|`PONumber`|`string`|`extract`|A purchase order reference number|PO-3333|
|`RemittanceAddress`|`string`|`extract`|Explicit remittance or payment address for the customer|123 Remit St New York, NY, 10001|
|`RemittanceAddressRecipient`|`string`|`extract`|Name associated with the RemittanceAddress|Contoso Billing|
|`ServiceAddress`|`string`|`extract`|Explicit service address or property address for the customer|123 Service St, Redmond WA, 98052|
|`ServiceAddressRecipient`|`string`|`extract`|Name associated with the ServiceAddress|Microsoft Services|
|`ShippingAddress`|`string`|`extract`|Explicit shipping address for the customer|123 Ship St, Redmond WA, 98052|
|`ShippingAddressRecipient`|`string`|`extract`|Name associated with the ShippingAddress|Microsoft Delivery|
|`SubtotalAmount`|`object`|`generate`|Subtotal field identified on this invoice||
|`SubtotalAmount.Amount`|`number`|`generate`||150|
|`SubtotalAmount.CurrencyCode`|`string`|`generate`||USD|
|`TaxDetails`|`array`|`generate`|List of tax details||
|`TaxDetails.*`|`object`|`generate`|||
|`TaxDetails.*.Amount`|`object`|`generate`|The amount of the tax detail||
|`TaxDetails.*.Amount.Amount`|`number`|`extract`||15|
|`TaxDetails.*.Amount.CurrencyCode`|`string`|`generate`||USD|
|`TaxDetails.*.Description`|`string`|`extract`|The description of the tax detail|Sales Tax|
|`TaxDetails.*.NetAmount`|`object`|`generate`|The net amount before tax.||
|`TaxDetails.*.NetAmount.Amount`|`number`|`extract`||10|
|`TaxDetails.*.NetAmount.CurrencyCode`|`string`|`generate`||USD|
|`TaxDetails.*.Rate`|`number`|`extract`|The rate of the tax detail (decimal fraction)|0.18|
|`TotalAmount`|`object`|`generate`|Total new charges associated with this invoice||
|`TotalAmount.Amount`|`number`|`extract`||165|
|`TotalAmount.CurrencyCode`|`string`|`generate`||USD|
|`TotalDiscountAmount`|`object`|`generate`|Total discount field identified on this invoice||
|`TotalDiscountAmount.Amount`|`number`|`extract`||10|
|`TotalDiscountAmount.CurrencyCode`|`string`|`generate`||USD|
|`TotalTaxAmount`|`object`|`generate`|Total tax field identified on this invoice||
|`TotalTaxAmount.Amount`|`number`|`generate`||15|
|`TotalTaxAmount.CurrencyCode`|`string`|`generate`||USD|
|`VendorAddress`|`string`|`extract`|Mailing address for the Vendor|123 456th St, New York, NY 10001|
|`VendorAddressRecipient`|`string`|`extract`|Name associated with the VendorAddress|Contoso Headquarters|
|`VendorName`|`string`|`extract`|Vendor who has created this invoice|CONTOSO LTD.|
|`VendorTaxId`|`string`|`extract`|The government ID number associated with the vendor|123456-7|

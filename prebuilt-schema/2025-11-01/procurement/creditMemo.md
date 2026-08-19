| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`AdjustmentReason`|`string`|`extract`|Reason for the adjustment.|Returned goods due to quality issues. Credit is issued to offset the original invoice amount.|
|`BillingAddress`|`string`|`extract`|Billing address associated with the credit memo.|123 Bill St, Redmond WA, 98052|
|`BillingAddressRecipient`|`string`|`extract`|Recipient name at the billing address.|Microsoft Services|
|`CountryRegion`|`string`|`generate`|Country or region where the credit memo was issued|USA|
|`CreditMemoDate`|`date`|`extract`|Date the credit memo was issued.|2025-07-23|
|`CreditMemoId`|`string`|`extract`|Identifier or number of the credit memo.|CN-0006|
|`CustomerAddress`|`string`|`extract`|Mailing address for the Customer|123 Other St, Redmond WA, 98052|
|`CustomerAddressRecipient`|`string`|`extract`|Name associated with the CustomerAddress|Microsoft Corp|
|`CustomerId`|`string`|`extract`|Internal identifier of the customer.|CID-12345|
|`CustomerName`|`string`|`extract`|Name of the customer receiving the credit.|Microsoft Corp|
|`CustomerTaxId`|`string`|`extract`|Tax identification number of the customer.|765432-1|
|`DueDate`|`date`|`extract`|The date by which the adjustment amount is due.|2019-12-15|
|`LineItems`|`array`|`generate`|Line items included in the credit memo.||
|`LineItems.*`|`object`|`generate`|||
|`LineItems.*.Description`|`string`|`extract`|Description of the item.|Consulting service|
|`LineItems.*.ProductCode`|`string`|`extract`|Product or service code.|A123|
|`LineItems.*.Quantity`|`number`|`extract`|Quantity credited.|2|
|`LineItems.*.QuantityUnit`|`string`|`extract`|The unit of the line item, e.g., kg, lb, hours|hours|
|`LineItems.*.Reason`|`string`|`extract`|Reason for crediting this line item.|Returned item|
|`LineItems.*.TaxAmount`|`object`|`generate`|Tax amount for the line item.||
|`LineItems.*.TaxAmount.Amount`|`number`|`extract`|Numeric value of the tax amount.|-10|
|`LineItems.*.TaxAmount.CurrencyCode`|`string`|`generate`|Currency code of the tax amount.|USD|
|`LineItems.*.TaxRate`|`number`|`extract`|Applicable tax rate for the line item.|0.18|
|`LineItems.*.TotalAmount`|`object`|`generate`|Total line amount for the credited quantity.||
|`LineItems.*.TotalAmount.Amount`|`number`|`extract`|Numeric value of the total line amount.|-40|
|`LineItems.*.TotalAmount.CurrencyCode`|`string`|`generate`|Currency code of the total line amount.|USD|
|`LineItems.*.UnitPrice`|`object`|`generate`|Unit price of the item.||
|`LineItems.*.UnitPrice.Amount`|`number`|`extract`|Numeric value of the unit price.|40|
|`LineItems.*.UnitPrice.CurrencyCode`|`string`|`generate`|Currency code of the unit price.|USD|
|`OriginalInvoiceDate`|`date`|`extract`|Date of the original invoice being credited.|2025-01-15|
|`OriginalInvoiceId`|`string`|`extract`|Identifier of the original invoice.|INV-300|
|`PaymentTerm`|`string`|`extract`|The payment terms associated with the adjustment.|Net90|
|`PONumber`|`string`|`extract`|Related purchase order number.|PO-3333|
|`RemittanceAddress`|`string`|`extract`|Explicit remittance or payment address for the customer|123 Remit St New York, NY, 10001|
|`RemittanceAddressRecipient`|`string`|`extract`|Name associated with the RemittanceAddress|Contoso Billing|
|`ShippingAddress`|`string`|`extract`|Shipping address for returned or credited goods.|123 Ship St, Redmond WA, 98052|
|`ShippingAddressRecipient`|`string`|`extract`|Recipient name at the shipping address.|Microsoft Delivery|
|`SubtotalAmount`|`object`|`generate`|Subtotal of all line items before tax.||
|`SubtotalAmount.Amount`|`number`|`generate`|Numeric value of the subtotal amount.|-69.97|
|`SubtotalAmount.CurrencyCode`|`string`|`generate`|Currency code of the subtotal amount.|USD|
|`TaxDetails`|`array`|`generate`|List of tax details||
|`TaxDetails.*`|`object`|`generate`|||
|`TaxDetails.*.Amount`|`object`|`generate`|The amount of the tax detail||
|`TaxDetails.*.Amount.Amount`|`number`|`extract`||-2.8|
|`TaxDetails.*.Amount.CurrencyCode`|`string`|`generate`||USD|
|`TaxDetails.*.Description`|`string`|`extract`|The description of the tax detail|Sales Tax|
|`TaxDetails.*.NetAmount`|`object`|`generate`|The net amount before tax.||
|`TaxDetails.*.NetAmount.Amount`|`number`|`extract`||-69.97|
|`TaxDetails.*.NetAmount.CurrencyCode`|`string`|`generate`||USD|
|`TaxDetails.*.Rate`|`number`|`extract`|The rate of the tax detail (decimal fraction)|0.18|
|`TotalAmount`|`object`|`generate`|Total credit amount (subtotal plus taxes).||
|`TotalAmount.Amount`|`number`|`extract`|Numeric value of the total credit amount.|72.77|
|`TotalAmount.CurrencyCode`|`string`|`generate`|Currency code of the total amount.|USD|
|`TotalDiscountAmount`|`object`|`generate`|Total discount field identified on this invoice||
|`TotalDiscountAmount.Amount`|`number`|`extract`||-10|
|`TotalDiscountAmount.CurrencyCode`|`string`|`generate`||USD|
|`TotalTaxAmount`|`object`|`generate`|Total tax amount across all line items.||
|`TotalTaxAmount.Amount`|`number`|`generate`|Numeric value of the total tax amount.|-2.8|
|`TotalTaxAmount.CurrencyCode`|`string`|`generate`|Currency code of the total tax amount.|USD|
|`TransactionType`|`string`|`classify`|Type of the document. Possible values: CreditMemo or DebitMemo.|Credit|
|`VendorAddress`|`string`|`extract`|Mailing address of the vendor.|123 456th St, New York, NY 10001|
|`VendorAddressRecipient`|`string`|`extract`|Name associated with the VendorAddress|Contoso Headquarters|
|`VendorName`|`string`|`extract`|Name of the vendor issuing the credit memo.|CONTOSO LTD.|
|`VendorTaxId`|`string`|`extract`|Tax identification number of the vendor.|123456-7|

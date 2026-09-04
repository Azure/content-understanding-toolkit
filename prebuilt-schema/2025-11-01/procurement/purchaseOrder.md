**Analyzer ID:** `prebuilt-purchaseOrder`

**Description:** Purchase order forms.

| Field | Type | Method | Description | Example |
|:------|:-----|:-------|:------------|:--------|
|`BillingAddress`|`string`|`extract`|Explicit billing address for the customer|123 Bill St, Redmond WA, 98052|
|`BillingAddressRecipient`|`string`|`extract`|Name associated with the BillingAddress|Microsoft Services|
|`CountryRegion`|`string`|`generate`|Country or region where the PO was issued|USA|
|`CustomerAddress`|`string`|`extract`|The address of the customer to whom the purchase order is issued.|123 Other St, Redmond WA, 98052|
|`CustomerAddressRecipient`|`string`|`extract`|The name of the recipient at the customer's address.|Microsoft Corp|
|`CustomerId`|`string`|`extract`|The identification number assigned to the customer.|CID-12345|
|`CustomerName`|`string`|`extract`|The name of the customer to whom the purchase order is issued.|Microsoft Corp|
|`LineItems`|`array`|`generate`|The items included in the purchase order.||
|`LineItems.*`|`object`|`generate`|||
|`LineItems.*.TotalAmount`|`object`|`generate`|The total amount for the item, including taxes and discounts.||
|`LineItems.*.TotalAmount.Amount`|`number`|`extract`||10799.97|
|`LineItems.*.TotalAmount.CurrencyCode`|`string`|`generate`||USD|
|`LineItems.*.Description`|`string`|`extract`|The description of the item.|Consulting service|
|`LineItems.*.ProductCode`|`string`|`extract`|The product code or SKU of the item.|A123|
|`LineItems.*.Quantity`|`number`|`extract`|The quantity of the item ordered.|2|
|`LineItems.*.QuantityUnit`|`string`|`extract`|The unit of measurement for the item.|hours|
|`LineItems.*.TaxAmount`|`object`|`generate`|Tax amount for the line item.||
|`LineItems.*.TaxAmount.Amount`|`number`|`extract`|Numeric value of the tax amount.|10|
|`LineItems.*.TaxAmount.CurrencyCode`|`string`|`generate`|Currency code of the tax amount.|USD|
|`LineItems.*.TaxRate`|`number`|`extract`|Applicable tax rate for the line item.|0.18|
|`LineItems.*.UnitPrice`|`object`|`generate`|The price per unit of the item.||
|`LineItems.*.UnitPrice.Amount`|`number`|`extract`||3599.99|
|`LineItems.*.UnitPrice.CurrencyCode`|`string`|`generate`||USD|
|`PaymentTerm`|`string`|`extract`|The payment terms specified for the purchase order.|Net90|
|`PODate`|`date`|`extract`|The date the purchase order was issued.|2025-08-31|
|`PONumber`|`string`|`extract`|The purchase order number.|PO-3333|
|`ShippingAddress`|`string`|`extract`|Explicit shipping address for the customer|123 Ship St, Redmond WA, 98052|
|`ShippingAddressRecipient`|`string`|`extract`|Name associated with the ShippingAddress|Microsoft Delivery|
|`SubtotalAmount`|`object`|`generate`|The subtotal amount for all items before taxes.||
|`SubtotalAmount.Amount`|`number`|`generate`||12069.84|
|`SubtotalAmount.CurrencyCode`|`string`|`generate`||USD|
|`TotalAmount`|`object`|`generate`|The total amount payable including taxes.||
|`TotalAmount.Amount`|`number`|`extract`||12914.73|
|`TotalAmount.CurrencyCode`|`string`|`generate`||USD|
|`TotalTaxAmount`|`object`|`generate`|The total tax amount applied to the purchase order.||
|`TotalTaxAmount.Amount`|`number`|`generate`||844.89|
|`TotalTaxAmount.CurrencyCode`|`string`|`generate`||USD|
|`VendorAddress`|`string`|`extract`|The address of the vendor supplying the goods or services.|123 456th St, New York, NY 10001|
|`VendorAddressRecipient`|`string`|`extract`|The name of the recipient at the vendor's address.|Contoso Headquarters|
|`VendorId`|`string`|`extract`|The identification number assigned to the vendor.|VENDOR-1001|
|`VendorName`|`string`|`extract`|The name of the vendor.|CONTOSO LTD.|
|`VendorTaxId`|`string`|`extract`|The tax identification number of the vendor.|123456-7|
